from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07513ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.13")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.13}', compose)
        self.assertIn("| Mapa | v0.75.13 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.13 |", self.read("VERSIONS.md"))

    def test_note_pointer_events_fix(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07513_NOTE_POINTER_EVENTS", css)
        self.assertIn("pointer-events: auto;", css)

    def test_obstacle_aware_routing(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        for token in (
            "MAP_V07513_OBSTACLE_ROUTING",
            "function nodeObstacleRects",
            "function findClearLevel",
        ):
            self.assertIn(token, runtime)
        self.assertIn("const clearY = findClearLevel(middleY", runtime)
        self.assertIn("const clearX = findClearLevel(middleX", runtime)

    def test_legacy_link_handles_disabled(self):
        canvas = self.read("static/js/map-master-suite.js")
        self.assertIn("MAP_V07513_DISABLE_LEGACY_HANDLES", canvas)
        self.assertNotIn('circle.setAttribute("r", "7")', canvas)

    def test_handle_hitbox_and_refresh_button(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn('circle.setAttribute("r", "13")', runtime)
        toolbar = self.read("static/js/map-v0750-tower-workspace.js")
        self.assertIn("data-container-refresh-v07513", toolbar)
        self.assertIn("openContainerWorkspace(id)", toolbar)

    def test_fibers_button_hidden_on_tower(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("MAP_V07513_HIDE_FIBERS_ON_TOWER", core_ui)
        self.assertIn('toolbarFibersButton.hidden = identity.type === "tower"', core_ui)

    def test_olt_uplink_card(self):
        canvas = self.read("static/js/map-master-suite.js")
        self.assertIn("MAP_V07513_OLT_UPLINK_CARD", canvas)
        self.assertIn('olt: ["rj45_1g", "sfp_1g", "sfp_plus_10g", "power"]', canvas)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.13.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
