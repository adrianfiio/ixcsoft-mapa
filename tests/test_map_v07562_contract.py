import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07562ContractTests(unittest.TestCase):
    def test_rack_canvas_no_longer_renders_cable_widgets(self):
        # MAP_V07562_RACK_CABLES_MATRIX_ONLY: a pedido do usuário -- o
        # cabo (card com fibras coloridas, arraste até um DIO) não
        # aparece mais sozinho no Canvas do Rack. A Torre não muda.
        js = content("static/js/map-master-suite.js")
        start = js.index("function renderContainerCanvas()")
        end = js.index("function installNoteDrag", start)
        block = js[start:end]
        self.assertIn('const isRackContainer = state.container.data.container?.type === "rack";', block)
        self.assertIn(
            'const cables = isRackContainer ? [] : (state.container.data.cables || []);',
            block,
        )

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.62")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.62", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
