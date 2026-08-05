import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07540ContractTests(unittest.TestCase):
    def test_v07538_generated_controls_use_matching_dataset_versions(self):
        runtime = content("static/js/map-dio-fusion-v07538.js")
        self.assertIn('summary.dataset.rackCableSummaryV07538 = "1";', runtime)
        self.assertIn('target.dataset.dioCableTargetV07538 = String(id);', runtime)
        self.assertIn('button.dataset.openDioFusionsV07538 = String(id);', runtime)
        self.assertNotIn('summary.dataset.rackCableSummaryV07537 = "1";', runtime)
        self.assertNotIn('target.dataset.dioCableTargetV07537 = String(id);', runtime)
        self.assertNotIn('button.dataset.openDioFusionsV07537 = String(id);', runtime)

    def test_physical_rack_module_is_loaded_after_v07539(self):
        template = content("templates/map.html")
        old_index = template.index("map-v07539-suite.js")
        new_index = template.index("map-rack-physical-v07542.js")
        self.assertLess(old_index, new_index)
        self.assertIn("map-rack-physical-v07542.css", template)

    def test_rack_is_mounted_by_units_and_locked(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        for token in ("buildAssignments", "explicitRackUnit", "height_units", "rack_unit", "v07540-drag-locked", "lockDrag"):
            self.assertIn(token, runtime)
        for token in ("v07540-rack-frame", "v07540-rack-units", "v07540-rack-mounted", "cursor: default"):
            self.assertIn(token, css)

    def test_side_ducts_and_rear_spine_exist(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        css = content("static/css/map-rack-physical-v07542.css")
        self.assertIn("v07540-duct left", runtime)
        self.assertIn("v07540-duct right", runtime)
        self.assertIn("TRASEIRA · CABOS EXTERNOS", runtime)
        self.assertIn("v07540-rear-spine", css)

    def test_front_links_start_at_exact_port_elements_and_use_ducts(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("centerInCanvas", runtime)
        self.assertIn(".master-node-port[data-link-id]", runtime)
        self.assertIn("drawFrontLinks", runtime)
        self.assertIn("H ${ductX} V ${end.y} H ${end.x}", runtime)
        self.assertIn("v07540-port-dot", runtime)

    def test_external_cable_uses_one_rear_trunk_per_cable(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("drawRearCableTrunks", runtime)
        self.assertIn("const targets = new Map()", runtime)
        self.assertIn("data-cable-id", runtime)
        self.assertIn("v07540-rear-trunk", runtime)
        self.assertIn("v07540-rear-branch", runtime)

    def test_duplicate_cables_and_controls_are_removed(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        for token in ("normalizeGeneratedControls", "uniqueCableNodes", "node.dataset.v07540DuplicateCable", "rows.slice(1).forEach"):
            self.assertIn(token, runtime)
        self.assertIn("[data-rack-cable-summary-v07538], [data-rack-cable-summary-v07537]", runtime)
        self.assertIn("[data-dio-cable-target-v07538], [data-dio-cable-target-v07537]", runtime)

    def test_tower_keeps_free_layout_but_gets_duplicate_cleanup(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertIn('if (kind === "rack") applyPhysicalRack(root, data, normalizedCableNodes);', runtime)
        self.assertIn("else resetPhysicalMode(root);", runtime)
        self.assertIn("const normalizedCableNodes = uniqueCableNodes(root);", runtime)
        self.assertIn("dataset?.containerType", runtime)
        enhance = runtime.split("function enhance(eventData = null)", 1)[1]
        self.assertLess(enhance.index("normalizeGeneratedControls(root)"), enhance.index("detectKind(data, root)"))

    def test_no_mutation_observer_or_new_backend(self):
        runtime = content("static/js/map-rack-physical-v07542.js")
        self.assertNotIn("MutationObserver", runtime)
        self.assertNotIn("setInterval", runtime)
        self.assertFalse((ROOT / "apps/network_map/api/map_v07540.py").exists())
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07540*")))

    def test_version_is_current(self):
        settings = content("config/settings.py")
        compose = content("docker-compose.yml")
        versions = content("VERSIONS.md")
        release = content("docs/releases/map/map-v0.75.45.md")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.45")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.45}', compose)
        self.assertIn("Mapa | v0.75.45", versions)
        self.assertIn("MAP v0.75.45", release)


if __name__ == "__main__":
    unittest.main(verbosity=2)
