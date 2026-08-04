from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07521ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.21")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.21}', compose)
        self.assertIn("| Mapa | v0.75.21 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.21 |", self.read("VERSIONS.md"))

    def test_quick_toolbar_is_additive(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("MAP_V07521_CEO_QUICK_TOOLBAR", editor)
        self.assertIn("ceo-quick-toolbar-v07521", editor)
        self.assertIn("data-ceo-quick-add", editor)
        # a barra antiga precisa continuar existindo, palavra por palavra
        self.assertIn(
            '<div class="ceo-instructions">Arraste os blocos. Clique em duas fibras para ligar, '
            'ou nas portas do splitter. Botão direito no fundo do quadro para adicionar splitter '
            'ou nota. Clique numa linha para excluir.',
            editor,
        )
        self.assertIn('id="unifilar-zoom-out"', editor)
        self.assertIn('id="unifilar-zoom-in"', editor)
        self.assertIn('id="unifilar-zoom-reset"', editor)
        self.assertIn('id="unifilar-feedback"', editor)
        self.assertIn('class="unifilar-zoom"', editor)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.21.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
