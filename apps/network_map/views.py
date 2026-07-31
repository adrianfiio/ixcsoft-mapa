from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    DeleteView,
    DetailView,
    ListView,
    RedirectView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.core.access import can_edit_company, editable_company_ids, scope_company_queryset

from .forms import NetworkElementForm
from .models import NetworkElement, NetworkProject
from .services import project_structure_counts, wipe_project_structure


class CompanyEquipmentMixin(LoginRequiredMixin):
    def get_queryset(self):
        return scope_company_queryset(
            super().get_queryset(),
            self.request.user,
        )


class CompanyEquipmentFormMixin(CompanyEquipmentMixin):
    def dispatch(self, request, *args, **kwargs):
        if editable_company_ids(request.user) == []:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company_ids"] = editable_company_ids(self.request.user)
        return kwargs


class EquipmentListView(CompanyEquipmentMixin, ListView):
    model = NetworkElement
    template_name = "network_map/equipment/list.html"
    context_object_name = "equipments"
    paginate_by = 20

    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist("selected")
        if request.POST.get("bulk_action") != "delete" or not selected_ids:
            messages.warning(request, "Selecione ao menos um equipamento.")
            return redirect(request.get_full_path())
        queryset = scope_company_queryset(
            NetworkElement.objects.filter(pk__in=selected_ids),
            request.user,
        )
        allowed_ids = [
            item.pk
            for item in queryset.only("pk", "company_id")
            if can_edit_company(request.user, item.company_id)
        ]
        selected_count = len(allowed_ids)
        NetworkElement.objects.filter(pk__in=allowed_ids).delete()
        messages.success(request, f"{selected_count} equipamento(s) excluído(s).")
        return redirect(request.get_full_path())

    def get_queryset(self):
        queryset = scope_company_queryset(
            NetworkElement.objects
            .select_related("company")
            .order_by("element_type", "name"),
            self.request.user,
        )

        search = self.request.GET.get("q", "").strip()
        element_type = self.request.GET.get("type", "").strip()
        status = self.request.GET.get("status", "").strip()
        enabled = self.request.GET.get("enabled", "").strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
            )

        valid_types = dict(NetworkElement.ElementType.choices)
        if element_type in valid_types:
            queryset = queryset.filter(element_type=element_type)

        valid_statuses = dict(
            NetworkElement._meta.get_field("status").choices
        )
        if status in valid_statuses:
            queryset = queryset.filter(status=status)

        if enabled == "1":
            queryset = queryset.filter(enabled=True)
        elif enabled == "0":
            queryset = queryset.filter(enabled=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["element_types"] = NetworkElement.ElementType.choices
        context["status_choices"] = (
            NetworkElement._meta.get_field("status").choices
        )

        context["filters"] = {
            "q": self.request.GET.get("q", ""),
            "type": self.request.GET.get("type", ""),
            "status": self.request.GET.get("status", ""),
            "enabled": self.request.GET.get("enabled", ""),
        }
        context["can_edit_equipment"] = editable_company_ids(self.request.user) != []

        return context


class EquipmentDetailView(CompanyEquipmentMixin, DetailView):
    model = NetworkElement
    template_name = "network_map/equipment/detail.html"
    context_object_name = "equipment"


class EquipmentCreateView(LoginRequiredMixin, RedirectView):
    """Cadastro de equipamento fica só pelo mapa, onde já existe projeto e posição."""

    pattern_name = "map"

    def get(self, request, *args, **kwargs):
        messages.info(
            request,
            "Cadastre novos equipamentos pelo mapa — lá o projeto e a posição já ficam definidos.",
        )
        return super().get(request, *args, **kwargs)


class EquipmentUpdateView(CompanyEquipmentFormMixin, UpdateView):
    model = NetworkElement
    form_class = NetworkElementForm
    template_name = "network_map/equipment/form.html"
    context_object_name = "equipment"
    success_url = reverse_lazy("equipment-list")

    def form_valid(self, form):
        project = form.cleaned_data.get("project")
        if not project or not can_edit_company(self.request.user, project.company_id):
            raise PermissionDenied
        form.instance.company = project.company
        messages.success(
            self.request,
            "Equipamento atualizado com sucesso.",
        )
        return super().form_valid(form)


class EquipmentDeleteView(CompanyEquipmentMixin, DeleteView):
    model = NetworkElement
    template_name = "network_map/equipment/delete.html"
    context_object_name = "equipment"
    success_url = reverse_lazy("equipment-list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_edit_company(request.user, self.object.company_id):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if not can_edit_company(self.request.user, self.object.company_id):
            raise PermissionDenied
        messages.success(
            self.request,
            "Equipamento excluído com sucesso.",
        )
        return super().form_valid(form)


class NetworkProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Exclusão definitiva de um projeto de rede inteiro, com tudo que ele
    contém (postes, CTOs, cabos, splitters, fusões, reservas, lotes de
    importação KMZ, POP). Usada pelo painel de administração da empresa."""

    model = NetworkProject
    template_name = "network_map/project_delete.html"
    context_object_name = "project"
    success_url = reverse_lazy("account-panel")

    def get_queryset(self):
        return scope_company_queryset(NetworkProject.objects.all(), self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_edit_company(request.user, self.object.company_id):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["structure_counts"] = project_structure_counts(self.object)
        return context

    def post(self, request, *args, **kwargs):
        typed_code = request.POST.get("confirm_code", "").strip()
        if typed_code != self.object.code:
            messages.error(
                request,
                "O código digitado não confere com o código do projeto. Nada foi apagado.",
            )
            return redirect("project-delete", pk=self.object.pk)
        project = self.object
        project_name = project.name
        wipe_project_structure(project)
        project.delete()
        messages.success(
            request,
            f'Projeto "{project_name}" excluído com sucesso, junto com toda a estrutura.',
        )
        return redirect(self.success_url)
