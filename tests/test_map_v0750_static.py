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

    def test_tower_opens_directly_in_canvas(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for token in ("activateCanvas", 'data-tab="canvas"', "Canvas 2D da estrutura", "map:container-rendered"):
            self.assertIn(token, runtime)

    def test_required_toolbar_and_connections_exist(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for kind in ("dio", "pto", "access_point", "ptp", "switch", "router", "onu"):
            self.assertIn(f'data-quick-add="{kind}"', runtime)
        for action in ('data-connect-ports', 'data-open-panel="matrix"', "data-organize-canvas", "data-fit-canvas", "data-zoom-out", "data-zoom-in"):
            self.assertIn(action, runtime)

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
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.77.0"))', settings)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.0")', settings)
        self.assertIn('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.77.0}', compose)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.0}', compose)


if __name__ == "__main__":
    unittest.main(verbosity=2)
