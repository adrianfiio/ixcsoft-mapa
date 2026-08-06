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
    splice_box_trays,
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
from apps.network_map.api.device_type_views import import_container_device_type_yaml
from apps.network_map.api.ptp_links import ptp_link_candidates, ptp_link_detail, ptp_links
from apps.network_map.api.optical_editor_v2 import register_cable_passage
from apps.network_map.api.topology_actions import cut_cable_at_element
from apps.network_map.api.optical_editor_v3 import (
    assign_asset_route_v3,
    container_equipment_details_v3,
    container_layout_v3,
    create_passive_endpoint_v3,
    fusion_cable_membership,
    fusion_cable_state,
)
from apps.network_map.api.dio_fusion_v07537 import dio_fusion_matrix_v07537
from apps.network_map.api.map_v07539 import (
    cable_workspace_v07539,
    dio_dual_face_v07539,
    drop_terminations_v07539,
    equipment_collection_v07539,
    equipment_editor_v07539,
    layout_v07539,
)
from apps.network_map.api.map_v07543 import olt_hardware_v07543
from apps.network_map.api.map_v07544 import equipment_collection_v07544, olt_hardware_v07544
from apps.network_map.api.map_v07545 import equipment_collection_v07545, olt_chassis_v07545
from apps.network_map.api.map_v07547 import equipment_collection_v07547, olt_chassis_v07547
from apps.network_map.api.map_v07548 import olt_editor_v07548, olt_port_path_v07548, rack_topology_v07548
from apps.network_map.api.map_v07549 import olt_uplink_slots_v07549
from apps.network_map.api.map_v07551 import import_equipment_yaml_v07551, switch_hardware_v07551
from apps.network_map.api.map_v07552 import olt_uplink_slots_v07552
from apps.network_map.api.map_master_views import (
    assign_cable_route_master,
    asset_qr_master,
    asset_report_master,
    create_cable_reserve_master,
    diagram_revisions_master,
    equipment_master_detail,
    lifecycle_master,
    map_master_bootstrap,
    optical_trace_master,
    route_topology_master,
    splitter_ports_master,
)
from apps.network_map.kmz_import_api import (
    analyze_kmz_import,
    cleanup_legacy_kmz_import,
    element_cable_topology,
    execute_kmz_import,
    kmz_import_batches,
    preview_kmz_import,
    repair_kmz_batch_fibers,
    topology_kmz_import,
    undo_kmz_import,
)
from apps.network_map.project_api import (
    project_detail,
    project_routes_geojson,
    projects,
)


app_name = "network_map_api"


