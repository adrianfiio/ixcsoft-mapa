from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import NetworkElementForm
from .models import NetworkElement


class EquipmentListView(ListView):
    model = NetworkElement
    template_name = "network_map/equipment/list.html"
    context_object_name = "equipments"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            NetworkElement.objects
            .select_related("company")
            .order_by("element_type", "name")
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

        return context


class EquipmentDetailView(DetailView):
    model = NetworkElement
    template_name = "network_map/equipment/detail.html"
    context_object_name = "equipment"


class EquipmentCreateView(CreateView):
    model = NetworkElement
    form_class = NetworkElementForm
    template_name = "network_map/equipment/form.html"
    success_url = reverse_lazy("equipment-list")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Equipamento cadastrado com sucesso.",
        )
        return super().form_valid(form)


class EquipmentUpdateView(UpdateView):
    model = NetworkElement
    form_class = NetworkElementForm
    template_name = "network_map/equipment/form.html"
    context_object_name = "equipment"
    success_url = reverse_lazy("equipment-list")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Equipamento atualizado com sucesso.",
        )
        return super().form_valid(form)


class EquipmentDeleteView(DeleteView):
    model = NetworkElement
    template_name = "network_map/equipment/delete.html"
    context_object_name = "equipment"
    success_url = reverse_lazy("equipment-list")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Equipamento excluído com sucesso.",
        )
        return super().form_valid(form)
