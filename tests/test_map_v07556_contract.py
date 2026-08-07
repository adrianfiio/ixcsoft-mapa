import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07556ContractTests(unittest.TestCase):
    def test_rack_equipment_priority_no_longer_favors_olt(self):
        js = content("static/js/map-rack-physical-v07542.js")
        start = js.index("function priority(")
        end = js.index("function rangeIsFree", start)
        priority_block = js[start:end]
        self.assertNotIn("olt: 1", priority_block)
        self.assertNotIn('{ olt:', priority_block)
        self.assertIn("return 20;", priority_block)
        # ordem de criação (a.id - b.id) continua sendo o desempate real
        self.assertIn("priority(a) - priority(b) || a.id - b.id", js)

    def test_rack_drag_swap_still_intact(self):
        js = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("function swapCandidate", js)
        self.assertIn("is-swap-target-v07552", js)

    def test_dio_front_dot_reflects_pon_state_not_connector(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        start = js.index("async function enhanceDio")
        end = js.index("// ------", start)
        block = js[start:end]
        self.assertIn('front?.classList.toggle("is-pon-linked-v07556", Boolean(row.front));', block)

        css = content("static/css/map-rack-maintenance-v07549.css")
        self.assertIn(".v07549-dio-front > i { background: #e34f5f !important;", css)
        self.assertIn(".v07549-dio-front.is-pon-linked-v07556 > i { background: #19d18a !important;", css)
        # a bolinha da frente não segue mais a cor do conector diretamente
        self.assertNotIn(".is-sc-apc > i", css)
        self.assertNotIn(".is-sc-upc > i", css)
        # a borda por conector continua intacta
        self.assertIn(".v07549-dio-front.is-sc-apc { border-color: #2acb8c !important; }", css)
        self.assertIn(".v07549-dio-front.is-sc-upc { border-color: #27a9ff !important; }", css)
        # o lado de trás (fusão) não foi tocado
        self.assertIn("rear-free-v07549", css)
        self.assertIn("has-rear-v07549", css)

    def test_cable_left_click_no_longer_opens_a_popup(self):
        js = content("static/js/map-editor.js")
        start = js.index("MAP_V07556_CABLE_CONTEXT_MENU: clique esquerdo")
        end = js.index("line.addTo(cableLayer);", start)
        block = js[start:end]
        self.assertNotIn("line.bindPopup(", block)
        self.assertIn('line.bindTooltip(escapeHtml(p.nome)', block)
        self.assertIn('line.on("click"', block)
        self.assertIn('line.on("contextmenu"', block)
        self.assertIn("openCableContextMenu(p, event, editing);", block)

    def test_cable_context_menu_keeps_every_old_action_plus_edit_route(self):
        js = content("static/js/map-editor.js")
        start = js.index("function openCableContextMenu")
        end = js.index("document.getElementById(\"collapse-sidebar\")", start)
        block = js[start:end]
        for action in ("route", "edit", "reserve", "insert", "delete"):
            self.assertIn(f'data-cable-action="{action}"', block)
        self.assertIn("startGeometryEdit(p.id)", block)
        self.assertIn("editCable(p.id)", block)
        self.assertIn("deleteCable(p.id)", block)

    def test_start_geometry_edit_accepts_direct_cable_id_and_is_dashed(self):
        js = content("static/js/map-editor.js")
        start = js.index("async function startGeometryEdit")
        end = js.index("state.geometryHandles = coordinates.map", start)
        block = js[start:end]
        self.assertIn("async function startGeometryEdit(cableId)", js)
        self.assertIn("if (cableId != null) state.editingCableId = cableId;", block)
        self.assertIn('dashArray: "10 6"', block)
        # chamada antiga (botão dentro do diálogo) continua sem argumento
        self.assertIn("startGeometryEdit().catch(", js)

    def test_optical_cut_api_and_ui_wired(self):
        api_js = content("static/js/optical/optical-api.js")
        self.assertIn("cutCable(elementId, cableId, signal)", api_js)
        self.assertIn("/cables/${cableId}/cut/", api_js)

        workspace_js = content("static/js/optical/optical-workspace.js")
        self.assertIn('data-action="cut-passing-cable"', workspace_js)
        self.assertIn("async function cutPassingCable(session, cableId)", workspace_js)
        self.assertIn('if (action === "cut-passing-cable")', workspace_js)
        self.assertIn("cableHit?.type === \"cable\"", workspace_js)
        self.assertIn("cable?.requires_cut", workspace_js)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.56")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.56", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
