(function () {
    "use strict";

    const canEdit = document.body.dataset.canEdit === "true";
    const sidebar = document.getElementById("map-sidebar");
    const projectSelect = document.getElementById("project-select");
    const message = document.getElementById("editor-message");
    const projectDialog = document.getElementById("project-dialog");
    const elementDialog = document.getElementById("element-dialog");
    const cableDialog = document.getElementById("cable-dialog");
    const unifilarDialog = document.getElementById("unifilar-dialog");
    const elementForm = document.getElementById("element-form");
    const cableForm = document.getElementById("cable-form");
    const drawingBar = document.getElementById("drawing-bar");
    const state = {
        projectId: null, projects: [], elements: [], tool: null,
        cableCoordinates: [], drawingLine: null,
        editingElementId: null, editingCableId: null,
    };

    const map = L.map("map", { preferCanvas: true }).setView([-24.45, -50.62], 10);
    const streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 20, attribution: "&copy; OpenStreetMap" });
    const satelliteLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 20, attribution: "Tiles &copy; Esri" });
    streetLayer.addTo(map);
    L.control.layers({ "Mapa": streetLayer, "Satélite": satelliteLayer }, {}, { position: "topright" }).addTo(map);

    const clientLayers = {
        online: L.markerClusterGroup({ chunkedLoading: true }),
        offline: L.markerClusterGroup({ chunkedLoading: true }),
        unknown: L.markerClusterGroup({ chunkedLoading: true }),
    };
    const structureLayer = L.layerGroup().addTo(map);
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
    }
    function escapeHtml(value) {
        const item = document.createElement("span");
        item.textContent = value == null ? "" : String(value);
        return item.innerHTML;
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
        updateTools();
    }
    function clientIcon(status) {
        return L.divIcon({ className: "", html: `<div class="client-dot ${status}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
    }
    async function loadClients() {
        const data = await api("/api/map/access-points/");
        Object.values(clientLayers).forEach((layer) => layer.clearLayers());
        data.features.forEach((feature) => {
            const p = feature.properties || {};
            const status = ["online", "offline"].includes(p.status) ? p.status : "unknown";
            const [longitude, latitude] = feature.geometry.coordinates;
            const marker = L.marker([latitude, longitude], { icon: clientIcon(status) });
            marker.bindPopup(`<strong>${escapeHtml(p.cliente || "Cliente")}</strong><br>${escapeHtml(p.login || "")}<br>Status: ${escapeHtml(status)}<br>CTO: ${escapeHtml(p.cto || "-")}`);
            clientLayers[status].addLayer(marker);
        });
        document.getElementById("client-count").textContent = data.count || data.features.length;
    }
    function networkIcon(type) {
        const labels = { pole: "P", cto: "CTO", splice_box: "CEO", olt: "OLT", dio: "DIO" };
        return L.divIcon({ className: "", html: `<div class="network-marker ${type}">${labels[type] || "•"}</div>`, iconSize: [31, 31], iconAnchor: [15, 15] });
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
        document.getElementById("cto-fields").hidden = !isCto;
        if (isCto && element.cto) {
            const splitter = element.cto.splitters[0];
            elementForm.elements.cto_capacity.value = element.cto.capacity || 8;
            elementForm.elements.splitter_ratio.value = splitter?.ratio || element.cto.splitter_ratio || "1:8";
            elementForm.elements.splitter_ports.value = splitter?.output_ports || element.cto.capacity || 8;
            populateSplitterCables(element.cto, splitter?.input_cable?.id);
            await loadSplitterFibers(splitter?.input_cable?.id, splitter?.input_fiber?.id);
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
    async function editCable(id) {
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
        cableDialog.showModal();
    }
    async function loadStructure(fit = false) {
        structureLayer.clearLayers();
        if (!state.projectId) {
            state.elements = [];
            document.getElementById("element-count").textContent = "0";
            document.getElementById("cable-count").textContent = "0";
            populateConnectionSelects();
            return;
        }
        const query = `?project_id=${encodeURIComponent(state.projectId)}`;
        const [elements, cables, routes] = await Promise.all([api(`/api/map/elements/${query}`), api(`/api/map/cables/${query}`), api(`/api/map/routes/${query}`)]);
        state.elements = elements.features;
        populateConnectionSelects();
        const bounds = [];
        elements.features.forEach((feature) => {
            const p = feature.properties;
            const [longitude, latitude] = feature.geometry.coordinates;
            const marker = L.marker([latitude, longitude], { icon: networkIcon(p.tipo), draggable: canEdit });
            const actions = canEdit ? `<br><button type="button" data-edit-element="${p.id}">Editar</button>${p.tipo === "cto" ? `<button type="button" data-unifilar="${p.id}">Unifilar</button>` : ""}<button class="danger" type="button" data-delete-element="${p.id}">Excluir</button>` : "";
            marker.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>${escapeHtml(p.tipo.toUpperCase())}<br>${escapeHtml(p.codigo || "")}${actions}`);
            marker.on("popupopen", () => {
                popupAction(`[data-edit-element="${p.id}"]`, () => editElement(p.id).catch((error) => notify(error.message, true)));
                popupAction(`[data-unifilar="${p.id}"]`, () => showUnifilar(p.id).catch((error) => notify(error.message, true)));
                popupAction(`[data-delete-element="${p.id}"]`, () => deleteElement(p.id).catch((error) => notify(error.message, true)));
            });
            if (canEdit) marker.on("dragend", async () => {
                const position = marker.getLatLng();
                try {
                    await api(`/api/map/elements/${p.id}/position/`, { method: "PATCH", body: JSON.stringify({ latitude: position.lat, longitude: position.lng }) });
                    await loadStructure();
                    notify("Posição e pontas dos cabos atualizadas.");
                } catch (error) { notify(error.message, true); loadStructure(); }
            });
            marker.addTo(structureLayer);
            bounds.push([latitude, longitude]);
        });
        cables.features.forEach((feature) => {
            const p = feature.properties;
            const line = L.geoJSON(feature, { style: { color: selectedProject()?.color || "#2dd4bf", weight: 4, opacity: .86 } });
            const actions = canEdit ? `<br><button type="button" data-edit-cable="${p.id}">Editar/conectar</button><button class="danger" type="button" data-delete-cable="${p.id}">Excluir</button>` : "";
            line.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>Cabo óptico · ${p.fibras} fibras<br>${escapeHtml(p.origem || "Sem origem")} → ${escapeHtml(p.destino || "Sem destino")}${actions}`);
            line.on("popupopen", () => {
                popupAction(`[data-edit-cable="${p.id}"]`, () => editCable(p.id).catch((error) => notify(error.message, true)));
                popupAction(`[data-delete-cable="${p.id}"]`, () => deleteCable(p.id).catch((error) => notify(error.message, true)));
            });
            line.addTo(structureLayer);
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
        map.getContainer().style.cursor = "crosshair";
        if (tool === "cable") {
            state.cableCoordinates = [];
            state.drawingLine = L.polyline([], { color: "#2dd4bf", dashArray: "8 6", weight: 4 }).addTo(map);
            drawingBar.hidden = false;
            notify("Clique no mapa para adicionar os pontos do cabo.");
        } else notify("Clique no mapa para posicionar o elemento.");
    }
    function clearTool() {
        state.tool = null;
        state.cableCoordinates = [];
        if (state.drawingLine) map.removeLayer(state.drawingLine);
        state.drawingLine = null;
        drawingBar.hidden = true;
        map.getContainer().style.cursor = "";
        document.querySelectorAll(".tool-button").forEach((button) => button.classList.remove("active"));
    }
    map.on("click", (event) => {
        if (!state.tool) return;
        if (state.tool === "cable") {
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
        populateSplitterCables(null);
        loadSplitterFibers("");
        const titles = { pole: "Novo poste", cto: "Nova CTO", splice_box: "Nova CEO" };
        document.getElementById("element-dialog-title").textContent = titles[state.tool] || "Novo elemento";
        elementDialog.showModal();
    });

    document.getElementById("collapse-sidebar").onclick = () => { sidebar.classList.toggle("collapsed"); setTimeout(() => map.invalidateSize(), 220); };
    projectSelect.onchange = async () => {
        state.projectId = projectSelect.value || null;
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
    elementForm.onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
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
    document.getElementById("finish-drawing").onclick = () => {
        if (state.cableCoordinates.length < 2) return notify("O cabo precisa de pelo menos dois pontos.", true);
        state.editingCableId = null; cableForm.reset(); populateConnectionSelects(); cableForm.elements.cable_model_id.disabled = false;
        document.getElementById("cable-dialog-title").textContent = "Novo cabo";
        cableDialog.showModal();
    };
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
    [["structure", structureLayer], ["online", clientLayers.online], ["offline", clientLayers.offline], ["unknown", clientLayers.unknown]].forEach(([name, layer]) => {
        document.getElementById(`layer-${name}`).onchange = (event) => { if (event.target.checked) layer.addTo(map); else map.removeLayer(layer); };
    });
    Promise.all([
        loadProjects(), loadClients(),
        api("/api/map/cable-models/").then((data) => data.models.forEach((model) => cableForm.elements.cable_model_id.add(new Option(`${model.name} · ${model.fiber_count} fibras`, model.id)))),
    ]).then(() => { updateTools(); notify(canEdit ? "Selecione ou crie um projeto." : "Visualização ativa. Entre como administrador para editar."); })
      .catch((error) => notify(error.message, true));
})();
