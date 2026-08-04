from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07526ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.26")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.26}', compose)
        self.assertIn("| Mapa | v0.75.26 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.26 |", self.read("VERSIONS.md"))

    def test_cto_suite_file_exists_and_is_wired(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn("MAP_V07526_CTO_SUITE", suite)
        self.assertIn("async function render(element, content)", suite)
        self.assertIn("window.mapCtoSuite = { render };", suite)
        template = self.read("templates/map.html")
        self.assertIn("js/map-cto-suite.js", template)
        # carrega logo depois de map-editor.js, antes dos decoradores
        editor_pos = template.index("js/map-editor.js")
        suite_pos = template.index("js/map-cto-suite.js")
        polish_pos = template.index("js/map-fusion-polish.js")
        self.assertTrue(editor_pos < suite_pos < polish_pos)

    def test_editor_delegates_to_cto_suite(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("MAP_V07526_CTO_SUITE", editor)
        self.assertIn("await window.mapCtoSuite.render(element, content);", editor)
        # o bloco antigo de ~600 linhas não vive mais aqui
        self.assertNotIn("const splitterRatioOptions = [", editor)

    def test_dependencies_exposed_on_network_map(self):
        editor = self.read("static/js/map-editor.js")
        for dep in (
            "api,", "escapeHtml,", "askValue,", "centerWithin,",
            "formatBudgetTooltip,", "splitterLossLabel,",
            "openRouteInfoDialog,", "unifilarDialog,",
        ):
            self.assertIn(dep, editor)

    def test_cto_suite_keeps_same_dom_hooks_for_decorators(self):
        # os 3 scripts decoradores (fusion-polish, optical-editor-v2/v3)
        # dependem de .unifilar-zoom / .ceo-instructions-like structure /
        # #unifilar-feedback existirem -- confirma que a extração manteve
        # essas classes/ids intactos
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn('class="unifilar-zoom"', suite)
        self.assertIn('id="unifilar-feedback"', suite)
        self.assertIn('class="optical-links"', suite)
        self.assertIn("tower-workspace-toolbar-v0750 ceo-quick-toolbar-v07521", suite)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.26.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
