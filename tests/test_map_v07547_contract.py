import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07547ContractTests(unittest.TestCase):
    def test_template_loads_v07547_after_chassis(self):
        template = text("templates/map.html")
        self.assertIn("map-rack-ux-v07547.css", template)
        self.assertIn("map-rack-ux-v07547.js", template)
        self.assertLess(template.index("map-rack-chassis-v07545.js"), template.index("map-rack-ux-v07547.js"))

    def test_olt_form_has_service_and_uplink_slots_without_pons_per_slot(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        self.assertIn('name="service_slot_count"', runtime)
        self.assertIn('name="uplink_slot_count"', runtime)
        self.assertNotIn('name="pons_per_card"', runtime)
        self.assertNotIn("PONs por slot", runtime)

    def test_olt_creation_uses_dedicated_endpoint(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        urls = text("apps/network_map/api/urls.py")
        self.assertIn("/api/map/v07547/elements/", runtime)
        self.assertIn("equipment_collection_v07547", urls)
        self.assertIn("olt_chassis_v07547", urls)

    def test_backend_creates_empty_chassis(self):
        backend = text("apps/network_map/api/map_v07547.py")
        self.assertIn('pons_per_card=0', backend)
        self.assertIn('"service_slot_count"', backend)
        self.assertIn('"uplink_slot_count"', backend)
        self.assertNotIn("_create_card_ports(equipment, card", backend.split("def equipment_collection_v07547", 1)[1].split("def olt_chassis_v07547", 1)[0])

    def test_pon_number_is_above_connection_point(self):
        css = text("static/css/map-rack-ux-v07547.css")
        self.assertIn(".v07547-pon-number", css)
        self.assertIn("top: 4px", css)
        self.assertIn(".v07547-pon-point", css)
        self.assertIn("bottom: 6px", css)

    def test_primary_button_pan_keeps_current_scale(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        self.assertIn("button: event.button", runtime)
        self.assertIn("scale: gesture.scale", runtime)
        self.assertIn("tx: gesture.tx + dx", runtime)
        self.assertIn("ty: gesture.ty + dy", runtime)

    def test_pan_intercepts_legacy_handlers_before_scroll(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        self.assertIn('document.addEventListener("pointerdown", beginPan, true)', runtime)
        self.assertIn("event.stopImmediatePropagation()", runtime)
        self.assertIn('document.addEventListener("wheel", interceptWheel', runtime)

    def test_rack_palette_hides_pto_and_other(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        self.assertIn('/^(PTO|Outro)', runtime)
        self.assertIn("data.hiddenRackV07547", runtime.replace("dataset.hiddenRackV07547", "data.hiddenRackV07547"))

    def test_uplink_slots_are_empty_placeholders(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        backend = text("apps/network_map/api/map_v07547.py")
        self.assertIn("v07547-uplink-slot is-empty", runtime)
        self.assertIn('"empty": True', backend)
        self.assertNotIn("install_uplink", backend)

    def test_no_native_browser_popups_or_migration(self):
        runtime = text("static/js/map-rack-ux-v07547.js")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, runtime)
        release = text("docs/releases/map/map-v0.75.47.md")
        self.assertIn("Nenhuma migration", release)


if __name__ == "__main__":
    unittest.main(verbosity=2)
