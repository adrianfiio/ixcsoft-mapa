from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07512ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions_and_assets(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        template = self.read("templates/map.html")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.12")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.12}', compose)
        self.assertIn("map-v07512-links-ptp.js", template)
        self.assertIn("map-v07512-links-ptp.css", template)
        self.assertEqual(template.count("{{ map_version }}-tower-r17"), 5)
        self.assertIn("| Mapa | v0.75.12 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.12 |", self.read("VERSIONS.md"))

    def test_ptp_api_has_no_migration_dependency(self):
        backend = self.read("apps/network_map/api/ptp_links.py")
        urls = self.read("apps/network_map/api/urls.py")
        for token in (
            "def ptp_links",
            "def ptp_link_candidates",
            "def ptp_link_detail",
            "ContainerPortLink.LinkType.WIRELESS",
            "Enlace PTP torre a torre",
        ):
            self.assertIn(token, backend)
        for token in ('path("ptp-links/"', 'path("ptp-links/candidates/"', 'path("ptp-links/<int:link_id>/"'):
            self.assertIn(token, urls)

    def test_drop_targets_and_connectors(self):
        backend = self.read("apps/network_map/api/views.py")
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        for token in (
            "DROP só pode terminar no fundo do DIO, em PTO ou porta PON de ONU/ONT",
            "Cabo alimentador/distribuição só pode ser fundido no fundo de uma porta DIO",
            "Fusão traseira no DIO",
            "termination_method",
            "method_labels",
            "dio_rear",
            "direct_connector",
            "SC/APC",
            "SC/UPC",
        ):
            self.assertIn(token, backend)
        for token in (
            "terminateDropDirectly",
            "selectContainerPort() continua recebendo qualquer fibra de cabo",
            "master-link-connector",
            "connectorKind",
        ):
            self.assertIn(token, runtime)
        canvas = self.read("static/js/map-master-suite.js")
        self.assertIn('if (button.dataset.portRole === "rear")', canvas)
        self.assertIn("cable_fiber_id: fiber.id", canvas)

    def test_olt_guides_tooltips_notes_and_routing(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        css = self.read("static/css/map-v07512-links-ptp.css")
        for token in (
            "master-olt-cable-guide-v07512",
            "linkedTargetForPort",
            "roundedPolyline",
            "beginNoteDrag",
            "nearestSegmentIndex",
            "refreshContainer",
        ):
            self.assertIn(token, runtime)
        for token in ("master-olt-board-v07512", "master-link-hit-v07512", "map-v07512-port-tooltip"):
            self.assertIn(token, css)

    def test_coordinate_search_and_marker_generation_guard(self):
        runtime = self.read("static/js/map-v07512-links-ptp.js")
        editor = self.read("static/js/map-editor.js")
        self.assertIn("parseCoordinates", runtime)
        self.assertIn("structureLoadGeneration", editor)
        self.assertNotIn("já tinha marker registrado nesta carga", editor)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.12.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
