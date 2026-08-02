from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MapUiV0722StaticTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = Path(settings.BASE_DIR)
        cls.template = (cls.base / "templates" / "map.html").read_text(encoding="utf-8")
        cls.script = (cls.base / "static" / "js" / "map-ui-v0722.js").read_text(encoding="utf-8")
        cls.styles = (cls.base / "static" / "css" / "map-ui-v0722.css").read_text(encoding="utf-8")

    def test_template_loads_only_latest_runtime_hotfix(self):
        self.assertIn("map-ui-v0722.css", self.template)
        self.assertIn("map-ui-v0722.js", self.template)
        self.assertNotIn("map-ui-v0721.css", self.template)
        self.assertNotIn("map-ui-v0721.js", self.template)
        self.assertLess(self.template.index("map-ui-v072.js"), self.template.index("map-ui-v0722.js"))

    def test_popup_runtime_has_no_mutation_observer_loop(self):
        self.assertNotIn("new MutationObserver", self.script)
        self.assertIn("const timers = [100, 420]", self.script)
        self.assertIn("content._uiV0722Identity", self.script)
        self.assertIn("content.dataset.uiV0722Signature", self.script)

    def test_popup_actions_keep_clean_labels_and_click_target(self):
        self.assertIn("button.replaceChildren(iconNode, document.createTextNode(label))", self.script)
        self.assertIn("pointer-events: none !important", self.styles)
        self.assertIn("map-popup-action-v0722", self.styles)

    def test_toolbar_has_grouped_boxes_and_cancel(self):
        self.assertIn("<span>Caixas</span>", self.script)
        self.assertIn('data-v0722-tool="cto"', self.script)
        self.assertIn('data-v0722-tool="splice_box"', self.script)
        self.assertIn('data-v0722-tool="cdo"', self.script)
        self.assertIn("data-v0722-cancel", self.script)
        self.assertIn("cancelActiveTool", self.script)

    def test_search_resets_legacy_absolute_transform(self):
        self.assertIn("#map-search-shell-v0722 #map-search.map-search-v0722", self.styles)
        self.assertIn("transform: none !important", self.styles)
        self.assertIn("position: static !important", self.styles)

    def test_routes_toggle_real_drawer_only(self):
        self.assertIn('qs(".route-master-item", drawer)', self.script)
        self.assertIn('drawer.classList.toggle("collapsed", currentlyOpen)', self.script)
