from django.urls import path

from apps.core.technician_app import TechnicianAppView, technician_service_worker

from .views import (
    EquipmentCreateView,
    EquipmentDeleteView,
    EquipmentDetailView,
    EquipmentListView,
    EquipmentUpdateView,
    NetworkProjectDeleteView,
)


urlpatterns = [
    path("app/", TechnicianAppView.as_view(), name="technician-app"),
    path(
        "app/sw.js",
        technician_service_worker,
        name="technician-service-worker",
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
