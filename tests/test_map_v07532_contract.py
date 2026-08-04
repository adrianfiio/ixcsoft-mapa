from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07532ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.32")', self.read("config/settings.py"))
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.32}', self.read("docker-compose.yml"))
        self.assertIn("| Mapa | v0.75.32 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.32 |", self.read("VERSIONS.md"))

    def test_optical_canvas_has_disposable_sessions(self):
        suite = self.read("static/js/map-cto-suite.js")
        for needle in (
            "MAP_V07532_OPTICAL_BOX_SESSION",
            "function dispose()",
            "function createSession(content, elementId)",
            "function isActive(session)",
            "function listen(session, target, type, handler, options)",
            "window.mapCtoSuite = Object.freeze({ render, dispose });",
        ):
            self.assertIn(needle, suite)

    def test_redraw_never_reads_global_connection_style(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertNotIn('document.getElementById("connection-style").value', suite)
        self.assertIn('content.querySelector("#connection-style")?.value', suite)
        self.assertIn("if (!ensureActive()) return;", suite)

    def test_zoom_and_tools_are_scoped_to_current_canvas(self):
        suite = self.read("static/js/map-cto-suite.js")
        self.assertIn('content.querySelector("#unifilar-zoom-value")', suite)
        self.assertIn('content.querySelector("#unifilar-zoom-out")', suite)
        self.assertIn('content.querySelector("#cto-tools-menu-v07523")', suite)
        self.assertNotIn('const styleSelect = document.getElementById("connection-style")', suite)

    def test_shell_cancels_stale_fetches_and_disposes_on_close(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("let opticalBoxRenderGeneration = 0;", core)
        self.assertIn("const generation = ++opticalBoxRenderGeneration;", core)
        self.assertIn("generation === opticalBoxRenderGeneration", core)
        self.assertIn("window.mapCtoSuite?.dispose?.();", core)
        self.assertIn('opticalBoxContainerDialog.addEventListener("close"', core)

    def test_cto_widget_separates_service_ports_from_fusions(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn("port.access_point_id", core)
        self.assertIn("atendimentos · ${fusedOutputs}/${opticalOutputs.length} saídas fusionadas", core)
        self.assertNotIn("portas (clientes/DROPs)", core)

    def test_loading_and_error_state_live_inside_canvas(self):
        core = self.read("static/js/map-v0758-core-ui.js")
        css = self.read("static/css/map-v0758-core-ui.css")
        self.assertIn("optical-box-canvas-state-v07532", core)
        self.assertIn("MAP_V07532_OPTICAL_BOX_SESSION", css)

    def test_no_migrations(self):
        self.assertIn("Sem migrations", self.read("docs/releases/map/map-v0.75.32.md"))


if __name__ == "__main__":
    unittest.main()
