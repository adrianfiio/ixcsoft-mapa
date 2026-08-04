from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07523ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.23")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.23}', compose)
        self.assertIn("| Mapa | v0.75.23 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.23 |", self.read("VERSIONS.md"))

    def test_cto_toolbar_reuses_tower_classes(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("MAP_V07523_CTO_TOWER_TOOLBAR", editor)
        # a barra reaproveita as MESMAS classes CSS do Rack/Torre — não
        # cria nenhum sistema de toolbar paralelo
        self.assertIn('tower-workspace-toolbar-v0750 ceo-quick-toolbar-v07521', editor)
        self.assertIn('tower-workspace-actions-v0750', editor)
        self.assertIn('tower-toolbar-menu-v0750', editor)
        self.assertIn('class="tower-popover-v0750 tower-tools-menu-v0750"', editor)
        self.assertIn('class="tower-drawer-v0750 cto-structure-drawer-v07523"', editor)
        self.assertIn('tower-structure-hero-v0750', editor)
        self.assertIn('tower-structure-list-v0750', editor)

    def test_no_generic_equipment_options_in_cto_toolbar(self):
        editor = self.read("static/js/map-editor.js")
        # busca só dentro do trecho novo do toolbar da CTO/CDO/CEO — não deve
        # conter os botões de equipamento genérico que só fazem sentido no
        # Rack/Torre (adicionar equipamento, ligar portas, editar linhas,
        # importar YAML, organizar equipamentos)
        start = editor.index('content.innerHTML = `<div class="tower-workspace-toolbar-v0750')
        end = editor.index("optical-graph\">", start)
        toolbar_block = editor[start:end]
        for forbidden in (
            "data-container-add",
            "data-connect-ports",
            "data-edit-lines",
            "Importar YAML",
            "Organizar equipamentos",
        ):
            self.assertNotIn(forbidden, toolbar_block)

    def test_structure_and_fiber_focus_buttons_present(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("data-cto-structure-v07523", editor)
        self.assertIn("data-cto-fiber-focus-v07523", editor)
        self.assertIn("data-cto-refresh-v07523", editor)

    def test_cable_and_splice_logic_untouched(self):
        editor = self.read("static/js/map-editor.js")
        # a lógica de clique-para-ligar fibras/splitter continua idêntica —
        # só a moldura ao redor mudou
        self.assertIn('content.querySelectorAll(".fiber-port")', editor)
        self.assertIn('content.querySelectorAll(".splitter-input-port")', editor)
        self.assertIn('content.querySelectorAll(".splitter-output-port")', editor)
        self.assertIn('async (input, output) => {', editor)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.23.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
