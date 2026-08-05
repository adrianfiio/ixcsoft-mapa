import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07543ContractTests(unittest.TestCase):
    def test_rack_canvas_has_background_pan(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        css = content("static/css/map-rack-hardware-v07544.css")
        self.assertIn("function installNavigation", runtime)
        self.assertIn("translate(${view.tx}px", runtime)
        self.assertIn("worldX", runtime)
        self.assertIn("v07544-navigation-enabled", css)
        self.assertIn("is-panning-v07544", css)

    def test_old_routing_is_replaced_by_organizer_routing(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        css = content("static/css/map-rack-hardware-v07544.css")
        self.assertIn("organizerForPort", runtime)
        self.assertIn("startOrganizer.y", runtime)
        self.assertIn("endOrganizer.y", runtime)
        self.assertIn('.v07542-rack-links', css)
        self.assertIn("display: none", css)

    def test_every_dio_cavity_receives_an_organizer(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn('qsa(".v07539-dio-cavity", node).forEach', runtime)
        self.assertIn("cavity.after(organizer)", runtime)
        self.assertIn("ORGANIZADOR ÓPTICO · CAVIDADE", runtime)

    def test_olt_has_separate_uplink_panel(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        css = content("static/css/map-rack-hardware-v07544.css")
        self.assertIn("renderOltFace", runtime)
        self.assertIn("v07544-service-stack", runtime)
        self.assertIn("v07544-uplink-stack", runtime)
        self.assertIn("UPLINKS", runtime)
        self.assertIn("grid-template-columns: minmax(0, 1.65fr) minmax(210px, .75fr)", css)

    def test_uplink_editor_supports_rj45_sfp_and_sfp_plus(self):
        backend = content("apps/network_map/api/map_v07543.py")
        runtime = content("static/js/map-rack-hardware-v07544.js")
        for token in ("rj45_1g", "sfp_1g", "sfp_plus_10g"):
            self.assertIn(token, backend)
        self.assertIn("openUplinkConfiguration", runtime)
        self.assertIn("replace_uplink_groups", runtime)
        self.assertIn("Desligue o uplink antes de alterar", backend)

    def test_service_cards_have_model_and_technology_editor(self):
        backend = content("apps/network_map/api/map_v07543.py")
        runtime = content("static/js/map-rack-hardware-v07544.js")
        for token in ("gpon", "xgpon", "xgspon"):
            self.assertIn(token, backend)
        self.assertIn("openCardEditor", runtime)
        self.assertIn("save_card", runtime)
        self.assertIn("openCardEditor", runtime)

    def test_toolbar_removes_redundant_link_buttons(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        self.assertIn("hideRedundantToolbarActions", runtime)
        self.assertIn('label === "ligar portas"', runtime)
        self.assertIn('label === "editar linhas"', runtime)
        self.assertIn("data-container-lines", runtime)

    def test_backend_is_scoped_and_has_no_migration(self):
        backend = content("apps/network_map/api/map_v07543.py")
        self.assertIn("scope_company_queryset", backend)
        self.assertIn("can_edit_company", backend)
        self.assertIn("transaction.atomic", backend)
        self.assertFalse(any((ROOT / "apps/network_map/migrations").glob("*07543*")))

    def test_urls_template_and_version_are_current(self):
        urls = content("apps/network_map/api/urls.py")
        template = content("templates/map.html")
        self.assertIn("olt_hardware_v07543", urls)
        self.assertIn("olt-hardware-v07543", urls)
        self.assertIn("map-rack-hardware-v07544.js", template)
        self.assertIn("map-rack-hardware-v07544.css", template)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.46")', content("config/settings.py"))
        self.assertIn("Mapa | v0.75.46", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.46", content("docs/releases/map/map-v0.75.46.md"))

    def test_no_native_browser_popup(self):
        runtime = content("static/js/map-rack-hardware-v07544.js")
        for forbidden in (
            "window.alert(", "window.prompt(", "window.confirm(",
            "global.alert(", "global.prompt(", "global.confirm(",
        ):
            self.assertNotIn(forbidden, runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
