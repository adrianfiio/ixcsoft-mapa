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
        lightSourceId: null, lightAnimationGeneration: 0, mapMode: "view",
    };

    const googleConfigElement = document.getElementById("google-maps-config");
    const googleConfig = googleConfigElement
        ? JSON.parse(googleConfigElement.textContent)
        : { enabled: false, defaultLayer: "esri_satellite" };
    const map = L.map("map", { preferCanvas: true, maxZoom: 23 }).setView([-24.45, -50.62], 10);
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
    const structureLayer = L.layerGroup().addTo(map);
    const equipmentClusterLayer = L.markerClusterGroup({ chunkedLoading: true }).addTo(map);
    const equipmentPlainLayer = L.layerGroup();
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
        if (!response.ok) throw new Error(data.error || Object.values(data.errors || {}).flat().join(" ") || `Erro HTTP ${response.status}`);
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
        ["online", "offline"].forEach((status) => {
            map.removeLayer(clientLayers[status]);
            map.removeLayer(clientPlainLayers[status]);
            if (!document.getElementById(`layer-${status}`).checked) return;
            (grouped ? clientLayers[status] : clientPlainLayers[status]).addTo(map);
        });
    }
    function refreshEquipmentLayer() {
        map.removeLayer(equipmentClusterLayer);
        map.removeLayer(equipmentPlainLayer);
        if (!document.getElementById("layer-structure").checked) return;
        (document.getElementById("group-equipment").checked ? equipmentClusterLayer : equipmentPlainLayer).addTo(map);
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
    function networkIcon(type) {
        const labels = { cto: "CTO", splice_box: "CEO", olt: "OLT", dio: "DIO", rack: "RACK", tower: "TORRE" };
        const symbols = {
            pole: '<svg viewBox="0 0 24 28" aria-hidden="true"><path d="M3 7h18M12 2v23M6 25h12M7 7l5 6 5-6M8 17h8"></path></svg>',
            cto: '<svg viewBox="0 0 24 18" aria-hidden="true"><rect x="3" y="2" width="18" height="12" rx="2"></rect><path d="M7 6h10M7 10h10M7 14v3m5-3v3m5-3v3"></path></svg><small>CTO</small>',
            splice_box: '<svg viewBox="0 0 24 18" aria-hidden="true"><path d="M7 2h10l3 4v7l-3 3H7l-3-3V6z"></path><path d="M8 6h8M8 9h8M8 12h8"></path></svg><small>CEO</small>',
            olt: '<svg viewBox="0 0 24 18" aria-hidden="true"><rect x="3" y="2" width="18" height="14" rx="2"></rect><path d="M7 6h10M7 10h10M7 14h6"></path></svg><small>OLT</small>',
            rack: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="2"></rect><path d="M8 6h8M8 11h8M8 16h8"></path></svg><small>RACK</small>',
            tower: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 6 22m6-20 6 20M8 15h8M9 10h6M5 22h14"></path></svg><small>TORRE</small>',
        };
        const large = ["cto", "splice_box", "olt", "rack", "tower"].includes(type);
        return L.divIcon({
            className: "",
            html: `<div class="network-marker ${type}">${symbols[type] || labels[type] || "•"}</div>`,
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
            }).addTo(structureLayer);
            const duration = Math.max(2200, Math.min(8500, total * 7));
            const startedAt = performance.now();
            const frame = (timestamp) => {
                if (generation !== state.lightAnimationGeneration || !structureLayer.hasLayer(marker)) return;
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
        if (button) button.onclick = callback;
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
        const isCto = element.element_type === "cto";
        const isCeo = element.element_type === "splice_box";
        const isContainer = ["rack", "tower"].includes(element.element_type);
        document.getElementById("cto-fields").hidden = !isCto;
        document.getElementById("ceo-fields").hidden = !isCeo;
        document.getElementById("container-fields").hidden = !isContainer;
        document.getElementById("container-fields-title").textContent = element.element_type === "tower" ? "Equipamentos da torre" : "Equipamentos do rack";
        elementForm.elements.internal_equipment_text.value = (element.internal_equipment || []).join("\n");
        if (isCto && element.cto) {
            const splitter = element.cto.splitters[0];
            elementForm.elements.cto_capacity.value = element.cto.capacity || 8;
            elementForm.elements.splitter_ratio.value = splitter?.ratio || element.cto.splitter_ratio || "1:8";
            elementForm.elements.splitter_ports.value = splitter?.output_ports || element.cto.capacity || 8;
            populateSplitterCables(element.cto, splitter?.input_cable?.id);
            await loadSplitterFibers(splitter?.input_cable?.id, splitter?.input_fiber?.id);
        }
        if (isCeo && element.splice_box) {
            elementForm.elements.ceo_tray_count.value = element.splice_box.tray_count || 1;
            elementForm.elements.ceo_splitters_per_tray.value = element.splice_box.splitters_per_tray || 0;
            elementForm.elements.ceo_splitter_ratio.value = element.splice_box.splitter_ratio || "1:8";
        }
        document.getElementById("element-dialog-title").textContent = `Editar ${element.name}`;
        elementDialog.showModal();
    }
    async function showUnifilar(id) {
        const data = await api(`/api/map/elements/${id}/`);
        const element = data.element;
        document.getElementById("unifilar-title").textContent = `Unifilar · ${element.name}`;
        document.getElementById("unifilar-subtitle").textContent = `${element.code || "Sem código"} · capacidade ${element.cto?.capacity || 0}`;
        const content = document.getElementById("unifilar-content");
        if (element.splice_box) {
            const [optical, savedLayout] = await Promise.all([
                api(`/api/map/elements/${element.id}/splices/`),
                api(`/api/map/elements/${element.id}/layout/`),
            ]);
            const layout = savedLayout.layout || {};
            const expandedCables = new Set((layout.expandedCables || []).map(String));
            const fiberById = new Map(optical.cables.flatMap((cable) => cable.fibers.map((fiber) => [String(fiber.id), fiber])));
            document.getElementById("unifilar-subtitle").textContent = `${element.code || "Sem código"} · ${element.splice_box.tray_count} bandeja(s)`;
            let selectedTrayId = element.splice_box.trays[0]?.id || null;
            const usedFiberIds = new Set([
                ...optical.splices.flatMap((splice) => [splice.input_fiber_id, splice.output_fiber_id]),
                ...optical.splitter_links.flatMap((link) => [
                    link.input_fiber_id,
                    ...link.ports.map((port) => port.output_fiber_id),
                ]),
            ].filter(Boolean));
            const incomingCables = optical.cables.filter((cable) => String(cable.destination_id) === String(element.id));
            const outgoingCables = optical.cables.filter((cable) => String(cable.origin_id) === String(element.id));
            const otherCables = optical.cables.filter((cable) => !incomingCables.includes(cable) && !outgoingCables.includes(cable));
            const orderedCables = [...incomingCables, ...outgoingCables, ...otherCables];
            const cableColumns = orderedCables.map((cable) => {
                const incomingIndex = incomingCables.indexOf(cable);
                const outgoingIndex = outgoingCables.indexOf(cable);
                const otherIndex = otherCables.indexOf(cable);
                const defaultPosition = incomingIndex >= 0
                    ? { x: 20, y: 30 + incomingIndex * 330 }
                    : outgoingIndex >= 0
                        ? { x: 900, y: 30 + outgoingIndex * 330 }
                        : { x: 20 + (otherIndex % 2) * 880, y: 30 + Math.floor(otherIndex / 2) * 330 };
                const position = layout[`cable-${cable.id}`] || defaultPosition;
                return `<section class="fiber-cable-node graph-node ${expandedCables.has(String(cable.id)) ? "expanded" : ""}" data-node-key="cable-${cable.id}" data-cable-node-id="${cable.id}" style="left:${position.x}px;top:${position.y}px"><header>${escapeHtml(cable.name)}<span><button class="expand-fibers" type="button" data-expand-cable="${cable.id}" title="Expandir ou recolher todas as fibras">${expandedCables.has(String(cable.id)) ? "−" : "+"}</button><span class="drag-grip">⋮⋮</span></span></header>
                <div class="fiber-port-list">${cable.fibers.map((fiber) => `<button type="button" class="fiber-port ${usedFiberIds.has(fiber.id) ? "used" : ""}" ${usedFiberIds.has(fiber.id) ? "" : 'draggable="true"'} data-used="${usedFiberIds.has(fiber.id)}" data-fiber-id="${fiber.id}" data-cable-id="${cable.id}" style="--fiber-color:${escapeHtml(fiber.color_hex)}"><i></i>F${fiber.number} · ${escapeHtml(fiber.color_name)}${usedFiberIds.has(fiber.id) ? " · Em uso" : ""}</button>`).join("") || '<span>Sem fibras geradas</span>'}</div></section>`;
            }).join("");
            const trayNodes = element.splice_box.trays.map((tray, index) => {
                const position = layout[`tray-${tray.id}`] || { x: 470, y: 40 + index * 155 };
                return `<div class="tray-node graph-node" data-node-key="tray-${tray.id}" data-tray-id="${tray.id}" style="left:${position.x}px;top:${position.y}px"><strong>${escapeHtml(tray.name || `Bandeja ${tray.number}`)} <span class="drag-grip">⋮⋮</span></strong><span>${tray.splice_count} fusões</span>
                ${tray.splitters.map((splitter) => `<div class="graph-splitter"><button type="button" class="splitter-input-port ${splitter.input_fiber_id ? "linked" : ""}" data-linked="${splitter.input_fiber_id || ""}" data-splitter-id="${splitter.id}">ENT</button><b>${escapeHtml(splitter.ratio)}</b><div class="splitter-output-grid">${splitter.ports.map((port) => `<button type="button" class="splitter-output-port ${port.output_fiber_id ? "linked" : ""}" data-linked="${port.output_fiber_id || ""}" data-port-id="${port.id}" title="Fibra ${port.number} de saída do splitter">F${port.number}</button>`).join("")}</div><div class="splitter-actions"><button type="button" data-edit-tray-splitter="${splitter.id}" data-ratio="${escapeHtml(splitter.ratio)}">Editar</button><button type="button" data-delete-tray-splitter="${splitter.id}">×</button></div></div>`).join("")}
                <button type="button" class="add-splitter-button" data-add-tray-splitter="${tray.id}">+ Splitter</button></div>`;
            }).join("");
            content.innerHTML = `<div class="ceo-instructions">Arraste os blocos. Clique numa bandeja para selecioná-la e em duas fibras para ligar. Clique numa linha para excluir. <label>Linhas <select id="connection-style"><option value="curve">Curvas</option><option value="straight">Retas</option><option value="orthogonal">Ortogonal</option></select></label><span class="unifilar-zoom"><button id="unifilar-zoom-out" type="button" title="Diminuir">−</button><output id="unifilar-zoom-value">100%</output><button id="unifilar-zoom-in" type="button" title="Ampliar">+</button><button id="unifilar-zoom-reset" type="button" title="Ajustar">Ajustar</button></span><div id="unifilar-feedback">F identifica as fibras do cabo e as fibras de saída do splitter.</div></div>
                <div class="optical-graph"><svg class="optical-links"></svg><div class="graph-nodes">${cableColumns || '<p>Nenhum cabo conectado à CEO.</p>'}${trayNodes}</div></div>`;
            let draggedFiber = null;
            let selectedFiber = null;
            let selectedSplitterPort = null;
            const createSplice = async (input, output) => {
                if (!input || input === output) return;
                const inputNode = content.querySelector(`[data-fiber-id="${input}"]`);
                const outputNode = content.querySelector(`[data-fiber-id="${output}"]`);
                if (inputNode.dataset.cableId === outputNode.dataset.cableId) return notify("Escolha fibras de cabos diferentes.", true);
                await api(`/api/map/elements/${element.id}/splices/`, {
                    method: "POST",
                    body: JSON.stringify({ tray_id: selectedTrayId, input_fiber_id: input, output_fiber_id: output }),
                });
                unifilarDialog.close(); await showUnifilar(element.id); notify("Fusão criada na caixa.");
            };
            content.querySelectorAll(".fiber-port").forEach((chip) => {
                chip.ondragstart = (event) => {
                    if (chip.dataset.used === "true") {
                        event.preventDefault();
                        return notify("Esta fibra já está em uso. Clique na linha atual para removê-la antes de reutilizar.", true);
                    }
                    draggedFiber = chip.dataset.fiberId;
                };
                chip.ondragover = (event) => event.preventDefault();
                chip.ondrop = async (event) => {
                    event.preventDefault();
                    try { await createSplice(draggedFiber, chip.dataset.fiberId); }
                    catch (error) { notify(error.message, true); }
                };
                chip.onclick = async () => {
                    if (chip.dataset.used === "true") {
                        return notify("Esta fibra já está em uso. Clique na linha atual para excluir a ligação antes de reutilizar.", true);
                    }
                    if (selectedSplitterPort) {
                        try {
                            await api(`/api/map/elements/${element.id}/splices/`, {
                                method: "POST",
                                body: JSON.stringify({ connection_type: "splitter_output", port_id: selectedSplitterPort, fiber_id: chip.dataset.fiberId }),
                            });
                            unifilarDialog.close(); await showUnifilar(element.id); notify("Saída do splitter conectada à fibra.");
                        } catch (error) { notify(error.message, true); }
                        return;
                    }
                    if (!selectedFiber) {
                        selectedFiber = chip.dataset.fiberId; chip.classList.add("selected");
                        notify("Primeira porta selecionada. Clique na porta de destino.");
                        return;
                    }
                    try { await createSplice(selectedFiber, chip.dataset.fiberId); }
                    catch (error) { notify(error.message, true); }
                };
            });
            content.querySelectorAll(".splitter-input-port").forEach((button) => {
                button.onclick = async () => {
                    if (button.dataset.linked) return notify("A entrada já está ligada. Clique na linha para removê-la antes de trocar.", true);
                    if (!selectedFiber) return notify("Selecione primeiro a fibra que alimentará o splitter.", true);
                    try {
                        await api(`/api/map/elements/${element.id}/splices/`, {
                            method: "POST",
                            body: JSON.stringify({ connection_type: "splitter_input", splitter_id: button.dataset.splitterId, fiber_id: selectedFiber }),
                        });
                        unifilarDialog.close(); await showUnifilar(element.id); notify("Fibra conectada à entrada do splitter.");
                    } catch (error) { notify(error.message, true); }
                };
                button.oncontextmenu = async (event) => {
                    event.preventDefault();
                    if (!button.dataset.linked || !confirm("Remover a fibra da entrada deste splitter?")) return;
                    await api(`/api/map/elements/${element.id}/splices/`, {
                        method: "POST",
                        body: JSON.stringify({ connection_type: "clear_splitter_input", splitter_id: button.dataset.splitterId }),
                    });
                    unifilarDialog.close(); await showUnifilar(element.id); notify("Ligação removida.");
                };
            });
            content.querySelectorAll(".splitter-output-port").forEach((button) => {
                button.onclick = () => {
                    if (button.dataset.linked) return notify(`A saída ${button.textContent} já está ligada. Clique na linha para removê-la antes de trocar.`, true);
                    selectedFiber = null;
                    selectedSplitterPort = button.dataset.portId;
                    content.querySelectorAll(".splitter-output-port").forEach((item) => item.classList.remove("selected"));
                    button.classList.add("selected");
                    notify("Saída do splitter selecionada. Clique na fibra de destino.");
                };
                button.oncontextmenu = async (event) => {
                    event.preventDefault();
                    if (!button.dataset.linked || !confirm("Remover a fibra desta saída?")) return;
                    await api(`/api/map/elements/${element.id}/splices/`, {
                        method: "POST",
                        body: JSON.stringify({ connection_type: "clear_splitter_output", port_id: button.dataset.portId }),
                    });
                    unifilarDialog.close(); await showUnifilar(element.id); notify("Ligação removida.");
                };
            });
            const redrawOpticalLinks = () => {
                const graph = content.querySelector(".optical-graph");
                const svg = content.querySelector(".optical-links");
                const graphRect = graph.getBoundingClientRect();
                svg.innerHTML = "";
                svg.setAttribute("viewBox", `0 0 ${graphRect.width} ${graphRect.height}`);
                const lineStyle = document.getElementById("connection-style").value;
                let gradientIndex = 0;
                const drawLink = (source, target, colors, action = null) => {
                    if (!source || !target) return;
                    const a = source.getBoundingClientRect(), b = target.getBoundingClientRect();
                    const x1 = a.left + a.width / 2 - graphRect.left, y1 = a.top + a.height / 2 - graphRect.top;
                    const x2 = b.left + b.width / 2 - graphRect.left, y2 = b.top + b.height / 2 - graphRect.top;
                    let path = `M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`;
                    if (lineStyle === "straight") path = `M${x1},${y1} L${x2},${y2}`;
                    if (lineStyle === "orthogonal") path = `M${x1},${y1} H${(x1+x2)/2} V${y2} H${x2}`;
                    const palette = (Array.isArray(colors) ? colors : [colors]).filter(Boolean);
                    let stroke = escapeHtml(palette[0] || "#94a3b8");
                    if (palette.length > 1 && palette[0] !== palette[1]) {
                        const gradientId = `fiber-gradient-${element.id}-${gradientIndex++}`;
                        svg.insertAdjacentHTML("beforeend", `<defs><linearGradient id="${gradientId}" gradientUnits="userSpaceOnUse" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"><stop offset="0%" stop-color="${escapeHtml(palette[0])}"></stop><stop offset="46%" stop-color="${escapeHtml(palette[0])}"></stop><stop offset="54%" stop-color="${escapeHtml(palette[1])}"></stop><stop offset="100%" stop-color="${escapeHtml(palette[1])}"></stop></linearGradient></defs>`);
                        stroke = `url(#${gradientId})`;
                    }
                    const actionData = action ? `data-link-type="${action.type}" data-link-id="${action.id}"` : "";
                    svg.insertAdjacentHTML("beforeend", `<path d="${path}" stroke="${stroke}" ${actionData}></path>`);
                };
                optical.splices.forEach((splice) => drawLink(
                    content.querySelector(`[data-fiber-id="${splice.input_fiber_id}"]`),
                    content.querySelector(`[data-fiber-id="${splice.output_fiber_id}"]`),
                    [splice.input.color_hex, splice.output.color_hex],
                    { type: "splice", id: splice.id }
                ));
                optical.splitter_links.forEach((link) => {
                    const inputColor = fiberById.get(String(link.input_fiber_id))?.color_hex;
                    if (link.input_fiber_id) drawLink(
                        content.querySelector(`[data-fiber-id="${link.input_fiber_id}"]`),
                        content.querySelector(`[data-splitter-id="${link.splitter_id}"]`),
                        inputColor,
                        { type: "splitter_input", id: link.splitter_id }
                    );
                    link.ports.forEach((port) => {
                        if (port.output_fiber_id) drawLink(
                            content.querySelector(`[data-port-id="${port.id}"]`),
                            content.querySelector(`[data-fiber-id="${port.output_fiber_id}"]`),
                            [inputColor, fiberById.get(String(port.output_fiber_id))?.color_hex],
                            { type: "splitter_output", id: port.id }
                        );
                    });
                });
                svg.querySelectorAll("[data-link-type]").forEach((path) => {
                    path.onclick = async () => {
                        if (!confirm("Excluir esta ligação para redesenhar?")) return;
                        if (path.dataset.linkType === "splice") {
                            await api(`/api/map/elements/${element.id}/splices/${path.dataset.linkId}/`, { method: "DELETE" });
                        } else {
                            await api(`/api/map/elements/${element.id}/splices/`, {
                                method: "POST",
                                body: JSON.stringify({
                                    connection_type: `clear_${path.dataset.linkType}`,
                                    [path.dataset.linkType === "splitter_input" ? "splitter_id" : "port_id"]: path.dataset.linkId,
                                }),
                            });
                        }
                        unifilarDialog.close(); await showUnifilar(element.id); notify("Ligação removida.");
                    };
                });
            };
            const styleSelect = document.getElementById("connection-style");
            styleSelect.value = layout.connectionStyle || "curve";
            styleSelect.onchange = async () => {
                layout.connectionStyle = styleSelect.value;
                redrawOpticalLinks();
                await api(`/api/map/elements/${element.id}/layout/`, {
                    method: "PATCH", body: JSON.stringify({ layout }),
                });
            };
            const graphNodes = content.querySelector(".graph-nodes");
            const zoomOutput = document.getElementById("unifilar-zoom-value");
            let graphZoom = Math.max(.5, Math.min(1.6, Number(layout.zoom) || 1));
            const applyGraphZoom = () => {
                graphNodes.style.transform = `scale(${graphZoom})`;
                graphNodes.style.transformOrigin = "top left";
                zoomOutput.value = `${Math.round(graphZoom * 100)}%`;
                requestAnimationFrame(redrawOpticalLinks);
            };
            const saveZoom = () => {
                layout.zoom = graphZoom;
                return api(`/api/map/elements/${element.id}/layout/`, {
                    method: "PATCH", body: JSON.stringify({ layout }),
                });
            };
            document.getElementById("unifilar-zoom-out").onclick = () => {
                graphZoom = Math.max(.5, graphZoom - .1); applyGraphZoom(); saveZoom();
            };
            document.getElementById("unifilar-zoom-in").onclick = () => {
                graphZoom = Math.min(1.6, graphZoom + .1); applyGraphZoom(); saveZoom();
            };
            document.getElementById("unifilar-zoom-reset").onclick = () => {
                const graph = content.querySelector(".optical-graph");
                graphZoom = Math.max(.5, Math.min(1, (graph.clientWidth - 40) / graphNodes.scrollWidth));
                applyGraphZoom(); saveZoom();
            };
            applyGraphZoom();
            content.querySelectorAll("[data-expand-cable]").forEach((button) => {
                button.onclick = async () => {
                    const cableId = String(button.dataset.expandCable);
                    const cableNode = content.querySelector(`[data-cable-node-id="${cableId}"]`);
                    cableNode.classList.toggle("expanded");
                    if (cableNode.classList.contains("expanded")) expandedCables.add(cableId);
                    else expandedCables.delete(cableId);
                    button.textContent = cableNode.classList.contains("expanded") ? "−" : "+";
                    layout.expandedCables = [...expandedCables];
                    redrawOpticalLinks();
                    await api(`/api/map/elements/${element.id}/layout/`, {
                        method: "PATCH", body: JSON.stringify({ layout }),
                    });
                };
            });
            content.querySelectorAll(".tray-node").forEach((tray) => {
                if (String(tray.dataset.trayId) === String(selectedTrayId)) tray.classList.add("active");
                tray.addEventListener("click", (event) => {
                    if (event.target.closest("button")) return;
                    selectedTrayId = tray.dataset.trayId;
                    content.querySelectorAll(".tray-node").forEach((item) => item.classList.remove("active"));
                    tray.classList.add("active");
                    notify("Bandeja selecionada para a próxima fusão.");
                });
            });
            content.querySelectorAll(".graph-node").forEach((node) => {
                const grip = node.querySelector(".drag-grip");
                grip.onpointerdown = (event) => {
                    event.preventDefault();
                    const graph = content.querySelector(".optical-graph");
                    const startX = event.clientX, startY = event.clientY;
                    const originX = parseFloat(node.style.left), originY = parseFloat(node.style.top);
                    grip.setPointerCapture(event.pointerId);
                    grip.onpointermove = (move) => {
                        node.style.left = `${Math.max(0, originX + (move.clientX - startX) / graphZoom)}px`;
                        node.style.top = `${Math.max(0, originY + (move.clientY - startY) / graphZoom)}px`;
                        redrawOpticalLinks();
                    };
                    grip.onpointerup = async () => {
                        grip.onpointermove = null;
                        layout[node.dataset.nodeKey] = {
                            x: Math.round(parseFloat(node.style.left)),
                            y: Math.round(parseFloat(node.style.top)),
                        };
                        await api(`/api/map/elements/${element.id}/layout/`, {
                            method: "PATCH", body: JSON.stringify({ layout }),
                        });
                        notify("Posição salva.");
                    };
                };
            });
            content.querySelectorAll("[data-add-tray-splitter]").forEach((button) => {
                button.onclick = async () => {
                    const ratio = await askValue({ title: "Adicionar splitter", label: "Proporção", value: "1:4", options: ["1:2", "1:4", "1:8", "1:16", "1:32", "1:64"].map((item) => ({ value: item, label: item })) });
                    if (!ratio) return;
                    try {
                        await api(`/api/map/elements/${element.id}/splitters/`, {
                            method: "POST",
                            body: JSON.stringify({ tray_id: button.dataset.addTraySplitter, ratio, output_ports: Number(ratio.split(":")[1]) }),
                        });
                        unifilarDialog.close(); await showUnifilar(element.id); notify("Splitter adicionado à bandeja.");
                    } catch (error) { notify(error.message, true); }
                };
            });
            content.querySelectorAll("[data-edit-tray-splitter]").forEach((button) => {
                button.onclick = async () => {
                    const ratio = await askValue({ title: "Editar splitter", label: "Nova proporção", value: button.dataset.ratio, options: ["1:2", "1:4", "1:8", "1:16", "1:32", "1:64"].map((item) => ({ value: item, label: item })) });
                    if (!ratio) return;
                    try {
                        await api(`/api/map/elements/${element.id}/splitters/${button.dataset.editTraySplitter}/`, {
                            method: "PATCH",
                            body: JSON.stringify({ ratio, output_ports: Number(ratio.split(":")[1]) }),
                        });
                        unifilarDialog.close(); await showUnifilar(element.id); notify("Splitter atualizado.");
                    } catch (error) { notify(error.message, true); }
                };
            });
            content.querySelectorAll("[data-delete-tray-splitter]").forEach((button) => {
                button.onclick = async () => {
                    if (!confirm("Excluir este splitter e suas ligações?")) return;
                    await api(`/api/map/elements/${element.id}/splitters/${button.dataset.deleteTraySplitter}/`, { method: "DELETE" });
                    unifilarDialog.close(); await showUnifilar(element.id); notify("Splitter excluído.");
                };
            });
            unifilarDialog.showModal();
            requestAnimationFrame(redrawOpticalLinks);
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
        unifilarDialog.showModal();
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
        const choice = await askValue({ title: "Transformar reserva", label: "Novo equipamento", value: "CEO", options: [{ value: "CEO", label: "CEO" }, { value: "CTO", label: "CTO" }] });
        if (!choice) return;
        const normalized = choice.trim().toUpperCase();
        if (!["CTO", "CEO"].includes(normalized)) return notify("Escolha CTO ou CEO.", true);
        const name = await askValue({ title: `Nova ${normalized}`, label: "Nome do equipamento", value: `${normalized}-${reserveId}` });
        if (!name) return;
        await api(`/api/map/cables/${cableId}/reserves/${reserveId}/convert/`, {
            method: "POST",
            body: JSON.stringify({ element_type: normalized === "CTO" ? "cto" : "splice_box", name, code: name }),
        });
        await loadStructure();
        notify(`${normalized} inserida e cabo dividido em dois trechos.`);
    }
    async function insertElementAt(cableId, latlng) {
        const choice = await askValue({ title: "Inserir no cabo", label: "Equipamento", value: "CEO", options: [{ value: "CEO", label: "CEO" }, { value: "CTO", label: "CTO" }] });
        if (!choice) return;
        const normalized = choice.trim().toUpperCase();
        if (!["CTO", "CEO"].includes(normalized)) return notify("Escolha CTO ou CEO.", true);
        const name = await askValue({ title: `Nova ${normalized}`, label: "Nome do equipamento", value: `${normalized}-NOVO` });
        if (!name) return;
        const created = await api(`/api/map/cables/${cableId}/reserves/`, {
            method: "POST",
            body: JSON.stringify({ latitude: latlng.lat, longitude: latlng.lng, length_m: 1, label: "Conversão" }),
        });
        await api(`/api/map/cables/${cableId}/reserves/${created.reserve.id}/convert/`, {
            method: "POST",
            body: JSON.stringify({ element_type: normalized === "CTO" ? "cto" : "splice_box", name, code: name }),
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
    async function startGeometryEdit() {
        const data = await api(`/api/map/cables/${state.editingCableId}/`);
        cableDialog.close();
        map.closePopup();
        clearTool();
        state.geometryCableId = data.cable.id;
        state.tool = "geometry";
        const coordinates = data.cable.geometry.coordinates[0];
        state.drawingLine = L.polyline(coordinates.map((p) => [p[1], p[0]]), { color: "#2dd4bf", weight: 5 }).addTo(map);
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
        state.lightAnimationGeneration += 1;
        const lightGeneration = state.lightAnimationGeneration;
        structureLayer.clearLayers();
        equipmentClusterLayer.clearLayers();
        equipmentPlainLayer.clearLayers();
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
        state.elements = elements.features;
        state.cables = cables.features;
        const lightSelect = document.getElementById("light-source-select");
        const currentLight = state.lightSourceId || lightSelect.value;
        lightSelect.innerHTML = '<option value="">Selecione a OLT de origem</option>';
        elements.features.filter((feature) => feature.properties.tipo === "olt").forEach((feature) => {
            lightSelect.add(new Option(feature.properties.nome, feature.properties.id));
        });
        if (currentLight) lightSelect.value = String(currentLight);
        state.lightSourceId = lightSelect.value || null;
        populateConnectionSelects();
        const bounds = [];
        const showLabels = document.getElementById("layer-labels").checked;
        elements.features.forEach((feature) => {
            const p = feature.properties;
            const [longitude, latitude] = feature.geometry.coordinates;
            const editing = canEdit && state.mapMode === "edit";
            const actions = editing ? `<br><button type="button" data-edit-element="${p.id}">Editar</button>${["cto", "splice_box"].includes(p.tipo) ? `<button type="button" data-unifilar="${p.id}">Unifilar</button>` : ""}${p.tipo === "pole" ? `<button type="button" data-manage-pole="${p.id}">Infraestrutura</button>` : ""}<button class="danger" type="button" data-delete-element="${p.id}">Excluir</button>` : "";
            const createMarker = () => {
                const marker = L.marker([latitude, longitude], { icon: networkIcon(p.tipo), draggable: editing });
                marker.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>${escapeHtml(p.tipo.toUpperCase())}<br>${escapeHtml(p.codigo || "")}${actions}`);
                if (showLabels) marker.bindTooltip(escapeHtml(p.nome), { permanent: true, direction: "top", offset: [0, -22], className: "network-name-label" });
                marker.on("click", (event) => {
                    if (state.tool !== "cable") return;
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
                marker.on("popupopen", () => {
                    popupAction(`[data-edit-element="${p.id}"]`, () => editElement(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-unifilar="${p.id}"]`, () => showUnifilar(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-manage-pole="${p.id}"]`, () => managePole(p.id).catch((error) => notify(error.message, true)));
                    popupAction(`[data-delete-element="${p.id}"]`, () => deleteElement(p.id).catch((error) => notify(error.message, true)));
                });
                if (editing) marker.on("dragend", async () => {
                    const position = marker.getLatLng();
                    try {
                        await api(`/api/map/elements/${p.id}/position/`, { method: "PATCH", body: JSON.stringify({ latitude: position.lat, longitude: position.lng }) });
                        await loadStructure();
                        notify("Posição e pontas dos cabos atualizadas.");
                    } catch (error) { notify(error.message, true); loadStructure(); }
                });
                return marker;
            };
            createMarker().addTo(equipmentClusterLayer);
            createMarker().addTo(equipmentPlainLayer);
            bounds.push([latitude, longitude]);
        });
        refreshEquipmentLayer();
        const illuminatedCables = new Set();
        if (state.lightSourceId && document.getElementById("layer-light-flow").checked) {
            const cableById = new Map(cables.features.map((feature) => [feature.properties.id, feature]));
            const queue = cables.features
                .filter((feature) => feature.properties.origin_id === Number(state.lightSourceId))
                .map((feature) => feature.properties.id);
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
        }
        cables.features.forEach((feature) => {
            const p = feature.properties;
            const illuminated = illuminatedCables.has(p.id);
            const line = L.geoJSON(feature, { style: {
                color: selectedProject()?.color || "#2dd4bf",
                weight: 4,
                opacity: .86,
            } });
            const editing = canEdit && state.mapMode === "edit";
            const actions = editing ? `<br><button type="button" data-edit-cable="${p.id}">Editar/conectar</button><button type="button" data-reserve-cable="${p.id}">+ Reserva</button><button type="button" data-insert-cable="${p.id}">+ CTO/CEO</button><button class="danger" type="button" data-delete-cable="${p.id}">Excluir</button>` : "";
            line.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>Cabo óptico · ${p.fibras} fibras<br>${escapeHtml(p.origem || "Sem origem")} → ${escapeHtml(p.destino || "Sem destino")}${actions}`);
            if (showLabels) line.bindTooltip(escapeHtml(p.nome), { permanent: true, sticky: true, className: "cable-name-label" });
            line.on("popupopen", () => {
                popupAction(`[data-edit-cable="${p.id}"]`, () => editCable(p.id).catch((error) => notify(error.message, true)));
                popupAction(`[data-delete-cable="${p.id}"]`, () => deleteCable(p.id).catch((error) => notify(error.message, true)));
                popupAction(`[data-reserve-cable="${p.id}"]`, () => {
                    map.closePopup(); clearTool(); state.tool = "reserve"; state.reserveCableId = p.id;
                    notify("Clique no ponto do cabo onde ficará a reserva.");
                });
                popupAction(`[data-insert-cable="${p.id}"]`, () => {
                    map.closePopup(); clearTool(); state.tool = "insert"; state.insertCableId = p.id;
                    notify("Clique no ponto do cabo onde deseja inserir a CTO ou CEO.");
                });
            });
            line.on("click", (event) => {
                if (state.tool === "reserve" && state.reserveCableId === p.id) {
                    L.DomEvent.stopPropagation(event);
                    createReserveAt(p.id, event.latlng).catch((error) => notify(error.message, true));
                } else if (state.tool === "insert" && state.insertCableId === p.id) {
                    L.DomEvent.stopPropagation(event);
                    insertElementAt(p.id, event.latlng).catch((error) => notify(error.message, true));
                }
            });
            line.addTo(structureLayer);
            if (illuminated) {
                const light = L.geoJSON(feature, { interactive: false, style: {
                    color: "#fff7a3", weight: 7, opacity: 1,
                    dashArray: "1 20", lineCap: "round",
                } }).addTo(structureLayer);
                light.eachLayer((part) => part.getElement()?.classList.add("optical-light-path"));
                animateLightDirection(feature, lightGeneration);
            }
            (p.reservas || []).forEach((reserve) => {
                const marker = L.marker([reserve.latitude, reserve.longitude], {
                    draggable: editing,
                    icon: L.divIcon({ className: "", html: '<div class="reserve-marker">↻</div>', iconSize: [32, 32], iconAnchor: [16, 16] }),
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
                marker.addTo(structureLayer);
            });
            line.getLayers().forEach((part) => part.getLatLngs().flat(Infinity).forEach((point) => bounds.push([point.lat, point.lng])));
        });
        routes.features.forEach((feature) => {
            const p = feature.properties;
            const line = L.geoJSON(feature, { style: { color: "#f7b731", weight: 4, opacity: .86 } });
            line.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>Rota importada`);
            line.addTo(structureLayer);
            line.getLayers().forEach((part) => part.getLatLngs().flat(Infinity).forEach((point) => bounds.push([point.lat, point.lng])));
        });
        document.getElementById("element-count").textContent = elements.count;
        document.getElementById("cable-count").textContent = cables.count + routes.count;
        if (fit && bounds.length) map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 });
    }
    function setTool(tool) {
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
    map.on("click", (event) => {
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
        state.editingElementId = null;
        elementForm.reset();
        elementForm.elements.element_type.value = state.tool;
        elementForm.elements.latitude.value = event.latlng.lat;
        elementForm.elements.longitude.value = event.latlng.lng;
        document.getElementById("cto-fields").hidden = state.tool !== "cto";
        document.getElementById("ceo-fields").hidden = state.tool !== "splice_box";
        document.getElementById("container-fields").hidden = !["rack", "tower"].includes(state.tool);
        document.getElementById("container-fields-title").textContent = state.tool === "tower" ? "Equipamentos da torre" : "Equipamentos do rack";
        populateSplitterCables(null);
        loadSplitterFibers("");
        const titles = { pole: "Novo poste", cto: "Nova CTO", splice_box: "Nova CEO", rack: "Novo rack", tower: "Nova torre" };
        document.getElementById("element-dialog-title").textContent = titles[state.tool] || "Novo elemento";
        elementDialog.showModal();
    });

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
        const payload = Object.fromEntries(new FormData(event.target));
        payload.internal_equipment = String(payload.internal_equipment_text || "")
            .split("\n").map((item) => item.trim()).filter(Boolean);
        delete payload.internal_equipment_text;
        if (!payload.splitter_input_cable_id) delete payload.splitter_input_cable_id;
        if (!payload.splitter_input_fiber_id) delete payload.splitter_input_fiber_id;
        payload.project = state.projectId; payload.enabled = true;
        try {
            const editing = Boolean(state.editingElementId);
            await api(editing ? `/api/map/elements/${state.editingElementId}/` : "/api/map/elements/create/", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
            elementDialog.close(); state.editingElementId = null; clearTool(); await loadStructure();
            notify(editing ? "Elemento atualizado." : "Elemento adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
    };
    elementForm.elements.splitter_input_cable_id.onchange = (event) => {
        loadSplitterFibers(event.target.value).catch((error) => notify(error.message, true));
    };
    function updateCableDefaults() {
        const model = state.cableModels.get(String(cableForm.elements.cable_model_id.value));
        if (model) cableForm.elements.fiber_count.value = model.fiber_count;
        cableForm.elements.fiber_count.readOnly = Boolean(model);
        if (!cableForm.elements.name.value && state.cableOriginId && state.cableDestinationId) {
            const origin = state.elements.find((feature) => String(feature.properties.id) === String(state.cableOriginId));
            const destination = state.elements.find((feature) => String(feature.properties.id) === String(state.cableDestinationId));
            const fiberCount = model?.fiber_count || cableForm.elements.fiber_count.value;
            cableForm.elements.name.value = `CABO ${origin?.properties.nome || "ORIGEM"} → ${destination?.properties.nome || "DESTINO"} · ${fiberCount}F`;
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
        cableForm.elements.fiber_count.readOnly = false;
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
        }
        try {
            await api(editing ? `/api/map/cables/${state.editingCableId}/` : "/api/map/cables/create/", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
            cableDialog.close(); state.editingCableId = null; clearTool(); await loadStructure();
            notify(editing ? "Cabo e conexões atualizados." : "Cabo conectado e adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
    };
    document.getElementById("import-button").onclick = () => document.getElementById("import-file").click();
    document.getElementById("import-file").onchange = async (event) => {
        const file = event.target.files[0];
        if (!file || !state.projectId) return;
        const formData = new FormData(); formData.append("file", file); notify(`Importando ${file.name}...`);
        try {
            const data = await api(`/api/map/projects/${state.projectId}/import/`, { method: "POST", body: formData });
            await loadStructure(true); notify(`Importação concluída: ${data.imported.elements} pontos e ${data.imported.routes} rotas.`);
        } catch (error) { notify(error.message, true); }
        event.target.value = "";
    };
    document.getElementById("layer-structure").onchange = (event) => {
        if (event.target.checked) structureLayer.addTo(map); else map.removeLayer(structureLayer);
        refreshEquipmentLayer();
    };
    ["online", "offline"].forEach((status) => {
        document.getElementById(`layer-${status}`).onchange = refreshClientLayers;
    });
    document.getElementById("group-clients").onchange = refreshClientLayers;
    document.getElementById("group-equipment").onchange = refreshEquipmentLayer;
    document.getElementById("light-source-select").onchange = (event) => {
        state.lightSourceId = event.target.value || null;
        loadStructure().catch((error) => notify(error.message, true));
    };
    document.getElementById("layer-light-flow").onchange = () => loadStructure().catch((error) => notify(error.message, true));
    document.getElementById("layer-labels").onchange = () => loadStructure().catch((error) => notify(error.message, true));
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
})();
