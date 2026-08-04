from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07527ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.27")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.27}', compose)
        self.assertIn("| Mapa | v0.75.27 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.27 |", self.read("VERSIONS.md"))

    def test_dialog_shell_matches_tower_exactly(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        tower_css = self.read("static/css/map-v0750-tower-workspace.css")
        self.assertIn("MAP_V07527_CTO_WINDOW_PARITY", css)
        # mesmos valores literais do shell da Torre (não só a mesma ideia)
        self.assertIn("border-left: 1px solid rgba(56, 189, 248, .2) !important;", css)
        self.assertIn("border-left: 1px solid rgba(56, 189, 248, .2) !important;", tower_css)
        self.assertIn("box-shadow: -18px 0 55px rgba(0, 0, 0, .38) !important;", css)
        self.assertIn("box-shadow: -18px 0 55px rgba(0, 0, 0, .38) !important;", tower_css)
        self.assertIn("z-index: 1800 !important;", css)
        self.assertIn("left: 72px !important;", css)
        self.assertIn("left: 54px !important;", css)
        self.assertIn("#unifilar-dialog.map-v0758-optical-workspace::backdrop {", css)

    def test_native_header_hidden_only_for_cto_ceo_cdo(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn(
            "#unifilar-dialog.map-v0758-optical-workspace.map-cto-suite-active-v07527 > section > header {\n"
            "    display: none !important;\n"
            "}",
            css,
        )
        # a classe só é ligada quando é CTO/CDO/CEO -- Rack e fallback
        # continuam com o cabeçalho nativo visível
        editor = self.read("static/js/map-editor.js")
        self.assertIn(
            'unifilarDialog.classList.toggle("map-cto-suite-active-v07527", Boolean(element.splice_box));',
            editor,
        )

    def test_toolbar_has_its_own_close_button(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn('class="tower-workspace-close-v0758"', suite)
        self.assertIn("data-cto-close-v07527", suite)
        self.assertIn('content.querySelector("[data-cto-close-v07527]").onclick = () => unifilarDialog.close();', suite)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.27.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
