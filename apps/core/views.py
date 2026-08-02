import json

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db.models.functions import Length, Transform
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.utils.text import slugify
from django.db.models import Count, FloatField, Q, Sum
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from redis import Redis

from apps.access.models import AccessPoint
from apps.alerts.models import AlertEvent
from apps.ixc_integration.models import IXCCustomer, IXCLogin, IXCSyncExecution
from apps.network_map.models import CTO, ContainerEquipment, NetworkElement
from apps.core.enums import OperationalStatus
from apps.core.crypto import SecretCipher
from apps.core.dashboard_widgets import (
    PLATFORM_WIDGETS,
    clean_layout_payload,
    widget_meta,
    widget_meta_for,
    widgets_for,
)
from apps.core.models import (
    Company,
    CompanyDashboardLayout,
    CompanyEmailConfiguration,
    MapBaseConfiguration,
    PlatformDashboardLayout,
)
from apps.core.platform_overview import platform_overview_summary
from apps.core.access import accessible_company_ids, has_any_edit_access, onboarding_redirect_name
from apps.core.models import CompanyMembership
from apps.core.services.email import send_company_email
from apps.network_map.models import FiberCable, NetworkProject
from apps.network_map.models import POP
from apps.olt_integration.models import OLT
from apps.optical.models import DIO
from apps.core.access import editable_company_ids
from apps.core.forms import (
    CompanyBrandingForm,
    CompanyEmailConfigurationForm,
    CompanyOnboardingForm,
    CompanyProviderModeForm,
    CompanyTeamMemberForm,
    DIOPlatformForm,
    ERPOnboardingForm,
    OLTPlatformForm,
    POPPlatformForm,
    SuperadminCompanyEditForm,
    SuperadminCompanyForm,
    TeamPasswordResetForm,
)
from apps.ixc_integration.models import IXCConfiguration
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.ixc_integration.clients.ixc_client import IXCClient
from apps.ixc_integration.clients.exceptions import IXCClientError
from apps.ixc_integration.tasks import synchronize_ixc_configuration
from apps.olt_integration.models import OLT, ONU


