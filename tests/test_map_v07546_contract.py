import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class MapV07546ContractTests(unittest.TestCase):
    def test_viewport_runtime_loads_before_legacy_rack_runtimes(self):
        template = content("templates/map.html")
        viewport = template.index("js/map-rack-viewport-v07546.js")
        physical = template.index("js/map-rack-physical-v07542.js")
        chassis = template.index("js/map-rack-chassis-v07545.js")
        self.assertLess(viewport, physical)
        self.assertLess(viewport, chassis)
        self.assertIn("css/map-rack-viewport-v07546.css", template)

    def test_legacy_navigation_handlers_are_gated(self):
        physical = content("static/js/map-rack-physical-v07542.js")
        chassis = content("static/js/map-rack-chassis-v07545.js")
        self.assertIn("if (!global.mapRackViewportV07546) installRackZoom(root, scroll);", physical)
        self.assertIn("if (!global.mapRackViewportV07546) installNavigation(state.scroll);", chassis)

    def test_single_controller_owns_zoom_and_pan(self):
        runtime = content("static/js/map-rack-viewport-v07546.js")
        self.assertIn('scroll.addEventListener("wheel"', runtime)
        self.assertIn('global.addEventListener("pointermove", movePan, true)', runtime)
        self.assertIn('global.addEventListener("pointerup", finishPan, true)', runtime)
        self.assertIn('Math.hypot(dx, dy) < 4', runtime)
        self.assertIn('translate(${normalized.tx}px, ${normalized.ty}px) scale(${normalized.scale})', runtime)

    def test_pan_is_not_limited_to_empty_canvas_outside_rack(self):
        runtime = content("static/js/map-rack-viewport-v07546.js")
        blocked = runtime.split("function blockedPrimaryTarget", 1)[1].split("function beginPan", 1)[0]
        self.assertNotIn('".master-canvas-node"', blocked)
        self.assertNotIn('".master-cable-node"', blocked)
        self.assertIn('".v07542-rack-mounted > header"', blocked)
        self.assertIn('"[data-port-id]"', blocked)

    def test_zoom_buttons_are_owned_by_same_controller(self):
        runtime = content("static/js/map-rack-viewport-v07546.js")
        self.assertIn("[data-canvas-zoom-in], [data-canvas-zoom-out], [data-canvas-zoom-fit]", runtime)
        self.assertIn("fitView(root)", runtime)
        self.assertIn("zoomAround", runtime)

    def test_current_version_and_release_document(self):
        settings = content("config/settings.py")
        versions = content("VERSIONS.md")
        release = content("docs/releases/map/map-v0.75.50.md")
        self.assertIn('0.75.50', settings)
        self.assertIn('v0.75.50', versions)
        self.assertIn('MAP v0.75.50', release)

    def test_no_native_browser_popups(self):
        runtime = content("static/js/map-rack-viewport-v07546.js")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
