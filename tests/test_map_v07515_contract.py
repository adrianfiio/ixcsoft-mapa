from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07515ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.15")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.15}', compose)
        self.assertIn("| Mapa | v0.75.15 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.15 |", self.read("VERSIONS.md"))

    def test_handle_pointer_events_forced(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07515_HANDLE_HIT_POINTER_EVENTS", runtime)
        self.assertIn('hit.style.pointerEvents = "all";', runtime)

    def test_olt_dio_drop_avoids_sibling_ports(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07515_OLT_DROP_AVOIDS_SIBLING_PORTS", runtime)
        self.assertIn("siblingPorts", runtime)
        self.assertIn('findClearLevel(source.x, "x", source.y, guideY, siblingPorts)', runtime)

    def test_olt_pon_only_and_fluid_grid(self):
        canvas = self.read("static/js/map-master-suite.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07515_OLT_PON_ONLY", canvas)
        self.assertNotIn("master-olt-utility-grid-v07510", canvas)
        self.assertIn("repeat(auto-fill, minmax(140px, 1fr))", css)

    def test_olt_resize_grip(self):
        canvas = self.read("static/js/map-master-suite.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07515_OLT_RESIZE", canvas)
        self.assertIn("installOltResizeGripV07515", canvas)
        self.assertIn("nodeWidths", canvas)
        self.assertIn(".master-olt-resize-grip-v07515", css)
        self.assertIn("var(--olt-width, 840px)", css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.15.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
