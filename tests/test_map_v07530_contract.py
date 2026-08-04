from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07530ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.30")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.30}', compose)
        self.assertIn("| Mapa | v0.75.30 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.30 |", self.read("VERSIONS.md"))

    def test_cto_canvas_embedded_not_a_separate_dialog(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("MAP_V07530_CTO_EMBEDDED_CANVAS", core_ui)
        self.assertIn("async function ensureCtoEmbeddedCanvas(root, dialog)", core_ui)
        self.assertIn('embedded.className = "cto-embedded-canvas-v07530";', core_ui)
        self.assertIn("panel.appendChild(embedded);", core_ui)
        # o antigo caminho que abria #unifilar-dialog como janela separada
        # pra CTO (bug reportado pelo usuário) nao existe mais
        self.assertNotIn("async function openCtoFusionEditor", core_ui)

    def test_refresh_does_not_reopen_dialog_when_embedded(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn("MAP_V07530_CTO_EMBEDDED_CANVAS", suite)
        self.assertIn("const refreshCtoView = options.onRefresh", suite)
        self.assertIn("await refreshCtoView();", suite)
        # nenhum dos ~15 pontos de refresh interno reabre o dialog direto
        self.assertNotIn('unifilarDialog.close(); await showUnifilar(element.id); notify(', suite)

    def test_embedded_mode_skips_dialog_specific_calls(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn("if (options.embedded) {", suite)
        self.assertIn('content.classList.add("cto-embedded-canvas-v07530");', suite)
        self.assertIn("if (!options.embedded) {", suite)

    def test_resize_listener_cleaned_up_between_renders(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn("let activeResizeHandler = null;", suite)
        self.assertIn('window.removeEventListener("resize", activeResizeHandler);', suite)

    def test_quick_add_and_structure_click_the_embedded_buttons(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("function triggerCtoAction(root, action)", core_ui)
        self.assertIn('embedded.querySelector("[data-cto-structure-v07523]")?.click();', core_ui)
        self.assertIn('embedded.querySelector(`[data-ceo-quick-add="${action}"]`)?.click();', core_ui)

    def test_fibers_button_hidden_for_cto_now(self):
        # antes (v0.75.28/29) o botao "Fibras"/"Fusoes" abria uma janela
        # separada pra CTO -- agora nem aparece, o Canvas embutido ja
        # cobre isso; só o Rack continua com o botão (highlight de fibra)
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn('toolbarFibersButton.hidden = identity.type !== "rack";', core_ui)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.30.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
