from django.conf import settings
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from redis import Redis

from apps.access.models import AccessPoint
from apps.alerts.models import AlertEvent
from apps.ixc_integration.models import IXCCustomer, IXCSyncExecution
from apps.network_map.models import CTO, NetworkElement
from apps.core.enums import OperationalStatus
from apps.core.crypto import SecretCipher
from apps.core.models import MapBaseConfiguration
from apps.core.access import accessible_company_ids, has_any_edit_access
from apps.core.models import CompanyMembership
from apps.network_map.models import FiberCable, NetworkProject
from apps.network_map.models import POP
from apps.olt_integration.models import OLT
from apps.optical.models import DIO
from apps.core.access import editable_company_ids
from apps.core.forms import DIOPlatformForm, OLTPlatformForm, POPPlatformForm
from apps.olt_integration.models import OLT, ONU


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_ids = accessible_company_ids(self.request.user)
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
        onu_summary = ONU.objects.aggregate(
            total=Count("id"),
            online=Count(
                "id",
                filter=Q(operational_status=OperationalStatus.NORMAL),
            ),
            offline=Count(
                "id",
                filter=Q(operational_status=OperationalStatus.OFFLINE),
            ),
            los=Count("id", filter=Q(los=True)),
        )
        active_alert_states = [
            AlertEvent.State.OPEN,
            AlertEvent.State.ACKNOWLEDGED,
            AlertEvent.State.RECOVERING,
        ]

        context.update(
            {
                "app_version": settings.APP_VERSION,
                "access": access_summary,
                "onus": onu_summary,
                "customer_count": IXCCustomer.objects.count() if company_ids is None else 0,
                "olt_count": OLT.objects.count(),
                "element_count": NetworkElement.objects.count(),
                "cto_count": CTO.objects.count(),
                "active_alert_count": AlertEvent.objects.filter(
                    state__in=active_alert_states
                ).count(),
                "recent_alerts": AlertEvent.objects.filter(
                    state__in=active_alert_states
                ).select_related("rule")[:5],
                "latest_sync": IXCSyncExecution.objects.order_by(
                    "-started_at", "-created_at"
                ).first(),
            }
        )
        if self.template_name == "map.html":
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


class AccountPanelView(LoginRequiredMixin, TemplateView):
    template_name = "account_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_ids = accessible_company_ids(self.request.user)
        project_queryset = NetworkProject.objects.select_related("company").order_by("name")
        element_queryset = NetworkElement.objects.select_related("project", "company").order_by("name")
        cable_queryset = FiberCable.objects.select_related("project", "company").order_by("name")
        if company_ids is not None:
            project_queryset = project_queryset.filter(company_id__in=company_ids)
            element_queryset = element_queryset.filter(company_id__in=company_ids)
            cable_queryset = cable_queryset.filter(company_id__in=company_ids)
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
                "is_platform_admin": self.request.user.is_superuser,
                "can_manage_assets": has_any_edit_access(self.request.user),
            }
        )
        return context


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
