import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "apps/network_map/device_type_yaml_v07551.py"
spec = importlib.util.spec_from_file_location("device_type_yaml_v07551", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class DeviceTypeYamlV07551Tests(unittest.TestCase):
    def test_generic_yaml_preserves_names_and_types(self):
        parsed = module.parse_equipment_yaml_v07551(
            """
equipment:
  external_key: sw-pop-01
  type: switch
  name: SW-POP-01
  vendor: FiberHome
  model: S4820
  ports:
    - name: ge-0/0/1
      connector_type: RJ45
      speed_gbps: 1
    - name: xge-0/0/17
      connector_type: SFP+
      speed_gbps: 10
    - name: xfp-0/0/19
      connector_type: XFP
      speed_gbps: 10
    - name: forty-gig-0/0/21
      connector_type: QSFP+
      speed_gbps: 40
"""
        )
        equipment = parsed.equipments[0]
        self.assertEqual(equipment.external_key, "sw-pop-01")
        self.assertEqual(
            [port.name for port in equipment.ports],
            ["ge-0/0/1", "xge-0/0/17", "xfp-0/0/19", "forty-gig-0/0/21"],
        )
        self.assertEqual(
            [port.connector_type for port in equipment.ports],
            ["rj45", "sfp_plus", "xfp", "qsfp_plus"],
        )
        self.assertEqual([float(port.speed_gbps) for port in equipment.ports], [1, 10, 10, 40])

    def test_netbox_ranges_expand_without_renaming(self):
        parsed = module.parse_equipment_yaml_v07551(
            """
manufacturer: MikroTik
model: CRS-16
slug: crs-16
interfaces:
  - name: ether[1-16]
    type: 1000base-t
"""
        )
        ports = parsed.equipments[0].ports
        self.assertEqual(len(ports), 16)
        self.assertEqual(ports[0].name, "ether1")
        self.assertEqual(ports[-1].name, "ether16")
        self.assertTrue(all(port.connector_type == "rj45" for port in ports))

    def test_speed_and_connector_matrix(self):
        parsed = module.parse_equipment_yaml_v07551(
            """
equipments:
  - name: SW-MIXED
    type: switch
    ports:
      - {name: p1, connector_type: RJ45, speed_gbps: 1}
      - {name: p2, connector_type: SFP, speed_gbps: 1}
      - {name: p3, connector_type: SFP+, speed_gbps: 10}
      - {name: p4, connector_type: SFP+, speed_gbps: 25}
      - {name: p5, connector_type: QSFP+, speed_gbps: 40}
      - {name: p6, connector_type: QSFP+, speed_gbps: 100}
"""
        )
        ports = parsed.equipments[0].ports
        self.assertEqual(
            [port.port_type for port in ports],
            ["rj45_1g", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "qsfp_plus_40g", "qsfp28_100g"],
        )

    def test_python_object_tags_are_rejected(self):
        with self.assertRaises(module.EquipmentYAMLV07551Error):
            module.parse_equipment_yaml_v07551("!!python/object/apply:os.system ['echo unsafe']")

    def test_duplicate_names_are_rejected(self):
        with self.assertRaises(module.EquipmentYAMLV07551Error):
            module.parse_equipment_yaml_v07551(
                """
equipment:
  name: SW
  ports:
    - {name: eth1, connector_type: RJ45, speed_gbps: 1}
    - {name: ETH1, connector_type: RJ45, speed_gbps: 1}
"""
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
