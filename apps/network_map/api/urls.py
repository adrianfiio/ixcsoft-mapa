from django.urls import path

from apps.network_map.api.views import (
    access_points_geojson,
    cable_fibers,
    cable_models,
    create_fiber_cable,
    delete_fiber_cable,
    create_network_element,
    fiber_cables_geojson,
    generate_fibers,
    network_elements_geojson,
    network_element_detail,
    update_network_element_position,
    update_cable_geometry,
)
from apps.network_map.project_api import (
    import_project_file,
    project_detail,
    project_routes_geojson,
    projects,
)


app_name = "network_map_api"


urlpatterns = [
    path("projects/", projects, name="projects"),
    path("routes/", project_routes_geojson, name="project-routes"),
    path("projects/<int:project_id>/", project_detail, name="project-detail"),
    path(
        "projects/<int:project_id>/import/",
        import_project_file,
        name="project-import",
    ),
    path(
        "access-points/",
        access_points_geojson,
        name="access-points-geojson",
    ),
    path(
        "elements/",
        network_elements_geojson,
        name="network-elements-geojson",
    ),
    path(
        "elements/create/",
        create_network_element,
        name="create-network-element",
    ),
    path(
        "elements/<int:element_id>/",
        network_element_detail,
        name="network-element-detail",
    ),
    path(
        "elements/<int:element_id>/position/",
        update_network_element_position,
        name="update-network-element-position",
    ),
    path(
        "cables/",
        fiber_cables_geojson,
        name="fiber-cables-geojson",
    ),
    path(
        "cable-models/",
        cable_models,
        name="cable-models",
    ),
    path(
        "cables/create/",
        create_fiber_cable,
        name="create-fiber-cable",
    ),
    path(
        "cables/<int:cable_id>/",
        delete_fiber_cable,
        name="delete-fiber-cable",
    ),
    path(
        "cables/<int:cable_id>/geometry/",
        update_cable_geometry,
        name="update-cable-geometry",
    ),
    path(
        "cables/<int:cable_id>/fibers/",
        cable_fibers,
        name="cable-fibers",
    ),
    path(
        "cables/<int:cable_id>/generate-fibers/",
        generate_fibers,
        name="generate-cable-fibers",
    ),
]
