import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07536ContractTests(unittest.TestCase):
    def test_ceo_and_cdo_share_distribution_box_flow(self):
        state = content("static/js/optical/optical-state.js")
        renderer = content("static/js/optical/optical-renderer.js")
        workspace = content("static/js/optical/optical-workspace.js")
        self.assertIn('element_type === "splice_box"', state)
        self.assertIn("isDistributionBox(session)", renderer)
        self.assertIn("distributionCableWidth", renderer)
        self.assertIn("columns: 1", renderer)
        for forbidden in ('=== "ceo"', '=== "cdo"', 'import_subtype ==='):
            self.assertNotIn(forbidden, workspace)
            self.assertNotIn(forbidden, renderer)

    def test_layout_v3_persists_manual_link_routes(self):
        state = content("static/js/optical/optical-state.js")
        renderer = content("static/js/optical/optical-renderer.js")
        for token in (
            "version: 6", "links: {}", "normalizeLinkRoute", "route.mode = \"manual\"",
            "ensureManualRoute", "insertLinkPoint", "moveLinkPoint", "removeLinkPoint",
            "autoRoute", "setLinkStyle",
        ):
            self.assertIn(token, state + renderer)
        for style in ('"curve"', '"orthogonal"', '"straight"'):
            self.assertIn(style, renderer)

    def test_custom_context_menu_and_double_click_disconnect_exist(self):
        workspace = content("static/js/optical/optical-workspace.js")
        css = content("static/css/map-optical-workspace-v07535.css")
        for token in (
            "data-optical-context-menu", "openCanvasContextMenu", 'addEventListener("contextmenu"',
            'addEventListener("dblclick"', "disconnectLink", "Romper fusão",
            "Adicionar splitter", "Adicionar nota", "Autoajustar linha", "Editar traçado",
        ):
            self.assertIn(token, workspace)
        self.assertIn(".ixc-optical-context-menu", css)
        self.assertIn("data-optical-context-action", workspace)

    def test_no_native_browser_prompts_in_optical_runtime(self):
        combined = "\n".join(content(path) for path in (
            "static/js/optical/optical-api.js",
            "static/js/optical/optical-state.js",
            "static/js/optical/optical-renderer.js",
            "static/js/optical/optical-workspace.js",
        ))
        for forbidden in ("global.alert(", "global.prompt(", "global.confirm(", "window.alert(", "window.prompt(", "window.confirm("):
            self.assertNotIn(forbidden, combined)
        self.assertIn("IXCMapDialog", combined)

    def test_capture_radius_is_hard_limited_to_five_meters(self):
        api = content("static/js/optical/optical-api.js")
        optical_backend = content("apps/network_map/api/optical_editor_v3.py")
        views = content("apps/network_map/api/views.py")
        self.assertIn("fusion-cables/?radius_m=5", api)
        self.assertIn("max_distance_m: 5", api)
        self.assertIn("OPTICAL_BOX_CAPTURE_RADIUS_M = 5.0", optical_backend)
        self.assertIn("min(requested_radius, OPTICAL_BOX_CAPTURE_RADIUS_M)", optical_backend)
        self.assertIn("min(requested_max_distance, OPTICAL_BOX_CAPTURE_RADIUS_M)", optical_backend)
        self.assertIn("<= OPTICAL_BOX_CAPTURE_RADIUS_M", views)

    def test_splice_gradient_and_splitter_fiber_color(self):
        state = content("static/js/optical/optical-state.js")
        renderer = content("static/js/optical/optical-renderer.js")
        self.assertIn("fiberColor(session, splice.input_fiber_id)", state)
        self.assertIn("fiberColor(session, splice.output_fiber_id)", state)
        self.assertIn("fiberColor(session, port.output_fiber_id)", state)
        self.assertIn("createLinearGradient", renderer)
        self.assertIn("gradient.addColorStop(0.48, first)", renderer)
        self.assertIn("gradient.addColorStop(0.52, second)", renderer)

    def test_optical_workspace_stays_isolated_from_rack_tower_dom(self):
        combined = "\n".join(content(path) for path in (
            "static/js/optical/optical-state.js",
            "static/js/optical/optical-renderer.js",
            "static/js/optical/optical-workspace.js",
        ))
        for forbidden in ("#map-master-container", "#container-dialog", "#unifilar-dialog", "openContainerWorkspace"):
            self.assertNotIn(forbidden, combined)

    def test_versions_and_release_are_updated_without_migration(self):
        settings = content("config/settings.py")
        compose = content("docker-compose.yml")
        release = content("docs/releases/map/map-v0.75.36.md")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.45")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.45}', compose)
        self.assertIn("MAP v0.75.36", release)
        migrations = list((ROOT / "apps/network_map/migrations").glob("*.py"))
        self.assertFalse(any(path.name.startswith("00") and "07536" in path.name for path in migrations))


if __name__ == "__main__":
    unittest.main(verbosity=2)
