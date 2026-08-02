import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV0750StaticTests(unittest.TestCase):
    def test_assets_are_loaded_with_map_version(self):
        template = content("templates/map.html")
        for asset in ("map-v0750-tower-workspace.css", "map-v0750-tower-workspace.js"):
            self.assertIn(f"{asset}' %}}?v={{{{ map_version }}}}", template)
        self.assertEqual(template.count("{{ map_version }}-tower-r9"), 5)

    def test_tower_workspace_fills_area_beside_sidebar_without_locking_it(self):
        css = content("static/css/map-v0750-tower-workspace.css")
        editor = content("static/js/map-editor.js")
        self.assertIn("#container-dialog.tower-workspace-dialog-v0750", css)
        self.assertIn("inset: 0 0 0 var(--v072-sidebar, 292px) !important", css)
        self.assertIn("#map-sidebar.v072-collapsed", css)
        self.assertIn("containerDialog.show()", editor)
        self.assertNotIn("containerDialog.showModal()", editor)

    def test_map_has_independent_label_and_client_visibility_controls(self):
        template = content("templates/map.html")
        editor = content("static/js/map-editor.js")
        css = content("static/css/map-editor.css")
        for token in ('data-layer-toggle="layer-labels"', 'data-layer-toggle="layer-clients"', 'id="layer-clients"'):
            self.assertIn(token, template)
        self.assertIn("clientsVisible", editor)
        self.assertIn("refreshMapLabels", editor)
        self.assertIn("map-labels-hidden", css)
        self.assertIn("map-client-visibility-toggle.active", css)

    def test_sidebar_does_not_duplicate_labels_and_created_link_stays_editable(self):
        template = content("templates/map.html")
        sidebar = content("static/js/map-v074-ui.js")
        canvas = content("static/js/map-master-suite.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        self.assertNotIn("nav.appendChild(labels)", sidebar)
        self.assertIn("selectCreatedLinkForEditing", canvas)
        self.assertIn("created.link?.id", canvas)
        self.assertIn("top: auto !important", css)
        self.assertIn("flex-direction: row !important", css)
        self.assertEqual(template.count("workspace-r4"), 1)

    def test_workspace_position_is_locked_and_always_closable(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("lockWorkspacePosition", "getBoundingClientRect().right", 'event.key !== "Escape"', "dialog.close()"):
            self.assertIn(token, runtime)
        self.assertIn("section > header", css)
        self.assertIn("position: sticky !important", css)

    def test_reopen_lines_version_forms_and_reports_are_polished(self):
        template = content("templates/map.html")
        tower = content("static/js/map-v0750-tower-workspace.js")
        canvas = content("static/js/map-master-suite.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        editor = content("static/js/map-editor.js")
        self.assertIn("map:container-opening", editor)
        self.assertIn("resetWorkspaceForOpen", tower)
        self.assertIn("data-edit-lines", tower)
        self.assertIn('qs("i", port)', canvas)
        self.assertIn("configureEquipmentEditorForType", canvas)
        self.assertIn("allowedPorts", canvas)
        self.assertIn('data-map-version="{{ map_version }}"', template)
        self.assertNotIn('class="map-version-badge"', template)
        self.assertIn("Ficha técnica fluida", css)
        self.assertIn("elimina aparência nativa", css)

    def test_tower_opens_directly_in_canvas(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for token in ("activateCanvas", 'data-tab="canvas"', "Canvas 2D da estrutura", "map:container-rendered"):
            self.assertIn(token, runtime)

    def test_required_toolbar_and_connections_exist(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for kind in ("dio", "pto", "access_point", "ptp", "switch", "router", "onu"):
            self.assertIn(f'data-quick-add="{kind}"', runtime)
        for action in ('data-connect-ports', 'data-open-panel="matrix"', "data-organize-canvas", "data-fit-canvas", "data-tower-menu"):
            self.assertIn(action, runtime)

    def test_tower_uses_compact_menus_and_bottom_left_zoom(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        zoom_runtime = content("static/js/map-v0741-ui.js")
        self.assertIn("tower-add-menu-v0750", runtime)
        self.assertIn("tower-tools-menu-v0750", runtime)
        self.assertIn("toggleToolbarMenu", runtime)
        self.assertIn('left: 12px !important;', css)
        self.assertIn('[data-canvas-zoom-fit] { display: none !important; }', css)
        self.assertIn('data-canvas-zoom-out', zoom_runtime)
        self.assertIn('data-canvas-zoom-in', zoom_runtime)
        self.assertIn('if (!event.ctrlKey) return;', zoom_runtime)

    def test_fullscreen_button_is_not_exposed_by_tower_toolbar(self):
        paths = (
            "static/js/map-v0750-tower-workspace.js",
            "static/js/map-fusion-polish.js",
            "static/js/map-master-suite.js",
            "static/js/map-optical-editor-v3.js",
        )
        for path in paths[1:]:
            runtime = content(path)
            for forbidden in ("requestFullscreen", "exitFullscreen", "document.fullscreenElement", "fullscreenchange"):
                self.assertNotIn(forbidden, runtime, f"{forbidden} ainda existe em {path}")
        tower = content(paths[0])
        self.assertNotIn('<button type="button" data-workspace-fullscreen>', tower)
        self.assertIn("document.exitFullscreen", tower)
        self.assertIn('addEventListener("cancel"', tower)

    def test_new_runtime_does_not_observe_own_rendering(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        self.assertNotIn("MutationObserver", runtime)
        self.assertIn("wrapFusionLoader", runtime)
        extension = content("static/js/container-device-type.js")
        self.assertNotIn("new MutationObserver", extension)
        self.assertIn("event.detail?.data", extension)
        self.assertNotIn('if (dialog.open) refreshExtensions()', extension)

    def test_fusion_and_canvas_have_no_visible_nested_scrollbars(self):
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("fusion-v0750", "scrollbar-width: none", ".master-canvas-scroll", "overflow: hidden !important", 'input[type="range"]'):
            self.assertIn(token, css)

    def test_yaml_import_is_bounded_and_has_clear_statuses(self):
        backend = content("apps/network_map/api/device_type_views.py")
        for token in ("MAX_IMPORTED_INTERFACES = 256", "validate_ipv46_address", "except IntegrityError", "status=409", "transaction.atomic", "full_clean"):
            self.assertIn(token, backend)
        for kind in ("ROUTER", "ACCESS_POINT", "PTP", "ONU", "PTO"):
            self.assertIn(f"EquipmentType.{kind}", backend)

    def test_connection_rules_are_preserved(self):
        backend = content("apps/network_map/api/views.py")
        for token in ("def container_port_links", "optical_ports", "RJ45 com RJ45", "wireless com wireless", "status=409", "termination_method"):
            self.assertIn(token, backend)

    def test_snmp_and_properties_are_available(self):
        runtime = content("static/js/map-v0750-tower-workspace.js")
        for token in ("openInspector", "data-inspector-snmp", "Ficha técnica", "Monitoramento"):
            self.assertIn(token, runtime)

    def test_versions_are_independent(self):
        settings = content("config/settings.py")
        compose = content("docker-compose.yml")
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.80.0"))', settings)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.4")', settings)
        self.assertIn('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.80.0}', compose)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.4}', compose)

    def test_tower_r7_has_contextual_creation_drop_and_fade(self):
        canvas = content("static/js/map-master-suite.js")
        backend = content("apps/network_map/api/views.py")
        css = content("static/css/map-v0750-tower-workspace.css")
        sidebar = content("static/js/map-ui-v072.js")
        for token in ('data-create-field="drop"', "configureEquipmentCreateForType", "drop_cable_id", "showEquipmentDialogWithFade"):
            self.assertIn(token, canvas)
        for token in ("DROP com conector direto na ONU / ONT", "source_port__equipment", "drop_cable_id"):
            self.assertIn(token, backend)
        self.assertIn("master-drop-entry", css)
        self.assertIn("towerEquipmentFadeIn", css)
        self.assertIn("map-version-menu-v072", sidebar)

    def test_new_links_are_clean_and_edit_mode_can_finish(self):
        canvas = content("static/js/map-master-suite.js")
        toolbar = content("static/js/map-v0750-tower-workspace.js")
        self.assertIn('state.container.layout.routes[String(linkId)] = [];', canvas)
        self.assertIn('"Concluir e salvar"', toolbar)
        self.assertIn('"Traçado concluído e salvo."', toolbar)

    def test_tower_r9_interactions_and_exports(self):
        canvas = content("static/js/map-master-suite.js")
        tower = content("static/js/map-v0750-tower-workspace.js")
        view = content("static/js/map-v0741-ui.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("master-node-edit", "data-drop-entry", "master-canvas-note", "exportContainerPdf", "Relatório de ligações"):
            self.assertIn(token, canvas)
        for token in ("Concluir ligação", "data-export-canvas=\"pdf\"", "tower-structure-list-v0750"):
            self.assertIn(token, tower)
        for token in ("buildContainerExportSvg", "data-edit-note", "data-port-role=\"rear\"", "Esta porta ${role} já está ligada"):
            self.assertIn(token, canvas)
        self.assertNotIn("<foreignObject", canvas)
        self.assertIn("event.button !== 1", view)
        self.assertIn("master-node-port.left i", css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
