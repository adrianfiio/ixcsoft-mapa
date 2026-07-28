from django.urls import path

from apps.network_map.api.views import access_points_geojson


app_name = "network_map_api"


urlpatterns = [
    path(
        "access-points/",
        access_points_geojson,
        name="access-points-geojson",
    ),
]
