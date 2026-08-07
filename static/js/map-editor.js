(function () {
    "use strict";

    const hasEditAccess = document.body.dataset.canEdit === "true";
    let canEdit = hasEditAccess;
    const sidebar = document.getElementById("map-sidebar");
    const projectSelect = document.getElementById("project-select");
    const message = document.getElementById("editor-message");
    const projectDialog = document.getElementById("project-dialog");
    const elementDialog = document.getElementById("element-dialog");
    const cableDialog = document.getElementById("cable-dialog");
    const unifilarDialog = document.getElementById("unifilar-dialog");
    const poleDialog = document.getElementById("pole-dialog");
    const poleForm = document.getElementById("pole-form");
    const poleActionDialog = document.getElementById("pole-action-dialog");
    const poleActionForm = document.getElementById("pole-action-form");
    const containerDialog = document.getElementById("container-dialog");
    const containerEquipmentForm = document.getElementById("container-equipment-form");
    const containerLinkForm = document.getElementById("container-link-form");
    const containerCardForm = document.getElementById("container-card-form");
    const containerPortForm = document.getElementById("container-port-form");
    const quickInputDialog = document.getElementById("quick-input-dialog");
    const quickInputForm = document.getElementById("quick-input-form");
    const elementForm = document.getElementById("element-form");
    const cableForm = document.getElementById("cable-form");
    const drawingBar = document.getElementById("drawing-bar");
    const state = {
        projectId: null, projects: [], elements: [], cables: [], tool: null,
        cableCoordinates: [], drawingLine: null,
        cableOriginId: null, cableDestinationId: null, cableModels: new Map(),
        editingElementId: null, editingCableId: null,
        drawingExistingCableId: null,
        geometryCableId: null, geometryHandles: [], reserveCableId: null, insertCableId: null,
        lightSourceId: null, lastAnnouncedLightSourceId: undefined, lightAnimationGeneration: 0, mapMode: "view",
        containerId: null, editingContainerEquipmentId: null, topologyZoom: 1,
        openingElementId: null, elementSubmitLock: false, structureLoadGeneration: 0,
        // Controle central: 1 registro por ID real de NetworkElement, nunca
        // por nome/coordenada. Ver loadStructure().
        elementMarkers: new Map(),
    };

    const googleConfigElement = document.getElementById("google-maps-config");
    const googleConfig = googleConfigElement
        ? JSON.parse(googleConfigElement.textContent)
        : { enabled: false, defaultLayer: "esri_satellite" };
    const map = L.map("map", { preferCanvas: true, maxZoom: 23 }).setView([-24.45, -50.62], 10);
    // Essas barras flutuam dentro de #map (para ficar centralizadas na área do
    // mapa, não na tela toda) — sem isso, cliques nelas vazam para o mapa e
    // acionam a ferramenta de posicionar equipamento quando ela está ativa.
    document.querySelectorAll(".map-mode-control, #map-search, #drawing-bar, .map-group-control").forEach((element) => {
        L.DomEvent.disableClickPropagation(element);
        L.DomEvent.disableScrollPropagation(element);
    });
    const streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxNativeZoom: 19, maxZoom: 23, attribution: "&copy; OpenStreetMap",
    });
    const satelliteLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxNativeZoom: 18, maxZoom: 23, attribution: "Tiles &copy; Esri",
    });
    const hybridImageryLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxNativeZoom: 18, maxZoom: 23, attribution: "Tiles &copy; Esri",
    });
    const hybridLabelsLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
        maxNativeZoom: 18, maxZoom: 23, attribution: "Labels &copy; Esri",
        pane: "overlayPane",
    });
    const satelliteHybridLayer = L.layerGroup([hybridImageryLayer, hybridLabelsLayer]);
    const baseLayers = {
        "Satélite + nomes e ruas": satelliteHybridLayer,
        "Satélite limpo": satelliteLayer,
        "Mapa de ruas": streetLayer,
    };
    const baseLayerControl = L.control.layers(baseLayers, {}, { position: "topright" }).addTo(map);
    const configuredFallback = googleConfig.defaultLayer === "openstreetmap" ? streetLayer : satelliteHybridLayer;
    configuredFallback.addTo(map);

    async function enableGoogleSatellite() {
        if (!googleConfig.enabled) return;
        try {
            const response = await fetch("/api/map/base-map/google/session/", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(
                    data.detail
                    || data.error?.message
                    || `Google Map Tiles: HTTP ${response.status}`
                );
            }
            const session = await response.json();
            if (!session.session) throw new Error("O servidor não retornou uma sessão válida.");
            const googleLayer = L.tileLayer(
                `/api/map/base-map/google/tiles/{z}/{x}/{y}/?session=${encodeURIComponent(session.session)}`,
                {
                    maxNativeZoom: 22,
                    maxZoom: 22,
                    attribution: "&copy; Google",
                },
            );
            baseLayerControl.addBaseLayer(googleLayer, "Google Satélite");
            if (googleConfig.defaultLayer === "google_satellite") {
                map.removeLayer(configuredFallback);
                googleLayer.addTo(map);
            }
        } catch (error) {
            notify(`Google Satélite indisponível; usando mapa alternativo. ${error.message}`, true);
        }
    }

    const clientLayers = {
        online: L.markerClusterGroup({ chunkedLoading: true }),
        offline: L.markerClusterGroup({ chunkedLoading: true }),
        unknown: L.markerClusterGroup({ chunkedLoading: true }),
    };
    const clientPlainLayers = {
        online: L.layerGroup(),
        offline: L.layerGroup(),
        unknown: L.layerGroup(),
    };
    const cableLayer = L.layerGroup().addTo(map);
    // Estrutura separada por categoria (CTO / CEO / demais equipamentos) para
    // permitir camadas independentes no painel de Camadas e na barra inferior.
    const structureLayers = {
        cto: { cluster: L.markerClusterGroup({ chunkedLoading: true }), plain: L.layerGroup() },
        splice_box: { cluster: L.markerClusterGroup({ chunkedLoading: true }), plain: L.layerGroup() },
        other: { cluster: L.markerClusterGroup({ chunkedLoading: true }), plain: L.layerGroup() },
    };
    Object.values(structureLayers).forEach((pair) => pair.cluster.addTo(map));
    clientLayers.online.addTo(map);
    clientLayers.offline.addTo(map);

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }
    async function api(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({ error: "Resposta inválida do servidor." }));
        if (!response.ok) throw new Error(data.detail || data.error || Object.values(data.errors || {}).flat().join(" ") || `Erro HTTP ${response.status}`);
        return data;
    }
    function notify(text, isError = false) {
        message.textContent = text;
        message.classList.toggle("error", isError);
        const feedback = document.getElementById("unifilar-feedback");
        if (feedback && unifilarDialog.open) {
            feedback.textContent = text;
            feedback.classList.toggle("error", isError);
        }
    }
    function askValue({ title, label, value = "", type = "text", options = null }) {
        document.getElementById("quick-input-title").textContent = title;
        document.getElementById("quick-input-label").textContent = label;
        const input = document.getElementById("quick-input-value");
        const select = document.getElementById("quick-input-select");
        input.hidden = Boolean(options);
        select.hidden = !options;
        input.type = type;
        input.value = value;
        input.min = type === "number" ? "0.01" : "";
        input.step = type === "number" ? "0.01" : "";
        if (options) {
            select.innerHTML = options.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === value ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("");
        }
        quickInputDialog.showModal();
        if (!options) input.focus();
        return new Promise((resolve) => {
            let completed = false;
            quickInputForm.onsubmit = (event) => {
                event.preventDefault();
                completed = true;
                const result = options ? select.value : input.value;
                quickInputDialog.close();
                resolve(result);
            };
            quickInputDialog.onclose = () => {
                if (!completed) resolve(null);
            };
        });
    }
    enableGoogleSatellite();

    function escapeHtml(value) {
        const item = document.createElement("span");
        item.textContent = value == null ? "" : String(value);
        return item.innerHTML;
    }
    function elementDuplicateKey(feature) {
        const properties = feature?.properties || {};
        const coordinates = feature?.geometry?.coordinates || [];
        return [
            String(properties.tipo || ""),
            String(properties.nome || "").trim().toLocaleLowerCase("pt-BR"),
            Number(coordinates[0]).toFixed(7),
            Number(coordinates[1]).toFixed(7),
        ].join("|");
    }
    // v0.75.9: a função de dedup-por-nome/coordenada foi removida — ela
    // escondia do Canvas o NetworkElement de maior ID sempre que dois
    // registros tinham o mesmo tipo/nome/coordenada, mesmo quando esse ID
    // escondido era o que tinha equipamentos/layout de verdade.
    // elementDuplicateKey() continua existindo só pro resolvedor manual
    // (menu de botão direito → "Resolver duplicados"), que mostra os IDs
    // reais e deixa o usuário decidir.
    function offsetWithin(el, container) {
        let x = 0, y = 0, node = el;
        while (node && node !== container) {
            x += node.offsetLeft;
            y += node.offsetTop;
            node = node.offsetParent;
        }
        return { x, y };
    }
    function centerWithin(el, container) {
        const { x, y } = offsetWithin(el, container);
        const cableNode = el.closest?.("[data-cable-node-id]");
        if (cableNode) {
            const nodeX = parseFloat(cableNode.style.left) || 0;
            const middle = Math.max(container.scrollWidth, container.clientWidth, 900) / 2;
            const sideRight = nodeX + cableNode.offsetWidth / 2 >= middle;
            cableNode.classList.toggle("side-right-v0758", sideRight);
            cableNode.classList.toggle("side-left-v0758", !sideRight);
            return { x: sideRight ? x : x + el.offsetWidth, y: y + el.offsetHeight / 2 };
        }
        return { x: x + el.offsetWidth / 2, y: y + el.offsetHeight / 2 };
    }
    const BALANCED_SPLITTER_LOSS_DB = { "1:2": 3.6, "1:4": 7.2, "1:8": 10.5, "1:16": 13.8, "1:32": 17.1, "1:64": 20.5 };
    function splitterLossLabel(ratio) {
        if (BALANCED_SPLITTER_LOSS_DB[ratio] !== undefined) return `~${BALANCED_SPLITTER_LOSS_DB[ratio]}dB`;
        const [a, b] = ratio.split(":").map(Number);
        if (!a || !b) return "";
        const legLoss = (percent) => (-10 * Math.log10(percent / 100) + 0.3).toFixed(1);
        return `~${legLoss(a)}/${legLoss(b)}dB`;
    }
    function formatBudgetTooltip(budget) {
        if (!budget) return "";
        const route = (budget.path || []).map((item) => item.name).join(" → ") || "Caminho não identificado";
        const power = budget.budget_dbm !== null && budget.budget_dbm !== undefined
            ? `Potência estimada: ${budget.budget_dbm} dBm`
            : "Potência não calculada (informe a potência de saída da OLT).";
        return `${route}\nPerda acumulada: ${budget.loss_db} dB\n${power}`;
    }
    const ROUTE_NODE_LABELS = { olt: "OLT", dio: "D.I.O", splice_box: "Caixa", splitter: "Splitter" };
    const routeInfoDialog = document.createElement("dialog");
    routeInfoDialog.className = "editor-dialog route-info-dialog";
    routeInfoDialog.innerHTML = `<section>
        <header><div><h2>Informações de rota</h2><p class="help-text">Caminho calculado da OLT até esta ligação.</p></div><button class="dialog-close" type="button">×</button></header>
        <div class="route-diagram"></div>
        <div class="route-summary"></div>
        <footer>
            <button class="secondary-button" type="button" data-route-export>Exportar (Excel/CSV)</button>
            <button class="primary-button" type="button" data-route-print>Imprimir</button>
        </footer>
    </section>`;
    document.body.appendChild(routeInfoDialog);
    routeInfoDialog.querySelector(".dialog-close").onclick = () => routeInfoDialog.close();
    let currentRouteBudget = null;
    function openRouteInfoDialog(budget) {
        currentRouteBudget = budget;
        const diagram = routeInfoDialog.querySelector(".route-diagram");
        const summary = routeInfoDialog.querySelector(".route-summary");
        const path = budget?.path || [];
        diagram.innerHTML = path.length
            ? path.map((node, index) => `${index > 0 ? '<span class="route-arrow">→</span>' : ""}<div class="route-chip"><small>${escapeHtml(ROUTE_NODE_LABELS[node.type] || node.type || "")}</small><strong>${escapeHtml(node.name)}</strong></div>`).join("")
            : '<p class="help-text">Sem trajeto calculado para esta ligação (falta OLT/fusão anterior cadastrada).</p>';
        const hasPower = budget && budget.budget_dbm !== null && budget.budget_dbm !== undefined;
        summary.classList.toggle("route-summary-warning", !hasPower);
        summary.innerHTML = budget
            ? `<div>Perda acumulada: <strong>${budget.loss_db} dB</strong></div><div>${hasPower ? `Potência estimada: <strong>${budget.budget_dbm} dBm</strong>` : "Potência não calculada — informe a potência de saída da OLT."}</div>`
            : '<div>Sem informações de rota calculadas para esta ligação.</div>';
        routeInfoDialog.showModal();
    }
    routeInfoDialog.querySelector("[data-route-print]").onclick = () => window.print();
    routeInfoDialog.querySelector("[data-route-export]").onclick = () => {
        const path = currentRouteBudget?.path || [];
        const rows = [["Ordem", "Tipo", "Nome"]];
        path.forEach((node, index) => rows.push([String(index + 1), ROUTE_NODE_LABELS[node.type] || node.type || "", node.name]));
        rows.push([]);
        rows.push(["Perda acumulada (dB)", String(currentRouteBudget?.loss_db ?? "")]);
        rows.push(["Potência estimada (dBm)", currentRouteBudget?.budget_dbm != null ? String(currentRouteBudget.budget_dbm) : "Não calculada"]);
        const csv = "﻿" + rows.map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `rota-${Date.now()}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    };
    function normalizeSearch(value) {
        return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    }
    function showMapSearchResults(items) {
        const results = document.getElementById("map-search-results");
        results.innerHTML = items.map((item, index) => `<button class="map-search-result" type="button" data-search-result="${index}">${escapeHtml(item.label)}</button>`).join("")
            || '<p class="help-text">Nenhum resultado encontrado.</p>';
        results.hidden = false;
        results.querySelectorAll("[data-search-result]").forEach((button) => {
            button.onclick = () => {
                items[Number(button.dataset.searchResult)].focus();
                results.hidden = true;
            };
        });
    }
    async function searchAddress(query) {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=8&countrycodes=br&q=${encodeURIComponent(query)}`, {
            headers: { "Accept-Language": "pt-BR" },
        });
        if (!response.ok) throw new Error("Não foi possível consultar endereços agora.");
        const data = await response.json();
        showMapSearchResults(data.map((item) => ({
            label: item.display_name,
            focus: () => {
                const bounds = item.boundingbox?.map(Number);
                if (bounds?.length === 4) map.fitBounds([[bounds[0], bounds[2]], [bounds[1], bounds[3]]], { maxZoom: 20 });
                else map.setView([Number(item.lat), Number(item.lon)], 19);
            },
        })));
    }
    function searchProject(query) {
        if (!state.projectId) return notify("Selecione um projeto antes de pesquisar sua estrutura.", true);
        const term = normalizeSearch(query);
        const typeNames = { cto: "CTO", splice_box: "CEO", olt: "OLT", dio: "DIO", pole: "Poste" };
        const items = [];
        state.elements.forEach((feature) => {
            const properties = feature.properties || {};
            const haystack = normalizeSearch(`${properties.nome} ${properties.codigo} ${properties.tipo} ${typeNames[properties.tipo] || ""}`);
            if (!haystack.includes(term)) return;
            const [longitude, latitude] = feature.geometry.coordinates;
            items.push({
                label: `${typeNames[properties.tipo] || properties.tipo} · ${properties.nome}${properties.codigo ? ` · ${properties.codigo}` : ""}`,
                focus: () => map.setView([latitude, longitude], 21),
            });
        });
        state.cables.forEach((feature) => {
            const properties = feature.properties || {};
            const haystack = normalizeSearch(`cabo ${properties.nome} ${properties.codigo}`);
            if (!haystack.includes(term)) return;
            const lines = feature.geometry.type === "MultiLineString" ? feature.geometry.coordinates : [feature.geometry.coordinates];
            const points = lines.flat().map(([longitude, latitude]) => [latitude, longitude]);
            items.push({
                label: `Cabo · ${properties.nome}${properties.codigo ? ` · ${properties.codigo}` : ""}`,
                focus: () => points.length && map.fitBounds(points, { padding: [45, 45], maxZoom: 21 }),
            });
        });
        showMapSearchResults(items.slice(0, 30));
    }
    async function executeMapSearch() {
        const query = document.getElementById("map-search-query").value.trim();
        if (!query) return notify("Digite o que deseja localizar.", true);
        const mode = document.getElementById("map-search-mode").value;
        if (mode === "address") await searchAddress(query);
        else searchProject(query);
    }
    function selectedProject() {
        return state.projects.find((item) => String(item.id) === String(state.projectId));
    }
    function updateTools() {
        const enabled = canEdit && Boolean(state.projectId);
        document.querySelectorAll(".tool-button, #import-button").forEach((button) => { button.disabled = !enabled; });
        const project = selectedProject();
        document.getElementById("project-help").textContent = project ? `${project.code} · ${project.status_label}` : "Crie ou selecione um projeto para editar a estrutura.";
    }
    async function loadProjects(selectId) {
        const data = await api("/api/map/projects/");
        state.projects = data.projects;
        projectSelect.innerHTML = '<option value="">Selecione um projeto</option>';
        data.projects.forEach((project) => projectSelect.add(new Option(`${project.name} (${project.code})`, project.id)));
        if (selectId) projectSelect.value = String(selectId);
        state.projectId = projectSelect.value || null;
        canEdit = selectedProject() ? Boolean(selectedProject().can_edit) : hasEditAccess;
        updateTools();
    }
    function clientIcon(status) {
        return L.divIcon({ className: "", html: `<div class="client-dot ${status}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
    }
    function refreshClientLayers() {
        const grouped = document.getElementById("group-clients").checked;
        const clientsVisible = document.getElementById("layer-clients")?.checked !== false;
        ["online", "offline"].forEach((status) => {
            map.removeLayer(clientLayers[status]);
            map.removeLayer(clientPlainLayers[status]);
            if (!clientsVisible || !document.getElementById(`layer-${status}`).checked) return;
            (grouped ? clientLayers[status] : clientPlainLayers[status]).addTo(map);
        });
    }
    function refreshMapLabels() {
        const visible = document.getElementById("layer-labels")?.checked !== false;
        document.body.classList.toggle("map-labels-hidden", !visible);
    }
    const structureCategoryCheckbox = { cto: "layer-cto", splice_box: "layer-ceo", other: null };
    function refreshEquipmentLayer() {
        const structureOn = document.getElementById("layer-structure").checked;
        const grouped = document.getElementById("group-equipment").checked;
        Object.entries(structureLayers).forEach(([category, pair]) => {
            map.removeLayer(pair.cluster);
            map.removeLayer(pair.plain);
            const checkboxId = structureCategoryCheckbox[category];
            const categoryOn = checkboxId ? document.getElementById(checkboxId).checked : true;
            if (!structureOn || !categoryOn) return;
            (grouped ? pair.cluster : pair.plain).addTo(map);
        });
    }
    function refreshCableLayer() {
        map.removeLayer(cableLayer);
        const structureOn = document.getElementById("layer-structure").checked;
        const cablesOn = document.getElementById("layer-cables").checked;
        if (structureOn && cablesOn) cableLayer.addTo(map);
    }
    async function loadClients() {
        const data = await api("/api/map/access-points/");
        Object.values(clientLayers).forEach((layer) => layer.clearLayers());
        Object.values(clientPlainLayers).forEach((layer) => layer.clearLayers());
        data.features.forEach((feature) => {
            const p = feature.properties || {};
            const status = ["online", "offline"].includes(p.status) ? p.status : "unknown";
            const [longitude, latitude] = feature.geometry.coordinates;
            [clientLayers[status], clientPlainLayers[status]].forEach((layer) => {
                const marker = L.marker([latitude, longitude], { icon: clientIcon(status) });
                marker.bindPopup(`<strong>${escapeHtml(p.cliente || "Cliente")}</strong><br>PPPoE: ${escapeHtml(p.login || "-")}<br>Status: ${escapeHtml(status)}<br>CTO: ${escapeHtml(p.cto || "-")}<br>Porta da CTO: ${escapeHtml(p.porta_ftth || "-")}<br>ONU: ${escapeHtml(p.onu_number || p.onu || "-")}<br>SN da ONU: ${escapeHtml(p.onu_serial || p.onu || "-")}`);
                layer.addLayer(marker);
            });
        });
        refreshClientLayers();
        document.getElementById("client-count").textContent = data.count || data.features.length;
    }
    function networkIcon(type, subtype = "") {
        const normalizedSubtype = String(subtype || "").toLowerCase();
        const displayType = ["cpd", "pop"].includes(normalizedSubtype)
            ? "cpd" : type === "splice_box" && normalizedSubtype === "cdo" ? "cdo" : type;
        const labels = { cto: "CTO", pto: "PTO", splice_box: "CEO", cdo: "CDO", cpd: "CPD", olt: "OLT", dio: "DIO", rack: "RACK", tower: "TORRE" };
        // MAP_V07525_ICON_SET: ícones substituídos pelo kit SVG fornecido
        // pelo usuário (icones.html), mesma referência visual usada em
        // todos os tipos de elemento do mapa. CDO e CEO continuam com o
        // mesmo desenho (domo de emenda), só muda a cor/rótulo — igual já
        // era antes, agora só com o traço novo.
        const symbols = {
            pole: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="14" y="6" width="4" height="24" rx="1"></rect><path d="M6 8h20M6 5h20"></path><circle cx="8" cy="8" r="1" fill="currentColor"></circle><circle cx="24" cy="8" r="1" fill="currentColor"></circle></svg>',
            cto: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="6" y="4" width="20" height="24" rx="4"></rect><path d="M10 4v3m12-3v3M10 28v2m12-2v2"></path><circle cx="12" cy="12" r="1" fill="currentColor"></circle><circle cx="16" cy="12" r="1" fill="currentColor"></circle><circle cx="20" cy="12" r="1" fill="currentColor"></circle><path d="M9 18h14"></path></svg><small>CTO</small>',
            pto: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="8" y="8" width="16" height="16" rx="3"></rect><circle cx="16" cy="16" r="3"></circle><path d="M16 4v4M16 24v4"></path></svg><small>PTO</small>',
            splice_box: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 2h10a5 5 0 0 1 5 5v18a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7a5 5 0 0 1 5-5z"></path><path d="M9 7h14M9 11h14M9 15h14M9 19h14M9 23h14"></path><path d="M12 27v3m8-3v3"></path></svg><small>CEO</small>',
            cdo: '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 2h10a5 5 0 0 1 5 5v18a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7a5 5 0 0 1 5-5z"></path><path d="M9 7h14M9 11h14M9 15h14M9 19h14M9 23h14"></path><path d="M12 27v3m8-3v3"></path></svg><small>CDO</small>',
            cpd: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="6" y="6" width="20" height="22" rx="2"></rect><path d="M10 10h4M18 10h4M10 16h4M18 16h4M10 22h4M18 22h4"></path><path d="M13 28v-4h6v4"></path></svg><small>CPD</small>',
            olt: '<svg viewBox="0 0 24 18" aria-hidden="true"><rect x="3" y="2" width="18" height="14" rx="2"></rect><path d="M7 6h10M7 10h10M7 14h6"></path></svg><small>OLT</small>',
            rack: '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="4" y="2" width="24" height="28" rx="2"></rect><line x1="4" y1="10" x2="28" y2="10"></line><line x1="4" y1="18" x2="28" y2="18"></line><rect x="8" y="5" width="8" height="2" fill="currentColor"></rect><rect x="8" y="13" width="12" height="2" fill="currentColor"></rect><rect x="8" y="22" width="10" height="2" fill="currentColor"></rect></svg><small>RACK</small>',
            tower: '<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="10" r="3"></circle><path d="M14 13L10 28h12l-4-15"></path><path d="M12 28h8"></path><path d="M11 7C9 9 9 11 11 13M7 5c-3 3-3 7 0 10"></path><path d="M21 7c2 2 2 4 0 6M25 5c3 3 3 7 0 10"></path></svg><small>TORRE</small>',
        };
        const large = ["cto", "pto", "splice_box", "cdo", "cpd", "olt", "rack", "tower"].includes(displayType);
        return L.divIcon({
            className: "",
            html: `<div class="network-marker ${type} ${displayType}">${symbols[displayType] || labels[displayType] || "•"}</div>`,
            iconSize: large ? [40, 44] : [31, 31],
            iconAnchor: large ? [20, 22] : [15, 15],
        });
    }

    function animateLightDirection(feature, generation) {
        const geometry = feature.geometry || {};
        const lines = geometry.type === "MultiLineString" ? geometry.coordinates : [geometry.coordinates];
        lines.filter((coordinates) => Array.isArray(coordinates) && coordinates.length > 1).forEach((coordinates) => {
            const points = coordinates.map(([longitude, latitude]) => L.latLng(latitude, longitude));
            const segments = [];
            let total = 0;
            for (let index = 1; index < points.length; index += 1) {
                const length = map.distance(points[index - 1], points[index]);
                segments.push({ start: points[index - 1], end: points[index], from: total, length });
                total += length;
            }
            if (!total) return;
            const marker = L.marker(points[0], {
                interactive: false,
                icon: L.divIcon({
                    className: "",
                    html: '<div class="light-direction-marker">➤</div>',
                    iconSize: [25, 25],
                    iconAnchor: [12, 12],
                }),
                zIndexOffset: 900,
            }).addTo(cableLayer);
            const duration = Math.max(2200, Math.min(8500, total * 7));
            const startedAt = performance.now();
            const frame = (timestamp) => {
                if (generation !== state.lightAnimationGeneration || !cableLayer.hasLayer(marker)) return;
                const travelled = (((timestamp - startedAt) % duration) / duration) * total;
                const segment = segments.find((item) => travelled <= item.from + item.length) || segments.at(-1);
                const ratio = segment.length ? (travelled - segment.from) / segment.length : 0;
                marker.setLatLng([
                    segment.start.lat + (segment.end.lat - segment.start.lat) * ratio,
                    segment.start.lng + (segment.end.lng - segment.start.lng) * ratio,
                ]);
                const startPoint = map.latLngToLayerPoint(segment.start);
                const endPoint = map.latLngToLayerPoint(segment.end);
                const angle = Math.atan2(endPoint.y - startPoint.y, endPoint.x - startPoint.x) * 180 / Math.PI;
                const arrow = marker.getElement()?.querySelector(".light-direction-marker");
                if (arrow) arrow.style.transform = `rotate(${angle}deg)`;
                requestAnimationFrame(frame);
            };
            requestAnimationFrame(frame);
        });
    }
    function populateConnectionSelects() {
        ["origin_id", "destination_id"].forEach((name) => {
            const select = cableForm.elements[name];
            const current = select.value;
            select.innerHTML = '<option value="">Sem conexão</option>';
            state.elements.forEach((feature) => {
                const p = feature.properties;
                select.add(new Option(`${p.nome} · ${String(p.tipo).toUpperCase()}`, p.id));
            });
            select.value = current;
        });
    }
    function populateSplitterCables(cto, selectedId = "") {
        const select = elementForm.elements.splitter_input_cable_id;
        select.innerHTML = '<option value="">Selecione o cabo conectado</option>';
        (cto?.connected_cables || []).forEach((cable) => {
            select.add(new Option(`${cable.name} · ${cable.fiber_count} fibras`, cable.id));
        });
        select.value = selectedId ? String(selectedId) : "";
    }
    async function loadSplitterFibers(cableId, selectedId = "") {
        const select = elementForm.elements.splitter_input_fiber_id;
        select.innerHTML = '<option value="">Selecione a fibra</option>';
        if (!cableId) {
            select.innerHTML = '<option value="">Selecione primeiro o cabo</option>';
            return;
        }
        const data = await api(`/api/map/cables/${cableId}/fibers/`);
        data.tubes.forEach((tube) => tube.fibers.forEach((fiber) => {
            const option = new Option(`Fibra ${fiber.number} · ${fiber.color.name} · ${fiber.status_label}`, fiber.id);
            option.dataset.color = fiber.color.hex;
            select.add(option);
        }));
        select.value = selectedId ? String(selectedId) : "";
        if (!data.tubes.some((tube) => tube.fibers.length)) {
            select.innerHTML = '<option value="">Cabo sem fibras geradas</option>';
        }
    }
    function popupAction(selector, callback) {
        const button = document.querySelector(selector);
        if (button) {
            button.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                return callback(event);
            };
        }
    }
    async function deleteElement(id) {
        if (!confirm("Excluir este elemento do projeto?")) return;
        await api(`/api/map/elements/${id}/`, { method: "DELETE" });
        await loadStructure();
        notify("Elemento excluído.");
    }
    async function editElement(id) {
        const data = await api(`/api/map/elements/${id}/`);
        const element = data.element;
        state.editingElementId = id;
        elementForm.reset();
        ["element_type", "latitude", "longitude", "name", "code", "description", "status"].forEach((name) => {
            elementForm.elements[name].value = element[name] ?? "";
        });
        const subtype = element.element_subtype || element.metadata?.import_subtype || "";
        elementForm.elements.element_subtype.value = subtype;
        const isCpd = ["cpd", "pop"].includes(String(subtype).toLowerCase())
            || /^(CPD|POP)\b/i.test(element.name || "");
        const cpdFields = document.getElementById("cpd-structure-fields-v092");
        cpdFields.hidden = !isCpd;
        elementForm.elements.structure_profile.value = isCpd && ["rack", "tower"].includes(element.element_type)
            ? element.element_type : "";
        const isCto = element.element_type === "cto";
        const isContainer = ["rack", "tower"].includes(element.element_type);
        document.getElementById("cto-fields").hidden = !isCto;
        document.getElementById("container-fields").hidden = !isContainer;
        document.getElementById("container-fields-title").textContent = element.element_type === "tower" ? "Equipamentos da torre" : "Equipamentos do rack";
        if (isCto && element.cto) {
            // MAP_V07553_EMPTY_CTO_GUARD: element.cto.splitters podia vir
            // ausente (não só vazio) numa CTO sem splitter cadastrado ainda,
            // e o acesso direto [0] derrubava a edição com "Cannot read
            // properties of undefined (reading '0')".
            const splitters = Array.isArray(element.cto.splitters) ? element.cto.splitters : [];
            const splitter = splitters[0];
            elementForm.elements.cto_capacity.value = element.cto.capacity || 8;
            elementForm.elements.splitter_ratio.value = splitter?.ratio || element.cto.splitter_ratio || "1:8";
            elementForm.elements.splitter_ports.value = splitter?.output_ports || element.cto.capacity || 8;
            populateSplitterCables(element.cto, splitter?.input_cable?.id);
            await loadSplitterFibers(splitter?.input_cable?.id, splitter?.input_fiber?.id);
        }
        document.getElementById("element-dialog-title").textContent = `Editar ${element.name}`;
        elementDialog.showModal();
    }
    function updateContainerEquipmentFields() {
        const type = containerEquipmentForm.elements.equipment_type.value;
        const mode = containerEquipmentForm.elements.provisioning_mode.value;
        document.getElementById("container-olt-fields").hidden = type !== "olt";
        document.getElementById("container-dio-fields").hidden = type !== "dio";
        document.getElementById("container-management-fields").hidden = type === "dio" || (type === "olt" && mode === "manual");
        document.getElementById("container-model-field").hidden = type === "dio" || type === "olt";
        document.getElementById("container-serial-field").hidden = type === "dio" || type === "olt";
        document.getElementById("container-provisioning-field").hidden = type === "dio";
        document.getElementById("container-snmp-fields").hidden = mode !== "snmp" || type === "dio";
        const name = containerEquipmentForm.elements.name;
        name.placeholder = type === "olt" ? "Ex.: OLT principal"
            : type === "dio" ? "Ex.: DIO 36 portas"
            : type === "switch" ? "Ex.: Switch principal da torre"
            : type === "access_point" ? "Ex.: AP setor norte"
            : type === "onu" ? "Ex.: ONU interna da torre"
            : "Ex.: Enlace PTP prefeitura";
    }
    // Ponto de entrada único (v0.75.9) pra abrir o editor de Rack/Torre a
    // partir de um clique novo (marker/menu de botão direito). Delega pro
    // Canvas novo (map-master-suite.js), que faz sozinho: 1 chamada
    // equipment/, 1 chamada container-layout-v3/, desenha o Canvas, e só
    // então abre o dialog — nunca o renderer legado de lista (manageContainer
    // abaixo continua existindo só como refresh interno de formulários
    // legados já ocultos, não é mais chamado ao abrir um Rack/Torre do zero).
    function openContainerWorkspace(id) {
        if (!window.mapMasterSuite?.openContainerWorkspace) {
            return Promise.reject(new Error("Editor de estrutura (Canvas) ainda não carregou — recarregue a página."));
        }
        return window.mapMasterSuite.openContainerWorkspace(id);
    }
    async function manageContainer(id) {
        const data = await api(`/api/map/elements/${id}/equipment/`);
        state.containerId = id;
        containerDialog.dataset.elementId = String(id);
        containerDialog.dataset.containerType = String(data.container.type || "tower");
        containerDialog.dataset.containerName = String(data.container.name || "Estrutura");
        document.getElementById("container-dialog-title").textContent = `Estrutura · ${data.container.name}`;
        document.getElementById("container-dialog-subtitle").textContent = data.container.type === "rack"
            ? "OLT e DIO instalados neste rack"
            : "OLT, switches, APs, DIOs, ONUs e rádios PTP instalados nesta torre";
        const types = data.container.type === "rack"
            ? [["olt", "OLT"], ["dio", "DIO"], ["switch", "Switch"], ["router", "Roteador"], ["firewall", "Firewall"], ["server", "Servidor"], ["pto", "PTO"], ["other", "Outro"]]
            : [["olt", "OLT"], ["switch", "Switch"], ["router", "Roteador"], ["firewall", "Firewall"], ["access_point", "Access point"], ["ptp", "Rádio PTP"], ["dio", "DIO"], ["onu", "ONU / ONT"], ["pto", "PTO"], ["other", "Outro"]];
        containerEquipmentForm.reset();
        state.editingContainerEquipmentId = null;
        containerEquipmentForm.elements.equipment_type.disabled = false;
        containerEquipmentForm.querySelector("button[type='submit']").textContent = "Adicionar à estrutura";
        containerEquipmentForm.elements.equipment_type.innerHTML = types
            .map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
        updateContainerEquipmentFields();
        document.getElementById("container-equipment-list").innerHTML = data.equipment.length
            ? data.equipment.map((item) => {
                const detail = item.type === "olt"
                    ? `${item.card_count} placa(s) · ${item.pon_count} PONs${item.tx_power_dbm !== null && item.tx_power_dbm !== undefined ? ` · ${item.tx_power_dbm} dBm` : ""}`
                    : item.type === "dio" ? `${item.dio_port_capacity} portas${item.connector_type ? ` · ${escapeHtml(item.connector_type_label)}` : ""}` : (item.management_ip || "Sem IP");
                const cards = item.cards?.length
                    ? `<div class="equipment-card-list">${item.cards.map((card) => `<span><b>Slot ${card.slot} · ${escapeHtml(card.name)}</b><br>${card.pon_count} PONs${card.model ? ` · ${escapeHtml(card.model)}` : ""}</span>`).join("")}</div>`
                    : "";
                const connectorClass = item.type === "dio" && item.connector_type
                    ? (item.connector_type.endsWith("_upc") ? "connector-upc" : "connector-apc")
                    : "";
                const ports = item.ports?.length
                    ? `<div class="equipment-port-grid">${item.ports.map((port) => `<button type="button" class="equipment-port ${port.used ? `used ${connectorClass}` : ""}" data-port-id="${port.id}" data-port-type="${port.type}" ${port.link_id ? `data-link-id="${port.link_id}"` : ""} data-loss-db="${port.link_loss_db ?? ""}" data-budget-dbm="${port.budget_dbm ?? ""}">${escapeHtml(port.label)}${port.linked_cable ? ` · ${escapeHtml(port.linked_cable)}` : port.used ? " · ligada" : ""}</button>`).join("")}</div>`
                    : '<p class="field-help">Nenhuma porta cadastrada.</p>';
                const configure = item.type === "olt"
                    ? `<button class="secondary-button" type="button" data-add-equipment-card="${item.id}">+ Placa</button>`
                    : ["switch", "access_point", "ptp", "onu", "other"].includes(item.type)
                        ? `<button class="secondary-button" type="button" data-add-equipment-ports="${item.id}">+ Portas</button>`
                        : "";
                return `<article><div class="equipment-head"><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.type_label)} · ${escapeHtml(detail)}${item.management_ip ? ` · ${escapeHtml(item.management_ip)}` : ""}</small></div><div class="equipment-head-actions"><button class="secondary-button" type="button" data-edit-container-equipment="${item.id}">Editar</button><button class="danger" type="button" data-delete-container-equipment="${item.id}">Excluir</button></div></div>${cards}${ports}<div class="equipment-actions">${configure}</div></article>`;
            }).join("")
            : "<p>Nenhum equipamento instalado.</p>";
        const sourcePorts = data.equipment.flatMap((item) => item.ports
            .filter((port) => !port.used && (data.container.type === "tower" || port.type === "pon"))
            .map((port) => ({ ...port, equipment: item.name })));
        const destinationPorts = data.equipment.flatMap((item) => item.ports
            .filter((port) => !port.used && (data.container.type === "tower" || port.type === "dio"))
            .map((port) => ({ ...port, equipment: item.name })));
        const isRack = data.container.type === "rack";
        const opticalLinks = document.getElementById("container-optical-links");
        opticalLinks.hidden = !data.equipment.length;
        document.getElementById("container-link-title").textContent = isRack
            ? "Ligações de cordões — OLT → DIO" : "Diagrama e ligações da torre";
        document.getElementById("container-link-help").textContent = isRack
            ? "Clique numa porta PON da OLT e depois numa porta do DIO, nos equipamentos acima, para criar o cordão. Clique numa porta já ligada para desligar. Para fundir a fibra do cabo no fundo da porta, use o botão Fusões."
            : "Ligue switch, AP e rádio PTP por RJ45/SFP ou registre o enlace wireless.";
        const openFusionsButton = document.getElementById("container-open-fusions");
        openFusionsButton.hidden = !isRack;
        openFusionsButton.onclick = () => showUnifilar(id).catch((error) => notify(error.message, true));
        containerLinkForm.hidden = isRack;
        containerLinkForm.elements.link_type.value = isRack ? "fiber" : "copper";
        containerLinkForm.elements.source_port_id.innerHTML = sourcePorts
            .map((port) => `<option value="${port.id}">${escapeHtml(port.equipment)} · ${escapeHtml(port.label)}</option>`).join("");
        containerLinkForm.elements.destination_port_id.innerHTML = destinationPorts
            .map((port) => `<option value="${port.id}">${escapeHtml(port.equipment)} · ${escapeHtml(port.label)}</option>`).join("");
        containerLinkForm.elements.cable_id.innerHTML = '<option value="">Ainda sem cabo vinculado</option>'
            + data.cables.map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${cable.fiber_count}F</option>`).join("");
        containerLinkForm.querySelector("button[type='submit']").disabled = !sourcePorts.length || !destinationPorts.length;
        document.getElementById("container-link-list").innerHTML = data.links.length
            ? data.links.map((link) => `<article><div><strong>${escapeHtml(link.source)} → ${escapeHtml(link.destination)}</strong><small>${escapeHtml(link.link_type_label)}${link.cable ? ` · Cabo: ${escapeHtml(link.cable)}` : ""}</small></div><button class="danger" type="button" data-delete-container-link="${link.id}">Desligar</button></article>`).join("")
            : "<p>Nenhuma ligação interna registrada.</p>";
        // Workspace não modal: o menu principal continua visível e utilizável.
        if (!containerDialog.open) containerDialog.show();
        document.dispatchEvent(new CustomEvent("map:container-opening", {
            detail: { dialog: containerDialog, elementId: id },
        }));
        containerCardForm.hidden = true;
        containerPortForm.hidden = true;
        document.querySelectorAll("[data-add-equipment-card]").forEach((button) => {
            button.onclick = () => {
                containerCardForm.reset();
                const equipmentId = button.dataset.addEquipmentCard;
                const equipment = data.equipment.find((item) => String(item.id) === String(equipmentId));
                const usedSlots = new Set((equipment?.cards || []).map((card) => Number(card.slot)));
                let nextSlot = 1;
                while (usedSlots.has(nextSlot)) nextSlot += 1;
                containerCardForm.elements.equipment_id.value = equipmentId;
                containerCardForm.elements.slot.value = nextSlot;
                containerCardForm.hidden = false;
                containerPortForm.hidden = true;
                containerCardForm.scrollIntoView({ behavior: "smooth", block: "center" });
            };
        });
        document.querySelectorAll("[data-add-equipment-ports]").forEach((button) => {
            button.onclick = () => {
                containerPortForm.reset();
                containerPortForm.elements.equipment_id.value = button.dataset.addEquipmentPorts;
                containerPortForm.hidden = false;
                containerCardForm.hidden = true;
                containerPortForm.scrollIntoView({ behavior: "smooth", block: "center" });
            };
        });
        document.querySelectorAll("[data-delete-container-equipment]").forEach((button) => {
            button.onclick = async () => {
                if (!confirm("Excluir este equipamento da estrutura?")) return;
                await api(`/api/map/elements/${id}/equipment/${button.dataset.deleteContainerEquipment}/`, { method: "DELETE" });
                await manageContainer(id);
            };
        });
        document.querySelectorAll("[data-edit-container-equipment]").forEach((button) => {
            button.onclick = () => {
                const item = data.equipment.find((equipment) => String(equipment.id) === String(button.dataset.editContainerEquipment));
                if (!item) return;
                state.editingContainerEquipmentId = item.id;
                containerEquipmentForm.elements.equipment_type.value = item.type;
                containerEquipmentForm.elements.equipment_type.disabled = true;
                containerEquipmentForm.elements.name.value = item.name;
                containerEquipmentForm.elements.vendor.value = item.vendor || "";
                containerEquipmentForm.elements.model.value = item.model || "";
                containerEquipmentForm.elements.serial_number.value = item.serial_number || "";
                containerEquipmentForm.elements.management_ip.value = item.management_ip || "";
                containerEquipmentForm.elements.provisioning_mode.value = item.provisioning_mode || "manual";
                containerEquipmentForm.elements.snmp_community.value = "";
                if (containerEquipmentForm.elements.connector_type) {
                    containerEquipmentForm.elements.connector_type.value = item.connector_type || "";
                }
                if (containerEquipmentForm.elements.tx_power_dbm) {
                    containerEquipmentForm.elements.tx_power_dbm.value = item.tx_power_dbm ?? "";
                }
                updateContainerEquipmentFields();
                containerEquipmentForm.elements.equipment_type.dispatchEvent(new Event("change"));
                containerEquipmentForm.querySelector("button[type='submit']").textContent = "Salvar alterações";
                containerEquipmentForm.scrollIntoView({ behavior: "smooth", block: "center" });
            };
        });
        document.querySelectorAll("[data-delete-container-link]").forEach((button) => {
            button.onclick = async () => {
                if (!confirm("Remover esta ligação entre a OLT e o DIO?")) return;
                await api(`/api/map/elements/${id}/equipment-links/${button.dataset.deleteContainerLink}/`, { method: "DELETE" });
                await manageContainer(id);
            };
        });
        if (isRack) {
            let selectedSourcePortId = null;
            document.querySelectorAll(".equipment-port").forEach((button) => {
                button.onclick = async () => {
                    if (button.classList.contains("used")) {
                        if (!button.dataset.linkId) return;
                        const details = [
                            button.dataset.lossDb ? `Perda do cordão: ${button.dataset.lossDb} dB` : "",
                            button.dataset.budgetDbm ? `Potência estimada no cabo: ${button.dataset.budgetDbm} dBm` : "Potência estimada: informe a potência de saída da OLT para calcular.",
                        ].filter(Boolean).join("\n");
                        if (!confirm(`${details}\n\nDesligar este cordão?`)) return;
                        await api(`/api/map/elements/${id}/equipment-links/${button.dataset.linkId}/`, { method: "DELETE" });
                        await manageContainer(id);
                        return;
                    }
                    if (!selectedSourcePortId) {
                        if (button.dataset.portType !== "pon") return notify("Selecione primeiro uma porta PON da OLT.", true);
                        selectedSourcePortId = button.dataset.portId;
                        button.classList.add("selected");
                        notify("Porta PON selecionada. Clique na porta do DIO.");
                        return;
                    }
                    try {
                        await api(`/api/map/elements/${id}/equipment-links/`, {
                            method: "POST",
                            body: JSON.stringify({ source_port_id: selectedSourcePortId, destination_port_id: button.dataset.portId }),
                        });
                        notify("Cordão criado.");
                        await manageContainer(id);
                    } catch (error) { notify(error.message, true); }
                };
            });
        }
        const topologyEl = document.getElementById("container-equipment-list");
        const applyTopologyZoom = () => {
            topologyEl.style.transform = `scale(${state.topologyZoom})`;
            document.getElementById("topology-zoom-value").value = `${Math.round(state.topologyZoom * 100)}%`;
        };
        document.getElementById("topology-zoom-out").onclick = () => {
            state.topologyZoom = Math.max(.5, state.topologyZoom - .1); applyTopologyZoom();
        };
        document.getElementById("topology-zoom-in").onclick = () => {
            state.topologyZoom = Math.min(1.5, state.topologyZoom + .1); applyTopologyZoom();
        };
        document.getElementById("topology-zoom-reset").onclick = () => {
            state.topologyZoom = 1; applyTopologyZoom();
        };
        applyTopologyZoom();
    }
    async function showUnifilar(id) {
        // Não recarregue toda a estrutura ao abrir as fusões. Isso fechava o
        // popup do Leaflet durante o primeiro clique e causava o efeito de
        // piscar/abrir somente na segunda tentativa.
        map.closePopup();
        unifilarDialog.dataset.elementId = String(id);
        const content = document.getElementById("unifilar-content");
        document.getElementById("unifilar-title").textContent = "Carregando fusões...";
        document.getElementById("unifilar-subtitle").textContent = "Consultando cabos, fibras e layout";
        content.innerHTML = '<div class="fusion-loading"><span class="fusion-spinner"></span><strong>Preparando diagrama óptico</strong></div>';
        unifilarDialog.classList.add("map-v0758-optical-workspace");
        if (!unifilarDialog.open) unifilarDialog.showModal();
        const data = await api(`/api/map/elements/${id}/`);
        const element = data.element;
        document.getElementById("unifilar-title").textContent = `Fusões · ${element.name}`;
        document.getElementById("unifilar-subtitle").textContent = `${element.code || "Sem código"} · capacidade ${element.cto?.capacity || 0}`;
        // MAP_V07533_OPTICAL_CLEANUP: o editor óptico de CTO/CEO/CDO (fusões,
        // splitters) foi desativado temporariamente para reconstrução -- a
        // versão anterior compartilhava o mesmo DOM/estado do editor de
        // Rack/Torre e corrompia esse estado entre aberturas. Não reabre o
        // #unifilar-dialog antigo nem chama nenhum renderizador óptico.
        if (element.splice_box) {
            unifilarDialog.close();
            notify("Editor óptico temporariamente desativado para reconstrução.");
            return;
        }
        if (element.element_type === "rack") {
            await renderRackFusionDiagram(element, content);
            unifilarDialog.classList.add("map-v0758-optical-workspace");
            if (!unifilarDialog.open) unifilarDialog.showModal();
            return;
        }
        const splitters = element.cto?.splitters || [];
        content.innerHTML = splitters.length ? splitters.map((splitter) => `
            <article class="splitter-card">
                <div class="splitter-head"><strong>${escapeHtml(splitter.name)}</strong><span>${escapeHtml(splitter.ratio)} · ${splitter.output_ports} saídas</span></div>
                <div class="unifilar-source">
                    ${splitter.input_cable ? `<strong>${escapeHtml(splitter.input_cable.name)}</strong><span>Fibra ${splitter.input_fiber?.number || "não escolhida"} · ${escapeHtml(splitter.input_fiber?.color_name || "sem cor")}</span>` : "<strong>Cabo não conectado</strong><span>Edite a CTO para escolher cabo e fibra</span>"}
                </div>
                <div class="unifilar-flow" style="--fiber-color:${escapeHtml(splitter.input_fiber?.color_hex || "#2dd4bf")}">
                    <div class="unifilar-input">Entrada do splitter</div><div class="unifilar-line"></div>
                    <div class="port-grid">${splitter.ports.map((port) => `<div class="port ${escapeHtml(port.status)}">P${port.number}<br>${escapeHtml(port.status_label)}</div>`).join("")}</div>
                </div>
            </article>`).join("") : '<p class="help-text">Nenhum splitter configurado.</p>';
        unifilarDialog.classList.add("map-v0758-optical-workspace");
        if (!unifilarDialog.open) unifilarDialog.showModal();
    }
    async function renderRackFusionDiagram(element, content) {
        document.getElementById("unifilar-subtitle").textContent = "Fusão de fibras nas portas do DIO";
        const [data, savedLayout] = await Promise.all([
            api(`/api/map/elements/${element.id}/equipment/`),
            api(`/api/map/elements/${element.id}/layout/`),
        ]);
        const layout = savedLayout.layout || {};
        const notes = layout.notes || [];
        const dios = data.equipment.filter((item) => item.type === "dio");
        const cables = data.cables || [];
        const dioCards = dios.map((dio, index) => {
            const position = layout[`dio-${dio.id}`] || { x: 680, y: 20 + index * 260 };
            const nodeKey = `dio-${dio.id}`;
            const usedCount = dio.ports.filter((port) => port.fusion_used).length;
            const hasUsedPort = usedCount > 0;
            const explicit = (layout.cardState || {})[nodeKey];
            const isExpanded = explicit ? explicit === "expanded" : true;
            const toggleButton = `<button class="expand-fibers" type="button" data-expand-node="${nodeKey}" title="Expandir ou recolher todas as portas">${isExpanded ? "−" : "+"}</button>`;
            const summary = !isExpanded && hasUsedPort ? `<small>${usedCount}/${dio.ports.length} em uso</small>` : "";
            const visiblePorts = isExpanded ? dio.ports : dio.ports.filter((port) => !port.fusion_used);
            return `<section class="fiber-cable-node graph-node ${isExpanded ? "expanded" : ""}" data-node-key="${nodeKey}" style="left:${position.x}px;top:${position.y}px"><header>${escapeHtml(dio.name)}${dio.connector_type ? ` <small>${escapeHtml(dio.connector_type_label)}</small>` : ""}${summary}<span>${toggleButton}<span class="drag-grip">⋮⋮</span></span></header>
            <div class="fiber-port-list">${visiblePorts.map((port) => `<button type="button" class="fiber-port dio-fusion-port ${port.fusion_used ? "used" : ""}" data-used="${port.fusion_used}" data-port-id="${port.id}" ${port.fusion_link_id ? `data-link-id="${port.fusion_link_id}"` : ""} data-loss-db="${port.fusion_loss_db ?? ""}" data-budget-dbm="${port.budget_dbm ?? ""}">${escapeHtml(port.label)}${port.fusion_linked_cable ? ` · ${escapeHtml(port.fusion_linked_cable)}` : port.fusion_used ? " · fundida" : ""}</button>`).join("") || `<span>${isExpanded ? "Nenhuma porta cadastrada." : "Todas as portas em uso."}</span>`}</div>
        </section>`;
        }).join("");
        const cableCards = cables.map((cable, index) => {
            const position = layout[`cable-${cable.id}`] || { x: 20, y: 20 + index * 260 };
            const nodeKey = `cable-${cable.id}`;
            const usedCount = (cable.fibers || []).filter((fiber) => fiber.used).length;
            const hasUsedFiber = usedCount > 0;
            const explicit = (layout.cardState || {})[nodeKey];
            const isExpanded = explicit ? explicit === "expanded" : true;
            const toggleButton = `<button class="expand-fibers" type="button" data-expand-node="${nodeKey}" title="Expandir ou recolher todas as fibras">${isExpanded ? "−" : "+"}</button>`;
            const summary = !isExpanded && hasUsedFiber ? `<small>${usedCount}/${(cable.fibers || []).length} em uso</small>` : "";
            const visibleFibers = isExpanded ? (cable.fibers || []) : (cable.fibers || []).filter((fiber) => !fiber.used);
            return `<section class="fiber-cable-node graph-node ${isExpanded ? "expanded" : ""}" data-node-key="${nodeKey}" style="left:${position.x}px;top:${position.y}px"><header>${escapeHtml(cable.name)}${summary}<span>${toggleButton}<span class="drag-grip">⋮⋮</span></span></header>
            <div class="fiber-port-list">${visibleFibers.map((fiber) => `<button type="button" class="fiber-port ${fiber.used ? "used" : ""}" data-used="${fiber.used}" data-fiber-id="${fiber.id}" ${fiber.link_id ? `data-link-id="${fiber.link_id}"` : ""} style="--fiber-color:${escapeHtml(fiber.color_hex)}"><i></i>F${fiber.number} · ${escapeHtml(fiber.color_name)}${fiber.used ? " · Em uso" : ""}</button>`).join("") || `<span>${isExpanded ? "Sem fibras geradas" : "Todas as fibras em uso"}</span>`}</div>
        </section>`;
        }).join("");
        const noteNodes = notes.map((note) => `<div class="note-node graph-node" data-node-key="note-${note.id}" style="left:${note.x}px;top:${note.y}px">
            <header><span class="drag-grip">⋮⋮</span><span class="note-node-actions"><button type="button" class="note-edit" data-edit-fusion-note="${note.id}" title="Editar nota" aria-label="Editar nota"><svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"></path><path d="m13.5 6.5 3.5 3.5"></path></svg></button><button type="button" class="note-delete" data-delete-note="${note.id}" title="Excluir nota" aria-label="Excluir nota"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6"></path></svg></button></span></header>
            <div class="note-text" data-note-id="${note.id}">${escapeHtml(note.text)}</div></div>`).join("");
        content.innerHTML = `<div class="ceo-instructions">Arraste os blocos pelo ⋮⋮. Clique numa fibra do cabo e depois numa porta do DIO para criar a fusão. Clique numa fibra ou porta já ligada para desfazer. Botão direito no fundo do quadro para adicionar nota.<span class="unifilar-zoom"><button id="unifilar-zoom-out" type="button" title="Diminuir">−</button><output id="unifilar-zoom-value">100%</output><button id="unifilar-zoom-in" type="button" title="Ampliar">+</button><button id="unifilar-zoom-reset" type="button" title="Ajustar">Ajustar</button></span></div>
            <div class="optical-graph rack-fusion"><div class="graph-nodes"><svg class="optical-links"></svg>${dioCards || "<p>Nenhum DIO cadastrado.</p>"}${cableCards || "<p>Nenhum cabo ligado ao rack.</p>"}${noteNodes}</div><div class="map-context-menu rack-canvas-menu" hidden><button type="button" data-canvas-action="add-note">+ Adicionar nota</button></div></div>`;
        const redrawRackFusionLinks = () => {
            const graphNodesEl = content.querySelector(".graph-nodes");
            const svg = content.querySelector(".optical-links");
            if (!graphNodesEl || !svg) return;
            const width = graphNodesEl.scrollWidth, height = graphNodesEl.scrollHeight;
            svg.innerHTML = "";
            svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
            svg.style.width = `${width}px`;
            svg.style.height = `${height}px`;
            content.querySelectorAll(".fiber-port[data-link-id]").forEach((fiberChip) => {
                const portButton = content.querySelector(`.dio-fusion-port[data-link-id="${fiberChip.dataset.linkId}"]`);
                if (!portButton) return;
                const start = centerWithin(fiberChip, graphNodesEl);
                const end = centerWithin(portButton, graphNodesEl);
                const x1 = start.x, y1 = start.y;
                const x2 = end.x, y2 = end.y;
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                path.setAttribute("d", `M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`);
                path.setAttribute("stroke", fiberChip.style.getPropertyValue("--fiber-color") || "#94a3b8");
                svg.appendChild(path);
            });
        };
        const graphNodes = content.querySelector(".graph-nodes");
        const zoomOutput = document.getElementById("unifilar-zoom-value");
        const fitZoom = () => {
            const graph = content.querySelector(".optical-graph");
            const widthZoom = (graph.clientWidth - 48) / Math.max(1, graphNodes.scrollWidth);
            const heightZoom = (graph.clientHeight - 48) / Math.max(1, graphNodes.scrollHeight);
            return Math.max(.4, Math.min(1.15, widthZoom, heightZoom));
        };
        let graphZoom = layout.zoom ? Math.max(.4, Math.min(1.6, Number(layout.zoom))) : .7;
        if (graphZoom < .65) graphZoom = .7;
        const applyGraphZoom = () => {
            if (graphZoom === null) graphZoom = fitZoom();
            graphNodes.style.transform = `scale(${graphZoom})`;
            graphNodes.style.transformOrigin = "top left";
            zoomOutput.value = `${Math.round(graphZoom * 100)}%`;
            requestAnimationFrame(redrawRackFusionLinks);
        };
        const saveLayout = () => api(`/api/map/elements/${element.id}/layout/`, {
            method: "PATCH", body: JSON.stringify({ layout }),
        });
        document.getElementById("unifilar-zoom-out").onclick = () => {
            graphZoom = Math.max(.5, graphZoom - .1); applyGraphZoom(); layout.zoom = graphZoom; saveLayout();
        };
        document.getElementById("unifilar-zoom-in").onclick = () => {
            graphZoom = Math.min(1.6, graphZoom + .1); applyGraphZoom(); layout.zoom = graphZoom; saveLayout();
        };
        document.getElementById("unifilar-zoom-reset").onclick = () => {
            graphZoom = fitZoom(); applyGraphZoom(); layout.zoom = graphZoom; saveLayout();
        };
        applyGraphZoom();
        content.querySelectorAll("[data-expand-node]").forEach((button) => {
            button.onclick = async () => {
                const nodeKey = button.dataset.expandNode;
                const node = content.querySelector(`[data-node-key="${nodeKey}"]`);
                const nowExpanded = !node.classList.contains("expanded");
                layout.cardState = { ...(layout.cardState || {}), [nodeKey]: nowExpanded ? "expanded" : "collapsed" };
                await saveLayout();
                unifilarDialog.close(); await showUnifilar(element.id);
            };
        });
        content.querySelectorAll(".graph-node").forEach((node) => {
            const grip = node.querySelector(".drag-grip");
            grip.onpointerdown = (event) => {
                event.preventDefault();
                const startX = event.clientX, startY = event.clientY;
                const originX = parseFloat(node.style.left), originY = parseFloat(node.style.top);
                grip.setPointerCapture(event.pointerId);
                const isNote = node.dataset.nodeKey.startsWith("note-");
                grip.onpointermove = (move) => {
                    const candidateX = originX + (move.clientX - startX) / graphZoom;
                    const candidateY = originY + (move.clientY - startY) / graphZoom;
                    const width = node.offsetWidth, height = node.offsetHeight;
                    const collides = !isNote && [...content.querySelectorAll(".graph-node")].some((other) => {
                        if (other === node || other.dataset.nodeKey.startsWith("note-")) return false;
                        const ox = parseFloat(other.style.left) || 0, oy = parseFloat(other.style.top) || 0;
                        return candidateX < ox + other.offsetWidth && candidateX + width > ox
                            && candidateY < oy + other.offsetHeight && candidateY + height > oy;
                    });
                    if (collides) return;
                    node.style.left = `${candidateX}px`;
                    node.style.top = `${candidateY}px`;
                    redrawRackFusionLinks();
                };
                grip.onpointerup = async () => {
                    grip.onpointermove = null;
                    const x = Math.round(parseFloat(node.style.left));
                    const y = Math.round(parseFloat(node.style.top));
                    if (node.dataset.nodeKey.startsWith("note-")) {
                        const noteId = node.dataset.nodeKey.slice("note-".length);
                        layout.notes = notes.map((note) => String(note.id) === noteId ? { ...note, x, y } : note);
                    } else {
                        layout[node.dataset.nodeKey] = { x, y };
                    }
                    await saveLayout();
                    notify("Posição salva.");
                };
            };
        });
        const rackGraphEl = content.querySelector(".optical-graph");
        const rackCanvasMenu = content.querySelector(".rack-canvas-menu");
        let rackCanvasMenuPoint = null;
        rackGraphEl.addEventListener("contextmenu", (event) => {
            if (event.target.closest(".graph-node") || event.target.closest(".rack-canvas-menu")) return;
            event.preventDefault();
            const graphRect = rackGraphEl.getBoundingClientRect();
            rackCanvasMenuPoint = {
                x: (event.clientX - graphRect.left + rackGraphEl.scrollLeft) / graphZoom,
                y: (event.clientY - graphRect.top + rackGraphEl.scrollTop) / graphZoom,
            };
            rackCanvasMenu.style.left = `${event.clientX - graphRect.left}px`;
            rackCanvasMenu.style.top = `${event.clientY - graphRect.top}px`;
            rackCanvasMenu.hidden = false;
        });
        content.addEventListener("click", (event) => {
            if (!event.target.closest(".rack-canvas-menu")) rackCanvasMenu.hidden = true;
        });
        rackCanvasMenu.querySelector('[data-canvas-action="add-note"]').onclick = async () => {
            rackCanvasMenu.hidden = true;
            if (!rackCanvasMenuPoint) return;
            const text = await window.mapV0758?.editLongText?.({ title: "Adicionar nota", label: "Texto da nota" });
            if (!text) return;
            layout.notes = [...notes, { id: `n${Date.now()}`, x: Math.round(rackCanvasMenuPoint.x), y: Math.round(rackCanvasMenuPoint.y), text }];
            await saveLayout();
            unifilarDialog.close(); await showUnifilar(element.id); notify("Nota adicionada.");
        };
        content.querySelectorAll("[data-delete-note]").forEach((button) => {
            button.onclick = async () => {
                const accepted = await window.mapV0758?.confirmAction?.({
                        title: "Excluir nota",
                        message: "A nota será removida do diagrama de fusões.",
                        confirmLabel: "Excluir nota",
                        cancelLabel: "Cancelar",
                        danger: true,
                    });
                    if (!accepted) return;
                layout.notes = notes.filter((note) => String(note.id) !== String(button.dataset.deleteNote));
                await saveLayout();
                unifilarDialog.close(); await showUnifilar(element.id); notify("Nota excluída.");
            };
        });
        content.querySelectorAll("[data-edit-fusion-note]").forEach((button) => {
            button.onclick = async () => {
                const note = notes.find((item) => String(item.id) === String(button.dataset.editFusionNote));
                if (!note) return;
                const text = await window.mapV0758?.editLongText?.({ title: "Editar nota", label: "Texto da nota", value: note.text || "" });
                if (!text?.trim()) return;
                layout.notes = notes.map((item) => String(item.id) === String(note.id) ? { ...item, text: text.trim() } : item);
                await saveLayout();
                unifilarDialog.close(); await showUnifilar(element.id); notify("Nota atualizada.");
            };
        });
        content.querySelectorAll("[data-note-id]").forEach((textEl) => {
            textEl.onclick = async () => {
                const note = notes.find((item) => String(item.id) === String(textEl.dataset.noteId));
                const text = await window.mapV0758?.editLongText?.({ title: "Editar nota", label: "Texto da nota", value: note?.text || "" });
                if (text === null) return;
                layout.notes = notes.map((item) => String(item.id) === String(textEl.dataset.noteId) ? { ...item, text } : item);
                await saveLayout();
                unifilarDialog.close(); await showUnifilar(element.id); notify("Nota atualizada.");
            };
        });
        let selectedFiberId = null;
        let selectedPortId = null;
        const tryCreateRackFusion = async () => {
            if (!selectedFiberId || !selectedPortId) return;
            try {
                await api(`/api/map/elements/${element.id}/equipment-links/`, {
                    method: "POST",
                    body: JSON.stringify({ destination_port_id: selectedPortId, cable_fiber_id: selectedFiberId }),
                });
                unifilarDialog.close(); await showUnifilar(element.id); notify("Fusão criada.");
            } catch (error) {
                notify(error.message, true);
                selectedFiberId = null; selectedPortId = null;
                content.querySelectorAll(".fiber-port.selected").forEach((item) => item.classList.remove("selected"));
            }
        };
        content.querySelectorAll(".fiber-port:not(.dio-fusion-port)").forEach((chip) => {
            chip.onclick = async () => {
                if (chip.dataset.used === "true") {
                    if (!confirm("Remover esta fusão?")) return;
                    await api(`/api/map/elements/${element.id}/equipment-links/${chip.dataset.linkId}/`, { method: "DELETE" });
                    unifilarDialog.close(); await showUnifilar(element.id); notify("Fusão removida.");
                    return;
                }
                content.querySelectorAll(".fiber-port:not(.dio-fusion-port).selected").forEach((item) => item.classList.remove("selected"));
                selectedFiberId = chip.dataset.fiberId;
                chip.classList.add("selected");
                if (selectedPortId) { await tryCreateRackFusion(); }
                else { notify("Fibra selecionada. Clique na porta do DIO (ou comece pela porta do DIO)."); }
            };
        });
        content.querySelectorAll(".dio-fusion-port").forEach((button) => {
            button.onclick = async () => {
                if (button.dataset.used === "true") {
                    const details = [
                        button.dataset.lossDb ? `Perda da fusão: ${button.dataset.lossDb} dB` : "",
                        button.dataset.budgetDbm ? `Potência estimada no cabo: ${button.dataset.budgetDbm} dBm` : "",
                    ].filter(Boolean).join("\n");
                    if (!confirm(`${details}${details ? "\n\n" : ""}Remover esta fusão?`)) return;
                    await api(`/api/map/elements/${element.id}/equipment-links/${button.dataset.linkId}/`, { method: "DELETE" });
                    unifilarDialog.close(); await showUnifilar(element.id); notify("Fusão removida.");
                    return;
                }
                content.querySelectorAll(".dio-fusion-port.selected").forEach((item) => item.classList.remove("selected"));
                selectedPortId = button.dataset.portId;
                button.classList.add("selected");
                if (selectedFiberId) { await tryCreateRackFusion(); }
                else { notify("Porta do DIO selecionada. Clique na fibra do cabo."); }
            };
        });
        requestAnimationFrame(redrawRackFusionLinks);
        window.addEventListener("resize", redrawRackFusionLinks);
        content.querySelector(".optical-graph").addEventListener("scroll", redrawRackFusionLinks);
        content.addEventListener("scroll", redrawRackFusionLinks);
        unifilarDialog.addEventListener("close", () => window.removeEventListener("resize", redrawRackFusionLinks), { once: true });
    }
    async function deleteCable(id) {
        if (!confirm("Excluir este cabo do projeto?")) return;
        try {
            await api(`/api/map/cables/${id}/`, { method: "DELETE" });
        } catch (error) {
            if (!confirm(`${error.message}\nDeseja forçar a exclusão?`)) throw error;
            await api(`/api/map/cables/${id}/?force=1`, { method: "DELETE" });
        }
        await loadStructure();
        notify("Cabo excluído.");
    }
    async function createReserveAt(cableId, latlng) {
        const length = Number(await askValue({ title: "Nova reserva técnica", label: "Metragem da reserva", value: "20", type: "number" }));
        if (!length || length <= 0) return notify("Informe uma metragem válida.", true);
        await api(`/api/map/cables/${cableId}/reserves/`, {
            method: "POST",
            body: JSON.stringify({ latitude: latlng.lat, longitude: latlng.lng, length_m: length }),
        });
        clearTool();
        await loadStructure();
        notify(`Reserva de ${length} m adicionada.`);
    }
    async function editReserve(cableId, reserve) {
        const length = Number(await askValue({ title: "Editar reserva técnica", label: "Nova metragem", value: String(reserve.metragem), type: "number" }));
        if (!length || length <= 0) return;
        await api(`/api/map/cables/${cableId}/reserves/${reserve.id}/`, {
            method: "PATCH",
            body: JSON.stringify({ latitude: reserve.latitude, longitude: reserve.longitude, length_m: length, label: reserve.label || "" }),
        });
        await loadStructure();
        notify("Reserva atualizada.");
    }
    async function deleteReserve(cableId, reserveId) {
        if (!confirm("Excluir esta reserva técnica?")) return;
        await api(`/api/map/cables/${cableId}/reserves/${reserveId}/`, { method: "DELETE" });
        await loadStructure();
        notify("Reserva excluída.");
    }
    async function convertReserve(cableId, reserveId) {
        const choice = await askValue({ title: "Transformar reserva", label: "Novo equipamento", value: "CEO", options: [{ value: "CEO", label: "CEO" }, { value: "CDO", label: "CDO" }, { value: "CTO", label: "CTO" }] });
        if (!choice) return;
        const normalized = choice.trim().toUpperCase();
        if (!["CTO", "CEO", "CDO"].includes(normalized)) return notify("Escolha CTO, CEO ou CDO.", true);
        const name = await askValue({ title: `Nova ${normalized}`, label: "Nome do equipamento", value: `${normalized}-${reserveId}` });
        if (!name) return;
        await api(`/api/map/cables/${cableId}/reserves/${reserveId}/convert/`, {
            method: "POST",
            body: JSON.stringify({ element_type: normalized === "CTO" ? "cto" : "splice_box", element_subtype: normalized.toLowerCase(), name, code: name }),
        });
        await loadStructure();
        notify(`${normalized} inserida e cabo dividido em dois trechos.`);
    }
    async function insertElementAt(cableId, latlng) {
        const choice = await askValue({ title: "Inserir no cabo", label: "Equipamento", value: "CEO", options: [{ value: "CEO", label: "CEO" }, { value: "CDO", label: "CDO" }, { value: "CTO", label: "CTO" }] });
        if (!choice) return;
        const normalized = choice.trim().toUpperCase();
        if (!["CTO", "CEO", "CDO"].includes(normalized)) return notify("Escolha CTO, CEO ou CDO.", true);
        const name = await askValue({ title: `Nova ${normalized}`, label: "Nome do equipamento", value: `${normalized}-NOVO` });
        if (!name) return;
        const created = await api(`/api/map/cables/${cableId}/reserves/`, {
            method: "POST",
            body: JSON.stringify({ latitude: latlng.lat, longitude: latlng.lng, length_m: 1, label: "Conversão" }),
        });
        await api(`/api/map/cables/${cableId}/reserves/${created.reserve.id}/convert/`, {
            method: "POST",
            body: JSON.stringify({ element_type: normalized === "CTO" ? "cto" : "splice_box", element_subtype: normalized.toLowerCase(), name, code: name }),
        });
        clearTool();
        await loadStructure();
        notify(`${normalized} inserida; o cabo foi dividido em dois trechos.`);
    }
    async function editCable(id) {
        map.closePopup();
        const data = await api(`/api/map/cables/${id}/`);
        const cable = data.cable;
        state.editingCableId = id;
        cableForm.reset();
        populateConnectionSelects();
        ["name", "code", "description", "cable_type", "fiber_count", "cable_model_id", "origin_id", "destination_id"].forEach((name) => {
            cableForm.elements[name].value = cable[name] ?? "";
        });
        cableForm.elements.cable_model_id.disabled = true;
        document.getElementById("cable-dialog-title").textContent = `Editar ${cable.name}`;
        document.getElementById("edit-geometry-button").hidden = false;
        cableDialog.showModal();
    }
    async function managePole(id) {
        const data = await api(`/api/map/elements/${id}/pole/`);
        poleForm.querySelector('[name="pole_id"]').value = id;
        poleForm.dataset.cables = JSON.stringify(data.cables);
        document.getElementById("pole-dialog-title").textContent = `Infraestrutura · ${data.pole.name}`;
        document.getElementById("pole-cables").innerHTML = data.cables.map((item) =>
            `<div class="pole-list-item"><svg viewBox="0 0 24 24"><path d="M3 17c5 0 5-10 10-10s4 7 8 7"></path><circle cx="3" cy="17" r="2"></circle><circle cx="21" cy="14" r="2"></circle></svg>${escapeHtml(item.name)}</div>`
        ).join("") || '<p class="help-text">Nenhum cabo passa a até 8 metros deste poste.</p>';
        document.getElementById("pole-equipment").innerHTML = data.equipment.map((item) =>
            `<div class="pole-list-item">${escapeHtml(item.name)} · ${escapeHtml(item.type === "splice_box" ? "CEO" : "CTO")}</div>`
        ).join("") || '<p class="help-text">Nenhuma CTO ou CEO instalada neste poste.</p>';
        document.getElementById("pole-add-reserve").disabled = !data.cables.length;
        document.getElementById("pole-help").textContent = data.cables.length
            ? "A reserva será vinculada a um dos cabos detectados neste poste."
            : "Para adicionar reserva, primeiro desenhe ou mova um cabo para passar pelo poste.";
        if (!poleDialog.open) poleDialog.showModal();
    }
    function openPoleEquipmentForm(elementType) {
        const label = elementType === "cto" ? "CTO" : "CEO";
        poleActionForm.reset();
        poleActionForm.elements.action.value = "add_equipment";
        poleActionForm.elements.element_type.value = elementType;
        document.getElementById("pole-action-title").textContent = `Instalar ${label} no poste`;
        document.getElementById("pole-action-name-wrap").hidden = false;
        document.getElementById("pole-action-cable-wrap").hidden = true;
        document.getElementById("pole-action-length-wrap").hidden = true;
        document.getElementById("pole-action-label-wrap").hidden = true;
        poleActionDialog.showModal();
        poleActionForm.elements.name.focus();
    }
    function openPoleReserveForm() {
        const cables = JSON.parse(poleForm.dataset.cables || "[]");
        if (!cables.length) return notify("Nenhum cabo passa por este poste.", true);
        poleActionForm.reset();
        poleActionForm.elements.action.value = "add_reserve";
        poleActionForm.elements.cable_id.innerHTML = cables.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
        document.getElementById("pole-action-title").textContent = "Adicionar reserva no poste";
        document.getElementById("pole-action-name-wrap").hidden = true;
        document.getElementById("pole-action-cable-wrap").hidden = false;
        document.getElementById("pole-action-length-wrap").hidden = false;
        document.getElementById("pole-action-label-wrap").hidden = false;
        poleActionDialog.showModal();
    }
    async function savePoleAction() {
        const poleId = poleForm.querySelector('[name="pole_id"]').value;
        const payload = Object.fromEntries(new FormData(poleActionForm));
        await api(`/api/map/elements/${poleId}/pole/`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        poleActionDialog.close();
        await loadStructure();
        await managePole(poleId);
        notify(payload.action === "add_reserve" ? "Reserva adicionada ao cabo." : "Equipamento instalado no poste.");
    }
    function nearestElement(latlng) {
        let match = null;
        let distance = 36;
        state.elements.forEach((feature) => {
            const point = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
            const pixels = map.latLngToContainerPoint(latlng).distanceTo(map.latLngToContainerPoint(point));
            if (pixels < distance) { distance = pixels; match = feature; }
        });
        return match;
    }
    async function startGeometryEdit(cableId) {
        // MAP_V07556_CABLE_CONTEXT_MENU: aceita um id direto (chamado pelo
        // menu de botão direito, sem precisar abrir o diálogo antes); sem
        // argumento, cai no comportamento antigo (botão dentro do diálogo,
        // que já deixa state.editingCableId setado via editCable()).
        if (cableId != null) state.editingCableId = cableId;
        const data = await api(`/api/map/cables/${state.editingCableId}/`);
        if (cableDialog.open) cableDialog.close();
        map.closePopup();
        clearTool();
        state.geometryCableId = data.cable.id;
        state.tool = "geometry";
        const coordinates = data.cable.geometry.coordinates[0];
        state.drawingLine = L.polyline(coordinates.map((p) => [p[1], p[0]]), { color: "#2dd4bf", weight: 5, dashArray: "10 6" }).addTo(map);
        state.geometryHandles = coordinates.map((p, index) => {
            const handle = L.marker([p[1], p[0]], {
                draggable: true,
                icon: L.divIcon({ className: "", html: '<div class="geometry-handle"></div>', iconSize: [16, 16], iconAnchor: [8, 8] }),
            }).addTo(map);
            handle.on("drag", () => {
                const endpoint = index === 0 || index === state.geometryHandles.length - 1;
                const near = endpoint ? nearestElement(handle.getLatLng()) : null;
                if (near) {
                    const coords = near.geometry.coordinates;
                    handle.setLatLng([coords[1], coords[0]]);
                }
                state.drawingLine.setLatLngs(state.geometryHandles.map((item) => item.getLatLng()));
            });
            return handle;
        });
        drawingBar.hidden = false;
        drawingBar.querySelector("span").textContent = "Arraste os pontos. As pontas encaixam nos elementos próximos.";
        notify("Movendo o traçado do cabo.");
    }
    async function loadStructure(fit = false) {
        const structureLoadGeneration = ++state.structureLoadGeneration;
        state.lightAnimationGeneration += 1;
        const lightGeneration = state.lightAnimationGeneration;
        cableLayer.clearLayers();
        Object.values(structureLayers).forEach((pair) => { pair.cluster.clearLayers(); pair.plain.clearLayers(); });
        state.elementMarkers.clear();
        if (!state.projectId) {
            state.elements = [];
            state.cables = [];
            document.getElementById("element-count").textContent = "0";
            document.getElementById("cable-count").textContent = "0";
            populateConnectionSelects();
            return;
        }
        const query = `?project_id=${encodeURIComponent(state.projectId)}`;
        const [elements, cables, routes] = await Promise.all([api(`/api/map/elements/${query}`), api(`/api/map/cables/${query}`), api(`/api/map/routes/${query}`)]);
        if (structureLoadGeneration !== state.structureLoadGeneration) return;
        state.elements = elements.features;
        state.cables = cables.features;
        window.mapV092?.setData?.({
            routes: routes.features,
            elements: elements.features,
            cables: cables.features,
            projectId: state.projectId,
        });
        const lightSelect = document.getElementById("light-source-select");
        const currentLight = state.lightSourceId || lightSelect.value;
        lightSelect.innerHTML = '<option value="">Selecione a OLT de origem</option>';
        elements.features.filter((feature) => feature.properties.tipo === "olt").forEach((feature) => {
            lightSelect.add(new Option(`${feature.properties.nome} (elemento avulso)`, `element:${feature.properties.id}`));
        });
        const rackOlts = new Map();
        cables.features.forEach((feature) => {
            const p = feature.properties;
            if (p.origin_olt_id && !rackOlts.has(p.origin_olt_id)) {
                rackOlts.set(p.origin_olt_id, `${p.origin_olt_name || "OLT"} · rack ${p.origem || "?"}`);
            }
        });
        rackOlts.forEach((label, oltId) => {
            lightSelect.add(new Option(label, `equipment:${oltId}`));
        });
        if (currentLight) lightSelect.value = String(currentLight);
        state.lightSourceId = lightSelect.value || null;
        populateConnectionSelects();
        const bounds = [];
        const seenElementIds = new Set();
        elements.features.forEach((feature) => {
            // Dedup só por ID real repetido na MESMA resposta da API — nunca
            // por nome/tipo/coordenada. Dois NetworkElement distintos são
            // dois markers de verdade; esconder um deles pelo "menor ID"
            // já causou Rack/Torre vazios quando o ID escondido era o que
            // tinha os equipamentos de verdade.
            const elementId = String(feature?.properties?.id ?? "");
            if (elementId && seenElementIds.has(elementId)) {
                console.error(`map-editor: ID ${elementId} apareceu duas vezes na mesma resposta de /api/map/elements/ — segunda ocorrência ignorada no desenho (nenhum registro foi alterado).`);
                return;
            }
            if (elementId) seenElementIds.add(elementId);
            if (window.mapV092 && !window.mapV092.isElementVisible(feature)) return;
            const p = feature.properties;
            const [longitude, latitude] = feature.geometry.coordinates;
            const editing = canEdit && state.mapMode === "edit";
            const actions = editing ? `<br><button type="button" data-edit-element="${p.id}">Editar</button>${["cto", "splice_box", "rack"].includes(p.tipo) ? `<button type="button" data-unifilar="${p.id}">Fusões</button>` : ""}${p.tipo === "pole" ? `<button type="button" data-manage-pole="${p.id}">Infraestrutura</button>` : ""}${["rack", "tower"].includes(p.tipo) ? `<button type="button" data-manage-container="${p.id}">Equipamentos</button>` : ""}<button class="danger" type="button" data-delete-element="${p.id}">Excluir</button>` : "";
            const createMarker = () => {
                const marker = L.marker([latitude, longitude], { icon: networkIcon(p.tipo, p.subtype), draggable: editing });
                const unifiedEditor = ["rack", "tower", "cto", "splice_box"].includes(p.tipo);
                const typeLabel = ["cpd", "pop"].includes(String(p.subtype || "").toLowerCase())
                    ? "CPD/POP" : p.tipo === "splice_box" && p.subtype === "cdo" ? "CDO" : p.tipo.toUpperCase();
                if (!unifiedEditor) marker.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>${escapeHtml(typeLabel)}<br>${escapeHtml(p.codigo || "")}<br><button type="button" data-show-element-cables="${p.id}">Cabos e ligações</button>${actions}`);
                marker.bindTooltip(escapeHtml(p.nome), { permanent: true, direction: "top", offset: [0, -22], className: "network-name-label" });
                marker.on("click", (event) => {
                    if (state.tool !== "cable") {
                        if (!unifiedEditor) return;
                        if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
                        map.closePopup();
                        if (String(state.openingElementId || "") === String(p.id)) return;
                        state.openingElementId = p.id;
                        // MAP_V07534_ISOLATED_OPTICAL_WORKSPACE: CTO/CEO/CDO usam
                        // um runtime próprio, sem acessar #container-dialog,
                        // #map-master-container ou qualquer estado de Rack/Torre.
                        const opticalWorkspace = window.IXCOpticalWorkspace;
                        const opening = ["rack", "tower"].includes(p.tipo)
                            ? openContainerWorkspace(p.id)
                            : ["cto", "splice_box"].includes(p.tipo)
                                ? opticalWorkspace?.open
                                    ? opticalWorkspace.open(p.id)
                                    : Promise.reject(new Error("Editor óptico não foi carregado. Atualize os arquivos estáticos."))
                                : showUnifilar(p.id);
                        opening
                            .catch((error) => notify(error.message, true))
                            .finally(() => window.setTimeout(() => {
                                if (String(state.openingElementId || "") === String(p.id)) state.openingElementId = null;
                            }, 220));
                        return;
                    }
                    if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
                    map.closePopup();
                    const exactPoint = L.latLng(latitude, longitude);
                    if (!state.cableOriginId) {
                        state.cableOriginId = p.id;
                        state.cableCoordinates = [[longitude, latitude]];
                        state.drawingLine.setLatLngs([exactPoint]);
                        notify(`Origem: ${p.nome}. Desenhe o trajeto e clique no equipamento de destino.`);
                        return;
                    }
                    if (String(state.cableOriginId) === String(p.id)) return notify("Escolha outro equipamento como destino.", true);
                    state.cableDestinationId = p.id;
                    state.cableCoordinates.push([longitude, latitude]);
                    state.drawingLine.addLatLng(exactPoint);
                    openNewCableDialog();
                });
                marker.on("contextmenu", (event) => {
                    // O evento nunca pode vazar pro menu global "Adicionar ao
                    // mapa" quando ocorreu sobre um marker — por isso o corte
                    // de propagação roda ANTES de qualquer checagem/return,
                    // não só no caminho feliz. Ver map-v074-ui.js:openContextMenu
                    // (exclusão por seletor) como segunda camada de proteção.
                    if (event.originalEvent) {
                        L.DomEvent.preventDefault(event.originalEvent);
                        L.DomEvent.stopPropagation(event.originalEvent);
                        event.originalEvent.stopImmediatePropagation?.();
                    }
                    if (!editing || !unifiedEditor || !window.mapV0758?.openElementMenu) return;
                    map.closePopup();
                    const currentFeature = {
                        geometry: { coordinates: [longitude, latitude] },
                        properties: p,
                    };
                    const duplicates = state.elements.filter(
                        (feature) => elementDuplicateKey(feature) === elementDuplicateKey(currentFeature),
                    );
                    const removeById = async (elementId) => {
                        await api(`/api/map/elements/${elementId}/`, { method: "DELETE" });
                        await loadStructure();
                        notify(`Registro ID ${elementId} excluído.`);
                    };
                    window.mapV0758.openElementMenu({
                        originalEvent: event.originalEvent,
                        element: p,
                        duplicates,
                        removeById,
                        edit: () => editElement(p.id).catch((error) => notify(error.message, true)),
                        // MAP_V07534_ISOLATED_OPTICAL_WORKSPACE: o menu de contexto
                        // acompanha o clique normal e mantém Rack/Torre isolados.
                        fusions: ["cto", "splice_box"].includes(p.tipo)
                            ? () => {
                                const opticalWorkspace = window.IXCOpticalWorkspace;
                                if (!opticalWorkspace?.open) {
                                    notify("Editor óptico não foi carregado. Atualize os arquivos estáticos.", true);
                                    return;
                                }
                                opticalWorkspace.open(p.id).catch((error) => notify(error.message, true));
                            }
                            : () => openContainerWorkspace(p.id).catch((error) => notify(error.message, true)),
                        remove: async () => {
                            try {
                                await removeById(p.id);
                            } catch (error) { notify(error.message, true); }
                        },
                    });
                });
                marker.on("popupopen", () => {
                    popupAction(`[data-edit-element="${p.id}"]`, () => editElement(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-unifilar="${p.id}"]`, () => showUnifilar(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-manage-pole="${p.id}"]`, () => managePole(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-manage-container="${p.id}"]`, () => openContainerWorkspace(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-delete-element="${p.id}"]`, () => deleteElement(p.id).catch((error) => notify(error.message, true)));
                });
                if (editing) marker.on("dragend", async () => {
                    const position = marker.getLatLng();
                    const original = L.latLng(latitude, longitude);
                    const accepted = await window.mapV0758?.confirmAction?.({
                        title: "Salvar nova posição?",
                        message: `O ponto ${p.nome} foi movido. Deseja gravar a nova posição e atualizar as pontas dos cabos?`,
                        confirmLabel: "Salvar posição",
                        cancelLabel: "Voltar ao local anterior",
                    });
                    if (!accepted) {
                        marker.setLatLng(original);
                        notify("Movimento cancelado; o ponto voltou à posição anterior.");
                        return;
                    }
                    try {
                        await api(`/api/map/elements/${p.id}/position/`, { method: "PATCH", body: JSON.stringify({ latitude: position.lat, longitude: position.lng }) });
                        await loadStructure();
                        notify("Posição e pontas dos cabos atualizadas.");
                    } catch (error) { marker.setLatLng(original); notify(error.message, true); loadStructure(); }
                });
                return marker;
            };
            const structureCategory = ["cto", "splice_box"].includes(p.tipo) ? p.tipo : "other";
            if (state.elementMarkers.has(elementId)) {
                // Proteção estrutural: nunca duas entradas no controle
                // central pro mesmo ID (não deveria acontecer, já que
                // seenElementIds acima cobre a mesma resposta — isso só
                // pegaria uma regressão futura no código, não dado real).
                return;
            }
            // Uma instância de marker por camada (plain/cluster), mas nunca
            // as duas camadas visíveis ao mesmo tempo — refreshEquipmentLayer()
            // é quem decide qual delas fica no mapa. Registradas juntas em
            // elementMarkers pra nunca perder o vínculo com o ID real.
            const clusterMarker = createMarker();
            const plainMarker = createMarker();
            clusterMarker.addTo(structureLayers[structureCategory].cluster);
            plainMarker.addTo(structureLayers[structureCategory].plain);
            if (elementId) state.elementMarkers.set(elementId, { plain: plainMarker, cluster: clusterMarker, category: structureCategory });
            bounds.push([latitude, longitude]);
        });
        refreshEquipmentLayer();
        const illuminatedCables = new Set();
        if (state.lightSourceId && document.getElementById("layer-light-flow").checked) {
            const cableById = new Map(cables.features.map((feature) => [feature.properties.id, feature]));
            const [sourceType, sourceId] = String(state.lightSourceId).split(":");
            const queue = cables.features
                .filter((feature) => sourceType === "equipment"
                    ? feature.properties.origin_olt_id === Number(sourceId)
                    : feature.properties.origin_id === Number(sourceId))
                .map((feature) => feature.properties.id);
            const seedCount = queue.length;
            while (queue.length) {
                const cableId = queue.shift();
                if (illuminatedCables.has(cableId)) continue;
                illuminatedCables.add(cableId);
                const cable = cableById.get(cableId);
                (cable?.properties.optical_next_cable_ids || []).forEach((nextId) => {
                    const next = cableById.get(nextId);
                    if (
                        next
                        && next.properties.origin_id === cable.properties.destination_id
                        && !illuminatedCables.has(nextId)
                    ) queue.push(nextId);
                });
            }
            if (state.lastAnnouncedLightSourceId !== state.lightSourceId) {
                state.lastAnnouncedLightSourceId = state.lightSourceId;
                if (!seedCount) {
                    notify("Nenhum cabo encontrado para essa OLT. Confira se há um cordão da PON e uma fusão de fibra na mesma porta do DIO.", true);
                } else {
                    notify(`Sinal de luz ligado em ${illuminatedCables.size} cabo(s) a partir de ${lightSelect.options[lightSelect.selectedIndex]?.text || "OLT"}.`);
                }
            }
        }
        cables.features.forEach((feature) => {
            if (window.mapV092 && !window.mapV092.isCableVisible(feature)) return;
            const p = feature.properties;
            const illuminated = illuminatedCables.has(p.id);
            const line = L.geoJSON(feature, { style: {
                color: selectedProject()?.color || "#2dd4bf",
                weight: 4,
                opacity: .86,
            } });
            const editing = canEdit && state.mapMode === "edit";
            // MAP_V07556_CABLE_CONTEXT_MENU: clique esquerdo não abre mais
            // popup nenhum (bindPopup removido) — só os fluxos de ferramenta
            // armada abaixo ("+ Reserva"/"+ CTO/CEO") continuam reagindo ao
            // clique esquerdo. Todas as ações que ficavam no popup (editar,
            // reserva, inserir, excluir) migraram pro menu de botão direito,
            // que também ganhou "Editar rota".
            line.bindTooltip(escapeHtml(p.nome), { permanent: true, sticky: true, className: "cable-name-label" });
            line.on("click", (event) => {
                if (state.tool === "reserve" && state.reserveCableId === p.id) {
                    L.DomEvent.stopPropagation(event);
                    createReserveAt(p.id, event.latlng).catch((error) => notify(error.message, true));
                } else if (state.tool === "insert" && state.insertCableId === p.id) {
                    L.DomEvent.stopPropagation(event);
                    insertElementAt(p.id, event.latlng).catch((error) => notify(error.message, true));
                }
            });
            line.on("contextmenu", (event) => {
                if (event.originalEvent) {
                    L.DomEvent.preventDefault(event.originalEvent);
                    L.DomEvent.stopPropagation(event.originalEvent);
                    event.originalEvent.stopImmediatePropagation?.();
                }
                mapContextMenu.hidden = true;
                openCableContextMenu(p, event, editing);
            });
            line.addTo(cableLayer);
            if (illuminated) {
                const light = L.geoJSON(feature, { interactive: false, style: {
                    color: "#fff7a3", weight: 7, opacity: 1,
                    dashArray: "1 20", lineCap: "round",
                } }).addTo(cableLayer);
                light.eachLayer((part) => part.getElement()?.classList.add("optical-light-path"));
                animateLightDirection(feature, lightGeneration);
            }
            if (!window.mapV092 || window.mapV092.areReservesVisible()) (p.reservas || []).forEach((reserve) => {
                const marker = L.marker([reserve.latitude, reserve.longitude], {
                    draggable: editing,
                    // MAP_V07525_ICON_SET: mesmo ícone de "espiral de cabo" do kit
                    // SVG fornecido, igual ao usado nos demais tipos de elemento.
                    icon: L.divIcon({ className: "", html: '<div class="reserve-marker"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 4C9.373 4 4 9.373 4 16s5.373 12 12 12 12-5.373 12-12c0-4.418-2.386-8.284-6-10.392"></path><path d="M16 10c-3.314 0-6 2.686-6 6s2.686 6 6 6 6-2.686 6-6c0-2.21-1.193-4.142-3-5.196"></path><path d="M16 14c-1.105 0-2 .895-2 2s.895 2 2 2 2-.895 2-2"></path></svg></div>', iconSize: [32, 32], iconAnchor: [16, 16] }),
                }).bindPopup(`<strong>Reserva técnica</strong><br>${reserve.metragem} m<br>${escapeHtml(reserve.label || "")}${editing ? `<br><button data-edit-reserve="${reserve.id}">Editar</button><button data-convert-reserve="${reserve.id}">Virar CTO/CEO</button><button class="danger" data-delete-reserve="${reserve.id}">Excluir</button>` : ""}`);
                marker.on("popupopen", () => {
                    popupAction(`[data-edit-reserve="${reserve.id}"]`, () => editReserve(p.id, reserve).catch((error) => notify(error.message, true)));
                    popupAction(`[data-convert-reserve="${reserve.id}"]`, () => convertReserve(p.id, reserve.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-delete-reserve="${reserve.id}"]`, () => deleteReserve(p.id, reserve.id).catch((error) => notify(error.message, true)));
                });
                if (editing) marker.on("dragend", () => {
                    const point = marker.getLatLng();
                    api(`/api/map/cables/${p.id}/reserves/${reserve.id}/`, {
                        method: "PATCH",
                        body: JSON.stringify({ latitude: point.lat, longitude: point.lng, length_m: reserve.metragem, label: reserve.label || "" }),
                    }).then(() => { reserve.latitude = point.lat; reserve.longitude = point.lng; notify("Reserva reposicionada."); })
                      .catch((error) => { notify(error.message, true); loadStructure(); });
                });
                marker.addTo(cableLayer);
            });
            line.getLayers().forEach((part) => part.getLatLngs().flat(Infinity).forEach((point) => bounds.push([point.lat, point.lng])));
        });
        routes.features.forEach((feature) => {
            if (!feature.geometry) return;
            if (window.mapV092 && !window.mapV092.isRouteVisible(feature)) return;
            const p = feature.properties;
            const line = L.geoJSON(feature, { style: { color: "#f7b731", weight: 4, opacity: .86 } });
            line.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>Rota importada`);
            line.addTo(cableLayer);
            line.getLayers().forEach((part) => part.getLatLngs().flat(Infinity).forEach((point) => bounds.push([point.lat, point.lng])));
        });
        document.getElementById("element-count").textContent = elements.count;
        document.getElementById("cable-count").textContent = cables.count + routes.count;
        if (fit && bounds.length) map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 });
    }
    function setTool(tool) {
        if (state.mapMode !== "edit") return notify("Clique no lápis para liberar as ferramentas de edição.", true);
        if (!state.projectId) return notify("Selecione um projeto primeiro.", true);
        clearTool();
        state.tool = tool;
        document.querySelectorAll(".tool-button").forEach((button) => button.classList.toggle("active", button.dataset.tool === tool));
        document.querySelectorAll("[data-quick-tool]").forEach((button) => button.classList.toggle("active", button.dataset.quickTool === tool));
        map.getContainer().style.cursor = "crosshair";
        if (tool === "cable") {
            state.cableCoordinates = [];
            state.cableOriginId = null;
            state.cableDestinationId = null;
            state.drawingLine = L.polyline([], { color: "#2dd4bf", dashArray: "8 6", weight: 4 }).addTo(map);
            drawingBar.hidden = false;
            notify("Clique no equipamento de origem, desenhe o trajeto e clique no equipamento de destino.");
        } else notify("Clique no mapa para posicionar o elemento.");
    }
    function clearTool() {
        state.tool = null;
        state.cableCoordinates = [];
        state.cableOriginId = null;
        state.cableDestinationId = null;
        if (state.drawingLine) map.removeLayer(state.drawingLine);
        state.geometryHandles.forEach((handle) => map.removeLayer(handle));
        state.geometryHandles = [];
        state.geometryCableId = null;
        state.reserveCableId = null;
        state.insertCableId = null;
        state.drawingExistingCableId = null;
        state.drawingLine = null;
        drawingBar.hidden = true;
        map.getContainer().style.cursor = "";
        document.querySelectorAll(".tool-button").forEach((button) => button.classList.remove("active"));
        document.querySelectorAll("[data-quick-tool]").forEach((button) => button.classList.remove("active"));
    }
    function openElementDialogAt(tool, latlng) {
        state.editingElementId = null;
        elementForm.reset();
        const actualTool = tool === "cdo" ? "splice_box" : tool === "cpd" ? "other" : tool;
        elementForm.elements.element_type.value = actualTool;
        elementForm.elements.element_subtype.value = tool === "cdo" ? "cdo" : tool === "splice_box" ? "ceo" : tool === "cpd" ? "pop" : "";
        document.getElementById("cpd-structure-fields-v092").hidden = tool !== "cpd";
        elementForm.elements.latitude.value = latlng.lat;
        elementForm.elements.longitude.value = latlng.lng;
        document.getElementById("cto-fields").hidden = actualTool !== "cto";
        document.getElementById("container-fields").hidden = !["rack", "tower"].includes(actualTool);
        document.getElementById("container-fields-title").textContent = actualTool === "tower" ? "Equipamentos da torre" : "Equipamentos do rack";
        populateSplitterCables(null);
        loadSplitterFibers("");
        const titles = { pole: "Novo poste", cto: "Nova CTO", splice_box: "Nova CEO", cdo: "Nova CDO", cpd: "Novo CPD/POP", rack: "Novo rack", tower: "Nova torre" };
        document.getElementById("element-dialog-title").textContent = titles[tool] || "Novo elemento";
        elementDialog.showModal();
    }
    map.on("click", (event) => {
        mapContextMenu.hidden = true;
        cableContextMenu.hidden = true;
        if (!state.tool) return;
        if (state.tool === "reserve") {
            createReserveAt(state.reserveCableId, event.latlng).catch((error) => notify(error.message, true));
            return;
        }
        if (state.tool === "insert") {
            insertElementAt(state.insertCableId, event.latlng).catch((error) => notify(error.message, true));
            return;
        }
        if (state.tool === "geometry") return;
        if (state.tool === "cable") {
            if (!state.cableOriginId) return notify("Primeiro clique no equipamento de origem.", true);
            state.cableCoordinates.push([event.latlng.lng, event.latlng.lat]);
            state.drawingLine.addLatLng(event.latlng);
            return;
        }
        openElementDialogAt(state.tool, event.latlng);
    });
    map.on("movestart zoomstart", () => { mapContextMenu.hidden = true; cableContextMenu.hidden = true; });
    // Menu de adicionar por clique direito: atalho para CTO/CEO/Rack/Torre
    // direto no ponto clicado, sem precisar armar a ferramenta na barra lateral.
    const mapContextMenu = document.createElement("div");
    mapContextMenu.className = "map-context-menu";
    mapContextMenu.hidden = true;
    mapContextMenu.innerHTML = [
        ["cto", "CTO"], ["splice_box", "CEO"], ["cdo", "CDO"], ["cpd", "CPD/POP"], ["rack", "Rack"], ["tower", "Torre"],
    ].map(([value, label]) => `<button type="button" data-add-at="${value}">${label}</button>`).join("");
    document.getElementById("map").appendChild(mapContextMenu);
    L.DomEvent.disableClickPropagation(mapContextMenu);
    let contextMenuLatLng = null;
    map.on("contextmenu", (event) => {
        if (event.originalEvent?.defaultPrevented || document.querySelector("#map-context-v074:not([hidden])")) return;
        L.DomEvent.preventDefault(event.originalEvent);
        if (state.mapMode !== "edit") return notify("Clique no lápis para liberar as ferramentas de edição.", true);
        if (!state.projectId) return notify("Selecione um projeto primeiro.", true);
        contextMenuLatLng = event.latlng;
        const point = map.latLngToContainerPoint(event.latlng);
        mapContextMenu.style.left = `${point.x}px`;
        mapContextMenu.style.top = `${point.y}px`;
        mapContextMenu.hidden = false;
    });
    mapContextMenu.querySelectorAll("[data-add-at]").forEach((button) => {
        button.addEventListener("click", () => {
            mapContextMenu.hidden = true;
            if (!contextMenuLatLng) return;
            clearTool();
            openElementDialogAt(button.dataset.addAt, contextMenuLatLng);
        });
    });

    // MAP_V07556_CABLE_CONTEXT_MENU: menu de botão direito do cabo — mesmo
    // padrão do mapContextMenu acima (div posicionada no ponto do clique,
    // clique propagado bloqueado pra não vazar pro mapa). "Editar rota" é
    // novo; as outras ações só migraram do popup antigo (removido) pra cá.
    const cableContextMenu = document.createElement("div");
    cableContextMenu.className = "map-context-menu map-cable-context-menu-v07556";
    cableContextMenu.hidden = true;
    document.getElementById("map").appendChild(cableContextMenu);
    L.DomEvent.disableClickPropagation(cableContextMenu);
    function openCableContextMenu(p, event, editing) {
        const point = map.latLngToContainerPoint(event.latlng);
        cableContextMenu.style.left = `${point.x}px`;
        cableContextMenu.style.top = `${point.y}px`;
        cableContextMenu.innerHTML = `
            <strong>${escapeHtml(p.nome)}</strong>
            <small>Cabo óptico · ${p.fibras} fibras · ${escapeHtml(p.origem || "Sem origem")} → ${escapeHtml(p.destino || "Sem destino")}</small>
            ${editing ? `
                <button type="button" data-cable-action="route">Editar rota</button>
                <button type="button" data-cable-action="edit">Editar/conectar</button>
                <button type="button" data-cable-action="reserve">+ Reserva</button>
                <button type="button" data-cable-action="insert">+ CTO/CEO</button>
                <button class="danger" type="button" data-cable-action="delete">Excluir</button>` : ""}`;
        cableContextMenu.hidden = false;
        if (!editing) return;
        cableContextMenu.querySelector('[data-cable-action="route"]').onclick = () => {
            cableContextMenu.hidden = true;
            startGeometryEdit(p.id).catch((error) => notify(error.message, true));
        };
        cableContextMenu.querySelector('[data-cable-action="edit"]').onclick = () => {
            cableContextMenu.hidden = true;
            editCable(p.id).catch((error) => notify(error.message, true));
        };
        cableContextMenu.querySelector('[data-cable-action="reserve"]').onclick = () => {
            cableContextMenu.hidden = true;
            clearTool(); state.tool = "reserve"; state.reserveCableId = p.id;
            notify("Clique no ponto do cabo onde ficará a reserva.");
        };
        cableContextMenu.querySelector('[data-cable-action="insert"]').onclick = () => {
            cableContextMenu.hidden = true;
            clearTool(); state.tool = "insert"; state.insertCableId = p.id;
            notify("Clique no ponto do cabo onde deseja inserir a CTO ou CEO.");
        };
        cableContextMenu.querySelector('[data-cable-action="delete"]').onclick = () => {
            cableContextMenu.hidden = true;
            deleteCable(p.id).catch((error) => notify(error.message, true));
        };
    }

    document.getElementById("collapse-sidebar").onclick = () => { sidebar.classList.toggle("collapsed"); setTimeout(() => map.invalidateSize(), 220); };
    document.querySelectorAll("[data-map-mode]").forEach((button) => {
        button.addEventListener("click", async () => {
            document.querySelectorAll("[data-map-mode]").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            const mode = button.dataset.mapMode;
            state.mapMode = mode;
            sidebar.classList.toggle("edit-mode", mode === "edit");
            clearTool();
            if (mode === "edit" && document.getElementById("map-sidebar").classList.contains("collapsed")) {
                document.getElementById("collapse-sidebar").click();
            }
            if (mode === "view" && !document.getElementById("map-sidebar").classList.contains("collapsed")) {
                document.getElementById("collapse-sidebar").click();
            }
            await loadStructure();
        });
    });
    document.getElementById("map-search-toggle").onclick = () => {
        const search = document.getElementById("map-search");
        search.hidden = !search.hidden;
        document.getElementById("map-search-toggle").classList.toggle("active", !search.hidden);
        if (!search.hidden) document.getElementById("map-search-query").focus();
    };

    document.getElementById("map-search-button").onclick = () => executeMapSearch().catch((error) => notify(error.message, true));
    document.getElementById("map-search-query").onkeydown = (event) => {
        if (event.key === "Enter") executeMapSearch().catch((error) => notify(error.message, true));
    };
    document.getElementById("map-search-mode").onchange = (event) => {
        const input = document.getElementById("map-search-query");
        input.placeholder = event.target.value === "address"
            ? "Rua, número, cidade e estado"
            : "CTO, CEO, OLT, poste, código ou cabo";
        document.getElementById("map-search-results").hidden = true;
        input.focus();
    };
    document.getElementById("map-gps-button").onclick = () => {
        if (!navigator.geolocation) return notify("Este navegador não oferece localização por GPS.", true);
        navigator.geolocation.getCurrentPosition(
            ({ coords }) => {
                map.setView([coords.latitude, coords.longitude], 20);
                L.circleMarker([coords.latitude, coords.longitude], { radius: 8, color: "#fff", fillColor: "#2dd4bf", fillOpacity: 1 }).addTo(map)
                    .bindTooltip("Minha localização", { permanent: false }).openTooltip();
            },
            () => notify("Não foi possível obter o GPS. Verifique a permissão do navegador.", true),
            { enableHighAccuracy: true, timeout: 12000 },
        );
    };
    document.querySelectorAll("[data-quick-tool]").forEach((button) => {
        button.onclick = () => setTool(button.dataset.quickTool);
    });
    document.querySelector("[data-quick-action='labels']").onclick = () => {
        const labels = document.getElementById("layer-labels");
        labels.checked = !labels.checked;
        loadStructure().catch((error) => notify(error.message, true));
    };
    projectSelect.onchange = async () => {
        state.projectId = projectSelect.value || null;
        canEdit = selectedProject() ? Boolean(selectedProject().can_edit) : hasEditAccess;
        clearTool(); updateTools();
        try { await loadStructure(true); notify(state.projectId ? "Projeto carregado. Escolha uma ferramenta para editar." : "Selecione um projeto."); }
        catch (error) { notify(error.message, true); }
    };
    document.querySelectorAll(".tool-button").forEach((button) => { button.onclick = () => setTool(button.dataset.tool); });
    document.querySelectorAll(".dialog-close").forEach((button) => { button.onclick = () => button.closest("dialog").close(); });
    document.getElementById("new-project-button").onclick = () => {
        if (!canEdit) return window.location.assign("/admin/login/?next=/mapa/");
        document.getElementById("project-form").reset(); projectDialog.showModal();
    };
    document.getElementById("project-form").onsubmit = async (event) => {
        event.preventDefault();
        try {
            const data = await api("/api/map/projects/", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(event.target))) });
            projectDialog.close(); await loadProjects(data.project.id); await loadStructure(); notify("Projeto criado. Agora você pode adicionar a estrutura.");
        } catch (error) { notify(error.message, true); }
    };
    document.getElementById("pole-add-cto").onclick = () => openPoleEquipmentForm("cto");
    document.getElementById("pole-add-ceo").onclick = () => openPoleEquipmentForm("splice_box");
    document.getElementById("pole-add-reserve").onclick = () => openPoleReserveForm();
    poleActionForm.onsubmit = (event) => {
        event.preventDefault();
        savePoleAction().catch((error) => notify(error.message, true));
    };
    elementForm.onsubmit = async (event) => {
        event.preventDefault();
        if (state.elementSubmitLock) return;
        state.elementSubmitLock = true;
        const submitButton = elementForm.querySelector('button[type="submit"]');
        if (submitButton) submitButton.disabled = true;
        const payload = Object.fromEntries(new FormData(event.target));
        const cpdFields = document.getElementById("cpd-structure-fields-v092");
        if (cpdFields && !cpdFields.hidden) payload.element_type = payload.structure_profile || "other";
        else if (payload.structure_profile) payload.element_type = payload.structure_profile;
        delete payload.structure_profile;
        if (!payload.element_subtype) delete payload.element_subtype;
        if (!payload.splitter_input_cable_id) delete payload.splitter_input_cable_id;
        if (!payload.splitter_input_fiber_id) delete payload.splitter_input_fiber_id;
        payload.project = state.projectId; payload.enabled = true;
        try {
            const editing = Boolean(state.editingElementId);
            await api(editing ? `/api/map/elements/${state.editingElementId}/` : "/api/map/elements/create/", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
            elementDialog.close(); state.editingElementId = null; clearTool(); await loadStructure();
            notify(editing ? "Elemento atualizado." : "Elemento adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
        finally {
            state.elementSubmitLock = false;
            if (submitButton) submitButton.disabled = false;
        }
    };
    containerEquipmentForm.elements.equipment_type.onchange = updateContainerEquipmentFields;
    containerEquipmentForm.elements.provisioning_mode.onchange = updateContainerEquipmentFields;
    containerEquipmentForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        const editingId = state.editingContainerEquipmentId;
        try {
            await api(
                editingId ? `/api/map/elements/${state.containerId}/equipment/${editingId}/` : `/api/map/elements/${state.containerId}/equipment/`,
                { method: editingId ? "PATCH" : "POST", body: JSON.stringify(payload) },
            );
            await manageContainer(state.containerId);
            notify(editingId ? "Equipamento atualizado." : "Equipamento adicionado à estrutura.");
        } catch (error) { notify(error.message, true); }
    };
    containerCardForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        const equipmentId = payload.equipment_id;
        delete payload.equipment_id;
        try {
            await api(`/api/map/elements/${state.containerId}/equipment/${equipmentId}/cards/`, {
                method: "POST", body: JSON.stringify(payload),
            });
            await manageContainer(state.containerId);
            notify("Placa adicionada à OLT.");
        } catch (error) { notify(error.message, true); }
    };
    containerPortForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        const equipmentId = payload.equipment_id;
        delete payload.equipment_id;
        try {
            await api(`/api/map/elements/${state.containerId}/equipment/${equipmentId}/ports/`, {
                method: "POST", body: JSON.stringify(payload),
            });
            await manageContainer(state.containerId);
            notify("Portas adicionadas ao equipamento.");
        } catch (error) { notify(error.message, true); }
    };
    containerLinkForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        if (!payload.cable_id) delete payload.cable_id;
        try {
            await api(`/api/map/elements/${state.containerId}/equipment-links/`, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            await manageContainer(state.containerId);
            notify("Ligação interna criada.");
        } catch (error) { notify(error.message, true); }
    };
    elementForm.elements.splitter_input_cable_id.onchange = (event) => {
        loadSplitterFibers(event.target.value).catch((error) => notify(error.message, true));
    };
    function updateCableDefaults() {
        const model = state.cableModels.get(String(cableForm.elements.cable_model_id.value));
        cableForm.elements.fiber_count.value = model ? model.fiber_count : "";
        if (!cableForm.elements.name.value && state.cableOriginId && state.cableDestinationId) {
            const origin = state.elements.find((feature) => String(feature.properties.id) === String(state.cableOriginId));
            const destination = state.elements.find((feature) => String(feature.properties.id) === String(state.cableDestinationId));
            const suffix = model ? ` · ${model.fiber_count}F` : "";
            cableForm.elements.name.value = `CABO ${origin?.properties.nome || "ORIGEM"} → ${destination?.properties.nome || "DESTINO"}${suffix}`;
        }
    }
    function openNewCableDialog() {
        if (state.cableCoordinates.length < 2) return notify("O cabo precisa de pelo menos dois pontos.", true);
        state.editingCableId = null;
        cableForm.reset();
        populateConnectionSelects();
        cableForm.elements.origin_id.value = String(state.cableOriginId || "");
        cableForm.elements.destination_id.value = String(state.cableDestinationId || "");
        cableForm.elements.cable_model_id.disabled = false;
        document.getElementById("edit-geometry-button").hidden = true;
        document.getElementById("cable-dialog-title").textContent = "Novo cabo";
        updateCableDefaults();
        cableDialog.showModal();
    }
    document.getElementById("finish-drawing").onclick = () => {
        if (state.tool === "geometry") {
            const cableId = state.geometryCableId;
            const points = state.geometryHandles.map((handle) => handle.getLatLng());
            const coordinates = points.map((point) => [point.lng, point.lat]);
            const origin = nearestElement(points[0]);
            const destination = nearestElement(points[points.length - 1]);
            api(`/api/map/cables/${cableId}/geometry/`, { method: "PATCH", body: JSON.stringify({ coordinates }) })
                .then(() => api(`/api/map/cables/${cableId}/`, { method: "PATCH", body: JSON.stringify({ origin_id: origin?.properties.id || "", destination_id: destination?.properties.id || "" }) }))
                .then(() => { clearTool(); loadStructure(); notify("Traçado movido e pontas conectadas."); })
                .catch((error) => notify(error.message, true));
            return;
        }
        if (!state.cableDestinationId) return notify("Finalize clicando no equipamento de destino.", true);
        if (state.drawingExistingCableId) {
            const cableId = state.drawingExistingCableId;
            api(`/api/map/cables/${cableId}/geometry/`, {
                method: "PATCH",
                body: JSON.stringify({ coordinates: state.cableCoordinates }),
            })
                .then(() => api(`/api/map/cables/${cableId}/`, {
                    method: "PATCH",
                    body: JSON.stringify({
                        origin_id: state.cableOriginId,
                        destination_id: state.cableDestinationId,
                    }),
                }))
                .then(() => {
                    clearTool();
                    loadStructure();
                    notify("Cabo importado ligado e traçado no mapa.");
                })
                .catch((error) => notify(error.message, true));
            return;
        }
        openNewCableDialog();
    };
    document.getElementById("edit-geometry-button").onclick = () => startGeometryEdit().catch((error) => notify(error.message, true));
    document.getElementById("cancel-drawing").onclick = () => { clearTool(); notify("Desenho cancelado."); };
    cableForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        const editing = Boolean(state.editingCableId);
        if (!editing) {
            payload.project_id = state.projectId; payload.coordinates = state.cableCoordinates;
            payload.generate_fibers = Boolean(payload.cable_model_id);
            const origin = state.elements.find((feature) => String(feature.properties.id) === String(payload.origin_id || state.cableOriginId));
            const destination = state.elements.find((feature) => String(feature.properties.id) === String(payload.destination_id || state.cableDestinationId));
            const invert = await window.mapV0758?.reviewCableDirection?.({ origin, destination });
            if (invert) {
                const oldOrigin = payload.origin_id || state.cableOriginId;
                payload.origin_id = payload.destination_id || state.cableDestinationId;
                payload.destination_id = oldOrigin;
                payload.coordinates = [...state.cableCoordinates].reverse();
                state.cableCoordinates = payload.coordinates;
                state.cableOriginId = payload.origin_id;
                state.cableDestinationId = payload.destination_id;
                cableForm.elements.origin_id.value = String(payload.origin_id || "");
                cableForm.elements.destination_id.value = String(payload.destination_id || "");
                const originName = destination?.properties?.nome || "ORIGEM";
                const destinationName = origin?.properties?.nome || "DESTINO";
                if (/^CABO\s/i.test(payload.name || "")) payload.name = `CABO ${originName} → ${destinationName}`;
            }
        }
        try {
            await api(editing ? `/api/map/cables/${state.editingCableId}/` : "/api/map/cables/create/", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
            cableDialog.close(); state.editingCableId = null; clearTool(); await loadStructure();
            notify(editing ? "Cabo e conexões atualizados." : "Cabo conectado e adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
    };
    // O botão de importação é controlado por kmz-import-wizard.js, que abre
    // o assistente de análise (sem gravar nada) antes de importar de fato.
    document.getElementById("layer-structure").onchange = () => {
        refreshCableLayer();
        refreshEquipmentLayer();
    };
    document.getElementById("layer-cables").onchange = refreshCableLayer;
    document.getElementById("layer-cto").onchange = refreshEquipmentLayer;
    document.getElementById("layer-ceo").onchange = refreshEquipmentLayer;
    ["online", "offline"].forEach((status) => {
        document.getElementById(`layer-${status}`).onchange = refreshClientLayers;
    });
    document.getElementById("group-clients").onchange = refreshClientLayers;
    document.getElementById("layer-clients").onchange = refreshClientLayers;
    document.getElementById("group-equipment").onchange = refreshEquipmentLayer;
    // Botões-ícone da barra inferior espelham os checkboxes de camada/agrupamento.
    document.querySelectorAll("[data-layer-toggle]").forEach((button) => {
        const checkbox = document.getElementById(button.dataset.layerToggle);
        if (!checkbox) return;
        const sync = () => {
            button.classList.toggle("active", checkbox.checked);
            button.setAttribute("aria-pressed", String(checkbox.checked));
        };
        sync();
        checkbox.addEventListener("change", sync);
        button.addEventListener("click", () => {
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event("change"));
        });
    });
    // Ícone de olho da trilha recolhida — espelha a camada "Geral"
    // (mesma técnica dos botões [data-layer-toggle] acima).
    const collapsedEyeToggle = document.getElementById("collapsed-eye-toggle");
    const structureCheckbox = document.getElementById("layer-structure");
    if (collapsedEyeToggle && structureCheckbox) {
        const syncCollapsedEye = () => collapsedEyeToggle.classList.toggle("is-hidden", !structureCheckbox.checked);
        syncCollapsedEye();
        structureCheckbox.addEventListener("change", syncCollapsedEye);
        collapsedEyeToggle.addEventListener("click", () => {
            structureCheckbox.checked = !structureCheckbox.checked;
            structureCheckbox.dispatchEvent(new Event("change"));
        });
    }
    document.getElementById("light-source-select").onchange = (event) => {
        state.lightSourceId = event.target.value || null;
        loadStructure().catch((error) => notify(error.message, true));
    };
    document.getElementById("layer-light-flow").onchange = () => loadStructure().catch((error) => notify(error.message, true));
    document.getElementById("layer-labels").onchange = refreshMapLabels;
    refreshMapLabels();
    cableForm.elements.cable_model_id.onchange = () => {
        if (!state.editingCableId) cableForm.elements.name.value = "";
        updateCableDefaults();
    };
    Promise.all([
        loadProjects(new URLSearchParams(window.location.search).get("project")), loadClients(),
        api("/api/map/cable-models/").then((data) => {
            const availableCounts = new Set();
            data.models.forEach((model) => {
                if (availableCounts.has(model.fiber_count)) return;
                availableCounts.add(model.fiber_count);
                state.cableModels.set(String(model.id), model);
                cableForm.elements.cable_model_id.add(new Option(`${model.fiber_count} fibras`, model.id));
            });
        }),
    ]).then(() => { updateTools(); notify(canEdit ? "Selecione ou crie um projeto." : "Visualização ativa. Entre como administrador para editar."); })
      .catch((error) => notify(error.message, true));

    // Usado pelo assistente de importação KMZ para desenhar a prévia
    // temporária no Leaflet sem gravar nada, e para recarregar a estrutura
    // depois de uma importação definitiva.
    window.networkMap = { map, loadStructure, showUnifilar, manageContainer, notify };
})();
