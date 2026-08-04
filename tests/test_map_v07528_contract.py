from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07528ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.28")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.28}', compose)
        self.assertIn("| Mapa | v0.75.28 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.28 |", self.read("VERSIONS.md"))

    def test_backend_endpoints_accept_cto(self):
        for path, needle in (
            ("apps/network_map/api/views.py", "def container_equipment(request, element_id):"),
            ("apps/network_map/api/views.py", "def container_port_links(request, element_id):"),
            ("apps/network_map/api/optical_editor_v3.py", "def container_layout_v3(request, element_id):"),
            ("apps/network_map/api/optical_editor_v3.py", "def create_passive_endpoint_v3(request, element_id):"),
            ("apps/network_map/api/device_type_views.py", "def import_container_device_type_yaml(request, element_id):"),
        ):
            content = self.read(path)
            start = content.index(needle)
            block = content[start:start + 550]
            self.assertIn("NetworkElement.ElementType.CTO", block, f"{path}::{needle} não libera CTO")

    def test_yaml_allowed_types_has_cto_key(self):
        content = self.read("apps/network_map/api/device_type_views.py")
        self.assertIn("NetworkElement.ElementType.CTO: TOWER_ALLOWED_TYPES,", content)

    def test_rack_and_tower_gates_unchanged(self):
        # todas as 5 rotas continuam aceitando rack/tower -- só ADICIONOU cto
        for path in (
            "apps/network_map/api/views.py",
            "apps/network_map/api/optical_editor_v3.py",
            "apps/network_map/api/device_type_views.py",
        ):
            content = self.read(path)
            self.assertIn("NetworkElement.ElementType.RACK", content)
            self.assertIn("NetworkElement.ElementType.TOWER", content)

    def test_frontend_dispatch_opens_torre_engine_for_cto(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn('["rack", "tower", "cto"].includes(p.tipo)', editor)

    def test_cto_gets_own_identity_not_collapsed_into_tower(self):
        core_ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn('type === "rack" ? "rack" : type === "cto" ? "cto" : "tower"', core_ui)
        self.assertIn("Editor técnico da CTO", core_ui)
        self.assertIn("ESTRUTURA DA CTO", core_ui)

    def test_fibers_button_opens_splice_editor_for_cto(self):
        tower_workspace = self.read("static/js/map-v0750-tower-workspace.js")
        self.assertIn('dialog?.dataset.containerType === "cto"', tower_workspace)
        self.assertIn("window.networkMap?.showUnifilar?.(id);", tower_workspace)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.28.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
