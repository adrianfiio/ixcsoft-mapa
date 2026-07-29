
from django.urls import path

from .views import equipment_list


urlpatterns = [
    path(
        "rede/equipamentos/",
        equipment_list,
        name="equipment-list",
    ),
]
