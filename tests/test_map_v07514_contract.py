from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07514ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.14")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.14}', compose)
        self.assertIn("| Mapa | v0.75.14 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.14 |", self.read("VERSIONS.md"))

    def test_handle_small_visual_big_hitbox(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07514_HANDLE_HITBOX", runtime)
        self.assertIn('circle.setAttribute("r", "6")', runtime)
        self.assertIn('hit.setAttribute("r", "14")', runtime)
        self.assertIn("master-link-handle-hit-v07514", runtime)

    def test_ptp_default_wireless_port_and_alert(self):
        backend = self.read("apps/network_map/api/views.py")
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07514_PTP_DEFAULT_WIRELESS_PORT", backend)
        self.assertIn("ContainerEquipment.EquipmentType.PTP,", backend)
        self.assertIn("ContainerEquipment.EquipmentType.ACCESS_POINT,", backend)
        self.assertIn("MAP_V07514_PTP_NO_CANDIDATES_ALERT", runtime)

    def test_dio_orientation_swapped(self):
        canvas = self.read("static/js/map-master-suite.js")
        css = self.read("static/css/map-v0750-tower-workspace.css")
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        self.assertIn("MAP_V07514_DIO_ORIENTATION", canvas)
        self.assertIn('class="master-node-port left dio-front', canvas)
        self.assertIn('class="master-node-port right dio-rear', canvas)
        self.assertIn(".master-node-port.dio-front { grid-column: 1; }", css)
        self.assertIn(".master-node-port.dio-rear { grid-column: 2; }", css)
        self.assertIn("MAP_V07514_DIO_ORIENTATION", runtime)
        self.assertIn("approachFromRight", runtime)

    def test_fusion_canvas_visual_update(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("MAP_V07514_FUSION_CANVAS_VISUAL", css)
        self.assertIn(".fiber-cable-node {", css)
        self.assertIn(".graph-splitter-node {", css)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.14.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
