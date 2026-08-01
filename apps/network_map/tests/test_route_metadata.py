from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.network_map.route_metadata import element_route_payload, route_name_from_metadata


class RouteMetadataTests(SimpleTestCase):
    def test_new_route_path(self):
        self.assertEqual(
            route_name_from_metadata({"route_path": "SUL-JANDAIA / ROTA 05"}),
            "ROTA 05",
        )

    def test_old_kmz_folder(self):
        self.assertEqual(
            route_name_from_metadata({"kmz_folder": "PROJETO / ROTA 03/04 / CTO"}),
            "ROTA 03/04",
        )

    def test_empty_metadata(self):
        self.assertEqual(route_name_from_metadata({}), "")

    def test_payload_keeps_metadata_route_without_relations(self):
        empty = MagicMock()
        empty.select_related.return_value.exclude.return_value.all.return_value = []
        passages = MagicMock()
        passages.select_related.return_value.exclude.return_value = []
        element = SimpleNamespace(
            metadata={"kmz_folder": "PROJETO / ROTA 11 / CDO"},
            outgoing_cables=empty,
            incoming_cables=empty,
            cable_passages=passages,
        )
        payload = element_route_payload(element)
        self.assertEqual(payload["route_names"], ["ROTA 11"])
