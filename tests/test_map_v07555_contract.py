import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07555ContractTests(unittest.TestCase):
    def test_pan_blocklist_no_longer_matches_the_outer_container_dialog(self):
        v07552 = content("static/js/map-rack-maintenance-v07552.js")
        v07546 = content("static/js/map-rack-viewport-v07546.js")
        pan_block_552 = v07552[v07552.index("target.closest(["):v07552.index("].join(\",\")));", v07552.index("target.closest(["))]
        pan_block_546 = v07546[v07546.index("target.closest(["):v07546.index("].join(\",\")));", v07546.index("target.closest(["))]
        self.assertNotIn('"dialog"', pan_block_552)
        self.assertNotIn('"dialog"', pan_block_546)
        self.assertIn('"button"', pan_block_552)
        self.assertIn('"button"', pan_block_546)

    def test_panning_cursor_css_matches_the_real_class_the_js_toggles(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        css = content("static/css/map-rack-maintenance-v07549.css")
        self.assertIn('classList.add("v07552-is-panning")', js)
        self.assertIn(".master-canvas-scroll.v07552-is-panning", css)

    def test_structure_backdrop_lives_beside_the_empty_card_not_inside_the_transformed_canvas(self):
        js = content("static/js/map-v0750-tower-workspace.js")
        start = js.index("function ensureStructureBackdrop")
        end = js.index("function nodeAction", start)
        block = js[start:end]
        self.assertIn('qs(".master-canvas-scroll", root)', block)
        self.assertIn("scroll.prepend(backdrop)", block)
        self.assertNotIn("canvas.prepend(backdrop)", block)

    def test_v07549_alignment_hack_no_longer_repositions_backdrop_or_card(self):
        css = content("static/css/map-rack-maintenance-v07549.css")
        self.assertNotIn("top: 52%", css)
        self.assertNotIn("top: 43%", css)
        # tamanho/estilo do backdrop maior do Rack continuam mantidos
        self.assertIn("width: min(680px, 72vw) !important", css)

    def test_equipment_create_dialog_awaits_bootstrap_before_reading_it(self):
        js = content("static/js/map-master-suite.js")
        start = js.index("async function openEquipmentCreateDialog")
        end = js.index("function equipmentEditorDialog", start)
        block = js[start:end]
        self.assertIn("if (!state.bootstrap) await refreshBootstrap();", block)
        self.assertIn("openEquipmentCreateDialog().catch(", js)

    def test_server_removed_from_rack_menus_and_olt_removed_from_tower_menus(self):
        core_ui = content("static/js/map-v0758-core-ui.js")
        master_suite = content("static/js/map-master-suite.js")
        self.assertNotIn('"server"', core_ui)
        tower_line_start = core_ui.index("towerAllowed = new Set")
        tower_line_end = core_ui.index("\n", tower_line_start)
        self.assertNotIn('"olt"', core_ui[tower_line_start:tower_line_end])
        dialog_block = master_suite[master_suite.index("async function openEquipmentCreateDialog"):master_suite.index("const types = (state.bootstrap")]
        self.assertNotIn('"server"', dialog_block)
        # "olt" só pode aparecer no ramo do rack (1x) — nunca no ramo da torre
        self.assertEqual(dialog_block.count('"olt"'), 1)

    def test_empty_state_buttons_are_rewritten_for_both_rack_and_tower(self):
        js = content("static/js/map-v0758-core-ui.js")
        start = js.index("if (empty) {")
        end = js.index("const rackAllowed", start)
        block = js[start:end]
        self.assertIn('identity.type === "rack"', block)
        self.assertIn("Adicionar OLT", block)
        self.assertIn("Adicionar PTO", block)
        self.assertIn("Adicionar Switch", block)

    def test_version_is_current_and_platform_untouched(self):
        settings = content("config/settings.py")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.61")', settings)
        self.assertIn('"0.83.1"', settings)
        self.assertIn("v0.75.61", content("VERSIONS.md"))

    def test_no_new_migration(self):
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
