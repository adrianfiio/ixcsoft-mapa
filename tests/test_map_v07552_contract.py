import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def content(path):
    return (ROOT / path).read_text(encoding="utf-8")

class MapV07552ContractTests(unittest.TestCase):
    def test_template_replaces_conflicting_runtimes(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-maintenance-v07552.js", template)
        self.assertIn("map-rack-switch-v07552.js", template)
        self.assertIn("map-rack-runtime-v07552.css", template)
        self.assertNotIn("map-rack-maintenance-v07550.js", template)
        self.assertNotIn("map-rack-switch-v07551.js", template)

    def test_pan_uses_left_button_and_preserves_slot_click(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        self.assertIn("event.button !== 0", js)
        self.assertIn("Math.hypot(dx, dy) < 5", js)
        self.assertIn("suppressClickUntil", js)
        self.assertNotIn("scroll.setPointerCapture?.(event.pointerId)", js)
        pan_block = js[js.index("function interactivePanTarget"):js.index("function installNavigation")]
        self.assertNotIn(".v07545-service-slot", pan_block)
        self.assertNotIn(".v07549-uplink-slot", pan_block)

    def test_switches_8_12_16_use_single_row(self):
        js = content("static/js/map-rack-switch-v07552.js")
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("[8, 12, 16].includes(data.ports.length)", js)
        self.assertIn('holder.classList.add("is-single-row")', js)
        self.assertIn("repeat(var(--port-count)", css)

    def test_uplink_is_single_top_section_and_editable(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        self.assertIn("/api/map/v07552/elements/", js)
        self.assertIn("port_specs", js)
        self.assertIn("RJ45, SFP, SFP+, XFP e QSFP+", js)
        self.assertIn('item.dataset.generatedBy !== "v07552"', js)
        self.assertIn("face.insertBefore(bank, serviceSlots)", js)

    def test_backend_supports_real_uplink_connectors_and_speed(self):
        py = content("apps/network_map/api/map_v07552.py")
        for value in ("rj45", "sfp", "sfp_plus", "xfp", "qsfp_plus"):
            self.assertIn(f'"{value}"', py)
        for value in ("1", "10", "25", "40", "100"):
            self.assertIn(f'Decimal("{value}")', py)
        self.assertIn("v07551_port_profiles", py)
        self.assertNotIn("models.Model", py)

    def test_rack_drag_can_swap_equipment(self):
        js = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("function swapCandidate", js)
        self.assertIn("is-swap-target-v07552", js)
        self.assertIn("state.preferences[String(drag.swapEquipmentId)]", js)
        self.assertIn("[4,8,12,16,24,48]", js)

    def test_dio_pairs_are_front_then_rear(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("pair.appendChild(front); pair.appendChild(rear);", js)
        self.assertIn('[data-port-role="front"] { order: 1; }', css)
        self.assertIn('[data-port-role="rear"] { order: 2; }', css)
        self.assertIn("grid-template-columns: repeat(12", css)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('0.75.54', content("config/settings.py"))
        self.assertIn('v0.75.54', content("VERSIONS.md"))
        self.assertIn('MAP v0.75.52', content("docs/releases/map/map-v0.75.52.md"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
