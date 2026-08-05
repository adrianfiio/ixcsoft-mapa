from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def content(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07535ContractTests(unittest.TestCase):
    def test_assets_are_loaded_in_safe_order(self):
        template = content("templates/map.html")
        for asset in (
            "css/map-dialogs-v07535.css",
            "css/map-optical-workspace-v07535.css",
            "css/map-rack-polish-v07535.css",
            "js/map-dialogs-v07535.js",
            "js/optical/optical-api.js",
            "js/optical/optical-state.js",
            "js/optical/optical-renderer.js",
            "js/optical/optical-workspace.js",
            "js/map-rack-polish-v07535.js",
        ):
            self.assertIn(asset, template)
        self.assertLess(template.index("js/map-dialogs-v07535.js"), template.index("js/optical/optical-workspace.js"))
        self.assertLess(template.index("js/optical/optical-workspace.js"), template.index("js/map-editor.js"))
        self.assertLess(template.index("js/map-v0750-tower-workspace.js"), template.index("js/map-rack-polish-v07535.js"))
        self.assertNotIn("map-optical-workspace-v07534.css", template)

    def test_no_native_browser_popup_is_used(self):
        files = (
            "static/js/map-dialogs-v07535.js",
            "static/js/optical/optical-workspace.js",
            "static/js/map-rack-polish-v07535.js",
        )
        combined = "\n".join(content(path) for path in files)
        for forbidden in (
            "global.alert(", "global.prompt(", "global.confirm(",
            "window.alert(", "window.prompt(", "window.confirm(",
        ):
            self.assertNotIn(forbidden, combined)
        dialogs = content("static/js/map-dialogs-v07535.js")
        self.assertIn("global.IXCMapDialog", dialogs)
        self.assertIn("showModal()", dialogs)
        workspace = content("static/js/optical/optical-workspace.js")
        self.assertIn("dialog.prompt", workspace)
        self.assertIn("dialog.confirm", workspace)

    def test_optical_ui_hides_internal_tray_concept(self):
        workspace = content("static/js/optical/optical-workspace.js")
        renderer = content("static/js/optical/optical-renderer.js")
        visible_runtime = workspace + "\n" + renderer
        self.assertNotRegex(visible_runtime, re.compile(r"bandeja", re.IGNORECASE))
        self.assertNotIn('data-action="add-tray"', visible_runtime)
        self.assertNotIn("renderTray", renderer)
        self.assertIn("createInternalGroup", workspace)
        self.assertIn("createInternalGroup", content("static/js/optical/optical-api.js"))

    def test_point_to_point_and_drag_connections_exist(self):
        workspace = content("static/js/optical/optical-workspace.js")
        renderer = content("static/js/optical/optical-renderer.js")
        for token in (
            "connectEndpoints",
            "chooseEndpoint",
            'type: "connection"',
            "hitTestEndpoint",
            "setConnectionDraft",
            "clearConnectionDraft",
            "splitter-input",
            "splitter-output",
        ):
            self.assertIn(token, workspace + renderer)
        self.assertIn("Clique em duas pontas ou arraste uma linha", workspace)

    def test_cables_are_organized_vertically(self):
        renderer = content("static/js/optical/optical-renderer.js")
        workspace = content("static/js/optical/optical-workspace.js")
        self.assertIn("organizeVertical", renderer)
        self.assertIn("cableSide", renderer)
        self.assertIn("cableNodeHeight(previous) + 34", renderer)
        self.assertIn("Cabos organizados em colunas verticais", workspace)
        self.assertIn('data-action="organize"', workspace)

    def test_workspace_uses_generic_optical_box_identity(self):
        workspace = content("static/js/optical/optical-workspace.js")
        state = content("static/js/optical/optical-state.js")
        self.assertIn("CAIXA ÓPTICA", workspace)
        self.assertIn('return "CAIXA ÓPTICA"', state)
        for label in ("CTO", "CEO", "CDO"):
            self.assertNotIn(f">{label}<", workspace)

    def test_rack_dio_and_cable_widgets_are_polished(self):
        runtime = content("static/js/map-rack-polish-v07535.js")
        css = content("static/css/map-rack-polish-v07535.css")
        for token in (
            "ENTRADA", "OLT / equipamento", "SAÍDA", "cabos / rede externa",
            "map-dio-upstream-v07535", "map-dio-cable-v07535",
            "map-cable-resize-v07535", "map-cable-expand-v07535",
            "localStorage", "--map-cable-width-v07535",
        ):
            self.assertIn(token, runtime + css)
        self.assertNotIn("MutationObserver", runtime)
        self.assertIn('document.addEventListener("map:container-rendered"', runtime)

    def test_optical_workspace_remains_isolated_from_rack_dom(self):
        combined = "\n".join(content(path) for path in (
            "static/js/optical/optical-api.js",
            "static/js/optical/optical-state.js",
            "static/js/optical/optical-renderer.js",
            "static/js/optical/optical-workspace.js",
        ))
        for forbidden in (
            "map-master-container", "container-dialog", "unifilar-dialog",
            "tower-workspace-actions", "openContainerWorkspace", "mapCtoSuite",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("AbortController", combined)
        self.assertIn("ResizeObserver", combined)

    def test_version_is_07535_and_no_migration_was_added(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.35")', content("config/settings.py"))
        self.assertIn("MAP_VERSION: ${MAP_VERSION:-0.75.35}", content("docker-compose.yml"))
        self.assertIn("Mapa | v0.75.35", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.35", content("docs/releases/map/map-v0.75.35.md"))
        migrations = [path.name for path in (ROOT / "apps/network_map/migrations").glob("*.py")]
        self.assertFalse(any("07535" in name for name in migrations))


if __name__ == "__main__":
    unittest.main(verbosity=2)
