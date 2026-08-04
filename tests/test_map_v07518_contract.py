from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07518ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.18")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.18}', compose)
        self.assertIn("| Mapa | v0.75.18 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.18 |", self.read("VERSIONS.md"))

    def test_optical_graph_wheel_zoom_and_pan(self):
        editor = self.read("static/js/map-editor.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07518_OPTICAL_CANVAS_PARITY", editor)
        self.assertIn('opticalGraph.addEventListener("wheel"', editor)
        self.assertIn('if (!event.ctrlKey) return;', editor)
        self.assertIn('opticalGraph.setPointerCapture?.(event.pointerId);', editor)
        self.assertIn(".optical-graph {", css)
        self.assertIn("cursor: grab;", css)
        self.assertIn(".panning-v07518", css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.18.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
