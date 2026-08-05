import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07542ContractTests(unittest.TestCase):
    def test_closest_bug_is_removed(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("root.contains(target)", runtime)
        self.assertNotIn("closest(root)", runtime)
        self.assertIn("target instanceof Element", runtime)

    def test_equipment_can_move_with_snap_in_u(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        for token in (
            "startRackDrag",
            "updateDragPreview",
            "rackUnitFromPointer",
            "findNearestAvailableUnit",
            "placementTop",
            "is-dragging-v07542",
        ):
            self.assertIn(token, runtime)
        self.assertNotIn('document.addEventListener("pointerdown", lockDrag', runtime)

    def test_collisions_are_resolved_instead_of_overlapping(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("rangeIsFree", runtime)
        self.assertIn("assignments.entries()", runtime)
        self.assertIn("findNearestAvailableUnit(row.preferredUnit", runtime)
        self.assertNotIn("for (let current = safeStart; current < safeStart + row.heightUnits", runtime)

    def test_measurement_happens_after_rack_width(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("prepareEquipmentMeasurement", runtime)
        self.assertIn("row.node.style.width", runtime)
        self.assertIn("void row.node.offsetHeight", runtime)
        self.assertIn("row.node.scrollHeight", runtime)

    def test_positions_are_persisted(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("rack_units_v07542", runtime)
        self.assertIn("schedulePreferenceSave", runtime)
        self.assertIn("/api/map/v07539/elements/${elementId}/layout/", runtime)
        self.assertIn('method: "PATCH"', runtime)

    def test_auto_organize_is_available(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        self.assertIn("Auto organizar", runtime)
        self.assertIn("autoOrganizeRack", runtime)
        self.assertIn("v07542-rack-toolbar", css)

    def test_tower_is_not_forced_into_physical_rack(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('if (kind === "rack") await applyPhysicalRack', runtime)
        self.assertIn("else resetPhysicalMode(root)", runtime)
        self.assertIn("uniqueCableNodes(root)", runtime)

    def test_new_assets_replace_old_assets(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-physical-v07542.css", template)
        self.assertIn("map-rack-physical-v07542.js", template)
        self.assertNotIn("map-rack-physical-v07540.css", template)
        self.assertNotIn("map-rack-physical-v07540.js", template)

    def test_versions_are_current(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.46")', content("config/settings.py"))
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.46}', content("docker-compose.yml"))
        self.assertIn("Mapa | v0.75.46", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.46", content("docs/releases/map/map-v0.75.46.md"))

    def test_no_new_backend_or_native_popup(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        for forbidden in (
            "window.alert(", "window.prompt(", "window.confirm(",
            "global.alert(", "global.prompt(", "global.confirm(",
            "MutationObserver",
        ):
            self.assertNotIn(forbidden, runtime)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07541*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
