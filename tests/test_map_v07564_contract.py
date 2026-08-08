import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07564ContractTests(unittest.TestCase):
    def test_switch_ports_grid_gets_a_half_divider(self):
        # MAP_V07564_SWITCH_ORGANIZER_DIVIDER: a pedido do usuário, uma
        # barra visual (só decorativa) divide a grade de portas do Switch
        # ao meio -- sem criar nenhum tipo de porta novo nem mexer na
        # numeração/posição das portas reais.
        js = content("static/js/map-rack-switch-v07552.js")
        start = js.index("function renderSwitchFace(node, data)")
        end = js.index("async function enhanceSwitchNode", start)
        block = js[start:end]
        self.assertIn('divider.className = "v07564-switch-half-divider";', block)
        self.assertIn("if (data.ports.length > 1) {", block)
        self.assertIn("holder.appendChild(divider);", block)

    def test_divider_css_is_out_of_grid_flow(self):
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn(".v07552-switch-ports > .v07564-switch-half-divider {", css)
        start = css.index(".v07552-switch-ports > .v07564-switch-half-divider {")
        end = css.index("}", start)
        block = css[start:end]
        self.assertIn("position: absolute;", block)
        self.assertIn("pointer-events: none;", block)
        ports_start = css.index(".v07552-switch-ports {")
        ports_end = css.index("}", ports_start)
        self.assertIn("position: relative;", css[ports_start:ports_end])

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.76.0")', content("config/settings.py"))
        self.assertIn('"0.85.0"', content("config/settings.py"))
        self.assertIn("v0.76.0", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
