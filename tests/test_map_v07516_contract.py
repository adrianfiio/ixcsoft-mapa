from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07516ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.16")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.16}', compose)
        self.assertIn("| Mapa | v0.75.16 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.16 |", self.read("VERSIONS.md"))

    def test_node_moved_event_dispatched(self):
        canvas = self.read("static/js/map-master-suite.js")
        self.assertIn("MAP_V07516_CLEAR_MANUAL_ROUTES_ON_MOVE", canvas)
        self.assertEqual(
            canvas.count('document.dispatchEvent(new CustomEvent("map:node-moved"'),
            3,
        )

    def test_node_moved_listener_clears_manual_routes(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07516_CLEAR_MANUAL_ROUTES_ON_MOVE", runtime)
        self.assertIn("function clearManualRoutesFor", runtime)
        self.assertIn('document.addEventListener("map:node-moved"', runtime)

    def test_link_hover_highlight(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07516_LINK_HOVER_HIGHLIGHT", runtime)
        self.assertIn("function bindLinkHover", runtime)
        self.assertIn("hoverBoundV07516", runtime)
        self.assertIn(".master-canvas-links path.link-hover-v07516", css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.16.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
