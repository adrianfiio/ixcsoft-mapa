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
        css = content("static/css/map-rack-runtime-v07552.css")
        start = css.index('#map-master-container .v07539-dio-pair {')
        end = css.index("MAP_V07557_DIO_STACKED_PAIR", start)
        self.assertGreater(end, start)
        block_end = css.index("}", start)
        pair_block = css[start:block_end]
        self.assertIn("grid-template-columns: 22px !important;", pair_block)
        self.assertIn("grid-template-rows: repeat(2, 26px) !important;", pair_block)

        # MAP_V07514_DIO_ORIENTATION (map-v0750-tower-workspace.css) força
        # .dio-front/.dio-rear em colunas 1/2 diferentes — sem esta
        # sobrescrita, o grid de 1 coluna acima nunca é suficiente pra
        # empilhar de verdade, porque o item já vem com grid-column
        # explícito daquele outro arquivo (explicit placement sempre vence
        # auto-placement, mesmo com display:grid + 1 coluna só).
        self.assertIn(
            '#map-master-container .v07539-dio-pair [data-port-role="front"] { grid-column: 1 !important; grid-row: 1 !important;',
            css,
        )
        self.assertIn(
            '#map-master-container .v07539-dio-pair [data-port-role="rear"] { grid-column: 1 !important; grid-row: 2 !important;',
            css,
        )

        tower_css = content("static/css/map-v0750-tower-workspace.css")
        self.assertIn(".master-node-port.dio-front { grid-column: 1; }", tower_css)
        self.assertIn(".master-node-port.dio-rear { grid-column: 2; }", tower_css)

        # a regra antiga em map-rack-maintenance-v07549.css não define mais
        # o grid do par (só sobrou o que map-rack-runtime-v07552.css não
        # define), pra não deixar duas versões conflitantes do layout.
        maintenance_css = content("static/css/map-rack-maintenance-v07549.css")
        old_start = maintenance_css.index("#map-master-container .v07539-dio-pair {")
        old_end = maintenance_css.index("}", old_start)
        old_block = maintenance_css[old_start:old_end]
        self.assertNotIn("grid-template-columns", old_block)
        self.assertNotIn("display: grid", old_block)

    def test_auto_fuse_button_has_blue_bolt_icon(self):
        js = content("static/js/map-dio-fusion-v07538.js")
        self.assertIn('<svg class="v07557-auto-fuse-bolt" viewBox="0 0 24 24" aria-hidden="true">', js)
        self.assertIn("<span>Auto fusão</span>", js)

        css = content("static/css/map-dio-fusion-v07538.css")
        self.assertIn(".v07557-auto-fuse-bolt {", css)
        self.assertIn("fill: #38bdf8;", css)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.57")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.57", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
