from django.test import SimpleTestCase

from apps.network_map.kmz_topology import build_topology_plan, detect_junctions


def _analysis(cable_type="distribution"):
    return {
        "points": [
            {
                "source_id": "ceo-1",
                "name": "CDO 05",
                "group_key": "alias_cdo",
                "folder": "PROJ / ROTA 05",
                "coordinates": [0.00005, 0.0],
            },
            {
                "source_id": "cto-1",
                "name": "05-8A",
                "group_key": "alias_cto",
                "folder": "PROJ / ROTA 05",
                "coordinates": [0.00007, 0.00001],
            },
        ],
        "lines": [
            {
                "source_id": "line-1",
                "name": "Cabo principal",
                "group_key": "green::fiber",
                "folder": "PROJ / CABOS",
                "coordinates": [[0.0, 0.0], [0.001, 0.0]],
                "cable_type_hint": cable_type,
            }
        ],
    }


def _decisions(cable_type="distribution"):
    return {
        "routes": ["PROJ / ROTA 05"],
        "point_groups": {
            "alias_cdo": {"type": "splice_box", "subtype": "cdo"},
            "alias_cto": {"type": "cto", "capacity": 16},
        },
        "point_items": {},
        "line_groups": {
            "green::fiber": {
                "action": "cable",
                "fiber_count": 12,
                "cable_type": cable_type,
            }
        },
        "line_items": {},
        "junctions": {},
        "topology": {
            "proximity_m": 30,
            "endpoint_tolerance_m": 4,
            "splice_box_proximity_m": 45,
            "priority_radius_m": 15,
        },
        "topology_defaults": {"cto": "cut", "splice_box": "cut"},
        "naming": {"project_prefix": "JDS", "preserve_source_names": True},
    }


class KMZTopologyPriorityTests(SimpleTestCase):
    def test_splice_box_suppresses_nearby_cto_on_trunk_cable(self):
        junctions = detect_junctions(
            _analysis(),
            _decisions(),
            proximity_m=30,
            endpoint_tolerance_m=4,
            splice_box_proximity_m=45,
            priority_radius_m=15,
        )
        by_point = {item["point_source_id"]: item for item in junctions}
        self.assertEqual(by_point["ceo-1"]["action"], "cut")
        self.assertEqual(by_point["cto-1"]["action"], "ignore")
        self.assertTrue(by_point["cto-1"]["priority_suppressed"])
        self.assertEqual(by_point["cto-1"]["priority_winner_id"], "ceo-1")

    def test_drop_still_connects_to_cto(self):
        analysis = _analysis(cable_type="drop")
        decisions = _decisions(cable_type="drop")
        junctions = detect_junctions(
            analysis,
            decisions,
            proximity_m=30,
            endpoint_tolerance_m=4,
            splice_box_proximity_m=45,
            priority_radius_m=15,
        )
        by_point = {item["point_source_id"]: item for item in junctions}
        self.assertNotEqual(by_point["cto-1"]["action"], "ignore")
        self.assertFalse(by_point["cto-1"]["priority_suppressed"])

    def test_manual_cto_override_wins_over_priority(self):
        decisions = _decisions()
        first = detect_junctions(
            _analysis(), decisions, 30, 4, 45, 15
        )
        cto = next(item for item in first if item["point_source_id"] == "cto-1")
        decisions["junctions"][cto["junction_id"]] = {"action": "branch"}
        second = detect_junctions(
            _analysis(), decisions, 30, 4, 45, 15
        )
        cto = next(item for item in second if item["point_source_id"] == "cto-1")
        self.assertEqual(cto["action"], "branch")
        self.assertTrue(cto["manual_override"])

    def test_build_plan_keeps_all_splice_box_cable_relations(self):
        analysis = _analysis()
        second_line = dict(analysis["lines"][0])
        second_line.update(
            source_id="line-2",
            name="Segundo cabo",
            coordinates=[[0.0, 0.00002], [0.001, 0.00002]],
        )
        analysis["lines"].append(second_line)
        plan = build_topology_plan(analysis, _decisions())
        ceo_relations = [
            item for item in plan["junctions"] if item["point_source_id"] == "ceo-1"
        ]
        self.assertEqual(len(ceo_relations), 2)
        self.assertTrue(all(item["action"] == "cut" for item in ceo_relations))
