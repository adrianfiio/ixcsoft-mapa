from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07511ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.11")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.11}', compose)

    def test_workspace_hotfix(self):
        css = self.read("static/css/map-v0758-core-ui.css")
        ui = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("MAP_V07511_EDITOR_CANVAS_NOTES", css)
        self.assertIn("position: absolute !important", css)
        self.assertIn("MAP_V07511_WORKSPACE_FIT", ui)
        self.assertIn("enforceWorkspaceFitV07511", ui)
        self.assertIn("ResizeObserver", ui)
        self.assertNotIn("MutationObserver", ui)
        template = self.read("templates/map.html")
        self.assertEqual(template.count("{{ map_version }}-tower-r16"), 5)

    def test_canvas_notes_and_cables(self):
        master = self.read("static/js/map-master-suite.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("noteStoreV07511", master)
        self.assertIn("installNoteDragV07511", master)
        self.assertIn("data-fiber-count", master)
        self.assertIn("--cable-accent", master)
        self.assertIn("master-v07511-note-dialog", css)

    def test_release(self):
        release = self.read("docs/releases/map/map-v0.75.11.md")
        self.assertIn("Sem migrations", release)
        self.assertIn("Canvas de Rack/Torre não colapsa mais", release)


if __name__ == "__main__":
    unittest.main()
