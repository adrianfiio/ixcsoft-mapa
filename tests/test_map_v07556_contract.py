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
        # MAP_V07558_DIO_SINGLE_PORT: front virou a bolinha central de um
        # elemento único (não mais um quadrado próprio com borda por
        # conector) — a cor por conector foi removida junto, a pedido do
        # usuário; só sobrou preto/azul por estado de OLT/PON.
        js = content("static/js/map-rack-maintenance-v07552.js")
        start = js.index("async function enhanceDio")
        end = js.index("node.dataset.dioEnhancedV07552 = ", start)
        block = js[start:end]
        self.assertIn('dot?.classList.toggle("is-pon-linked-v07558", Boolean(row.front));', block)

        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("#map-master-container .v07558-dio-dot {", css)
        self.assertIn("background: #0a0d10 !important;", css)
        self.assertIn(".v07558-dio-dot.is-pon-linked-v07558 {", css)
        self.assertIn("background: #29b6ff !important;", css)
        # o lado de trás (fusão) continua num toggle independente
        self.assertIn('unit?.classList.toggle("is-fused-v07558", Boolean(row.rear));', block)

    def test_cable_left_click_no_longer_opens_a_popup(self):
        # MAP_V07557_CABLE_MENU_MERGE: o menu de botão direito próprio deste
        # arquivo foi removido (conflitava com o menu real, já existente em
        # map-v07539-suite.js, que sempre vencia visualmente) — ver
        # test_map_v07557_contract.py para o que ficou no lugar. Este teste
        # continua cobrindo só a parte que não mudou: clique esquerdo sem
        # popup, clique com ferramenta armada intacto.
        js = content("static/js/map-editor.js")
        start = js.index("MAP_V07556_CABLE_CONTEXT_MENU: clique esquerdo")
        end = js.index("line.addTo(cableLayer);", start)
        block = js[start:end]
        self.assertNotIn("line.bindPopup(", block)
        self.assertIn('line.bindTooltip(escapeHtml(p.nome)', block)
        self.assertIn('line.on("click"', block)

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
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.76.0")', content("config/settings.py"))
        self.assertIn('"0.85.0"', content("config/settings.py"))
        self.assertIn("v0.76.0", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
