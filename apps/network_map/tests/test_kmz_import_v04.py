import io
import unittest

from apps.network_map.kmz_import import KMZAnalyzer, kml_color_to_hex
from apps.network_map.kmz_topology import build_topology_plan, preview_token


KML = b'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <Style id="black"><LineStyle><color>ff000000</color><width>4</width></LineStyle></Style>
  <Style id="green"><LineStyle><color>ff00ff00</color><width>4</width></LineStyle></Style>
  <Folder><name>ROTA 01</name>
    <Placemark id="p1"><name>CTO-01</name><Point><coordinates>-51.0,-23.0</coordinates></Point></Placemark>
    <Placemark id="p2"><name>CTO-02</name><Point><coordinates>-50.999,-23.0</coordinates></Point></Placemark>
    <Placemark id="p3"><name>CDO-01</name><Point><coordinates>-50.9995,-23.0</coordinates></Point></Placemark>
    <Placemark id="rt"><name>RT 30 m</name><Point><coordinates>-50.9994,-23.00002</coordinates></Point></Placemark>
  </Folder>
  <Folder><name>CABOS</name>
    <Placemark id="l1"><name>Drop 01 fo</name><styleUrl>#black</styleUrl><LineString><coordinates>-51.0,-23.0 -50.999,-23.0</coordinates></LineString></Placemark>
    <Placemark id="l2"><name>24 FO 100 m</name><styleUrl>#green</styleUrl><LineString><coordinates>-51.0,-23.001 -50.999,-23.001</coordinates></LineString></Placemark>
  </Folder>
</Document></kml>'''


class Upload(io.BytesIO):
    name = "fixture.kml"


class KMZImportV04Tests(unittest.TestCase):
    def analysis(self):
        return KMZAnalyzer.from_upload(Upload(KML)).analyze("fixture.kml")

    def test_kml_color_is_aabbggrr(self):
        self.assertEqual(kml_color_to_hex("ff00ff00")["hex"], "#00ff00")
        self.assertEqual(kml_color_to_hex("ffff0000")["hex"], "#0000ff")

    def test_drop_is_separate_and_one_fiber(self):
        analysis = self.analysis()
        drop = next(group for group in analysis["line_groups"] if group["profile"] == "drop")
        self.assertEqual(drop["default_action"], "cable")
        self.assertEqual(drop["suggested_fibers"], 1)
        self.assertEqual(drop["suggested_cable_type"], "drop")

    def test_point_aliases_and_dynamic_hints(self):
        analysis = self.analysis()
        points = {point["source_id"]: point for point in analysis["points"]}
        self.assertEqual(points["p1"]["suggested_type"], "cto")
        self.assertEqual(points["p3"]["suggested_type"], "splice_box")
        self.assertEqual(points["p3"]["subtype_hint"], "cdo")
        self.assertEqual(points["rt"]["suggested_type"], "technical_reserve")
        self.assertEqual(points["rt"]["length_hint_m"], 30.0)

    def test_topology_splits_at_cdo(self):
        analysis = self.analysis()
        decisions = {
            "routes": ["ROTA 01"],
            "line_groups": {},
            "line_items": {},
            "point_groups": {},
            "point_items": {},
            "topology": {"proximity_m": 15, "endpoint_tolerance_m": 15},
            "topology_defaults": {"cto": "cut", "splice_box": "cut", "other": "pass"},
            "junctions": {},
        }
        for group in analysis["line_groups"]:
            decisions["line_groups"][group["key"]] = {
                "action": "cable",
                "fiber_count": group["suggested_fibers"] or 24,
                "cable_type": group["suggested_cable_type"],
            }
        for group in analysis["point_groups"]:
            target = group["suggested_type"]
            decisions["point_groups"][group["key"]] = {
                "type": target,
                "capacity": 16,
                "subtype": group.get("subtype_hint") or "ceo",
                "length_m": group.get("length_hint_m") or 20,
            }
        plan = build_topology_plan(analysis, decisions)
        drop_segments = [item for item in plan["cables"] if item["source_id"] == "l1"]
        self.assertGreaterEqual(len(drop_segments), 2)
        self.assertTrue(any(item["destination_name"] == "CDO-01" for item in drop_segments))
        self.assertTrue(any(item["origin_name"] == "CDO-01" for item in drop_segments))

    def test_preview_token_changes_with_decisions(self):
        first = preview_token("abc", {"line_groups": {"x": {"action": "cable"}}})
        second = preview_token("abc", {"line_groups": {"x": {"action": "ignore"}}})
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
