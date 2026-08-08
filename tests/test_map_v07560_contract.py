import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07560ContractTests(unittest.TestCase):
    def test_dio_dot_is_bigger_and_truly_centered(self):
        # O usuário pediu a bolinha "maior e mais no meio" — testado ao
        # vivo: 20px -> 28px (dentro de um quadrado 44px -> 52px), e o
        # centered:true confirmado via getBoundingClientRect real no
        # navegador (não só CSS na teoria).
        css = content("static/css/map-rack-runtime-v07552.css")
        start = css.index("#map-master-container .v07558-dio-unit {")
        unit_end = css.index("}", start)
        unit_block = css[start:unit_end]
        self.assertIn("width: 52px !important;", unit_block)

        dot_start = css.index("#map-master-container .v07558-dio-dot {")
        dot_end = css.index("}", dot_start)
        dot_block = css[dot_start:dot_end]
        self.assertIn("width: 28px !important;", dot_block)
        # MAP_V07560: .master-node-port i (map-master-suite.css:669-677)
        # é a regra genérica de bolinha-de-status de QUALQUER porta —
        # top:50% + translateY(-50%), pensada pra position:absolute.
        # Como a bolinha do DIO é position:relative (pro fix do
        # z-index da v0.75.58), esse top/transform virava um
        # deslocamento relativo de verdade e empurrava a bolinha ~10px
        # pra baixo do centro real do quadrado — confirmado ao vivo
        # (getBoundingClientRect, offsetY:10, centered:false) antes
        # desta correção.
        self.assertIn("top: auto !important;", dot_block)
        self.assertIn("transform: none !important;", dot_block)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.76.0")', content("config/settings.py"))
        self.assertIn('"0.85.0"', content("config/settings.py"))
        self.assertIn("v0.76.0", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
