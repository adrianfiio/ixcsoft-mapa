import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07557ContractTests(unittest.TestCase):
    def test_tower_generic_equipment_endpoint_generates_ports_for_active_types(self):
        views = content("apps/network_map/api/views.py")
        start = views.index('port_count = int(request.data["port_count"])')
        end = views.index("snmp_community = str(", start)
        create_block = views[start:end]
        self.assertIn("if port_count and equipment_type in {", create_block)
        self.assertIn("ContainerEquipment.EquipmentType.SWITCH,", create_block)
        self.assertIn("ContainerEquipment.EquipmentType.ROUTER,", create_block)
        self.assertIn("ContainerEquipment.EquipmentType.FIREWALL,", create_block)
        self.assertIn("ContainerEquipment.EquipmentType.SERVER,", create_block)
        self.assertIn('metadata["port_count"] = max(1, min(port_count, 96))', create_block)

        start = views.index("def _generate_container_equipment_ports")
        end = views.index("elif equipment.equipment_type in {\n        ContainerEquipment.EquipmentType.PTP,", start)
        generate_block = views[start:end]
        self.assertIn("MAP_V07557_TOWER_SWITCH_PORTS", generate_block)
        self.assertIn(
            "default_count = 24 if equipment.equipment_type == ContainerEquipment.EquipmentType.SWITCH else 8",
            generate_block,
        )
        self.assertIn(
            'port_count = max(1, min(int(equipment.metadata.get("port_count") or default_count), 96))',
            generate_block,
        )

    def test_tower_equipment_create_dialog_has_port_count_field(self):
        js = content("static/js/map-master-suite.js")
        self.assertIn('data-create-field="port-count"', js)
        self.assertIn('<select name="port_count">', js)
        self.assertIn('const portCountTypes = ["switch", "router", "firewall", "server"];', js)
        self.assertIn('show("port-count", portCountTypes.includes(type));', js)

    def test_real_cable_menu_has_editar_rota(self):
        js = content("static/js/map-v07539-suite.js")
        self.assertIn('data-cable-action="route"', js)
        self.assertIn('if (action === "route") return global.networkMap?.startGeometryEdit?.(cableId);', js)

    def test_duplicate_cable_context_menu_system_is_gone(self):
        js = content("static/js/map-editor.js")
        self.assertNotIn("cableContextMenu", js)
        self.assertNotIn("openCableContextMenu", js)
        self.assertIn("startGeometryEdit", js)
        self.assertIn("window.networkMap = { map, loadStructure, showUnifilar, manageContainer, notify, startGeometryEdit };", js)

    def test_dio_pair_stacks_front_over_rear_not_side_by_side(self):
        # MAP_V07558_DIO_SINGLE_PORT (rodada seguinte) substituiu o par
        # empilhado por 1 elemento só — ver test_map_v07558_contract.py.
        # Aqui só confere que a classe do par antigo não sobrou em lugar
        # nenhum do CSS (limpeza completa, sem regra morta espalhada).
        for path in (
            "static/css/map-rack-runtime-v07552.css",
            "static/css/map-rack-maintenance-v07549.css",
            "static/css/map-v07539-suite.css",
        ):
            self.assertNotIn(".v07539-dio-pair", content(path))

    def test_auto_fuse_button_has_blue_bolt_icon(self):
        js = content("static/js/map-dio-fusion-v07538.js")
        self.assertIn('<svg class="v07557-auto-fuse-bolt" viewBox="0 0 24 24" aria-hidden="true">', js)
        self.assertIn("<span>Auto fusão</span>", js)

        css = content("static/css/map-dio-fusion-v07538.css")
        self.assertIn(".v07557-auto-fuse-bolt {", css)
        self.assertIn("fill: #38bdf8;", css)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.58")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.58", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
