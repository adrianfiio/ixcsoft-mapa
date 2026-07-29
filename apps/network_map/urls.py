from django.urls import path

from .views import (
    EquipmentCreateView,
    EquipmentDeleteView,
    EquipmentDetailView,
    EquipmentListView,
    EquipmentUpdateView,
)


urlpatterns = [
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
]
