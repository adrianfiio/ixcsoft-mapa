import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07550ContractTests(unittest.TestCase):
    def test_stable_runtime_replaces_v07549_in_template(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-maintenance-v07552.js", template)
        self.assertNotIn("map-rack-maintenance-v07549.js", template)
        self.assertIn("map-rack-maintenance-v07549.css", template)

    def test_uplink_requests_are_cached_and_deduplicated(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("pendingUplinks: new Map()", js)
        self.assertIn("uplinkFailures: new Map()", js)
        self.assertIn("state.pendingUplinks.has(key)", js)
        self.assertIn("now - cached.at < 30000", js)
        self.assertIn("retryAt: Date.now() + 5000", js)

    def test_background_enhance_never_forces_uplink_fetch(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        start = js.index("async function enhanceOlt")
        end = js.index("// ------------------------------------------------------------------", start)
        enhance_olt = js[start:end]
        self.assertIn("loadUplinks(id, oltId, false)", enhance_olt)
        self.assertNotIn("loadUplinks(id, oltId, true)", enhance_olt)

    def test_render_is_signature_guarded(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("renderedUplinks: new WeakMap()", js)
        self.assertIn("state.renderedUplinks.get(node) === signature", js)
        self.assertIn('bank.dataset.generatedBy = "v07550"', js)

    def test_observer_ignores_generated_uplink_dom(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn('node.dataset.generatedBy === "v07550"', js)
        self.assertIn("touchesEquipment", js)
        self.assertNotIn("new MutationObserver(() => scheduleEnhance())", js)

    def test_enhance_is_single_flight_and_debounced(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("state.enhancing", js)
        self.assertIn("state.rerun", js)
        self.assertIn("global.clearTimeout(state.enhanceTimer)", js)
        self.assertNotIn("global.setTimeout(() => enhance().catch(() => {}), 180)", js)
        self.assertNotIn("global.setTimeout(() => enhance().catch(() => {}), 520)", js)

    def test_physical_flow_does_not_recursively_refresh_rack(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        start = js.index("function ensurePhysicalFlow")
        end = js.index("function installResizeObserver", start)
        flow = js[start:end]
        self.assertNotIn("mapRackPhysicalV07542?.refresh", flow)
        self.assertIn("mapRackPhysicalV07542?.autoOrganize", flow)
        self.assertIn("lastAutoAt", flow)

    def test_uplink_failure_is_non_fatal(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("load_error", js)
        self.assertIn("Uplinks temporariamente indisponíveis", js)
        self.assertIn("return fallback", js)

    def test_version_and_release_are_current(self):
        self.assertIn('0.75.58', content("config/settings.py"))
        self.assertIn('v0.75.58', content("VERSIONS.md"))
        self.assertIn('MAP v0.75.50', content("docs/releases/map/map-v0.75.50.md"))

    def test_no_migration_or_native_browser_popup(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertNotIn("window.alert(", js)
        self.assertNotIn("window.prompt(", js)
        self.assertNotIn("window.confirm(", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
