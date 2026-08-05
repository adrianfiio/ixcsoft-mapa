import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def content(path):
    return (ROOT / path).read_text(encoding="utf-8")

class MapV07545RollingContractTests(unittest.TestCase):
    def test_current_runtime_replaces_v07544_asset(self):
        template = content("templates/map.html")
        self.assertIn("map-rack-chassis-v07545.js", template)
        self.assertIn("map-rack-chassis-v07545.css", template)
        self.assertNotIn("map-rack-hardware-v07544.js", template)

    def test_current_backend_keeps_old_module_and_adds_chassis_api(self):
        urls = content("apps/network_map/api/urls.py")
        self.assertIn("map_v07544", urls)
        self.assertIn("equipment_collection_v07545", urls)
        self.assertIn("olt_chassis_v07545", urls)

    def test_current_version(self):
        settings = content("config/settings.py")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.46")', settings)

if __name__ == "__main__":
    unittest.main(verbosity=2)
