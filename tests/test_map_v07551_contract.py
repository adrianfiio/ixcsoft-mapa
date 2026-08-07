import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07551ContractTests(unittest.TestCase):
    def test_template_loads_switch_runtime_after_stable_rack_runtime(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-runtime-v07552.css", template)
        self.assertIn("map-rack-switch-v07552.js", template)
        self.assertLess(
            template.index("map-rack-maintenance-v07552.js"),
            template.index("map-rack-switch-v07552.js"),
        )

    def test_switch_creation_has_explicit_16_port_option(self):
        physical = content("static/js/map-rack-physical-v07542.js")
        runtime = content("static/js/map-rack-switch-v07552.js")
        self.assertIn("[4,8,12,16,24,48]", physical.replace(" ", ""))
        self.assertIn("16 portas", runtime)
        self.assertIn('name="port_count"', runtime)

    def test_sixteen_ports_use_one_grid_row(self):
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn(".v07552-switch-ports.is-single-row", css)
        self.assertIn("repeat(var(--port-count), minmax(0, 1fr))", css)
        self.assertNotIn("grid-template-columns: repeat(8", css)

    def test_each_port_has_connector_and_speed_editor(self):
        js = content("static/js/map-rack-switch-v07552.js")
        for connector in ("RJ45", "SFP", "SFP+", "XFP", "QSFP+"):
            self.assertIn(f'"{connector}"', js)
        for speed in (1, 10, 25, 40, 100):
            self.assertIn(str(speed), js)
        self.assertIn('name="connector_type"', js)
        self.assertIn('name="speed_gbps"', js)
        self.assertIn("Aplicar em intervalo", js)

    def test_backend_preserves_links_while_editing_ports(self):
        backend = content("apps/network_map/api/map_v07551.py")
        start = backend.index("def switch_hardware_v07551")
        end = backend.index("def _find_equipment", start)
        editor = backend[start:end]
        self.assertIn("bulk_update", editor)
        self.assertNotIn("ContainerPortLink.objects", editor)
        self.assertNotIn(".delete()", editor)

    def test_yaml_import_is_safe_idempotent_and_preserves_names(self):
        parser = content("apps/network_map/device_type_yaml_v07551.py")
        backend = content("apps/network_map/api/map_v07551.py")
        self.assertIn("yaml.safe_load", parser)
        self.assertIn("source_name", parser)
        self.assertIn("external_key", parser)
        self.assertIn("_find_equipment", backend)
        self.assertIn("_upsert_ports", backend)
        self.assertIn("parsed_port.name", backend)
        self.assertIn("replace_ports", backend)
        self.assertIn("porta ligada, mantida", backend)

    def test_speed_colors_are_shared_by_port_and_link(self):
        css = content("static/css/map-rack-runtime-v07552.css")
        expected = {
            "--speed-1g": "#22c55e",
            "--speed-10g": "#0ea5e9",
            "--speed-25g": "#a855f7",
            "--speed-40g": "#f97316",
            "--speed-100g": "#ef4444",
        }
        for variable, color in expected.items():
            self.assertIn(f"{variable}: {color}", css)
        self.assertIn(".v07552-switch-port.is-linked", css)
        self.assertIn(".master-canvas-links path.speed-100g", css)
        self.assertIn(".v07542-rack-links path.speed-100g", css)

    def test_observers_never_fetch(self):
        js = content("static/js/map-rack-switch-v07552.js")
        svg_start = js.index("function observeLinkSvg")
        svg_end = js.index("function renderSwitchFace", svg_start)
        observer_start = js.index("function installObserver")
        observer_end = js.index("function init", observer_start)
        self.assertNotIn("request(", js[svg_start:svg_end])
        self.assertNotIn("loadSwitch(", js[svg_start:svg_end])
        self.assertNotIn("request(", js[observer_start:observer_end])
        self.assertNotIn("loadSwitch(", js[observer_start:observer_end])
        self.assertIn("state.pending.has(key)", js)

    def test_routes_and_yaml_frontend_use_v07551(self):
        urls = content("apps/network_map/api/urls.py")
        device_frontend = content("static/js/container-device-type.js")
        self.assertIn("switch_hardware_v07551", urls)
        self.assertIn("import_equipment_yaml_v07551", urls)
        self.assertIn("/api/map/v07551/elements/${id}/equipment/import-yaml/", device_frontend)
        self.assertIn("/api/map/elements/${id}/equipment/import-yaml/", device_frontend)
        self.assertIn("useTypedSwitch", device_frontend)
        self.assertIn("lastYamlEquipmentTypeV07551", device_frontend)

    def test_version_and_release_are_current_without_platform_bump(self):
        settings = content("config/settings.py")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.61")', settings)
        self.assertIn('"0.83.1"', settings)
        self.assertIn("v0.75.61", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.51", content("docs/releases/map/map-v0.75.51.md"))

    def test_runtime_has_no_native_popup_or_observer_fetch_loop(self):
        js = content("static/js/map-rack-switch-v07552.js")
        self.assertNotIn("window.alert(", js)
        self.assertNotIn("window.prompt(", js)
        self.assertNotIn("window.confirm(", js)
        self.assertNotIn("global.alert(", js)
        self.assertNotIn("global.prompt(", js)
        self.assertNotIn("global.confirm(", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
