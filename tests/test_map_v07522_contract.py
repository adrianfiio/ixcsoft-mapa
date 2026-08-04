from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07522ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.22")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.22}', compose)
        self.assertIn("| Mapa | v0.75.22 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.22 |", self.read("VERSIONS.md"))

    def test_cto_canvas_parity_forced_with_important(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07522_CTO_LEFT_RIGHT", css)
        self.assertIn(
            ".master-canvas-node.master-splitter-node-v07519,\n"
            ".master-canvas-node.master-cable-node-v07519 {\n"
            "    background: rgba(13, 26, 42, .96) !important;",
            css,
        )
        self.assertIn(".master-splitter-node-v07519 .splitter-output-grid", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(40px, 1fr));", css)

    def test_no_click_drag_logic_touched(self):
        editor = self.read("static/js/map-editor.js")
        # a única mudança desta versão é CSS puro — os manipuladores de
        # clique do splitter continuam com as mesmas classes de sempre
        self.assertIn('content.querySelectorAll(".splitter-input-port")', editor)
        self.assertIn('content.querySelectorAll(".splitter-output-port")', editor)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.22.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
