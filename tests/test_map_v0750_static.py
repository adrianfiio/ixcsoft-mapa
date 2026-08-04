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
        self.assertEqual(template.count("{{ map_version }}-tower-r17"), 5)

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
        self.assertIn('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.82.0"))', settings)
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.29")', settings)
        self.assertIn('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.82.0}', compose)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.29}', compose)

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

    def test_tower_r11_canvas_fibers_actions_and_icons(self):
        canvas = content("static/js/map-master-suite.js")
        tower = content("static/js/map-v0750-tower-workspace.js")
        view = content("static/js/map-v0741-ui.js")
        editor = content("static/js/map-editor.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        for token in ("data-node-delete", "setPointerCapture", "line-mode-active"):
            self.assertIn(token, canvas)
        self.assertIn("state.tx = origin.tx + moveEvent.clientX - origin.x", view)
        self.assertIn("fiber-focus-v0756", tower)
        self.assertIn('{ x: 20, y: 20 + index * 260 }', editor)
        for token in ('symbols = {', 'pto:', 'tower:', 'reserve-marker'):
            self.assertIn(token, editor)
        self.assertIn('#map-master-container.line-mode-active', css)

    def test_map_v0756_cables_fibers_and_dio_paging(self):
        backend = content("apps/network_map/api/views.py")
        canvas = content("static/js/map-master-suite.js")
        tower = content("static/js/map-v0750-tower-workspace.js")
        view = content("static/js/map-v0741-ui.js")
        editor = content("static/js/map-editor.js")
        css = content("static/css/map-v0750-tower-workspace.css")
        release = content("docs/releases/map/map-v0.75.6.md")

        for token in ('"relation": "input" if cable.destination_id == container.id else "output"', '"cable_fiber_id": link.cable_fiber_id', "dio_capacity > 24"):
            self.assertIn(token, backend)
        for token in ("cablePositions", "selectedFiber", "master-cable-node", "data-cable-fiber", "data-dio-page", "selectCableFiber", "fiberAnchor", "installCableDrag", "const cables = (state.container.data?.cables || []).map"):
            self.assertIn(token, canvas)
        self.assertIn('.master-canvas-node, .master-cable-node', view)
        self.assertIn("fiber-focus-v0756", tower)
        self.assertIn("unifiedEditor", editor)
        for token in ("MAP_V0756_CABLE_CARDS", ".master-cable-node", ".master-cable-fiber", ".master-dio-page"):
            self.assertIn(token, css)
        self.assertIn("MAP v0.75.6", release)

    def test_map_v0758_single_runtime_duplicate_resolver_and_workspaces(self):
        backend = content("apps/network_map/api/views.py")
        editor = content("static/js/map-editor.js")
        canvas = content("static/js/map-master-suite.js")
        view = content("static/js/map-v0741-ui.js")
        workspace = content("static/js/map-v0750-tower-workspace.js")
        runtime = content("static/js/map-v0758-core-ui.js")
        css = content("static/css/map-v0758-core-ui.css")
        template = content("templates/map.html")
        release = content("docs/releases/map/map-v0.75.8.md")

        rack_block = backend.split("if container.element_type == NetworkElement.ElementType.RACK", 1)[0].rsplit("{", 1)[-1]
        self.assertNotIn("EquipmentType.ONU", rack_block)
        self.assertIn("EquipmentType.SERVER", rack_block)
        self.assertIn('"duplicate": True', backend)
        self.assertIn("select_for_update", backend)
        for token in ("elementSubmitLock", "reviewCableDirection", "Salvar nova posição?", "map-v0758-optical-workspace", "openElementMenu", "elementDuplicateKey"):
            self.assertIn(token, editor)
        # v0.75.9 removeu o dedup silencioso por nome/coordenada.
        self.assertNotIn("canonicalElementFeatures", editor)
        for token in ("containerCanvasMidpoint", "side-right-v0758", "syncCableVisualSide", "allowed.has(value)", 'if (type === "server") return "Servidores";'):
            self.assertIn(token, canvas)
        self.assertIn(".master-canvas-note", view)
        self.assertIn('const VERSION = "0.75.10"', workspace)
        for token in ("editLongText", "confirmAction", "reviewCableDirection", "updateContainerIdentity", "openDuplicateResolver"):
            self.assertIn(token, runtime)
        self.assertNotIn("MutationObserver", runtime)
        self.assertNotIn("/api/map/", runtime)
        for token in ("MAP_V0758_CORE_UI", "map-v0758-optical-workspace", "white-space: pre-wrap", "tower-workspace-close-v0758", "map-v0758-duplicate-dialog"):
            self.assertIn(token, css)
        self.assertIn("map-v0758-core-ui.js", template)
        self.assertIn("map-v0758-core-ui.css", template)
        self.assertNotIn("map-v0757-field-usability", template)
        self.assertIn("MAP v0.75.8", release)

    def test_map_v0759_single_flow_no_duplicate_render(self):
        editor = content("static/js/map-editor.js")
        canvas = content("static/js/map-master-suite.js")
        view = content("static/js/map-v074-ui.js")
        runtime = content("static/js/map-v0758-core-ui.js")
        template = content("templates/map.html")
        release = content("docs/releases/map/map-v0.75.9.md")

        # map-v0757-field-usability continua ausente (não reintroduzido).
        self.assertNotIn("map-v0757-field-usability", template)
        self.assertNotIn("map-v0757-field-usability", editor)
        self.assertNotIn("map-v0757-field-usability", canvas)

        # Nenhum runtime paralelo novo foi criado — só os arquivos já
        # existentes (map-editor.js, map-master-suite.js, map-v074-ui.js,
        # map-v0758-core-ui.js, map-v0750-tower-workspace.js) foram tocados.
        self.assertNotIn("map-v0759", template)

        # Fluxo único de abertura de Rack/Torre: uma função pública só,
        # chamada direto pelo marker — não mais o manageContainer legado
        # como primeiro passo.
        self.assertIn("function openContainerWorkspace(id)", editor)
        self.assertIn("async function openContainerWorkspace(id)", canvas)
        self.assertIn("? openContainerWorkspace(p.id)", editor)
        self.assertIn("openContainerWorkspace,", canvas)

        # MutationObserver não dispara mais carregamento de dado do
        # container — o observer específico do #container-dialog (que
        # reagia a mudança de "open"/"data-element-id" chamando
        # enhanceContainer/loadContainerMaster) foi removido.
        self.assertNotIn('attributeFilter: ["open", "data-element-id"]', canvas)

        # Guarda de geração contra resposta atrasada.
        self.assertIn("openGeneration", canvas)
        self.assertIn("generation !== state.container.openGeneration", canvas)

        # Registro central de markers por ID real — nunca dedup por
        # nome/tipo/coordenada na hora de desenhar.
        self.assertIn("elementMarkers", editor)
        self.assertIn("seenElementIds", editor)
        self.assertNotIn("canonicalElementFeatures", editor)

        # contextmenu do marker corta a propagação ANTES de qualquer
        # checagem de modo de edição/disponibilidade do menu (nunca deixa
        # o clique vazar pro menu global mesmo no caminho de erro).
        stop_index = editor.index("event.originalEvent.stopImmediatePropagation")
        guard_index = editor.index("if (!editing || !unifiedEditor || !window.mapV0758?.openElementMenu) return;")
        self.assertLess(stop_index, guard_index)

        # Segunda camada: o menu global ignora o marker Leaflet.
        self.assertIn(".leaflet-marker-icon", view)
        self.assertIn(".leaflet-interactive", view)
        self.assertIn("[data-element-id]", view)

        # window.mapV0758 nunca fica undefined por um erro de inicialização
        # tardio no arquivo.
        self.assertIn("window.mapV0758 = window.mapV0758 || {};", runtime)
        self.assertIn("Object.assign(window.mapV0758,", runtime)
        self.assertNotIn("window.mapV0758 = {\n        VERSION,", runtime)

        self.assertIn("MAP v0.75.9", release)
        self.assertIn("67077444659639bec037a56632c95a611fe566a8", release)


if __name__ == "__main__":
    unittest.main(verbosity=2)
