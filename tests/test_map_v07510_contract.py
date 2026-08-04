from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MapV07510ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions_are_isolated(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.82.0"))', settings)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.10")', settings)
        self.assertIn("MAP_VERSION: ${MAP_VERSION:-0.75.10}", compose)
        self.assertIn("${DOCKER_SOCK_GID:-999}", compose)

    def test_canvas_grid_no_longer_collapses(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07510_DIO_OLT_YAML_CANVAS", css)
        self.assertIn("grid-template-rows: minmax(0, 1fr) !important", css)
        self.assertIn("grid-row: 1 !important", css)

    def test_dio_uses_twelve_port_trays(self):
        master = self.read("static/js/map-master-suite.js")
        self.assertIn("renderDioTraysV07510", master)
        self.assertIn("chunkV07510(ports, 12)", master)
        self.assertIn("master-dio-tray-v07510", master)
        self.assertNotIn("ports.slice(page * 24, page * 24 + 24)", master)

    def test_yaml_ranges_and_modular_olt(self):
        parser = self.read("apps/network_map/device_type_yaml.py")
        view = self.read("apps/network_map/api/device_type_views.py")
        master = self.read("static/js/map-master-suite.js")
        self.assertIn("_expand_interface_name", parser)
        self.assertIn('_parse_named_rows(document, "power-ports"', parser)
        self.assertIn('_parse_named_rows(document, "module-bays"', parser)
        self.assertIn('"canvas_renderer": "modular-chassis-v07510"', view)
        self.assertIn("renderOltChassisV07510", master)

    def test_vertical_cables_and_context_guard(self):
        master = self.read("static/js/map-master-suite.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        ui = self.read("static/js/map-v074-ui.js")
        self.assertIn("vertical-v07510", master)
        self.assertIn("master-cable-node.vertical-v07510", css)
        self.assertIn(".leaflet-tooltip", ui)
        self.assertIn(".network-name-label", ui)

    def test_no_migration_in_release(self):
        release = self.read("docs/releases/map/map-v0.75.10.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
