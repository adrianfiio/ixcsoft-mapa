from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MapUiV0721StaticTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = Path(settings.BASE_DIR)

    def test_hotfix_loaded_after_v072(self):
        template = (self.base / "templates" / "map.html").read_text(encoding="utf-8")
        self.assertIn("map-ui-v0721.css", template)
        self.assertIn("map-ui-v0721.js", template)
        self.assertLess(template.index("map-ui-v072.js"), template.index("map-ui-v0721.js"))

    def test_toolbar_has_modes_and_box_submenu(self):
        script = (self.base / "static" / "js" / "map-ui-v0721.js").read_text(encoding="utf-8")
        self.assertIn('data-v0721-mode="view"', script)
        self.assertIn('data-v0721-mode="edit"', script)
        self.assertIn('data-v0721-tool="cto"', script)
        self.assertIn('data-v0721-tool="splice_box"', script)
        self.assertIn('data-v0721-tool="cdo"', script)

    def test_sidebar_collapse_is_width_safe(self):
        css = (self.base / "static" / "css" / "map-ui-v0721.css").read_text(encoding="utf-8")
        self.assertIn("map-sidebar-master.map-sidebar-v072.v072-collapsed", css)
        self.assertIn("grid-template-columns: 72px", css)
        self.assertIn("max-width: 72px !important", css)

    def test_routes_and_search_are_contextual(self):
        script = (self.base / "static" / "js" / "map-ui-v0721.js").read_text(encoding="utf-8")
        self.assertIn("Ainda não existe uma rota óptica conectada", script)
        self.assertIn("map-search-shell-v0721", script)
        self.assertIn("drawer.classList.remove(\"collapsed\")", script)

    def test_popup_is_normalized_once(self):
        script = (self.base / "static" / "js" / "map-ui-v0721.js").read_text(encoding="utf-8")
        self.assertIn("map-popup-hud-v0721", script)
        self.assertIn("uiV0721Signature", script)
        self.assertIn("addFallbackActions", script)
