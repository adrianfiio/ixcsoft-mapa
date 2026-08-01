from django.test import SimpleTestCase

from apps.network_map.cto_defaults import splitter_sizes_for_capacity


class CTODefaultSplitterPlanTests(SimpleTestCase):
    def test_common_capacities(self):
        self.assertEqual(splitter_sizes_for_capacity(8), [8])
        self.assertEqual(splitter_sizes_for_capacity(16), [16])
        self.assertEqual(splitter_sizes_for_capacity(24), [16, 8])
        self.assertEqual(splitter_sizes_for_capacity(36), [32, 4])
        self.assertEqual(splitter_sizes_for_capacity(48), [32, 16])
        self.assertEqual(splitter_sizes_for_capacity(128), [64, 64])
