from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MonitoringPackageStaticTests(SimpleTestCase):
    def test_map_assets_are_loaded(self):
        template = (Path(settings.BASE_DIR) / "templates" / "map.html").read_text(encoding="utf-8")
        self.assertIn("map-link-monitoring.css", template)
        self.assertIn("map-link-monitoring.js", template)

    def test_monitoring_urls_are_registered(self):
        urls = (Path(settings.BASE_DIR) / "config" / "urls.py").read_text(encoding="utf-8")
        self.assertIn('path("api/monitoring/", include("apps.snmp_monitoring.urls"))', urls)

    def test_web_container_does_not_receive_docker_socket(self):
        compose = (Path(settings.BASE_DIR) / "docker-compose.yml").read_text(encoding="utf-8")
        web_part = compose.split("  worker:", 1)[0]
        self.assertNotIn("/var/run/docker.sock", web_part)

    def test_no_influx_token_is_hardcoded(self):
        settings_text = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text(encoding="utf-8")
        self.assertIn('os.getenv("INFLUXDB_TOKEN", "")', settings_text)
