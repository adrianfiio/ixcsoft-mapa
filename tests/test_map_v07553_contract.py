import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07553ContractTests(unittest.TestCase):
    """MAP v0.75.53 — o Rack fechado nunca deve continuar controlando o
    isRack() de outro editor (CTO/CDO/CEO isolados, Torre, ou outro Rack).

    Este é o mesmo estilo de teste "de contrato" usado desde a v0.75.34:
    asserções estruturais sobre o texto-fonte dos arquivos, porque este
    ambiente não tem navegador/Playwright disponível para rodar um teste
    de interação real. Não substitui validação visual real."""

    def test_rack_dialog_close_resets_physical_mode_marker(self):
        js = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("function teardownRackModeOnClose", js)
        self.assertIn('qs("#container-dialog")?.addEventListener("close", teardownRackModeOnClose)', js)
        teardown_start = js.index("function teardownRackModeOnClose")
        teardown_end = js.index("function init()", teardown_start)
        teardown = js[teardown_start:teardown_end]
        self.assertIn("resetPhysicalMode(root)", teardown)
        self.assertIn('delete dialog.dataset.containerType', teardown)
        self.assertIn('delete dialog.dataset.elementType', teardown)
        self.assertIn('state.currentKind = "unknown"', teardown)
        self.assertIn("state.enhanceGeneration += 1", teardown)

    def test_is_rack_family_all_check_the_same_persistent_markers(self):
        # Confirma que o fix em um único lugar (onde a classe é criada)
        # cobre todo runtime carregado que reimplementa isRack() — cada um
        # deles prioriza exatamente esses dois marcadores.
        for path in (
            "static/js/map-rack-viewport-v07546.js",
            "static/js/map-rack-ux-v07547.js",
            "static/js/map-rack-integrity-v07548.js",
            "static/js/map-rack-maintenance-v07552.js",
        ):
            js = content(path)
            self.assertIn('root.classList.contains("v07542-physical-rack")', js)

    def test_empty_cto_splitters_no_longer_crashes_on_index_zero(self):
        js = content("static/js/map-editor.js")
        self.assertIn("Array.isArray(element.cto.splitters)", js)
        self.assertNotIn("const splitter = element.cto.splitters[0];", js)

    def test_optical_hydrate_normalizes_backend_payload_shape(self):
        js = content("static/js/optical/optical-state.js")
        self.assertIn("function normalizeOptical", js)
        self.assertIn("function normalizeCableState", js)
        self.assertIn("session.optical = normalizeOptical(payload.optical);", js)
        self.assertIn("session.cableState = normalizeCableState(payload.cableState);", js)
        self.assertIn("Array.isArray(source.cables) ? source.cables : []", js)

    def test_isolated_optical_workspace_still_never_touches_rack_dom(self):
        # A garantia de isolamento da v0.75.34 continua valendo depois do
        # hotfix — o workspace óptico não passou a depender de
        # #container-dialog/#map-master-container.
        js = content("static/js/optical/optical-workspace.js")
        self.assertNotIn("container-dialog", js)
        self.assertNotIn("map-master-container", js)
        self.assertIn("document.body.appendChild(root)", js)

    def test_v07552_switch_single_row_behaviour_is_unchanged(self):
        js = content("static/js/map-rack-switch-v07552.js")
        css = content("static/css/map-rack-runtime-v07552.css")
        self.assertIn("[8, 12, 16].includes(data.ports.length)", js)
        self.assertIn('holder.classList.add("is-single-row")', js)
        self.assertIn("repeat(var(--port-count)", css)

    def test_v07552_pan_left_button_behaviour_is_unchanged(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        self.assertIn("event.button !== 0", js)
        self.assertIn("Math.hypot(dx, dy) < 5", js)

    def test_v07552_uplink_single_top_section_is_unchanged(self):
        js = content("static/js/map-rack-maintenance-v07552.js")
        self.assertIn("/api/map/v07552/elements/", js)
        self.assertIn("face.insertBefore(bank, serviceSlots)", js)

    def test_v07552_equipment_swap_is_unchanged(self):
        js = content("static/js/map-rack-physical-v07542.js")
        self.assertIn("function swapCandidate", js)
        self.assertIn("is-swap-target-v07552", js)

    def test_v07552_dio_pairs_are_unchanged(self):
        # MAP_V07558_DIO_SINGLE_PORT: substituiu o par de elementos por 1
        # elemento só — ver test_map_v07558_contract.py pro desenho novo.
        js = content("static/js/map-rack-maintenance-v07552.js")
        self.assertIn("async function enhanceDio(node, generation)", js)
        self.assertIn("dot?.classList.toggle", js)

    def test_version_is_current_and_platform_untouched(self):
        settings = content("config/settings.py")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.76.0")', settings)
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.85.0"))', settings)
        self.assertIn("v0.76.0", content("VERSIONS.md"))
        self.assertIn("MAP v0.75.53", content("docs/releases/map/map-v0.75.53.md"))

    def test_no_new_migration_was_added(self):
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        before = {"0001_initial.py"}  # marca mínima de que o diretório é o certo
        names = {path.name for path in migrations_dir.glob("*.py")}
        self.assertTrue(before.issubset(names))
        self.assertFalse(any("07553" in name for name in names))


if __name__ == "__main__":
    unittest.main(verbosity=2)
