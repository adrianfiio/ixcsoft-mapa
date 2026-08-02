from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.network_map.map_master_topology import (
    GraphEdge,
    _element_subtype,
    _ordered_cable_elements,
)


class MapMasterTopologyUnitTests(SimpleTestCase):
    def test_ordered_cable_elements_keeps_origin_passages_and_destination(self):
        cable = SimpleNamespace(origin_id=10, destination_id=40)
        passages = [
            SimpleNamespace(sequence=2, element_id=30),
            SimpleNamespace(sequence=1, element_id=20),
        ]
        self.assertEqual(_ordered_cable_elements(cable, passages), [10, 20, 30, 40])

    def test_ordered_cable_elements_removes_adjacent_duplicates(self):
        cable = SimpleNamespace(origin_id=10, destination_id=20)
        passages = [SimpleNamespace(sequence=1, element_id=10)]
        self.assertEqual(_ordered_cable_elements(cable, passages), [10, 20])

    def test_element_subtype_accepts_import_metadata(self):
        element = SimpleNamespace(metadata={"import_subtype": "CDO"})
        self.assertEqual(_element_subtype(element), "cdo")

    def test_graph_edge_defaults_to_fiber(self):
        edge = GraphEdge("element:1", "cable:2", cable_id=2)
        self.assertEqual(edge.kind, "fiber")
        self.assertEqual(edge.cable_id, 2)
