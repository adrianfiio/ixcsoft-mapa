from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07520ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.20")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.20}', compose)
        self.assertIn("| Mapa | v0.75.20 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.20 |", self.read("VERSIONS.md"))

    def test_splitter_and_cable_nodes_dual_classed(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn('graph-splitter-node graph-node master-canvas-node master-splitter-node-v07519', editor)
        self.assertIn('fiber-cable-node graph-node master-canvas-node master-cable-node-v07519', editor)
        self.assertIn('splitter-input-port master-node-port', editor)
        self.assertIn('splitter-output-port master-node-port', editor)

    def test_visual_parity_css_present(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07519_CTO_CANVAS_PARITY", css)
        self.assertIn(".master-canvas-node.master-splitter-node-v07519", css)
        self.assertIn("width: auto !important", css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.20.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
