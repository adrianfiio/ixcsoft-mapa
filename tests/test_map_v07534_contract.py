from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07534ContractTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_isolated_optical_assets_are_loaded(self):
        template = self.read("templates/map.html")
        expected = [
            "css/map-optical-workspace-v07534.css",
            "js/optical/optical-api.js",
            "js/optical/optical-state.js",
            "js/optical/optical-renderer.js",
            "js/optical/optical-workspace.js",
        ]
        for asset in expected:
            self.assertIn(asset, template)
        self.assertLess(template.index("js/optical/optical-workspace.js"), template.index("js/map-editor.js"))

    def test_optical_boxes_use_dedicated_workspace(self):
        editor = self.read("static/js/map-editor.js")
        self.assertIn("window.IXCOpticalWorkspace", editor)
        self.assertIn("opticalWorkspace.open(p.id)", editor)
        click_block = editor[editor.index("MAP_V07534_ISOLATED_OPTICAL_WORKSPACE"):]
        self.assertNotIn('Promise.resolve(notify("Editor óptico temporariamente desativado', click_block)

    def test_new_workspace_does_not_touch_rack_tower_dom(self):
        combined = "\n".join(self.read(path) for path in [
            "static/js/optical/optical-api.js",
            "static/js/optical/optical-state.js",
            "static/js/optical/optical-renderer.js",
            "static/js/optical/optical-workspace.js",
        ])
        for forbidden in (
            "map-master-container",
            "container-dialog",
            "unifilar-dialog",
            "tower-workspace-actions",
            "openContainerWorkspace",
            "mapCtoSuite",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("AbortController", combined)
        self.assertIn("ResizeObserver", combined)
        self.assertIn("IXCOpticalWorkspace", combined)
        self.assertIn("fitView", combined)
        self.assertIn("Portas de atendimento", combined)

    def test_backend_writes_require_company_edit_permission(self):
        views = self.read("apps/network_map/api/views.py")
        for marker in (
            "MAP_V07534_OPTICAL_WRITE_PERMISSION_FIBERS",
            "MAP_V07534_OPTICAL_WRITE_PERMISSION_LAYOUT",
            "MAP_V07534_OPTICAL_WRITE_PERMISSION_SPLITTERS",
            "MAP_V07534_OPTICAL_TRAYS",
        ):
            self.assertIn(marker, views)
        urls = self.read("apps/network_map/api/urls.py")
        self.assertIn('name="splice-box-trays"', urls)
        self.assertIn('name="splice-box-tray-detail"', urls)
        tray_block = views[views.index("def splice_box_trays"):views.index("def splice_box_fibers")]
        self.assertIn("scope_company_queryset", tray_block)
        self.assertIn("transaction", self.read("apps/network_map/api/views.py"))

    def test_version_is_07534(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        versions = self.read("VERSIONS.md")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.34")', settings)
        self.assertIn("MAP_VERSION: ${MAP_VERSION:-0.75.34}", compose)
        self.assertIn("Mapa | v0.75.34", versions)
        self.assertIn("MAP v0.75.34", self.read("docs/releases/map/map-v0.75.34.md"))

    def test_no_migration_was_added_for_release(self):
        names = [path.name for path in (ROOT / "apps/network_map/migrations").glob("*.py")]
        self.assertFalse(any("07534" in name for name in names))


if __name__ == "__main__":
    unittest.main()
