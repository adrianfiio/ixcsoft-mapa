from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07519ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.19")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.19}', compose)
        self.assertIn("| Mapa | v0.75.19 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.19 |", self.read("VERSIONS.md"))

    def test_ptp_status_both_sides(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07519_PTP_STATUS_BOTH_SIDES", runtime)
        self.assertIn("function ptpLinkForPort", runtime)
        self.assertIn("await refreshPtpLayer().catch(() => {});", runtime)

    def test_ptp_distance(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07519_PTP_DISTANCE", runtime)
        self.assertIn("function distanceKm", runtime)
        self.assertIn("function formatDistanceKm", runtime)
        self.assertIn("ptp-distance-v07519", runtime)

    def test_ptp_port_status_color(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07519_PTP_PORT_STATUS", css)
        self.assertIn('[data-v07512-ptp-status="free"]', css)
        self.assertIn('[data-v07512-ptp-status="linked"]', css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.19.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
