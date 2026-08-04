from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07531ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.31")', self.read("config/settings.py"))
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.31}', self.read("docker-compose.yml"))
        self.assertIn("| Mapa | v0.75.31 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.31 |", self.read("VERSIONS.md"))

    def test_all_shared_endpoints_accept_splice_box(self):
        checks = (
            ("apps/network_map/api/views.py", "def container_equipment(request, element_id):"),
            ("apps/network_map/api/views.py", "def container_port_links(request, element_id):"),
            ("apps/network_map/api/optical_editor_v3.py", "def container_layout_v3(request, element_id):"),
            ("apps/network_map/api/optical_editor_v3.py", "def create_passive_endpoint_v3(request, element_id):"),
            ("apps/network_map/api/device_type_views.py", "def import_container_device_type_yaml(request, element_id):"),
        )
        for path, needle in checks:
            content = self.read(path)
            start = content.index(needle)
            self.assertIn("NetworkElement.ElementType.SPLICE_BOX", content[start:start + 900], f"{path}::{needle}")

    def test_yaml_map_has_splice_box_key(self):
        self.assertIn(
            "NetworkElement.ElementType.SPLICE_BOX: TOWER_ALLOWED_TYPES,",
            self.read("apps/network_map/api/device_type_views.py"),
        )

    def test_container_payload_exposes_subtype(self):
        views = self.read("apps/network_map/api/views.py")
        self.assertIn('"subtype": container.metadata.get("import_subtype", "")', views)

    def test_click_and_context_menu_use_common_workspace(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn('["rack", "tower", "cto", "splice_box"].includes(p.tipo)', editor)
        self.assertIn("fusions: () => openContainerWorkspace(p.id)", editor)
        self.assertNotIn('fusions: ["cto", "splice_box"].includes(p.tipo)', editor)

    def test_identity_preserves_ceo_and_cdo(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn('["rack", "tower", "cto", "splice_box"].includes(rawType)', core)
        self.assertIn('subtype === "cdo" ? "CDO"', core)
        self.assertIn('subtype === "ceo" ? "CEO"', core)
        self.assertIn('dialog.classList.toggle("map-v0758-optical-box", identity.opticalBox);', core)

    def test_optical_boxes_hide_generic_equipment_and_embed_canvas(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        for needle in (
            "addMenuWrapper.hidden = identity.opticalBox;",
            "connectPortsButton.hidden = identity.opticalBox;",
            "editLinesButton.hidden = identity.opticalBox;",
            "inventoryItem.hidden = identity.opticalBox;",
            "matrixItem.hidden = identity.opticalBox;",
            "if (identity.opticalBox) {",
            'if (!["cto", "splice_box"].includes(dialog.dataset.containerType)) return;',
        ):
            self.assertIn(needle, core)
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("#container-dialog.map-v0758-optical-box .master-canvas-scroll", css)
        self.assertIn("#container-dialog:not(.map-v0758-optical-box) .cto-embedded-canvas-v07530", css)

    def test_widget_has_cto_and_splice_box_modes(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("portas (clientes/DROPs)", core)
        self.assertIn("fusões · ${splitters.length} splitter(s)", core)

    def test_no_migrations(self):
        self.assertIn("Sem migrations", self.read("docs/releases/map/map-v0.75.31.md"))


if __name__ == "__main__":
    unittest.main()
