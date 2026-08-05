import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07538ContractTests(unittest.TestCase):
    def test_distribution_boxes_draw_side_divider_and_two_sides(self):
        renderer = content("static/js/optical/optical-renderer.js")
        self.assertIn("drawDistributionDivider", renderer)
        self.assertIn('fillText("ENTRADA"', renderer)
        self.assertIn('fillText("SAÍDA"', renderer)
        self.assertIn('return { x: side === "left" ? 64 : 866, y };', renderer)

    def test_distribution_box_vertical_cables_can_render_from_both_sides(self):
        renderer = content("static/js/optical/optical-renderer.js")
        self.assertIn('const rightSide = side === "right";', renderer)
        self.assertIn('const endpointX = rightSide ? node.x : node.x + metrics.width;', renderer)
        self.assertIn('const relation = cable.requires_cut ? "passagem · cortar" : cable.relation_action === "pass" ? "passagem" : side === "left" ? "entrada" : "saída";', renderer)

    def test_new_dio_runtime_uses_left_anchor_and_smooth_drag(self):
        runtime = content("static/js/map-dio-fusion-v07538.js")
        css = content("static/css/map-dio-fusion-v07538.css")
        template = content("templates/map.html")
        self.assertIn("scheduleDragLine", runtime)
        self.assertIn('fusion-matrix-v07537', runtime)
        self.assertIn('data-rack-cable-anchor-v07538', runtime)
        self.assertIn('grid-template-columns: 32px minmax(0, 1fr);', css)
        self.assertIn('map-dio-fusion-v07538.js', template)
        self.assertIn('map-dio-fusion-v07538.css', template)

    def test_olt_has_expand_button(self):
        runtime = content("static/js/map-dio-fusion-v07538.js")
        css = content("static/css/map-dio-fusion-v07538.css")
        self.assertIn('data-olt-width-v07538', runtime)
        self.assertIn('is-wide-v07538', runtime)
        self.assertIn('map-olt-width-v07538', css)

    def test_optical_workspace_mentions_5m_and_current_version(self):
        workspace = content("static/js/optical/optical-workspace.js")
        settings = content("config/settings.py")
        versions = content("VERSIONS.md")
        release = content("docs/releases/map/map-v0.75.38.md")
        self.assertIn('captura máxima 5 m', workspace)
        self.assertIn('version: "0.75.38"', workspace)
        self.assertIn('0.75.38', settings)
        self.assertIn('v0.75.38', versions)
        self.assertIn('MAP v0.75.38', release)

    def test_no_browser_popups(self):
        runtime = content("static/js/map-dio-fusion-v07538.js")
        workspace = content("static/js/optical/optical-workspace.js")
        for forbidden in ("window.alert(", "window.prompt(", "window.confirm(", "global.alert(", "global.prompt(", "global.confirm("):
            self.assertNotIn(forbidden, runtime)
            self.assertNotIn(forbidden, workspace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
