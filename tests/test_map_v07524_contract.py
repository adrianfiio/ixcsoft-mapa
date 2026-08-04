from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07524ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.24")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.24}', compose)
        self.assertIn("| Mapa | v0.75.24 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.24 |", self.read("VERSIONS.md"))

    def test_fiber_port_grid_css(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07524_CTO_FIBER_PORT_GRID", css)
        self.assertIn(".master-cable-node-v07519 .fiber-port-list {", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(90px, 1fr));", css)
        self.assertIn(".master-cable-node-v07519 .fiber-port {", css)
        self.assertIn(".master-cable-node-v07519 .fiber-port.used {", css)

    def test_scoped_to_cto_cable_node_only(self):
        # a mudança não pode vazar pro card de fusão do rack
        # (renderRackFusionDiagram), que reaproveita .fiber-port sem a
        # classe master-cable-node-v07519 — esse card não deve mudar
        css = self.read("static/css/map-v0758-core-ui.css")
        start = css.index("MAP_V07524_CTO_FIBER_PORT_GRID")
        block = css[start:start + 1200]
        for selector in block.split("}"):
            if ".fiber-port" in selector:
                self.assertIn("master-cable-node-v07519", selector)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.24.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