class LoadingView(LoginRequiredMixin, TemplateView):
    """Tela de transição exibida logo após o login (ver
    `LOGIN_REDIRECT_URL`), antes de cair no dashboard de verdade — só
    estética, não carrega nada além do próprio HTML/CSS/SVG."""

    template_name = "loading.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = self.request.GET.get("next", "").strip()
        context["next_url"] = next_url if next_url.startswith("/") else reverse("dashboard")
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        redirect_name = onboarding_redirect_name(request.user)
        if redirect_name:
            return redirect(redirect_name)
        if self.template_name == "dashboard.html" and request.user.is_superuser:
            return redirect("platform-overview")
        return super().dispatch(request, *args, **kwargs)

    def _primary_company(self):
        if self.request.user.is_superuser:
            return None
        membership = (
            CompanyMembership.objects.filter(user=self.request.user, active=True)
            .select_related("company")
            .first()
        )
        return membership.company if membership else None

    def get_template_names(self):
        if self.template_name != "dashboard.html":
            return [self.template_name]
        company = self._primary_company()
        if company and company.is_designer:
            return ["dashboard_designer.html"]
        return ["dashboard.html"]

    def _designer_context(self, company):
        company_ids = [company.id]
        try:
            cable_length = (
                FiberCable.objects.filter(company_id__in=company_ids, geometry__isnull=False)
                # Transformado para Web Mercator (metros) só para uma estimativa de
                # km de cabo no dashboard — não precisa da precisão de uma geography.
                .annotate(length=Length(Transform("geometry", 3857), output_field=FloatField()))
                .aggregate(total=Sum("length"))["total"]
            )
        except Exception:
            cable_length = None
        return {
            "company": company,
            "project_count": NetworkProject.objects.filter(company_id__in=company_ids).count(),
            "element_count": NetworkElement.objects.filter(company_id__in=company_ids).count(),
            "cto_count": CTO.objects.filter(company_id__in=company_ids).count(),
            "ceo_count": NetworkElement.objects.filter(
                company_id__in=company_ids,
                element_type=NetworkElement.ElementType.SPLICE_BOX,
            ).count(),
            "dio_count": DIO.objects.filter(company_id__in=company_ids).count(),
            "olt_count": OLT.objects.filter(cpd__company_id__in=company_ids).count(),
            "cable_km": round((cable_length or 0) / 1000, 2),
        }

    def _can_edit_dashboard(self, company):
        """Mesmo critério de `company_email_settings`/`company_team`: só um
        membro EDIT ativo da PRÓPRIA empresa (nunca superusuário genérico,
        nunca outra empresa) pode reordenar/esconder os widgets dela."""
        if not company:
            return False
        return CompanyMembership.objects.filter(
            user=self.request.user,
            company=company,
            active=True,
            role=CompanyMembership.Role.EDIT,
        ).exists()

    def _dashboard_layout_context(self, company):
        """Posição/tamanho/visibilidade dos widgets (grid livre) e mensagem
        no topo do dashboard, conforme salvo em `CompanyDashboardLayout` —
        sem nada salvo, cai no auto-flow padrão (nada some, ordem de
        sempre). `can_edit_dashboard` só é considerado na própria "Visão
        geral" (`dashboard.html`), não no mapa, que reaproveita esse mesmo
        método de contexto."""
        layout = getattr(company, "dashboard_layout", None)
        can_edit_dashboard = self.template_name == "dashboard.html" and self._can_edit_dashboard(company)
        return {
            "widget_meta": widget_meta_for(company, layout),
            "dashboard_banner": layout.banner_text if layout else "",
            "can_edit_dashboard": can_edit_dashboard,
            "edit_mode": can_edit_dashboard and self.request.GET.get("edit") == "1",
        }

    def _provider_context(self, company_ids):
        company_filter = {} if company_ids is None else {"company_id__in": company_ids}

        access_summary = AccessPoint.objects.filter(**company_filter).aggregate(
            total=Count("id"),
            online=Count("id", filter=Q(status=AccessPoint.Status.ONLINE)),
            offline=Count("id", filter=Q(status=AccessPoint.Status.OFFLINE)),
            unknown=Count("id", filter=Q(status=AccessPoint.Status.UNKNOWN)),
            geolocated=Count(
                "id",
                filter=Q(latitude__isnull=False, longitude__isnull=False),
            ),
        )
        onu_queryset = ONU.objects.all()
        assigned_onu_queryset = IXCFiberAssignment.objects.filter(login__isnull=False)
        olt_queryset = OLT.objects.all()
        element_queryset = NetworkElement.objects.all()
        cto_queryset = CTO.objects.all()
        alert_queryset = AlertEvent.objects.all()
        customer_queryset = IXCCustomer.objects.all()
        sync_queryset = IXCSyncExecution.objects.select_related("configuration")
        if company_ids is not None:
            onu_queryset = onu_queryset.filter(
                pon_port__olt__cpd__company_id__in=company_ids
            )
            assigned_onu_queryset = assigned_onu_queryset.filter(company_id__in=company_ids)
            olt_queryset = olt_queryset.filter(cpd__company_id__in=company_ids)
            element_queryset = element_queryset.filter(company_id__in=company_ids)
            cto_queryset = cto_queryset.filter(company_id__in=company_ids)
            customer_queryset = customer_queryset.filter(company_id__in=company_ids)
            sync_queryset = sync_queryset.filter(configuration__company_id__in=company_ids)
            alert_queryset = alert_queryset.filter(
                Q(company_id__in=company_ids)
                | Q(cto__company_id__in=company_ids)
                | Q(olt__cpd__company_id__in=company_ids)
                | Q(route__company_id__in=company_ids)
            ).distinct()
        onu_summary = assigned_onu_queryset.aggregate(
            total=Count("id"),
            online=Count("id", filter=Q(login__online=True)),
            offline=Count("id", filter=Q(login__online=False)),
            los=Count("id", filter=Q(last_down_cause__icontains="LOS")),
        )
        active_alert_states = [
            AlertEvent.State.OPEN,
            AlertEvent.State.ACKNOWLEDGED,
            AlertEvent.State.RECOVERING,
        ]

        cable_queryset = FiberCable.objects.filter(geometry__isnull=False)
        if company_ids is not None:
            cable_queryset = cable_queryset.filter(company_id__in=company_ids)
        try:
            cable_length = (
                cable_queryset
                # Transformado para Web Mercator (metros) só para uma estimativa de
                # km de cabo no dashboard — não precisa da precisão de uma geography.
                .annotate(length=Length(Transform("geometry", 3857), output_field=FloatField()))
                .aggregate(total=Sum("length"))["total"]
            )
        except Exception:
            cable_length = None

        tower_equipment_queryset = ContainerEquipment.objects.filter(
            container__element_type=NetworkElement.ElementType.TOWER
        )
        rack_equipment_queryset = ContainerEquipment.objects.filter(
            container__element_type=NetworkElement.ElementType.RACK
        )
        if company_ids is not None:
            tower_equipment_queryset = tower_equipment_queryset.filter(company_id__in=company_ids)
            rack_equipment_queryset = rack_equipment_queryset.filter(company_id__in=company_ids)

        return {
            "access": access_summary,
            "onus": onu_summary,
            "onu_count": onu_queryset.count(),
            "customer_count": customer_queryset.count(),
            "olt_count": olt_queryset.count(),
            "element_count": element_queryset.count(),
            "cto_count": cto_queryset.count(),
            "ceo_count": element_queryset.filter(
                element_type=NetworkElement.ElementType.SPLICE_BOX
            ).count(),
            "tower_count": element_queryset.filter(
                element_type=NetworkElement.ElementType.TOWER
            ).count(),
            "rack_count": element_queryset.filter(
                element_type=NetworkElement.ElementType.RACK
            ).count(),
            "tower_equipment_count": tower_equipment_queryset.count(),
            "rack_equipment_count": rack_equipment_queryset.count(),
            "cable_km": round((cable_length or 0) / 1000, 2),
            "active_alert_count": alert_queryset.filter(
                state__in=active_alert_states
            ).count(),
            "recent_alerts": alert_queryset.filter(
                state__in=active_alert_states
            ).select_related("rule")[:5],
            "latest_sync": sync_queryset.order_by(
                "-started_at", "-created_at"
            ).first(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.template_name == "dashboard.html":
            company = self._primary_company()
            if company and company.is_designer:
                context.update(self._designer_context(company))
                context.update(self._dashboard_layout_context(company))
                return context
        company_ids = accessible_company_ids(self.request.user)
        context.update(self._provider_context(company_ids))
        company = self._primary_company()
        if company:
            context.update(self._dashboard_layout_context(company))
        if self.template_name == "map.html":
            context["hide_client_layers"] = bool(company and company.is_designer)
            context["can_edit_map"] = has_any_edit_access(self.request.user)
            map_config = MapBaseConfiguration.objects.first()
            google_api_key = ""
            if (
                map_config
                and map_config.google_tiles_enabled
                and map_config.google_api_key_encrypted
            ):
                try:
                    google_api_key = SecretCipher().decrypt(
                        map_config.google_api_key_encrypted
                    )
                except (RuntimeError, ValueError):
                    google_api_key = ""
            context["google_maps_config"] = {
                "enabled": bool(google_api_key),
                "defaultLayer": (
                    map_config.default_layer
                    if map_config
                    else MapBaseConfiguration.DefaultLayer.ESRI_SATELLITE
                ),
            }
        return context

    def post(self, request, *args, **kwargs):
        """Autoatendimento: um membro EDIT salva a ordem/visibilidade dos
        widgets da PRÓPRIA "Visão geral" (`?edit=1`). O JS do editor
        (`dashboard-layout-editor.js`) sempre envia pra
        `window.location.pathname`, então em `/` isso cai aqui."""
        company = self._primary_company()
        if not self._can_edit_dashboard(company):
            return JsonResponse(
                {"success": False, "error": "Sem permissão para editar este dashboard."},
                status=403,
            )
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

        widget_layout, banner_text = clean_layout_payload(widgets_for(company), payload)
        CompanyDashboardLayout.objects.update_or_create(
            company=company,
            defaults={
                "widget_layout": widget_layout,
                "banner_text": banner_text,
                "updated_by": request.user,
            },
        )
        return JsonResponse({"success": True})


class DashboardLayoutListView(LoginRequiredMixin, TemplateView):
    """Lista de empresas pra escolher qual dashboard editar (uso do
    superusuário pra entrar como suporte). Empresas também podem editar o
    próprio layout diretamente na "Visão geral" (ver `DashboardView.post`),
    sem passar por aqui."""

    template_name = "dashboard_layout_list.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["companies"] = Company.objects.filter(active=True).order_by("name")
        return context


class DashboardLayoutEditorView(DashboardView):
    """Editor visual (admin-only) da ordem/visibilidade dos widgets e da
    mensagem no topo do dashboard de UMA empresa escolhida. Reaproveita o
    mesmo template e o mesmo cálculo de contexto de `DashboardView`, só que
    pra empresa selecionada pelo admin, não pela empresa do usuário logado."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        self.company = get_object_or_404(Company, pk=kwargs["company_id"])
        return super(DashboardView, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return ["dashboard_designer.html" if self.company.is_designer else "dashboard.html"]

    def get_context_data(self, **kwargs):
        context = TemplateView.get_context_data(self, **kwargs)
        if self.company.is_designer:
            context.update(self._designer_context(self.company))
        else:
            context.update(self._provider_context([self.company.id]))
        context.update(self._dashboard_layout_context(self.company))
        context["edit_mode"] = True
        context["editor_company"] = self.company
        return context

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

        widget_layout, banner_text = clean_layout_payload(widgets_for(self.company), payload)
        CompanyDashboardLayout.objects.update_or_create(
            company=self.company,
            defaults={
                "widget_layout": widget_layout,
                "banner_text": banner_text,
                "updated_by": request.user,
            },
        )
        return JsonResponse({"success": True})


class PlatformOverviewView(LoginRequiredMixin, TemplateView):
    """"Visão da plataforma": resumo detalhado de todas as empresas ativas,
    só pra superusuário. Reaproveita o mesmo mecanismo de widgets
    editáveis do dashboard de empresa (`CompanyDashboardLayout`/
    `dashboard-layout-editor.js`), só que sobre um layout único da
    plataforma (`PlatformDashboardLayout`, sem empresa dona)."""

    template_name = "platform_overview.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def _layout(self):
        return PlatformDashboardLayout.objects.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(platform_overview_summary())
        layout = self._layout()
        context["widget_meta"] = widget_meta(PLATFORM_WIDGETS, layout)
        context["dashboard_banner"] = layout.banner_text if layout else ""
        context["edit_mode"] = self.request.GET.get("edit") == "1"
        return context

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "JSON inválido."}, status=400)

        widget_layout, banner_text = clean_layout_payload(PLATFORM_WIDGETS, payload)
        layout = self._layout()
        if layout is None:
            layout = PlatformDashboardLayout()
        layout.widget_layout = widget_layout
        layout.banner_text = banner_text
        layout.updated_by = request.user
        layout.save()
        return JsonResponse({"success": True})


def _unique_slug(name):
    base = slugify(name)[:170] or "empresa"
    slug = base
    suffix = 1
    while Company.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


@login_required
def platform_company_create(request):
    """Cadastro de empresa + primeiro usuário responsável pelo Superadmin,
    fora do Django Admin — hoje isso só existia via /admin/
    (`apps/core/admin.py`, `CompanyAdmin`)."""
    if not request.user.is_superuser:
        raise PermissionDenied
    form = SuperadminCompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            company = form.save(commit=False)
            company.slug = _unique_slug(form.cleaned_data["name"])
            if company.is_designer:
                company.integration_mode = ""
            company.onboarding_completed = True
            company.save()
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
            )
            CompanyMembership.objects.create(
                company=company,
                user=user,
                role=form.cleaned_data["role"],
                active=True,
            )
        messages.success(request, f"Empresa {company.trade_name or company.name} cadastrada.")
        return redirect("platform-overview")
    return render(request, "platform_company_form.html", {"form": form})


@login_required
def platform_company_edit(request, company_id):
    """Edição de cadastro + gestão de equipe/acessos de uma empresa já
    existente, pelo Superadmin — companheira de platform_company_create
    (que só cria). Diferente de company_team (self-service, escopada ao
    próprio vínculo EDIT do usuário logado): aqui o Superadmin gerencia
    a equipe de qualquer empresa via company_id na URL."""
    if not request.user.is_superuser:
        raise PermissionDenied
    company = get_object_or_404(Company, pk=company_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_company":
            form = SuperadminCompanyEditForm(request.POST, instance=company)
            if form.is_valid():
                saved = form.save(commit=False)
                if saved.is_designer:
                    saved.integration_mode = ""
                saved.save()
                messages.success(request, "Cadastro da empresa atualizado.")
            else:
                messages.error(request, "Não foi possível salvar — confira os dados.")
        elif action == "create_member":
            team_form = CompanyTeamMemberForm(request.POST)
            if team_form.is_valid():
                new_user = User.objects.create_user(
                    username=team_form.cleaned_data["username"],
                    password=team_form.cleaned_data["password"],
                    first_name=team_form.cleaned_data["first_name"],
                )
                CompanyMembership.objects.create(
                    company=company,
                    user=new_user,
                    role=team_form.cleaned_data["role"],
                    active=True,
                )
                messages.success(request, f"Usuário {new_user.username} cadastrado.")
            else:
                messages.error(request, "Não foi possível cadastrar — confira os dados.")
        elif action in ("toggle_active", "change_role"):
            target = CompanyMembership.objects.filter(
                pk=request.POST.get("membership_id"), company=company
            ).first()
            if target is None:
                messages.error(request, "Membro não encontrado nesta empresa.")
            elif action == "toggle_active":
                target.active = not target.active
                target.save(update_fields=["active"])
                messages.success(request, "Acesso do membro atualizado.")
            elif action == "change_role":
                new_role = request.POST.get("role")
                if new_role in CompanyMembership.Role.values:
                    target.role = new_role
                    target.save(update_fields=["role"])
                    messages.success(request, "Nível de acesso atualizado.")
        elif action == "reset_password":
            target = (
                CompanyMembership.objects.filter(pk=request.POST.get("membership_id"), company=company)
                .select_related("user")
                .first()
            )
            reset_form = TeamPasswordResetForm(request.POST)
            if target and reset_form.is_valid():
                target.user.set_password(reset_form.cleaned_data["password"])
                target.user.save(update_fields=["password"])
                messages.success(request, f"Senha de {target.user.username} redefinida.")
            else:
                messages.error(request, "Não foi possível redefinir a senha — confira os dados.")
        elif action == "delete_member":
            target = (
                CompanyMembership.objects.filter(pk=request.POST.get("membership_id"), company=company)
                .select_related("user")
                .first()
            )
            if target is None:
                messages.error(request, "Membro não encontrado nesta empresa.")
            elif target.user.company_memberships.exclude(pk=target.pk).exists():
                messages.error(
                    request,
                    "Este usuário também tem vínculo com outra empresa — remova o "
                    "vínculo lá antes de excluir, pra não tirar o acesso dele de "
                    "um lugar que não é esta empresa.",
                )
            else:
                username = target.user.username
                target.user.delete()  # cascade apaga o CompanyMembership junto
                messages.success(request, f"Usuário {username} e tudo relacionado a ele foram excluídos.")
        return redirect("platform-company-edit", company_id=company.id)

    return render(
        request,
        "platform_company_edit.html",
        {
            "company": company,
            "form": SuperadminCompanyEditForm(instance=company),
            "team_form": CompanyTeamMemberForm(),
            "reset_form": TeamPasswordResetForm(),
            "team": CompanyMembership.objects.filter(company=company)
            .select_related("user")
            .order_by("user__first_name", "user__username"),
        },
    )


class AccountPanelView(LoginRequiredMixin, TemplateView):
    template_name = "account_panel.html"

    def dispatch(self, request, *args, **kwargs):
        redirect_name = onboarding_redirect_name(request.user)
        if redirect_name:
            return redirect(redirect_name)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_ids = accessible_company_ids(self.request.user)
        project_queryset = NetworkProject.objects.select_related("company").order_by("name")
        element_queryset = NetworkElement.objects.select_related("project", "company").order_by("name")
        cable_queryset = FiberCable.objects.select_related("project", "company").order_by("name")
        assigned_onu_queryset = IXCFiberAssignment.objects.select_related(
            "company", "login", "login__customer", "cto"
        ).filter(login__isnull=False).order_by("login__customer__name", "onu_number")
        if company_ids is not None:
            project_queryset = project_queryset.filter(company_id__in=company_ids)
            element_queryset = element_queryset.filter(company_id__in=company_ids)
            cable_queryset = cable_queryset.filter(company_id__in=company_ids)
            assigned_onu_queryset = assigned_onu_queryset.filter(company_id__in=company_ids)
        pop_queryset = POP.objects.select_related("company").order_by("name")
        olt_queryset = OLT.objects.select_related("cpd", "cpd__company").order_by("name")
        dio_queryset = DIO.objects.select_related("pop", "company").order_by("name")
        if company_ids is not None:
            pop_queryset = pop_queryset.filter(company_id__in=company_ids)
            olt_queryset = olt_queryset.filter(cpd__company_id__in=company_ids)
            dio_queryset = dio_queryset.filter(company_id__in=company_ids)
        context.update(
            {
                "memberships": CompanyMembership.objects.filter(
                    user=self.request.user, active=True
                ).select_related("company"),
                "projects": project_queryset[:100],
                "elements": element_queryset[:100],
                "cables": cable_queryset[:100],
                "cpds": pop_queryset[:100],
                "olts": olt_queryset[:100],
                "dios": dio_queryset[:100],
                "assigned_onus": assigned_onu_queryset[:100],
                "assigned_onu_count": assigned_onu_queryset.count(),
                "is_platform_admin": self.request.user.is_superuser,
                "can_manage_assets": has_any_edit_access(self.request.user),
            }
        )
        return context


@login_required
def company_onboarding(request):
    membership = CompanyMembership.objects.filter(
        user=request.user,
        active=True,
    ).select_related("company").first()
    if request.user.is_superuser or membership is None:
        return redirect("account-panel")
    if membership.role != CompanyMembership.Role.EDIT:
        messages.info(
            request,
            "Seu acesso é somente para visualização. Solicite permissão de edição para configurar a empresa.",
        )
        return redirect("account-panel")
    company = membership.company
    form = CompanyOnboardingForm(
        request.POST or None,
        instance=company,
        lock_company_type=not company.needs_type_choice,
    )
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        if company.is_designer:
            company.integration_mode = ""
            company.onboarding_completed = True
        company.save()
        messages.success(request, "Dados da empresa salvos com sucesso.")
        if company.is_provider:
            return redirect("company-provider-mode")
        return redirect("account-panel")
    return render(request, "company_onboarding.html", {"form": form, "company": company})


@login_required
def company_provider_mode(request):
    membership = CompanyMembership.objects.filter(
        user=request.user,
        active=True,
    ).select_related("company").first()
    if request.user.is_superuser or membership is None:
        return redirect("account-panel")
    if membership.role != CompanyMembership.Role.EDIT:
        messages.info(
            request,
            "Seu acesso é somente para visualização. Solicite permissão de edição para configurar a empresa.",
        )
        return redirect("account-panel")
    company = membership.company
    if company.needs_type_choice:
        return redirect("company-onboarding")
    if not company.is_provider:
        return redirect("account-panel")
    form = CompanyProviderModeForm(request.POST or None, instance=company)
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        company.onboarding_completed = True
        company.save()
        messages.success(request, "Modo de operação da empresa salvo com sucesso.")
        if company.integration_mode == company.IntegrationMode.ERP:
            return redirect("erp-onboarding")
        return redirect("account-panel")
    return render(request, "company_provider_mode.html", {"form": form, "company": company})


@login_required
def company_team(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    if request.user.is_superuser or membership is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode gerenciar a equipe da empresa.",
        )
        return redirect("account-panel")
    company = membership.company
    action = request.POST.get("action") if request.method == "POST" else None

    if action in ("toggle_active", "change_role"):
        target = (
            CompanyMembership.objects.filter(
                pk=request.POST.get("membership_id"), company=company
            )
            .exclude(pk=membership.pk)
            .first()
        )
        if target is None:
            messages.error(request, "Membro não encontrado nesta empresa.")
        elif action == "toggle_active":
            target.active = not target.active
            target.save(update_fields=["active"])
            messages.success(request, "Acesso do membro atualizado.")
        elif action == "change_role":
            new_role = request.POST.get("role")
            if new_role in CompanyMembership.Role.values:
                target.role = new_role
                target.save(update_fields=["role"])
                messages.success(request, "Nível de acesso atualizado.")
        return redirect("company-team")

    form = CompanyTeamMemberForm(request.POST if action == "create" else None)
    if action == "create" and form.is_valid():
        new_user = User.objects.create_user(
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"],
        )
        CompanyMembership.objects.create(
            company=company,
            user=new_user,
            role=form.cleaned_data["role"],
            active=True,
        )
        messages.success(request, f"Usuário {new_user.username} cadastrado com sucesso.")
        return redirect("company-team")

    team = (
        CompanyMembership.objects.filter(company=company)
        .select_related("user")
        .order_by("user__first_name", "user__username")
    )
    return render(
        request,
        "company_team.html",
        {"form": form, "company": company, "team": team, "own_membership_id": membership.pk},
    )


@login_required
def company_email_settings(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    if request.user.is_superuser or membership is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode configurar o e-mail da empresa.",
        )
        return redirect("account-panel")
    company = membership.company
    configuration = CompanyEmailConfiguration.objects.filter(company=company).first()
    form = CompanyEmailConfigurationForm(request.POST or None, instance=configuration)
    action = request.POST.get("action") if request.method == "POST" else None

    if action == "test":
        if not configuration or not configuration.enabled:
            messages.error(request, "Salve a configuração antes de enviar um e-mail de teste.")
        elif not company.contact_email:
            messages.error(request, "Cadastre o e-mail de contato da empresa antes de testar.")
        else:
            try:
                send_company_email(
                    configuration,
                    subject="Teste de e-mail — AFService Map",
                    message=f"Este é um e-mail de teste da integração SMTP de {company}.",
                    to=[company.contact_email],
                )
            except Exception as exc:
                messages.error(request, f"Não foi possível enviar o e-mail de teste: {exc}")
            else:
                messages.success(request, f"E-mail de teste enviado para {company.contact_email}.")
        return redirect("company-email-settings")

    if action == "save" and form.is_valid():
        instance = form.save(commit=False)
        instance.company = company
        instance.save()
        messages.success(request, "Configuração de e-mail salva com sucesso.")
        return redirect("company-email-settings")

    return render(
        request,
        "company_email_settings.html",
        {"form": form, "company": company, "configuration": configuration},
    )


@login_required
def company_branding(request):
    membership = (
        CompanyMembership.objects.filter(
            user=request.user, active=True, role=CompanyMembership.Role.EDIT
        )
        .select_related("company")
        .first()
    )
    if request.user.is_superuser or membership is None:
        messages.info(
            request,
            "Somente um usuário com permissão de edição pode configurar a marca da empresa.",
        )
        return redirect("account-panel")
    company = membership.company
    form = CompanyBrandingForm(request.POST or None, request.FILES or None, instance=company)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Marca da empresa atualizada com sucesso.")
        return redirect("company-branding")

    return render(request, "company_branding.html", {"form": form, "company": company})


@login_required
def company_search(request):
    query = request.GET.get("q", "").strip()
    company_ids = accessible_company_ids(request.user)
    results = []

    def scoped(queryset, field="company_id"):
        return queryset if company_ids is None else queryset.filter(**{f"{field}__in": company_ids})

    if len(query) >= 2:
        projects = scoped(
            NetworkProject.objects.select_related("company").filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            )
        ).order_by("name")[:8]
        results.append(
            {
                "category": "Projetos",
                "items": [
                    {
                        "label": project.name,
                        "subtitle": f"{project.company} · {project.code}",
                        "url": f"{reverse('map')}?project={project.id}",
                    }
                    for project in projects
                ],
            }
        )

        elements = scoped(
            NetworkElement.objects.select_related("project", "company").filter(
                Q(name__icontains=query) | Q(code__icontains=query) | Q(element_type__icontains=query)
            )
        ).order_by("name")[:8]
        results.append(
            {
                "category": "Equipamentos e caixas",
                "items": [
                    {
                        "label": f"{element.name} ({element.get_element_type_display()})",
                        "subtitle": f"{element.company} · {element.project.name if element.project else 'sem projeto'}",
                        "url": f"{reverse('map')}?project={element.project_id}" if element.project_id else None,
                    }
                    for element in elements
                ],
            }
        )

        cables = scoped(
            FiberCable.objects.select_related("project", "company").filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            )
        ).order_by("name")[:8]
        results.append(
            {
                "category": "Cabos e rotas",
                "items": [
                    {
                        "label": cable.name,
                        "subtitle": f"{cable.company} · {cable.fiber_count} fibras",
                        "url": f"{reverse('map')}?project={cable.project_id}" if cable.project_id else None,
                    }
                    for cable in cables
                ],
            }
        )

        pops = scoped(
            POP.objects.select_related("company").filter(Q(name__icontains=query) | Q(code__icontains=query))
        ).order_by("name")[:8]
        results.append(
            {
                "category": "CPD / POP",
                "items": [
                    {"label": pop.name, "subtitle": f"{pop.company} · {pop.code}", "url": None}
                    for pop in pops
                ],
            }
        )

        olts = scoped(
            OLT.objects.select_related("cpd", "cpd__company").filter(
                Q(name__icontains=query) | Q(hostname__icontains=query) | Q(management_ip__icontains=query)
            ),
            field="cpd__company_id",
        ).order_by("name")[:8]
        results.append(
            {
                "category": "OLTs",
                "items": [
                    {
                        "label": olt.name,
                        "subtitle": f"{olt.cpd.company if olt.cpd else '—'} · {olt.management_ip or 'sem IP'}",
                        "url": None,
                    }
                    for olt in olts
                ],
            }
        )

        customers = scoped(
            IXCCustomer.objects.select_related("company").filter(
                Q(name__icontains=query) | Q(document__icontains=query)
            )
        ).order_by("name")[:8]
        results.append(
            {
                "category": "Clientes",
                "items": [
                    {
                        "label": customer.name,
                        "subtitle": f"{customer.company} · {customer.document or 'sem documento'}",
                        "url": None,
                    }
                    for customer in customers
                ],
            }
        )

        logins = scoped(
            IXCLogin.objects.select_related("customer", "cto").filter(
                Q(username__icontains=query) | Q(customer__name__icontains=query)
            )
        ).order_by("username")[:8]
        results.append(
            {
                "category": "Logins PPPoE",
                "items": [
                    {
                        "label": login.username,
                        "subtitle": f"{login.customer.name} · CTO {login.cto.name if login.cto else 'não vinculada'}",
                        "url": (
                            f"{reverse('map')}?project={login.cto.project_id}"
                            if login.cto_id and login.cto.project_id
                            else None
                        ),
                    }
                    for login in logins
                ],
            }
        )

    results = [group for group in results if group["items"]]
    return JsonResponse({"query": query, "results": results})


@login_required
def company_alerts(request):
    membership = CompanyMembership.objects.filter(
        user=request.user,
        active=True,
    ).select_related("company").first()
    if not request.user.is_superuser and membership and membership.company.is_designer:
        raise PermissionDenied
    company_ids = accessible_company_ids(request.user)
    alerts = AlertEvent.objects.select_related(
        "rule", "olt", "cto", "monitored_link", "container_equipment", "equipment_port",
    )
    if company_ids is not None:
        alerts = alerts.filter(
            Q(company_id__in=company_ids)
            | Q(cto__company_id__in=company_ids)
            | Q(olt__cpd__company_id__in=company_ids)
            | Q(route__company_id__in=company_ids)
        ).distinct()
    return render(request, "company_alerts.html", {"alerts": alerts[:200]})


@login_required
def create_company_asset(request, asset_type):
    forms = {
        "cpd": (POPPlatformForm, "CPD / POP"),
        "olt": (OLTPlatformForm, "OLT"),
        "dio": (DIOPlatformForm, "DIO"),
    }
    if asset_type not in forms or not has_any_edit_access(request.user):
        return redirect("account-panel")

    company_ids = editable_company_ids(request.user)
    form_class, label = forms[asset_type]
    form = form_class(
        request.POST or None,
        company_ids=company_ids,
    )
    if request.method == "POST" and form.is_valid():
        instance = form.save(commit=False)
        if asset_type == "olt":
            if not instance.cpd or (
                company_ids is not None and instance.cpd.company_id not in company_ids
            ):
                form.add_error("cpd", "Selecione um CPD permitido para sua empresa.")
            else:
                instance.save()
        elif asset_type == "dio":
            instance.company = instance.pop.company
            instance.save()
        else:
            instance.save()
        if not form.errors:
            messages.success(request, f"{label} cadastrado com sucesso.")
            return redirect("account-panel")

    return render(
        request,
        "company_asset_form.html",
        {"form": form, "asset_label": label, "asset_type": asset_type},
    )


@login_required
def erp_onboarding(request):
    if not has_any_edit_access(request.user):
        return redirect("account-panel")
    company_ids = editable_company_ids(request.user)
    if not request.user.is_superuser:
        has_erp_access = CompanyMembership.objects.filter(
            user=request.user,
            active=True,
            role=CompanyMembership.Role.EDIT,
            data_source=CompanyMembership.DataSource.ERP,
            company__integration_mode=Company.IntegrationMode.ERP,
        ).exists()
        if not has_erp_access:
            messages.info(request, "Esta empresa utiliza o cadastro manual, sem integração ERP.")
            return redirect("account-panel")
    existing = (
        IXCConfiguration.objects.filter(company_id__in=company_ids).first()
        if company_ids is not None
        else IXCConfiguration.objects.first()
    )
    form = ERPOnboardingForm(
        request.POST or None,
        instance=existing,
        company_ids=company_ids,
    )
    if request.method == "POST" and request.POST.get("action") == "synchronize":
        if not existing:
            form.add_error(None, "Salve e teste a integração antes de sincronizar.")
        else:
            running = existing.executions.filter(
                status=IXCSyncExecution.Status.RUNNING,
                started_at__gte=timezone.now() - timedelta(hours=1),
            ).exists()
            if running:
                messages.warning(request, "Já existe uma sincronização em andamento.")
            else:
                task = synchronize_ixc_configuration.delay(existing.pk)
                messages.success(request, f"Sincronização iniciada. Tarefa {task.id}.")
            return redirect("erp-onboarding")
    elif request.method == "POST" and form.is_valid():
        token = form.cleaned_data.get("api_token", "").strip()
        client = None
        if token:
            client = IXCClient(
                form.cleaned_data["base_url"],
                token,
                verify_ssl=form.cleaned_data["verify_ssl"],
            )
        try:
            result = client.test_connection() if client else {"total_clientes": "já vinculados"}
        except (IXCClientError, ValueError) as exc:
            form.add_error(None, f"Não foi possível validar o IXCSoft: {exc}")
        else:
            form.save()
            messages.success(
                request,
                f"IXCSoft conectado. {result['total_clientes']} clientes disponíveis.",
            )
            return redirect("account-panel")
    executions = (
        existing.executions.order_by("-started_at")[:10]
        if existing
        else []
    )
    sync_running = bool(
        existing
        and existing.executions.filter(
            status=IXCSyncExecution.Status.RUNNING,
            started_at__gte=timezone.now() - timedelta(hours=1),
        ).exists()
    )
    return render(
        request,
        "erp_onboarding.html",
        {
            "form": form,
            "configuration": existing,
            "executions": executions,
            "sync_running": sync_running,
        },
    )


def liveness_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "version": settings.APP_VERSION,
            "timestamp": timezone.now().isoformat(),
        }
    )


def readiness_check(request):
    services = {"database": False, "redis": False}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            services["database"] = cursor.fetchone()[0] == 1
    except Exception:
        services["database"] = False

    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        services["redis"] = bool(redis_client.ping())
    except Exception:
        services["redis"] = False

    healthy = all(services.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "version": settings.APP_VERSION,
            "timestamp": timezone.now().isoformat(),
            "services": services,
        },
        status=200 if healthy else 503,
    )


# Compatibilidade com o endpoint anterior.
health_check = readiness_check
