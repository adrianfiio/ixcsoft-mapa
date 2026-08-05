import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07542ContractTests(unittest.TestCase):
    def test_rack_is_compact_and_uses_19_inch_width(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        self.assertIn('innerWidth: 620', runtime)
        self.assertIn('RACK 19&quot;', runtime)
        self.assertIn('--rack-inner-width-v07542', css)
        self.assertNotIn('configuredUnits || 42', runtime)

    def test_equipment_spacing_reserves_one_u_for_organizer(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('unit <= end + 1', runtime)
        self.assertIn('candidateEnd >= start - 1', runtime)
        self.assertIn('renderRackOrganizers', runtime)
        self.assertIn('ORGANIZADOR DE CABOS', runtime)

    def test_front_links_route_through_organizers_and_ducts(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('organizerYs', runtime)
        self.assertIn('startDuct', runtime)
        self.assertIn('endDuct', runtime)
        self.assertIn('V ${organizerY}', runtime)

    def test_dio_matches_olt_and_has_optical_organizers(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        self.assertIn('enhanceDioNode', runtime)
        self.assertIn('ORGANIZADOR ÓPTICO', runtime)
        self.assertIn('.v07542-dio-19', css)
        self.assertIn('width: var(--rack-inner-width-v07542, 620px) !important;', css)

    def test_rear_cables_can_enter_dio_from_both_sides(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('const side = useLeft ? "left" : "right";', runtime)
        self.assertIn('sidePointInCanvas(target, canvas, side)', runtime)
        self.assertIn('.v07539-dio-cavity', runtime)

    def test_rack_zoom_uses_wheel_without_ctrl_and_keeps_buttons(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('installRackZoom', runtime)
        self.assertIn('event.deltaY < 0 ? "[data-canvas-zoom-in]"', runtime)
        self.assertNotIn('event.ctrlKey', runtime)
        self.assertIn('event.button === 1', runtime)

    def test_rack_creation_does_not_offer_pto_or_other(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        dialog = runtime[runtime.index('dialog.innerHTML ='):runtime.index('document.body.appendChild(dialog)')]
        self.assertIn('<option value="switch">Switch</option>', dialog)
        self.assertNotIn('<option value="pto">', dialog)
        self.assertNotIn('<option value="other">', dialog)
        self.assertNotIn('<option value="onu">', dialog)

    def test_backend_restricts_rack_equipment_types(self):
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn('rack_allowed = {', backend)
        self.assertIn('allowed = rack_allowed if container.element_type == NetworkElement.ElementType.RACK', backend)
        rack_block = backend[backend.index('rack_allowed = {'):backend.index('tower_allowed = {')]
        self.assertNotIn('EquipmentType.PTO', rack_block)
        self.assertNotIn('EquipmentType.OTHER', rack_block)

    def test_switch_creation_has_requested_fields(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        for label in ('Nome', 'Fabricante', 'Modelo', 'IP de gerência', 'Quantidade de portas'):
            self.assertIn(label, runtime)
        self.assertIn('name="port_count"', runtime)

    def test_backend_creates_switch_ports(self):
        backend = content("apps/network_map/api/map_v07539.py")
        self.assertIn('elif kind in {"switch", "router", "firewall"}:', backend)
        self.assertIn('metadata["port_count"] = port_count', backend)
        self.assertIn('label=f"Porta {number}"', backend)
        self.assertIn('PortType.RJ45_1G', backend)

    def test_switch_face_uses_twelve_ports_per_row(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        self.assertIn('enhanceSwitchNode', runtime)
        self.assertIn('grid-template-columns: repeat(12', css)
        self.assertIn('12 PORTAS POR LINHA', css)

    def test_no_migration_or_native_popup(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        backend = content("apps/network_map/api/map_v07539.py")
        for forbidden in ('window.alert(', 'window.prompt(', 'window.confirm(', 'global.alert(', 'global.prompt(', 'global.confirm('):
            self.assertNotIn(forbidden, runtime)
        self.assertNotIn('migrations', backend)
        migrations = ROOT / 'apps/network_map/migrations'
        if migrations.exists():
            self.assertFalse(any(migrations.glob('*07542*')))

    def test_current_version_assets_and_release(self):
        template = content("templates/map.html")
        self.assertIn('map-rack-physical-v07542.js', template)
        self.assertIn('map-rack-physical-v07542.css', template)
        self.assertIn('0.75.47', content('config/settings.py'))
        self.assertIn('v0.75.47', content('VERSIONS.md'))
        self.assertIn('MAP v0.75.47', content('docs/releases/map/map-v0.75.47.md'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
