import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV0750StaticTests(unittest.TestCase):
    def test_assets_are_loaded_with_map_version(self):
        template = content("templates/map.html")
        for asset in ("map-v0750-tower-workspace.css", "map-v0750-tower-workspace.js"):
            self.assertIn(f"{asset}' %}}?v={{{{ map_version }}}}", template)
        self.assertEqual(template.count("{{ map_version }}-tower-r5"), 2)

    def test_tower_workspace_fills_area_beside_sidebar_without_locking_it(self):
        css = content("static/css/map-v0750-tower-workspace.css")
        editor = content("static/js/map-editor.js")
        self.assertIn("#container-dialog.tower-workspace-dialog-v0750", css)
        self.assertIn("inset: 0 0 0 var(--v072-sidebar, 292px) !important", css)
        self.assertIn("#map-sidebar.v072-collapsed", css)
        self.assertIn("containerDialog.show()", editor)
        self.assertNotIn("containerDialog.showModal()", editor)

    def test_map_has_independent_label_and_client_visibility_controls(self):
        template = content("templates/map.html")
        editor = content("static/js/map-editor.js")
        css = content("static/css/map-editor.css")
        for token in ('data-layer-toggle="layer-labels"', 'data-layer-toggle="layer-clients"', 'id="layer-clients"'):
            self.assertIn(token, template)
        self.assertIn("clientsVisible", editor)
        self.assertIn("refreshMapLabels", editor)
        self.assertIn("map-labels-hidden", css)
        self.assertIn("map-client-visibility-toggle.active", css)

    def test_sidebar_does_not_duplicate_labels_and_created_link_stays_editable(self):
        template = content("templates/map.html")
        sidebar = content("static/js/map-v074-ui.js")
        canvas = content("static/js/map-master-suite.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        self.assertNotIn("nav.appendChild(labels)", sidebar)
        self.assertIn("selectCreatedLinkForEditing", canvas)
        self.assertIn("created.link?.id", canvas)
        self.assertIn("top: auto !important", css)
        self.assertIn("flex-direction: row !important", css)
        self.assertEqual(template.count("workspace-r4"), 2)

    def test_workspace_position_is_locked_and_always_closable(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("lockWorkspacePosition", "getBoundingClientRect().right", 'event.key !== "Escape"', "dialog.close()"):
            self.assertIn(token, runtime)
        self.assertIn("section > header", css)
        self.assertIn("position: sticky !important", css)

    def test_tower_opens_directly_in_canvas(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for token in ("activateCanvas", 'data-tab="canvas"', "Canvas 2D da estrutura", "map:container-rendered"):
            self.assertIn(token, runtime)

    def test_required_toolbar_and_connections_exist(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for kind in ("dio", "pto", "access_point", "ptp", "switch", "router", "onu"):
            self.assertIn(f'data-quick-add="{kind}"', runtime)
        for action in ('data-connect-ports', 'data-open-panel="matrix"', "data-organize-canvas", "data-fit-canvas", "data-tower-menu"):
            self.assertIn(action, runtime)

    def test_tower_uses_compact_menus_and_bottom_left_zoom(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        zoom_runtime = content("static/js/map-v0741-ui.js")
        self.assertIn("tower-add-menu-v0750", runtime)
        self.assertIn("tower-tools-menu-v0750", runtime)
        self.assertIn("toggleToolbarMenu", runtime)
        self.assertIn('left: 12px !important;', css)
        self.assertIn('[data-canvas-zoom-fit] { display: none !important; }', css)
        self.assertIn('data-canvas-zoom-out', zoom_runtime)
        self.assertIn('data-canvas-zoom-in', zoom_runtime)
        self.assertIn('if (!event.ctrlKey) return;', zoom_runtime)

    def test_fullscreen_is_css_only_in_loaded_runtimes(self):
        paths = (
            "static/js/map-v0750-tower-workspace.js",
            "static/js/map-fusion-polish.js",
            "static/js/map-master-suite.js",
            "static/js/map-optical-editor-v3.js",
        )
        for path in paths:
            runtime = content(path)
            for forbidden in ("requestFullscreen", "exitFullscreen", "document.fullscreenElement", "fullscreenchange"):
                self.assertNotIn(forbidden, runtime, f"{forbidden} ainda existe em {path}")
        self.assertIn('addEventListener("cancel"', content(paths[0]))

    def test_new_runtime_does_not_observe_own_rendering(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        self.assertNotIn("MutationObserver", runtime)
        self.assertIn("wrapFusionLoader", runtime)
        extension = content("static/js/container-device-type.js")
        self.assertNotIn("new MutationObserver", extension)
        self.assertIn("event.detail?.data", extension)
        self.assertNotIn('if (dialog.open) refreshExtensions()', extension)

    def test_fusion_and_canvas_have_no_visible_nested_scrollbars(self):
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("fusion-v0750", "scrollbar-width: none", ".master-canvas-scroll", "overflow: hidden !important", 'input[type="range"]'):
            self.assertIn(token, css)

    def test_yaml_import_is_bounded_and_has_clear_statuses(self):
        backend = content("apps/network_map/api/device_type_views.py")
        for token in ("MAX_IMPORTED_INTERFACES = 256", "validate_ipv46_address", "except IntegrityError", "status=409", "transaction.atomic", "full_clean"):
            self.assertIn(token, backend)
        for kind in ("ROUTER", "ACCESS_POINT", "PTP", "ONU", "PTO"):
            self.assertIn(f"EquipmentType.{kind}", backend)

    def test_connection_rules_are_preserved(self):
        backend = content("apps/network_map/api/views.py")
        for token in ("def container_port_links", "optical_ports", "RJ45 com RJ45", "wireless com wireless", "status=409", "termination_method"):
            self.assertIn(token, backend)

    def test_snmp_and_properties_are_available(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for token in ("openInspector", "data-inspector-snmp", "Ficha técnica", "Monitoramento"):
            self.assertIn(token, runtime)

    def test_versions_are_independent(self):
        settings = content("config/settings.py")
        compose = content("docker-compose.yml")
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.78.0"))', settings)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.0")', settings)
        self.assertIn('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.78.0}', compose)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.0}', compose)


if __name__ == "__main__":
    unittest.main(verbosity=2)
