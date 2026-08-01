from django.test import SimpleTestCase

from apps.network_map.api.optical_editor_v3 import _distance_m, _project_distance_m


class OpticalEditorV3GeometryTests(SimpleTestCase):
    def test_projected_point_on_segment_has_zero_distance(self):
        self.assertLess(_project_distance_m((0.5, 0.0), (0.0, 0.0), (1.0, 0.0)), 0.01)

    def test_distance_is_positive(self):
        self.assertGreater(_distance_m((-50.0, -24.0), (-50.001, -24.001)), 100)
