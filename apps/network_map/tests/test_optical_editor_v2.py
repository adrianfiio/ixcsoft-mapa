from django.test import SimpleTestCase

from apps.network_map.api.optical_editor_v2 import nearest_position_m


class OpticalEditorGeometryTests(SimpleTestCase):
    def test_nearest_position_projects_on_segment(self):
        result = nearest_position_m(
            [(-50.0, -24.0), (-49.999, -24.0)],
            (-49.9995, -23.9999),
        )
        self.assertIsNotNone(result)
        self.assertGreater(result["position_m"], 40)
        self.assertLess(result["position_m"], 70)
        self.assertGreater(result["distance_m"], 5)
        self.assertLess(result["distance_m"], 20)

    def test_nearest_position_uses_closest_segment(self):
        result = nearest_position_m(
            [(-50.0, -24.0), (-49.999, -24.0), (-49.999, -23.999)],
            (-49.99895, -23.9995),
        )
        self.assertIsNotNone(result)
        self.assertLess(result["distance_m"], 10)
        self.assertGreater(result["position_m"], 100)
