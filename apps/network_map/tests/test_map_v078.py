from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.network_map.api.map_v078 import _splitter_loss
from apps.network_map.api.route_exports_v078 import _safe_filename


ROOT = Path(__file__).resolve().parents[3]


class MapV078SourceContractTests(SimpleTestCase):
    """Regressões de contrato visual/integração que não precisam de banco."""

    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_switch_and_router_port_layout_contract_is_explicit(self):
        source = self.read("static/js/map-v078.js")
        self.assertIn("if (total <= 16) return total;", source)
        self.assertIn("if (total === 24) return 12;", source)
        self.assertIn("if (total === 48) return 24;", source)
        self.assertIn('.master-canvas-node[data-equipment-type="router"]', source)

    def test_router_physical_grid_overrides_legacy_12_column_runtime(self):
        source = self.read("static/js/map-v078.js")
        css = self.read("static/css/map-v078.css")
        legacy_js = self.read("static/js/map-rack-physical-v07542.js")
        legacy_css = self.read("static/css/map-rack-physical-v07542.css")

        # O runtime físico antigo realmente converte Router/Switch para este
        # grid e o CSS legado fixa 12 colunas. O v0.78 precisa reconhecer e
        # vencer EXATAMENTE esse renderer, não apenas o renderer do Switch.
        self.assertIn('grid.className = "v07542-switch-grid";', legacy_js)
        self.assertIn('grid-template-columns: repeat(12, minmax(28px, 1fr));', legacy_css)
        self.assertIn("12 PORTAS POR LINHA", legacy_css)
        self.assertIn(
            '".v07552-switch-ports, .v07542-switch-grid, :scope > .master-node-ports"',
            source,
        )
        self.assertIn('node.dataset.v078LayoutLabel = layoutLabel;', source)
        self.assertIn("inspectPortLayout", source)
        self.assertIn(
            '.v078-network-device .v07542-switch-grid.v078-port-grid {',
            css,
        )
        self.assertIn(
            'grid-template-columns: repeat(var(--v078-port-columns), minmax(0, 1fr)) !important;',
            css,
        )
        self.assertIn('min-width: 0 !important;', css)
        self.assertIn('content: attr(data-v078-layout-label) !important;', css)

    def test_reserve_render_does_not_reference_removed_editing_variable(self):
        source = self.read("static/js/map-editor.js")
        start_marker = (
            'if (!window.mapV092 || window.mapV092.areReservesVisible()) '
            '(p.reservas || []).forEach((reserve) => {'
        )
        end_marker = '            line.getLayers().forEach('
        self.assertIn(start_marker, source)
        reserve_tail = source.split(start_marker, 1)[1]
        self.assertIn(end_marker, reserve_tail)
        reserve_block = reserve_tail.split(end_marker, 1)[0]

        # `editing` é uma variável legítima no bloco de NetworkElement,
        # onde é declarada dentro de elements.features.forEach. O bug v0.78
        # era específico das reservas, renderizadas depois no loop de cabos,
        # fora daquele escopo. O contrato abaixo valida somente esse bloco.
        self.assertNotIn("draggable: editing,", reserve_block)
        self.assertNotIn('${editing ?', reserve_block)
        self.assertNotIn('if (editing) marker.on("dragend", () => {', reserve_block)
        self.assertIn(
            'draggable: canEdit && state.mapMode === "edit",',
            reserve_block,
        )
        self.assertIn(
            '${canEdit && state.mapMode === "edit" ?',
            reserve_block,
        )
        self.assertIn(
            'if (canEdit && state.mapMode === "edit") marker.on("dragend", () => {',
            reserve_block,
        )

        # Evita reintroduzir o falso positivo que motivou a revisão r1.
        self.assertIn(
            'const editing = canEdit && state.mapMode === "edit";',
            source,
        )
        self.assertIn(
            'if (editing) marker.on("dragend", async () => {',
            source,
        )

    def test_firewall_is_not_offered_in_new_rack_or_tower_add_ui(self):
        source = self.read("static/js/map-v0758-core-ui.js")
        self.assertNotIn('["firewall", "Firewall", "Segurança e borda"]', source)
        self.assertNotIn('new Set(["olt", "dio", "switch", "router", "firewall"])', source)
        self.assertNotIn('new Set(["dio", "switch", "router", "firewall", "access_point"', source)

    def test_tower_can_be_assigned_to_route_from_context_menu(self):
        source = self.read("static/js/map-v0758-core-ui.js")
        self.assertIn('["cto", "splice_box", "tower"].includes', source)
        backend = self.read("apps/network_map/api/optical_editor_v3.py")
        self.assertIn("NetworkElement.ElementType.TOWER", backend)

    def test_yaml_typed_import_accepts_router_ap_and_ptp(self):
        parser = self.read("apps/network_map/device_type_yaml_v07551.py")
        ui = self.read("static/js/container-device-type.js")
        api = self.read("apps/network_map/api/map_v07551.py")
        self.assertIn('"access_point"', parser)
        self.assertIn('"ptp"', parser)
        self.assertIn('"access_point"', ui)
        self.assertIn('"ptp"', ui)
        self.assertIn("ContainerEquipment.EquipmentType.ACCESS_POINT", api)
        self.assertIn("ContainerEquipment.EquipmentType.PTP", api)

    def test_legacy_optical_workspace_delegates_to_v078_bidirectional_trace(self):
        source = self.read("apps/network_map/api/views.py")
        self.assertIn("_trace_fiber_v078", source)
        self.assertIn("_trace_splitter_port_v078", source)
        self.assertIn("return _trace_fiber_v078(fiber, visited)", source)

    def test_release_metadata_is_map_v078(self):
        versions = self.read("VERSIONS.md")
        compose = self.read("docker-compose.yml")
        changelog = self.read("CHANGELOG_MAP.md")
        self.assertIn("| Mapa | v0.78.0 |", versions)
        self.assertIn("MAP_VERSION: ${MAP_VERSION:-0.78.0}", compose)
        self.assertTrue(changelog.startswith("## MAP v0.78.0"))

    def test_route_exports_are_registered(self):
        urls = self.read("apps/network_map/api/urls.py")
        self.assertIn('v078/routes/<int:route_id>/export.kmz', urls)
        self.assertIn('v078/routes/<int:route_id>/diagram.html', urls)

    def test_offline_html_export_has_no_external_script_or_stylesheet_dependency(self):
        source = self.read("apps/network_map/api/route_exports_v078.py")
        self.assertNotIn('<script src=', source)
        self.assertNotIn('<link rel="stylesheet"', source)
        self.assertIn("diagrama interativo offline", source)


class MapV078OpticalLossTests(SimpleTestCase):
    def port(self, ratio, number):
        return SimpleNamespace(splitter=SimpleNamespace(ratio=ratio), number=number)

    def test_balanced_splitter_reference_loss(self):
        self.assertEqual(_splitter_loss(self.port("1:8", 1)), 10.5)
        self.assertEqual(_splitter_loss(self.port("1:16", 7)), 13.5)

    def test_unbalanced_splitter_uses_loss_by_output_leg(self):
        self.assertEqual(_splitter_loss(self.port("10:90", 1)), 11.2)
        self.assertEqual(_splitter_loss(self.port("10:90", 2)), 0.8)
        self.assertEqual(_splitter_loss(self.port("40:60", 1)), 4.7)
        self.assertEqual(_splitter_loss(self.port("40:60", 2)), 2.7)

    def test_unknown_splitter_does_not_invent_loss(self):
        self.assertEqual(_splitter_loss(self.port("1:128", 1)), 0.0)


class MapV078ExportHelperTests(SimpleTestCase):
    def test_safe_filename(self):
        self.assertEqual(_safe_filename("Rota 03 / Centro", "rota"), "Rota-03-Centro")
        self.assertEqual(_safe_filename("***", "rota-9"), "rota-9")
