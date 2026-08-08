from pathlib import Path
from django.test import SimpleTestCase
from rest_framework import serializers

from apps.network_map.api.views import (
    BALANCED_SPLITTER_LOSS_DB,
    UNBALANCED_SPLITTER_LOSS_DB,
    DIO_PORT_LOSS_DB,
    FUSION_LOSS_DB,
    _splitter_output_loss_db,
)
from apps.network_map.serializers import NetworkElementSerializer


ROOT = Path(__file__).resolve().parents[3]


class MapV077OpticalBudgetTests(SimpleTestCase):
    def test_requested_fixed_losses(self):
        self.assertEqual(DIO_PORT_LOSS_DB, 0.50)
        self.assertEqual(FUSION_LOSS_DB, 0.10)

    def test_balanced_splitter_reference_losses(self):
        self.assertEqual(BALANCED_SPLITTER_LOSS_DB["1:8"], 10.5)
        self.assertEqual(BALANCED_SPLITTER_LOSS_DB["1:16"], 13.5)
        self.assertEqual(_splitter_output_loss_db("1:32", 1), 16.7)
        self.assertEqual(_splitter_output_loss_db("1:64", 1), 20.4)

    def test_unbalanced_splitter_is_directional(self):
        low_leg = _splitter_output_loss_db("10:90", 1)
        high_leg = _splitter_output_loss_db("10:90", 2)
        self.assertGreater(low_leg, high_leg)
        self.assertEqual(UNBALANCED_SPLITTER_LOSS_DB["10:90"], (11.2, 0.8))
        self.assertEqual(low_leg, 11.2)
        self.assertEqual(high_leg, 0.8)
        self.assertEqual(_splitter_output_loss_db("40:60", 1), 4.7)
        self.assertEqual(_splitter_output_loss_db("40:60", 2), 2.7)

    def test_cto_capacity_is_only_8_or_16(self):
        serializer = NetworkElementSerializer()
        self.assertEqual(serializer.validate_cto_capacity(8), 8)
        self.assertEqual(serializer.validate_cto_capacity(16), 16)
        with self.assertRaises(serializers.ValidationError):
            serializer.validate_cto_capacity(12)

class MapV077ToolbarRegressionTests(SimpleTestCase):
    def test_enlaces_shortcut_is_neutralized_for_both_toolbar_generations(self):
        source = (ROOT / "static/js/map-v077.js").read_text(encoding="utf-8")
        styles = (ROOT / "static/css/map-v077.css").read_text(encoding="utf-8")
        self.assertIn("[data-v072-links]", source)
        self.assertIn("[data-v0722-links]", source)
        self.assertIn("[data-v0722-links]", styles)
        self.assertIn("display: none !important", styles)

