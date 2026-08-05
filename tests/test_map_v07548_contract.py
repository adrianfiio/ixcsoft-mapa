import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07548ContractTests(unittest.TestCase):
    def test_assets_loaded_after_v07547(self):
        template = text("templates/map.html")
        self.assertIn("map-rack-integrity-v07548.css", template)
        self.assertIn("map-rack-integrity-v07548.js", template)
        self.assertGreater(template.index("map-rack-integrity-v07548.js"), template.index("map-v0758-core-ui.js"))

    def test_empty_rack_hides_frame_and_cables(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        css = text("static/css/map-rack-integrity-v07548.css")
        self.assertIn("v07548-rack-empty", js)
        self.assertIn("essentialNodes", js)
        self.assertIn("[data-rack-frame-v07542]", css)
        self.assertIn(".master-cable-node", css)

    def test_olt_creation_has_slots_without_pons_per_slot(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        self.assertIn("Slots de placas de serviço", js)
        self.assertIn("Slots de uplink", js)
        self.assertNotIn("PONs por slot", js)
        self.assertIn("/api/map/v07547/elements/", js)

    def test_olt_editor_can_resize_chassis_and_edit_port_power(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        backend = text("apps/network_map/api/map_v07548.py")
        self.assertIn("service_slot_count", js)
        self.assertIn("port_tx_power_dbm", js)
        self.assertIn("PORT_POWER_KEY", backend)
        self.assertIn("highest_card_slot", backend)

    def test_dio_ports_are_dots_and_cable_line_hits_port(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        css = text("static/css/map-rack-integrity-v07548.css")
        self.assertIn("v07548-dio-dot-port", js)
        self.assertIn("dio_port_id", js)
        self.assertIn("centerInCanvas(target", js)
        self.assertIn("v07548-rear-link", css)

    def test_rack_menu_hides_pto_and_other(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        self.assertIn('[data-quick-add="pto"]', js)
        self.assertIn('[data-quick-add="other"]', js)

    def test_rack_request_guard_avoids_splice_400_and_duplicate_link_posts(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        self.assertIn("ignored_for_rack", js)
        self.assertIn("pendingLinkRequests", js)
        self.assertIn("equipment-links", js)
        self.assertIn("/splices", js)

    def test_safe_core_ui_query_helpers(self):
        core = text("static/js/map-v0758-core-ui.js")
        self.assertIn("root?.querySelector?.(selector) || null", core)
        self.assertIn("root?.querySelectorAll?.(selector) || []", core)

    def test_optical_path_endpoint_and_ui(self):
        backend = text("apps/network_map/api/map_v07548.py")
        js = text("static/js/map-rack-integrity-v07548.js")
        self.assertIn("def olt_port_path_v07548", backend)
        self.assertIn("estimated_power_after_dio_dbm", backend)
        self.assertIn("map:optical-path-highlight", js)
        self.assertIn("Caminho óptico", js)

    def test_routes_registered(self):
        urls = text("apps/network_map/api/urls.py")
        self.assertIn("olt_editor_v07548", urls)
        self.assertIn("rack_topology_v07548", urls)
        self.assertIn("olt_port_path_v07548", urls)

    def test_no_native_browser_dialogs(self):
        js = text("static/js/map-rack-integrity-v07548.js")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
