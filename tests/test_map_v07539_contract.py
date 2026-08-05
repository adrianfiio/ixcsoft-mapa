import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07539ContractTests(unittest.TestCase):
    def test_dio_has_independent_front_and_rear_api(self):
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn("def dio_dual_face_v07539", backend)
        self.assertIn('action == "connect_front"', backend)
        self.assertIn('"disconnect_front", "disconnect_rear"', backend)
        self.assertIn("_front_link", backend)
        self.assertIn("_rear_link", backend)
        self.assertIn('"state": (', backend)

    def test_front_link_does_not_treat_rear_fusion_as_occupied(self):
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn("destination_port=destination, source_port__isnull=False", backend)
        self.assertIn("source_port=source", backend)
        self.assertIn("cable_fiber_id or (item.source_port_id is None and item.cable_id)", backend)

    def test_dio_cavities_and_face_colors_exist(self):
        runtime = content("static/js/map-v07539-suite.js")
        css = content("static/css/map-v07539-suite.css")
        self.assertIn("groupDioCavities", runtime)
        self.assertIn("CAVIDADE", runtime)
        self.assertIn("v07539-front-linked", css)
        self.assertIn("v07539-rear-linked", css)
        self.assertIn("#fb923c", css)
        self.assertIn("#a78bfa", css)

    def test_olt_size_is_persisted(self):
        runtime = content("static/js/map-v07539-suite.js")
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn("v07539-olt-size-controls", runtime)
        self.assertIn("equipment_width_", runtime)
        self.assertIn("saveLayoutPreference", runtime)
        self.assertIn("def layout_v07539", backend)
        self.assertIn("map_v07539_layout", backend)

    def test_modern_equipment_editor_replaces_legacy_click(self):
        runtime = content("static/js/map-v07539-suite.js")
        self.assertIn('[data-node-edit], [data-edit-equipment]', runtime)
        self.assertIn("openEquipmentEditor", runtime)
        self.assertIn("stopImmediatePropagation", runtime)
        self.assertIn("EDITOR MODERNO DE EQUIPAMENTOS", runtime)
        self.assertIn("openCreateEquipment", runtime)
        self.assertIn("def equipment_collection_v07539", content("apps/network_map/api/map_v07539.py"))
        self.assertIn("/api/map/v07539/elements/${elementId}/equipment/", runtime)

    def test_drop_destinations_are_limited_to_dio_pto_onu(self):
        backend = content("apps/network_map/api/map_v07539.py")
        runtime = content("static/js/map-v07539-suite.js")
        self.assertIn("def drop_terminations_v07539", backend)
        self.assertIn('return "dio"', backend)
        self.assertIn('return "pto"', backend)
        self.assertIn('return "onu"', backend)
        self.assertIn("O DROP só pode terminar em DIO, PTO ou PON de ONU/ONT.", backend)
        self.assertIn("Solte o DROP sobre a traseira do DIO, uma PTO ou a PON da ONU/ONT.", runtime)

    def test_pto_and_onu_have_specific_visual_language(self):
        runtime = content("static/js/map-v07539-suite.js")
        css = content("static/css/map-v07539-suite.css")
        self.assertIn("enhancePassiveEquipment", runtime)
        self.assertIn("ENTRADA FIBRA", runtime)
        self.assertIn("PON", runtime)
        self.assertIn("v07539-pto-node", css)
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn('label="Entrada fibra"', backend)
        self.assertIn('label=f"Saída {equipment.get_connector_type_display()', backend)
        self.assertIn("v07539-onu-node", css)

    def test_cto_ceo_cdo_share_directional_vertical_canvas(self):
        state = content("static/js/optical/optical-state.js")
        renderer = content("static/js/optical/optical-renderer.js")
        workspace = content("static/js/optical/optical-workspace.js")
        self.assertIn("function isOpticalBox", state)
        self.assertIn('["splice_box", "cto"]', state)
        self.assertIn("stateApi().isOpticalBox(session)", renderer)
        self.assertIn("cableTopologyRelation", renderer)
        self.assertIn("entrada visual", renderer)
        self.assertIn("saída visual", renderer)
        self.assertIn("state.isOpticalBox(session)", workspace)

    def test_cable_context_menu_contains_all_requested_actions(self):
        runtime = content("static/js/map-v07539-suite.js")
        for label in (
            "Informações", "Editar cabo", "Alterar sentido", "Adicionar CTO",
            "Adicionar CEO", "Adicionar CDO", "Adicionar reserva",
            "Associar à caixa", "Excluir cabo",
        ):
            self.assertIn(label, runtime)
        self.assertIn("openCableContext", runtime)
        self.assertIn("scanLeafletLayers", runtime)

    def test_reserve_records_type_position_responsible_notes(self):
        backend = content("apps/network_map/api/map_v07539.py")
        runtime = content("static/js/map-v07539-suite.js")
        self.assertIn("RESERVE_PREFIX", backend)
        self.assertIn('"reserve_type"', backend)
        self.assertIn('"position"', backend)
        self.assertIn('"responsible"', backend)
        self.assertIn('name="reserve_type"', runtime)
        self.assertIn('name="responsible"', runtime)

    def test_dio_front_shows_rear_fusion_without_blocking_front(self):
        runtime = content("static/js/map-v07539-suite.js")
        css = content("static/css/map-v07539-suite.css")
        self.assertIn("v07539-has-rear", runtime)
        self.assertIn("Frente livre para OLT", runtime)
        self.assertIn("dio-front.v07539-has-rear::after", css)
        self.assertIn("#f97316", css)

    def test_cable_information_contains_optical_budget(self):
        backend = content("apps/network_map/api/map_v07539.py")
        runtime = content("static/js/map-v07539-suite.js")
        self.assertIn("def _cable_optical_budget", backend)
        self.assertIn('"estimated_rx_dbm"', backend)
        self.assertIn('"optical_budget"', backend)
        self.assertIn("Perda estimada", runtime)
        self.assertIn("Potência estimada", runtime)

    def test_cable_information_panel_has_fibers_connections_boxes_and_reserves(self):
        runtime = content("static/js/map-v07539-suite.js")
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn("openCableInfo", runtime)
        self.assertIn("Fibras", runtime)
        self.assertIn("Conexões", runtime)
        self.assertIn("Reservas", runtime)
        self.assertIn("available_boxes", backend)
        self.assertIn("_cable_connections", backend)
        self.assertIn("_fiber_usage", backend)

    def test_connection_catalog_names_distinct_physical_operations(self):
        backend = content("apps/network_map/api/map_v07539.py")
        runtime = content("static/js/map-v07539-suite.js")
        for token in (
            "Fusão cabo ↔ cabo", "Ligação de entrada do splitter",
            "Ligação de saída do splitter", "Fusão na traseira do DIO",
            "Terminação DROP",
        ):
            self.assertIn(token, backend)
        for token in ("FUSÃO", "ENTRADA SPLITTER", "SAÍDA SPLITTER", "TERMINAÇÃO", "CORDÃO"):
            self.assertIn(token, runtime)

    def test_layout_persistence_covers_equipment_sizes_and_cavities(self):
        runtime = content("static/js/map-v07539-suite.js")
        self.assertIn("dio_cavity_", runtime)
        self.assertIn("equipment_width_", runtime)
        self.assertIn("/layout/", runtime)
        self.assertIn("saveLayoutPreference", runtime)

    def test_no_new_migration_or_browser_popup(self):
        runtime = content("static/js/map-v07539-suite.js")
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertNotIn("window.alert(", runtime)
        self.assertNotIn("window.prompt(", runtime)
        self.assertNotIn("window.confirm(", runtime)
        self.assertNotIn("global.alert(", runtime)
        self.assertNotIn("global.prompt(", runtime)
        self.assertNotIn("global.confirm(", runtime)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07539*")))
        self.assertNotIn("migrations", backend)

    def test_urls_template_and_version_are_current(self):
        urls = content("apps/network_map/api/urls.py")
        template = content("templates/map.html")
        self.assertIn("cable-workspace-v07539", urls)
        self.assertIn("dio-dual-face-v07539", urls)
        self.assertIn("drop-terminations-v07539", urls)
        self.assertIn("equipment-editor-v07539", urls)
        self.assertIn("equipment-collection-v07539", urls)
        self.assertIn("layout-v07539", urls)
        self.assertIn("map-v07539-suite.js", template)
        self.assertIn("map-v07539-suite.css", template)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.40")', content("config/settings.py"))
        self.assertIn("Mapa | v0.75.40", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.39", content("docs/releases/map/map-v0.75.39.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
