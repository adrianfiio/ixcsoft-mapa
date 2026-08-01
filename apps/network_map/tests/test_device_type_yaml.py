from django.test import SimpleTestCase

from apps.network_map.device_type_yaml import DeviceTypeYAMLError, parse_device_type_yaml
from apps.network_map.models import ContainerEquipment, ContainerEquipmentPort


class DeviceTypeYAMLTests(SimpleTestCase):
    def test_parses_netbox_style_rb911(self):
        parsed = parse_device_type_yaml(
            b"""
manufacturer: MikroTik
model: RB911G-5HPacD
slug: mikrotik-rb911g-5hpacd
interfaces:
  - name: ether1
    type: 1000base-t
  - name: wlan1
    type: ieee802.11ac
"""
        )
        self.assertEqual(parsed.suggested_equipment_type, ContainerEquipment.EquipmentType.PTP)
        self.assertEqual(
            [item.port_type for item in parsed.interfaces],
            [ContainerEquipmentPort.PortType.RJ45_1G, ContainerEquipmentPort.PortType.WIRELESS],
        )

    def test_skips_virtual_interfaces(self):
        parsed = parse_device_type_yaml(
            b"""
manufacturer: Teste
model: Switch 8
interfaces:
  - name: bridge1
    type: bridge
  - name: ether1
    type: 1000base-t
"""
        )
        self.assertEqual(len(parsed.interfaces), 1)
        self.assertEqual(len(parsed.skipped_interfaces), 1)

    def test_rejects_yaml_without_supported_interfaces(self):
        with self.assertRaises(DeviceTypeYAMLError):
            parse_device_type_yaml(
                b"""
manufacturer: Teste
model: Virtual
interfaces:
  - name: bridge1
    type: bridge
"""
            )
