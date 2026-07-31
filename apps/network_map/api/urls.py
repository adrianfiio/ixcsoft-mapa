from django.urls import path

from apps.network_map.api.views import (
    access_points_geojson,
    cable_fibers,
    cable_models,
    cable_reserves,
    container_equipment,
    container_equipment_detail,
    container_equipment_cards,
    container_equipment_ports,
    container_port_link_detail,
    container_port_links,
    reserve_to_element,
    splice_box_fibers,
    splice_box_layout,
    splice_box_splitters,
    create_fiber_cable,
    delete_fiber_cable,
    create_network_element,
    fiber_cables_geojson,
    generate_fibers,
    google_satellite_tile,
    google_tiles_session,
    pole_infrastructure,
    network_elements_geojson,
    network_element_detail,
    update_network_element_position,
    update_cable_geometry,
)
from apps.network_map.kmz_import_api import analyze_kmz_import, execute_kmz_import
from apps.network_map.project_api import (
    project_detail,
    project_routes_geojson,
    projects,
)


app_name = "network_map_api"


urlpatterns = [
    path("base-map/google/session/", google_tiles_session, name="google-tiles-session"),
    path(
        "base-map/google/tiles/<int:z>/<int:x>/<int:y>/",
        google_satellite_tile,
        name="google-satellite-tile",
    ),
    path("projects/", projects, name="projects"),
    path("elements/<int:element_id>/pole/", pole_infrastructure, name="pole-infrastructure"),
    path("elements/<int:element_id>/equipment/", container_equipment, name="container-equipment"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/", container_equipment_detail, name="container-equipment-detail"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/cards/", container_equipment_cards, name="container-equipment-cards"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/ports/", container_equipment_ports, name="container-equipment-ports"),
    path("elements/<int:element_id>/equipment-links/", container_port_links, name="container-port-links"),
    path("elements/<int:element_id>/equipment-links/<int:link_id>/", container_port_link_detail, name="container-port-link-detail"),
    path("routes/", project_routes_geojson, name="project-routes"),
    path("projects/<int:project_id>/", project_detail, name="project-detail"),
    path(
        "projects/<int:project_id>/import/analyze/",
        analyze_kmz_import,
        name="project-import-analyze",
    ),
    path(
        "projects/<int:project_id>/import/execute/",
        execute_kmz_import,
        name="project-import-execute",
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
    path("cables/<int:cable_id>/reserves/", cable_reserves, name="cable-reserves"),
    path("cables/<int:cable_id>/reserves/<int:reserve_id>/", cable_reserves, name="cable-reserve-detail"),
    path("cables/<int:cable_id>/reserves/<int:reserve_id>/convert/", reserve_to_element, name="reserve-to-element"),
    path("elements/<int:element_id>/splices/", splice_box_fibers, name="splice-box-fibers"),
    path("elements/<int:element_id>/splices/<int:splice_id>/", splice_box_fibers, name="splice-box-splice-detail"),
    path("elements/<int:element_id>/layout/", splice_box_layout, name="splice-box-layout"),
    path("elements/<int:element_id>/splitters/", splice_box_splitters, name="splice-box-splitters"),
    path("elements/<int:element_id>/splitters/<int:splitter_id>/", splice_box_splitters, name="splice-box-splitter-detail"),
    path(
        "cables/<int:cable_id>/generate-fibers/",
        generate_fibers,
        name="generate-cable-fibers",
    ),
]
