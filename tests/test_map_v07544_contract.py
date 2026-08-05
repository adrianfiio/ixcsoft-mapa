import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07544ContractTests(unittest.TestCase):
    def test_olt_creation_is_intercepted_by_current_runtime(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn('form.matches("[data-create-equipment]")', runtime)
        self.assertIn('payload.uplink_groups = readCreateGroups(form)', runtime)
        self.assertIn('/api/map/v07544/elements/${elementId}/equipment/', runtime)
        self.assertIn('event.stopImmediatePropagation()', runtime)

    def test_backend_creates_exact_service_cards_and_pon_ports(self):
        backend = content("apps/network_map/api/map_v07544.py")
        self.assertIn("def _create_service_cards", backend)
        self.assertIn("for slot in range(1, slot_count + 1)", backend)
        self.assertIn("for pon in range(1, pons_per_slot + 1)", backend)
        self.assertIn('label=f"S{slot} / PON {pon}"', backend)
        self.assertIn("card_count=slot_count", backend)
        self.assertIn("pons_per_card=pons_per_slot", backend)

    def test_zero_uplink_groups_creates_no_uplink_ports(self):
        backend = content("apps/network_map/api/map_v07544.py")
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn('groups = _validate_uplink_groups(data.get("uplink_groups") or [])', backend)
        self.assertIn('UPLINK_GROUPS_KEY: []', backend)
        self.assertIn("for group_index, group in enumerate(groups", backend)
        self.assertIn("Nenhum uplink será criado", runtime)

    def test_uplinks_are_explicit_metadata_not_all_cardless_ports(self):
        backend = content("apps/network_map/api/map_v07544.py")
        self.assertIn('UPLINK_GROUPS_KEY = "v07544_uplink_groups"', backend)
        self.assertIn('for raw_id in row.get("port_ids") or []', backend)
        self.assertIn('hidden_legacy_ports', backend)
        self.assertNotIn('card__isnull=True,\n            port_type__in=list(UPLINK_TYPES.values())', backend)

    def test_service_cards_render_from_backend_cards_only(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn("hardware.cards.forEach", runtime)
        self.assertIn("v07544-service-card", runtime)
        self.assertIn("card.ports.forEach", runtime)
        self.assertIn("v07544-legacy-hidden", runtime)
        self.assertNotIn("slots.slice(Math.max(0, slots.length - 2))", runtime)

    def test_uplink_groups_have_count_and_type(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        backend = content("apps/network_map/api/map_v07544.py")
        self.assertIn("data-group-count", runtime)
        self.assertIn("data-group-type", runtime)
        self.assertIn("replace_uplink_groups", runtime)
        self.assertIn("replace_uplink_groups", backend)
        for token in ("rj45_1g", "sfp_1g", "sfp_plus_10g"):
            self.assertIn(token, runtime)
            self.assertIn(token, backend)

    def test_pan_changes_canvas_transform_after_zoom(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn("function readView()", runtime)
        self.assertIn("function applyView(view)", runtime)
        self.assertIn("translate(${view.tx}px, ${view.ty}px) scale(${view.scale})", runtime)
        self.assertIn("worldX", runtime)
        self.assertNotIn("scroll.scrollLeft =", runtime)
        self.assertNotIn("scroll.scrollTop =", runtime)

    def test_dio_and_front_routes_still_use_local_organizers(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn("v07544-dio-organizer", runtime)
        self.assertIn("organizerForPort", runtime)
        self.assertIn("v07544-card-organizer", runtime)
        self.assertIn("v07544-uplink-organizer", runtime)
        self.assertIn("drawRearTrunks", runtime)

    def test_redundant_toolbar_actions_remain_hidden(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn('label === "ligar portas" || label === "editar linhas"', runtime)

    def test_urls_template_and_version_are_current(self):
        urls = content("apps/network_map/api/urls.py")
        template = content("templates/map.html")
        settings = content("config/settings.py")
        versions = content("VERSIONS.md")
        release = content("docs/releases/map/map-v0.75.44.md")
        self.assertIn("equipment_collection_v07544", urls)
        self.assertIn("olt_hardware_v07544", urls)
        self.assertIn("map-rack-hardware-v07544.js", template)
        self.assertIn("map-rack-hardware-v07544.css", template)
        self.assertNotIn("map-rack-routing-v07543.js", template)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.44")', settings)
        self.assertIn("Mapa | v0.75.44", versions)
        self.assertIn("MAP v0.75.44", release)

    def test_no_native_popup_or_migration(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        backend = content("apps/network_map/api/map_v07544.py")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, runtime)
        self.assertNotIn("migrations", backend)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07544*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
