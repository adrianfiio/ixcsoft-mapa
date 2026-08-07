import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07558ContractTests(unittest.TestCase):
    def test_dio_port_renders_as_single_unit_with_nested_dot(self):
        # MAP_V07558_DIO_SINGLE_PORT: 1 <button> só (quadrado = fusão,
        # data-port-role="rear") com uma <i> aninhada (bolinha = OLT/PON,
        # data-port-role="front") — não mais 2 <button> irmãos.
        js = content("static/js/map-master-suite.js")
        start = js.index("function renderDioPortPairV07510")
        end = js.index("function renderDioTraysV07510", start)
        block = js[start:end]
        self.assertIn('class="master-node-port v07558-dio-unit', block)
        self.assertIn('data-port-role="rear"', block)
        self.assertIn('<i class="v07558-dio-dot"', block)
        self.assertIn('data-port-role="front"', block)
        # a bolinha vem DENTRO do <button>, não como elemento irmão
        dot_index = block.index('<i class="v07558-dio-dot"')
        button_close_index = block.index("</button>")
        self.assertLess(dot_index, button_close_index)

    def test_port_click_stops_propagation_so_dot_does_not_also_fire_square(self):
        js = content("static/js/map-master-suite.js")
        self.assertIn(
            'qsa("[data-port-id]", nodes).forEach((button) => button.onclick = (event) => { event.stopPropagation(); selectContainerPort(button); });',
            js,
        )

    def test_capture_handler_resolves_nearest_port_target_not_ancestor(self):
        # Antes o seletor exigia link-id preenchido já no closest(), o que
        # fazia um clique na bolinha livre "vazar" pro link do quadrado
        # ancestral quando o quadrado tinha fusão feita. Agora acha o
        # elemento mais próximo (bolinha ou quadrado) e só depois confere
        # o link-id DELE, não do ancestral.
        js = content("static/js/map-v07539-suite.js")
        self.assertIn(
            'const dioButton = event.target.closest(\'.master-canvas-node[data-equipment-type="dio"] [data-port-id]\');',
            js,
        )
        self.assertIn(
            'if (dioButton && qs("#container-dialog")?.open && dioButton.dataset.linkId) {',
            js,
        )

    def test_group_dio_cavities_appends_unit_directly_no_pair_wrapper(self):
        js = content("static/js/map-v07539-suite.js")
        start = js.index("function groupDioCavities")
        end = js.index("function enhanceDio", start)
        block = js[start:end]
        self.assertIn('const unit = qs(`.master-node-port[data-port-id="${portId}"]`, node);', block)
        self.assertIn("if (unit) body.appendChild(unit);", block)
        self.assertNotIn("v07539-dio-pair", block)

    def test_enhance_dio_toggles_fusion_and_pon_independently(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        start = js.index("async function enhanceDio")
        end = js.index("node.dataset.dioEnhancedV07552 = ", start)
        block = js[start:end]
        self.assertIn('const unit = qs(`.v07558-dio-unit[data-port-id="${row.id}"]`, node);', block)
        self.assertIn('const dot = qs(`.v07558-dio-dot[data-port-id="${row.id}"]`, node);', block)
        self.assertIn('unit?.classList.toggle("is-fused-v07558", Boolean(row.rear));', block)
        self.assertIn('dot?.classList.toggle("is-pon-linked-v07558", Boolean(row.front));', block)

    def test_css_matches_the_exact_color_spec_from_user_mockup(self):
        # Quadrado vermelho/laranja = rua desconectada/fundida.
        # Bolinha preta/azul = OLT desconectada/conectada.
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("#map-master-container .v07558-dio-unit {", css)
        self.assertIn("border: 2px solid #e34f5f !important;", css)
        self.assertIn("#map-master-container .v07558-dio-unit.is-fused-v07558 {", css)
        self.assertIn("border-color: #ff8b1e !important;", css)
        self.assertIn("#map-master-container .v07558-dio-dot {", css)
        self.assertIn("background: #0a0d10 !important;", css)
        self.assertIn("#map-master-container .v07558-dio-dot.is-pon-linked-v07558 {", css)
        self.assertIn("background: #29b6ff !important;", css)
        # o número da porta some do visual, igual ao mockup (sem texto)
        self.assertIn("#map-master-container .v07558-dio-unit > span {\n    display: none !important;\n}", css)

    def test_dot_has_its_own_stacking_context_above_the_squares_hit_overlay(self):
        # map-v07512-links-ptp.css aplica .master-port-hit-v07512
        # genericamente a qualquer [data-port-id] (bolinha e quadrado
        # inclusive) — essa classe dá um ::before absolute com z-index:4
        # pro QUADRADO ampliar sua área de clique. Sem a bolinha virar seu
        # próprio contexto de posicionamento com z-index maior, aquele
        # ::before do quadrado ficava por cima da bolinha inteira (mesmo
        # ela vindo depois no DOM), e todo clique nela caía no quadrado
        # por baixo — confirmado ao vivo: clicar na bolinha abria "Desligar
        # traseira" em vez de "Desligar frente".
        css = content("static/css/map-rack-runtime-v07552.css")
        start = css.index("#map-master-container .v07558-dio-dot {")
        end = css.index("}", start)
        block = css[start:end]
        self.assertIn("position: relative !important;", block)
        self.assertIn("z-index: 5 !important;", block)

    def test_no_leftover_dead_pair_selector_in_any_dio_css(self):
        for path in (
            "static/css/map-rack-runtime-v07552.css",
            "static/css/map-rack-maintenance-v07549.css",
            "static/css/map-v07539-suite.css",
        ):
            self.assertNotIn(".v07539-dio-pair", content(path))

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.58")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.58", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
