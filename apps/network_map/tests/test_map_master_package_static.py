from pathlib import Path

from django.test import SimpleTestCase


class MapMasterStaticContractTests(SimpleTestCase):
    def test_master_javascript_is_loaded_after_legacy_editors(self):
        template = Path("templates/map.html")
        if not template.exists():
            self.skipTest("Template não disponível no diretório atual.")
        text = template.read_text(encoding="utf-8")
        self.assertIn("map-master-suite.js", text)
        self.assertGreater(text.index("map-master-suite.js"), text.index("map-optical-editor-v3.js"))

    def test_master_css_is_scoped(self):
        stylesheet = Path("static/css/map-master-suite.css")
        if not stylesheet.exists():
            self.skipTest("CSS não disponível no diretório atual.")
        text = stylesheet.read_text(encoding="utf-8")
        self.assertIn("body.map-master-suite", text)
        self.assertNotIn("body {", text)
