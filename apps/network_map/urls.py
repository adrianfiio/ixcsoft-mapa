from django.urls import path
from django.views.generic import TemplateView

from .views import (
    EquipmentCreateView,
    EquipmentDeleteView,
    EquipmentDetailView,
    EquipmentListView,
    EquipmentUpdateView,
    NetworkProjectDeleteView,
)


urlpatterns = [
    path(
        "app/",
        TemplateView.as_view(template_name="network_map/technician_app.py.html"),
        name="technician-app",
    ),
    path(
        "rede/equipamentos/",
        EquipmentListView.as_view(),
        name="equipment-list",
    ),
    path(
        "rede/equipamentos/novo/",
        EquipmentCreateView.as_view(),
        name="equipment-create",
    ),
    path(
        "rede/equipamentos/<int:pk>/",
        EquipmentDetailView.as_view(),
        name="equipment-detail",
    ),
    path(
        "rede/equipamentos/<int:pk>/editar/",
        EquipmentUpdateView.as_view(),
        name="equipment-update",
    ),
    path(
        "rede/equipamentos/<int:pk>/excluir/",
        EquipmentDeleteView.as_view(),
        name="equipment-delete",
    ),
    path(
        "rede/projetos/<int:pk>/excluir/",
        NetworkProjectDeleteView.as_view(),
        name="project-delete",
    ),
]
