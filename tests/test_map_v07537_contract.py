import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07537ContractTests(unittest.TestCase):
    def test_distribution_box_cables_are_single_vertical_columns(self):
        renderer = content("static/js/optical/optical-renderer.js")
        state = content("static/js/optical/optical-state.js")
        self.assertIn("distributionFiberPitch", renderer)
        self.assertIn("columns: 1", renderer)
        self.assertIn('if (stateApi().isOpticalBox(session)) return { x: side === "left" ? 62 : 866, y };', renderer)
        self.assertIn('version: 6', state)
        self.assertIn('< 6', state)

    def test_optical_panel_separates_fusions_from_splitter_links(self):
        workspace = content("static/js/optical/optical-workspace.js")
        self.assertIn("function renderConnectionList", workspace)
        self.assertIn("Fusões cabo ↔ cabo", workspace)
        self.assertIn("Ligações de splitter", workspace)
        self.assertIn('data-action="disconnect-link"', workspace)
        self.assertNotIn("Nenhuma fusão cadastrada.", workspace)

    def test_rack_cable_uses_one_aggregate_endpoint(self):
        runtime = content("static/js/map-dio-fusion-v07537.js")
        css = content("static/css/map-dio-fusion-v07537.css")
        self.assertIn("installCableSummary", runtime)
        self.assertIn("data-rack-cable-anchor-v07537", runtime)
        self.assertIn("startCableDrag", runtime)
        self.assertIn("attach_cable", runtime)
        self.assertIn(".master-cable-fibers", css)
        self.assertIn("display: none !important", css)

    def test_dio_has_dedicated_fusion_matrix_and_quick_flow(self):
        runtime = content("static/js/map-dio-fusion-v07537.js")
        backend = content("apps/network_map/api/dio_fusion_v07537.py")
        urls = content("apps/network_map/api/urls.py")
        template = content("templates/map.html")
        for token in (
            "MATRIZ DE FUSÃO",
            "Auto fusão",
            "createFusion",
            "autoFuse",
            "BANDEJA",
            "data-dio-fiber-v07537",
            "data-dio-port-v07537",
        ):
            self.assertIn(token, runtime)
        for token in (
            "def dio_fusion_matrix_v07537",
            'action == "create_fusion"',
            'action == "auto_fuse"',
            "MAX_AUTO_FUSIONS",
            "transaction.atomic",
        ):
            self.assertIn(token, backend)
        self.assertIn("fusion-matrix-v07537", urls)
        self.assertIn("map-dio-fusion-v07538.js", template)
        self.assertIn("map-dio-fusion-v07538.css", template)

    def test_dio_fusions_persist_without_migration(self):
        backend = content("apps/network_map/api/dio_fusion_v07537.py")
        self.assertIn("FUSION_CABLE_IDS_KEY", backend)
        self.assertIn("dio.metadata", backend)
        self.assertIn("ContainerPortLink.objects.create", backend)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07537*")))

    def test_olt_is_compact_slot_port_matrix(self):
        runtime = content("static/js/map-dio-fusion-v07537.js")
        css = content("static/css/map-dio-fusion-v07537.css")
        self.assertIn("installCompactOlt", runtime)
        self.assertIn("compactPortLabel", runtime)
        self.assertIn("repeat(16", css)
        self.assertIn("map-olt-compact-v07537", css)
        self.assertNotIn("MutationObserver", runtime)
        self.assertNotIn("setInterval", runtime)

    def test_custom_dialogs_are_used_instead_of_browser_popups(self):
        runtime = content("static/js/map-dio-fusion-v07537.js")
        for forbidden in ("global.alert(", "global.prompt(", "global.confirm(", "window.alert(", "window.prompt(", "window.confirm("):
            self.assertNotIn(forbidden, runtime)
        self.assertIn("IXCMapDialog", runtime)

    def test_current_map_version_is_v07537(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.43")', content("config/settings.py"))
        self.assertIn("MAP_VERSION: ${MAP_VERSION:-0.75.43}", content("docker-compose.yml"))
        self.assertIn("Mapa | v0.75.43", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.39", content("docs/releases/map/map-v0.75.39.md"))
        self.assertIn('version: "0.75.39"', content("static/js/optical/optical-workspace.js"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
