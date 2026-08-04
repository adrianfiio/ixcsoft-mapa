from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07529ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.29")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.29}', compose)
        self.assertIn("| Mapa | v0.75.29 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.29 |", self.read("VERSIONS.md"))

    def test_equipment_ui_hidden_for_cto(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("MAP_V07529_CTO_STRIP_EQUIPMENT", core_ui)
        self.assertIn('addMenuWrapper.hidden = identity.type === "cto";', core_ui)
        self.assertIn('connectPortsButton.hidden = identity.type === "cto";', core_ui)
        self.assertIn('editLinesButton.hidden = identity.type === "cto";', core_ui)
        self.assertIn('inventoryItem.hidden = identity.type === "cto";', core_ui)
        self.assertIn('matrixItem.hidden = identity.type === "cto";', core_ui)

    def test_splitter_note_and_fusions_reachable_for_cto(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("async function openCtoFusionEditor(dialog, action)", core_ui)
        self.assertIn("window.networkMap?.showUnifilar?.(id)", core_ui)
        self.assertIn('data-ceo-quick-add="${action}"', core_ui)
        self.assertIn("data-cto-quick-add-v07529", core_ui)

    def test_ports_widget_present(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("async function updateCtoPortsWidget(root, elementId)", core_ui)
        self.assertIn("tower-cto-ports-widget-v07529", core_ui)
        self.assertIn("portas (clientes/DROPs)", core_ui)
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn(".tower-cto-ports-widget-v07529 {", css)

    def test_no_raw_api_url_leak_into_core_ui(self):
        # map-v0758-core-ui.js nao pode ter URL de API escrita literal --
        # regra ja garantida pelo teste compartilhado test_map_v0750_static,
        # aqui so confirmamos que usamos o helper novo em vez de string crua
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertNotIn("/api/map/", core_ui)
        self.assertIn("window.networkMap?.fetchElement?.(elementId)", core_ui)
        editor = self.read("static/js/map-editor.js")
        self.assertIn("async function fetchElement(id)", editor)
        self.assertIn("fetchElement,", editor)

    def test_rack_and_tower_untouched(self):
        # os toggles sao sempre reavaliados (nao aditivos), entao rack/tower
        # continuam mostrando tudo que ja mostravam
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn('label.textContent = identity.type === "cto" ? "Fusões" : "Fibras";', core_ui)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.29.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
