from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07525ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.25")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.25}', compose)
        self.assertIn("| Mapa | v0.75.25 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.25 |", self.read("VERSIONS.md"))

    def test_new_icon_set_applied(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("MAP_V07525_ICON_SET", editor)
        # CTO: novo desenho com 3 portas em círculo, vindo do kit fornecido
        self.assertIn('circle cx="12" cy="12" r="1" fill="currentColor"', editor)
        self.assertIn('circle cx="16" cy="12" r="1" fill="currentColor"', editor)
        self.assertIn('circle cx="20" cy="12" r="1" fill="currentColor"', editor)
        # CDO e CEO continuam com o mesmo desenho de domo entre si
        self.assertIn('M11 2h10a5 5 0 0 1 5 5v18a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7a5 5 0 0 1 5-5z', editor)
        # reserva técnica também usa o ícone novo (espiral)
        self.assertIn('M16 4C9.373 4 4 9.373 4 16s5.373 12 12 12', editor)

    def test_duplicate_icon_mask_removed(self):
        v3css = self.read("static/css/map-optical-editor-v3.css")
        # o sistema de ícone ::before que competia com o SVG normal do CTO/
        # CEO/CDO/RACK (2 ícones no mesmo marcador) foi removido
        self.assertNotIn("network-marker-v3.cto::before", v3css)
        self.assertNotIn("network-marker-v3.splice_box::before", v3css)
        self.assertNotIn("network-marker-v3.rack::before", v3css)
        self.assertIn("MAP_V07525_ICON_SET", v3css)

    def test_cdo_label_not_duplicated(self):
        v092css = self.read("static/css/map-v092.css")
        self.assertNotIn('small::after { content: "CDO"; }', v092css)

    def test_organize_button_removed_for_cto(self):
        fusion = self.read("static/js/map-fusion-polish.js")
        self.assertIn("MAP_V07525_NO_ORGANIZE_ON_CTO", fusion)
        self.assertIn("ceo-quick-toolbar-v07521", fusion)
        self.assertIn("organizeButton.remove()", fusion)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.25.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
