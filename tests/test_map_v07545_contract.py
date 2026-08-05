import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07545ContractTests(unittest.TestCase):
    def test_olt_creation_uses_chassis_orientation_and_empty_slots(self):
        backend = content("apps/network_map/api/map_v07545.py")
        runtime = content("static/js/map-rack-chassis-v07545.js")
        self.assertIn('CHASSIS_SCHEMA_KEY = "v07545_chassis_schema"', backend)
        self.assertIn('ORIENTATIONS = {"vertical", "horizontal"}', backend)
        self.assertIn('card_count=slot_count', backend)
        self.assertIn('pons_per_card=0', backend)
        self.assertNotIn('_create_service_cards', backend)
        self.assertIn('data-chassis-orientation', runtime)
        self.assertIn('data-service-slot-count', runtime)

    def test_slots_support_vertical_and_horizontal_chassis(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        css = content("static/css/map-rack-chassis-v07545.css")
        self.assertIn('orientation === "vertical" ? "vertical" : "horizontal"', runtime)
        self.assertIn('Placas verticais · lado a lado', runtime)
        self.assertIn('Placas horizontais · uma sobre a outra', runtime)
        self.assertIn('.v07545-olt-face.is-vertical .v07545-chassis-slots', css)
        self.assertIn('.v07545-olt-face.is-horizontal .v07545-chassis-slots', css)

    def test_empty_slot_opens_card_editor_on_double_click_or_context_menu(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        self.assertIn('section.className = `v07545-service-slot is-empty', runtime)
        self.assertIn('slotElement.addEventListener("dblclick", open)', runtime)
        self.assertIn('slotElement.addEventListener("contextmenu", open)', runtime)
        self.assertIn('openSlotEditor(node, slotRow)', runtime)

    def test_card_editor_has_model_technology_and_exact_pon_count(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        backend = content("apps/network_map/api/map_v07545.py")
        for token in ('name="model"', 'name="technology"', 'name="pon_count"'):
            self.assertIn(token, runtime)
        for token in ('"gpon"', '"xgpon"', '"xgspon"'):
            self.assertIn(token, backend)
        self.assertIn('action: "install_card"', runtime)
        self.assertIn('if card.ports.count() != pon_count', backend)
        self.assertIn('label=f"S{card.slot} / PON {pon}"', backend)

    def test_uplinks_are_not_part_of_this_round(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        backend = content("apps/network_map/api/map_v07545.py")
        self.assertNotIn('openUplinkConfiguration', runtime)
        self.assertNotIn('replace_uplink_groups', runtime)
        self.assertIn('LEGACY_UPLINK_GROUPS_KEY: []', backend)
        self.assertIn('legacy_uplink_groups', backend)

    def test_pan_uses_window_pointer_events_after_zoom(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        self.assertIn('global.addEventListener("pointermove", move, true)', runtime)
        self.assertIn('global.addEventListener("pointerup", finish, true)', runtime)
        self.assertIn('translate(${view.tx}px, ${view.ty}px) scale(${view.scale})', runtime)
        self.assertIn('worldX', runtime)
        self.assertIn('[0, 1].includes(event.button)', runtime)

    def test_existing_cards_are_mapped_into_slots(self):
        backend = content("apps/network_map/api/map_v07545.py")
        self.assertIn('cards_by_slot = {', backend)
        self.assertIn('"empty": slot not in cards_by_slot', backend)
        self.assertIn('"card": cards_by_slot.get(slot)', backend)
        self.assertIn('orientation": "horizontal"', backend)

    def test_removing_or_resizing_linked_card_is_blocked(self):
        backend = content("apps/network_map/api/map_v07545.py")
        self.assertIn('if card and card.ports.count() != pon_count and _linked_card(card)', backend)
        self.assertIn('if _linked_card(card):', backend)
        self.assertIn('Desligue todas as portas da placa antes de removê-la.', backend)

    def test_dio_and_routes_remain_supported(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        self.assertIn('v07545-dio-organizer', runtime)
        self.assertIn('organizerForPort', runtime)
        self.assertIn('drawRearTrunks', runtime)
        self.assertIn('v07545-slot-organizer', runtime)

    def test_template_urls_and_version_are_current(self):
        urls = content("apps/network_map/api/urls.py")
        template = content("templates/map.html")
        settings = content("config/settings.py")
        versions = content("VERSIONS.md")
        release = content("docs/releases/map/map-v0.75.47.md")
        self.assertIn('equipment_collection_v07545', urls)
        self.assertIn('olt_chassis_v07545', urls)
        self.assertIn('map-rack-chassis-v07545.js', template)
        self.assertIn('map-rack-chassis-v07545.css', template)
        self.assertNotIn('map-rack-hardware-v07544.js', template)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.47")', settings)
        self.assertIn('Mapa | v0.75.47', versions)
        self.assertIn('MAP v0.75.47', release)

    def test_no_native_popup_or_migration(self):
        runtime = content("static/js/map-rack-chassis-v07545.js")
        backend = content("apps/network_map/api/map_v07545.py")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, runtime)
        self.assertNotIn("migrations", backend)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07545*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
