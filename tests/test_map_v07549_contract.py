import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07549ContractTests(unittest.TestCase):
    def test_assets_are_loaded_after_v07548(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-maintenance-v07549.css", template)
        self.assertIn("map-rack-maintenance-v07550.js", template)
        self.assertLess(template.index("map-rack-integrity-v07548.css"), template.index("map-rack-maintenance-v07549.css"))
        self.assertLess(template.index("map-rack-integrity-v07548.js"), template.index("map-rack-maintenance-v07550.js"))

    def test_empty_rack_is_aligned(self):
        css = content("static/css/map-rack-maintenance-v07549.css")
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("v07549-empty-aligned", css)
        self.assertIn("v07549-rack-backdrop", css)
        self.assertIn("syncEmptyAppearance", js)

    def test_left_mouse_pan_and_wheel_zoom_are_centralized(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn('event.button !== 0', js)
        self.assertIn('event.button === 1', js)
        self.assertIn('global.addEventListener("wheel"', js)
        self.assertIn("applyView({ scale", js)
        self.assertIn("v07550-is-panning", js)

    def test_service_slot_click_and_context_menu(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn('.v07545-service-slot.is-empty', js)
        self.assertIn('global.addEventListener("contextmenu"', js)
        self.assertIn("renderServiceDialog", js)
        self.assertIn("port_tx_power_dbm", js)
        self.assertIn("await renderServiceDialog", js)

    def test_uplink_cards_have_model_and_per_port_types(self):
        backend = content("apps/network_map/api/map_v07549.py")
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn('UPLINK_PROFILE_KEY = "v07549_uplink_profiles"', backend)
        self.assertIn("save_uplink_card", backend)
        self.assertIn("remove_uplink_card", backend)
        self.assertIn("RJ45 1G", backend)
        self.assertIn("SFP 1G", backend)
        self.assertIn("SFP+ 10G", backend)
        self.assertIn("data-uplink-port-type", js)
        self.assertIn("HU1A", js)

    def test_uplink_slots_are_rendered_before_service_slots(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("face.insertBefore(bank, serviceSlots)", js)
        self.assertIn("v07549-uplink-bank", js)

    def test_dio_connector_and_fusion_states_are_separate(self):
        # MAP_V07558_DIO_SINGLE_PORT: o conector deixou de ter cor própria
        # (o pedido do usuário não previa isso); o que continua separado
        # é o estado de fusão (quadrado) do estado de OLT/PON (bolinha),
        # agora dois elementos aninhados só, não mais dois quadrados.
        js = content("static/js/map-rack-maintenance-v07552.js")
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("is-fused-v07558", js)
        self.assertIn("is-pon-linked-v07558", js)
        self.assertIn("v07558-dio-unit.is-fused-v07558", css)
        self.assertIn("v07558-dio-dot.is-pon-linked-v07558", css)

    def test_rack_reflows_when_async_equipment_changes_size(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        self.assertIn("ResizeObserver", js)
        self.assertIn("overlapPairs", js)
        self.assertIn("mapRackPhysicalV07542?.autoOrganize", js)

    def test_fusion_matrix_is_compact_and_detach_dataset_is_fixed(self):
        css = content("static/css/map-rack-maintenance-v07549.css")
        fusion = content("static/js/map-dio-fusion-v07538.js")
        self.assertIn("max-width: 1460px", css)
        # MAP_V07561_DIO_FUSION_FIBERS_VISIBLE: "repeat(12, 30px)" fixo
        # nunca encolhia e cortava as últimas fibras da lista "CABOS
        # VINCULADOS" por baixo do overflow:hidden do card -- trocado
        # por 1fr sem mínimo, que sempre cabe.
        self.assertIn("repeat(12, 1fr) !important", css)
        self.assertIn("detach.dataset.dioDetachCableV07538", fusion)
        self.assertNotIn("detach.dataset.dioDetachCableV07537", fusion)

    def test_backend_route_is_registered(self):
        urls = content("apps/network_map/api/urls.py")
        self.assertIn("olt_uplink_slots_v07549", urls)
        self.assertIn("uplinks-v07549", urls)

    def test_version_and_release_are_current(self):
        self.assertIn('0.75.50', content("config/settings.py"))
        self.assertIn('v0.75.50', content("VERSIONS.md"))
        self.assertIn('MAP v0.75.50', content("docs/releases/map/map-v0.75.50.md"))

    def test_no_migration_or_native_browser_prompt(self):
        js = content("static/js/map-rack-maintenance-v07550.js")
        backend = content("apps/network_map/api/map_v07549.py")
        self.assertNotIn("window.alert(", js)
        self.assertNotIn("window.prompt(", js)
        self.assertNotIn("window.confirm(", js)
        self.assertNotIn("migrations", backend)


if __name__ == "__main__":
    unittest.main(verbosity=2)
