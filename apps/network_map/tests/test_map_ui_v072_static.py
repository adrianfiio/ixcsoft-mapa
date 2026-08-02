from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MapUiV072StaticTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = Path(settings.BASE_DIR)

    def test_map_template_loads_new_ui_last(self):
        template = (self.base / "templates" / "map.html").read_text(encoding="utf-8")
        self.assertIn("map-ui-v072.css", template)
        self.assertIn("map-ui-v072.js", template)
        self.assertNotIn("container-structure-v09.js", template)
        self.assertLess(template.index("map-link-monitoring.js"), template.index("map-ui-v072.js"))

    def test_map_uses_company_whitelabel_logo(self):
        template = (self.base / "templates" / "map.html").read_text(encoding="utf-8")
        self.assertIn("current_company.logo", template)
        self.assertIn("--map-brand-accent", template)
        self.assertIn("data-company-name", template)

    def test_ruler_can_create_real_cable(self):
        script = (self.base / "static" / "js" / "map-ui-v072.js").read_text(encoding="utf-8")
        self.assertIn("/api/map/cables/create/", script)
        self.assertIn("Transformar em cabo", script)
        self.assertIn("coordinates: state.ruler.points", script)
        self.assertIn("Exportar GeoJSON", script)
        self.assertIn("function areaSquareMeters", script)

    def test_legacy_route_and_container_interfaces_are_hidden(self):
        stylesheet = (self.base / "static" / "css" / "map-ui-v072.css").read_text(encoding="utf-8")
        self.assertIn("#route-filter-v092", stylesheet)
        self.assertIn(".container-tabs-v09", stylesheet)
        self.assertIn("#map-master-container", stylesheet)

    def test_alert_context_includes_company_owned_monitoring_events(self):
        source = (self.base / "apps" / "core" / "context_processors.py").read_text(encoding="utf-8")
        self.assertIn("Q(company_id=company.id)", source)
        self.assertIn("if current_company and not current_company.is_designer", source)