urlpatterns = [
    # IXCSOFT_MAP_MASTER_SUITE_V1
    path("master/bootstrap/", map_master_bootstrap, name="map-master-bootstrap"),
    path("master/projects/<int:project_id>/asset-report/", asset_report_master, name="map-master-asset-report"),
    path("master/projects/<int:project_id>/asset-qr/", asset_qr_master, name="map-master-asset-qr"),
    path("master/projects/<int:project_id>/routes/", route_topology_master, name="map-master-routes"),
    path("master/projects/<int:project_id>/trace/", optical_trace_master, name="map-master-trace"),
    path("master/projects/<int:project_id>/diagram-revisions/", diagram_revisions_master, name="map-master-revisions"),
    path("master/projects/<int:project_id>/lifecycle/", lifecycle_master, name="map-master-lifecycle"),
    path("master/cables/<int:cable_id>/route/", assign_cable_route_master, name="map-master-cable-route"),
    path("master/cables/<int:cable_id>/reserves/", create_cable_reserve_master, name="map-master-cable-reserve"),
    path("master/ctos/<int:cto_id>/splitter-ports/", splitter_ports_master, name="map-master-splitter-ports"),
    path("master/elements/<int:element_id>/equipment/<int:equipment_id>/", equipment_master_detail, name="map-master-equipment"),
    path("base-map/google/session/", google_tiles_session, name="google-tiles-session"),
    path(
        "base-map/google/tiles/<int:z>/<int:x>/<int:y>/",
        google_satellite_tile,
        name="google-satellite-tile",
    ),
    path("projects/", projects, name="projects"),
    path("elements/<int:element_id>/pole/", pole_infrastructure, name="pole-infrastructure"),
    path("elements/<int:element_id>/equipment/", container_equipment, name="container-equipment"),
    path("elements/<int:element_id>/cables/<int:cable_id>/cut/", cut_cable_at_element, name="cut-cable-at-element"),
    path("elements/<int:element_id>/fusion-cables/", fusion_cable_state, name="fusion-cable-state-v3"),
    path("elements/<int:element_id>/fusion-cables/<int:cable_id>/", fusion_cable_membership, name="fusion-cable-membership-v3"),
    path("elements/<int:element_id>/dio/<int:equipment_id>/fusion-matrix-v07537/", dio_fusion_matrix_v07537, name="dio-fusion-matrix-v07537"),
    path("v07539/cables/<int:cable_id>/workspace/", cable_workspace_v07539, name="cable-workspace-v07539"),
    path("v07539/elements/<int:element_id>/dio/<int:equipment_id>/dual-face/", dio_dual_face_v07539, name="dio-dual-face-v07539"),
    path("v07539/elements/<int:element_id>/drop-terminations/", drop_terminations_v07539, name="drop-terminations-v07539"),
    path("v07539/elements/<int:element_id>/equipment/", equipment_collection_v07539, name="equipment-collection-v07539"),
    path("v07539/elements/<int:element_id>/equipment/<int:equipment_id>/editor/", equipment_editor_v07539, name="equipment-editor-v07539"),
    path("v07539/elements/<int:element_id>/layout/", layout_v07539, name="layout-v07539"),
    path("v07543/elements/<int:element_id>/olt/<int:equipment_id>/hardware/", olt_hardware_v07543, name="olt-hardware-v07543"),
    path("v07545/elements/<int:element_id>/equipment/", equipment_collection_v07545, name="equipment-collection-v07545"),
    path("v07545/elements/<int:element_id>/olt/<int:equipment_id>/chassis/", olt_chassis_v07545, name="olt-chassis-v07545"),
    path("v07547/elements/<int:element_id>/equipment/", equipment_collection_v07547, name="equipment-collection-v07547"),
    path("v07547/elements/<int:element_id>/olt/<int:equipment_id>/chassis/", olt_chassis_v07547, name="olt-chassis-v07547"),
    path("v07548/elements/<int:element_id>/rack-topology/", rack_topology_v07548, name="rack-topology-v07548"),
    path("v07548/elements/<int:element_id>/olt/<int:equipment_id>/editor/", olt_editor_v07548, name="olt-editor-v07548"),
    path("v07548/elements/<int:element_id>/olt/<int:equipment_id>/ports/<int:port_id>/path/", olt_port_path_v07548, name="olt-port-path-v07548"),
    path("v07549/elements/<int:element_id>/olt/<int:equipment_id>/uplinks/", olt_uplink_slots_v07549, name="uplinks-v07549"),
    path("v07551/elements/<int:element_id>/switch/<int:equipment_id>/hardware/", switch_hardware_v07551, name="switch-hardware-v07551"),
    path("v07551/elements/<int:element_id>/equipment/import-yaml/", import_equipment_yaml_v07551, name="equipment-import-yaml-v07551"),
    path("v07552/elements/<int:element_id>/olt/<int:equipment_id>/uplinks/", olt_uplink_slots_v07552, name="uplinks-v07552"),
    path("elements/<int:element_id>/container-layout-v3/", container_layout_v3, name="container-layout-v3"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/details-v3/", container_equipment_details_v3, name="container-equipment-details-v3"),
    path("elements/<int:element_id>/passive-endpoints-v3/", create_passive_endpoint_v3, name="passive-endpoints-v3"),
    path("assets/route/", assign_asset_route_v3, name="assign-asset-route-v3"),
    path("elements/<int:element_id>/cables/<int:cable_id>/pass/", register_cable_passage, name="register-cable-passage"),
    path("elements/<int:element_id>/equipment/import-yaml/", import_container_device_type_yaml, name="container-equipment-import-yaml"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/", container_equipment_detail, name="container-equipment-detail"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/cards/", container_equipment_cards, name="container-equipment-cards"),
    path("elements/<int:element_id>/equipment/<int:equipment_id>/ports/", container_equipment_ports, name="container-equipment-ports"),
    path("elements/<int:element_id>/equipment-links/", container_port_links, name="container-port-links"),
    path("elements/<int:element_id>/equipment-links/<int:link_id>/", container_port_link_detail, name="container-port-link-detail"),
    path("ptp-links/", ptp_links, name="ptp-links"),
    path("ptp-links/candidates/", ptp_link_candidates, name="ptp-link-candidates"),
    path("ptp-links/<int:link_id>/", ptp_link_detail, name="ptp-link-detail"),
    path("routes/", project_routes_geojson, name="project-routes"),
    path("projects/<int:project_id>/", project_detail, name="project-detail"),
    path(
        "projects/<int:project_id>/import/analyze/",
        analyze_kmz_import,
        name="project-import-analyze",
    ),
    path(
        "projects/<int:project_id>/import/topology/",
        topology_kmz_import,
        name="kmz-import-topology",
    ),
    path(
        "projects/<int:project_id>/import/preview/",
        preview_kmz_import,
        name="kmz-import-preview",
    ),
    path(
        "projects/<int:project_id>/import/execute/",
        execute_kmz_import,
        name="project-import-execute",
    ),
    path(
        "projects/<int:project_id>/import/batches/",
        kmz_import_batches,
        name="kmz-import-batches",
    ),
    path(
        "projects/<int:project_id>/import/batches/<int:batch_id>/undo/",
        undo_kmz_import,
        name="kmz-import-undo",
    ),
    path(
        "projects/<int:project_id>/import/batches/<int:batch_id>/repair-fibers/",
        repair_kmz_batch_fibers,
        name="kmz-import-repair-fibers",
    ),
    path(
        "projects/<int:project_id>/import/cleanup-legacy/",
        cleanup_legacy_kmz_import,
        name="kmz-import-cleanup-legacy",
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
        "elements/<int:element_id>/cable-topology/",
        element_cable_topology,
        name="element-cable-topology",
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
    path("elements/<int:element_id>/trays/", splice_box_trays, name="splice-box-trays"),
    path("elements/<int:element_id>/trays/<int:tray_id>/", splice_box_trays, name="splice-box-tray-detail"),
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
