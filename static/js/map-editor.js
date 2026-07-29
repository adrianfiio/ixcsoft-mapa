(function () {
    "use strict";

    const canEdit = document.body.dataset.canEdit === "true";
    const sidebar = document.getElementById("map-sidebar");
    const projectSelect = document.getElementById("project-select");
    const message = document.getElementById("editor-message");
    const projectDialog = document.getElementById("project-dialog");
    const elementDialog = document.getElementById("element-dialog");
    const cableDialog = document.getElementById("cable-dialog");
    const drawingBar = document.getElementById("drawing-bar");
    const state = {
        projectId: null,
        projects: [],
        tool: null,
        cableCoordinates: [],
        drawingLine: null,
    };

    const map = L.map("map", { preferCanvas: true }).setView([-24.45, -50.62], 10);
    const streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 20,
        attribution: "&copy; OpenStreetMap",
    });
    const satelliteLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 20, attribution: "Tiles &copy; Esri" }
    );
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

    function selectedProject() {
        return state.projects.find((item) => String(item.id) === String(state.projectId));
    }

    function updateTools() {
        const enabled = canEdit && Boolean(state.projectId);
        document.querySelectorAll(".tool-button, #import-button").forEach((button) => { button.disabled = !enabled; });
        const project = selectedProject();
        document.getElementById("project-help").textContent = project
            ? `${project.code} · ${project.status_label}`
            : "Crie ou selecione um projeto para editar a estrutura.";
    }

    async function loadProjects(selectId) {
        const data = await api("/api/map/projects/");
        state.projects = data.projects;
        projectSelect.innerHTML = '<option value="">Selecione um projeto</option>';
        data.projects.forEach((project) => {
            const option = document.createElement("option");
            option.value = project.id;
            option.textContent = `${project.name} (${project.code})`;
            projectSelect.appendChild(option);
        });
        if (selectId) projectSelect.value = String(selectId);
        state.projectId = projectSelect.value || null;
        updateTools();
    }

    function clientIcon(status) {
        return L.divIcon({ className: "", html: `<div class="client-dot ${status}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
    }

    function escapeHtml(value) {
        const item = document.createElement("span");
        item.textContent = value == null ? "" : String(value);
        return item.innerHTML;
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
        return L.divIcon({
            className: "",
            html: `<div class="network-marker ${type}">${labels[type] || "•"}</div>`,
            iconSize: [31, 31],
            iconAnchor: [15, 15],
        });
    }

    async function deleteElement(id) {
        if (!confirm("Excluir este elemento do projeto?")) return;
        await api(`/api/map/elements/${id}/`, { method: "DELETE" });
        await loadStructure();
        notify("Elemento excluído.");
    }

    async function loadStructure(fit = false) {
        structureLayer.clearLayers();
        if (!state.projectId) {
            document.getElementById("element-count").textContent = "0";
            document.getElementById("cable-count").textContent = "0";
            return;
        }
        const query = `?project_id=${encodeURIComponent(state.projectId)}`;
        const [elements, cables, routes] = await Promise.all([
            api(`/api/map/elements/${query}`),
            api(`/api/map/cables/${query}`),
            api(`/api/map/routes/${query}`),
        ]);
        const bounds = [];
        elements.features.forEach((feature) => {
            const p = feature.properties;
            const [longitude, latitude] = feature.geometry.coordinates;
            const marker = L.marker([latitude, longitude], {
                icon: networkIcon(p.tipo),
                draggable: canEdit,
            });
            const remove = canEdit ? `<br><button type="button" data-delete-element="${p.id}">Excluir</button>` : "";
            marker.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>${escapeHtml(p.tipo.toUpperCase())}<br>${escapeHtml(p.codigo || "")}${remove}`);
            marker.on("popupopen", () => {
                const button = document.querySelector(`[data-delete-element="${p.id}"]`);
                if (button) button.onclick = () => deleteElement(p.id).catch((error) => notify(error.message, true));
            });
            if (canEdit) marker.on("dragend", async () => {
                const position = marker.getLatLng();
                try {
                    await api(`/api/map/elements/${p.id}/position/`, {
                        method: "PATCH",
                        body: JSON.stringify({ latitude: position.lat, longitude: position.lng }),
                    });
                    notify("Posição atualizada.");
                } catch (error) {
                    notify(error.message, true);
                    loadStructure();
                }
            });
            marker.addTo(structureLayer);
            bounds.push([latitude, longitude]);
        });
        [...cables.features, ...routes.features].forEach((feature) => {
            const p = feature.properties;
            const color = feature.properties.imported ? "#f7b731" : (selectedProject()?.color || "#2dd4bf");
            const line = L.geoJSON(feature, { style: { color, weight: 4, opacity: .86 } });
            line.bindPopup(`<strong>${escapeHtml(p.nome)}</strong><br>${p.imported ? "Rota importada" : "Cabo óptico"}`);
            line.addTo(structureLayer);
            line.getLayers().forEach((part) => part.getLatLngs().flat(Infinity).forEach((point) => bounds.push([point.lat, point.lng])));
        });
        document.getElementById("element-count").textContent = elements.count;
        document.getElementById("cable-count").textContent = cables.count + routes.count;
        if (fit && bounds.length) map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 });
    }

    function setTool(tool) {
        if (!state.projectId) return notify("Selecione um projeto primeiro.", true);
        state.tool = tool;
        document.querySelectorAll(".tool-button").forEach((button) => button.classList.toggle("active", button.dataset.tool === tool));
        map.getContainer().style.cursor = "crosshair";
        if (tool === "cable") {
            state.cableCoordinates = [];
            state.drawingLine = L.polyline([], { color: "#2dd4bf", dashArray: "8 6", weight: 4 }).addTo(map);
            drawingBar.hidden = false;
            notify("Clique no mapa para adicionar os pontos do cabo.");
        } else {
            notify("Clique no mapa para posicionar o elemento.");
        }
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
        const form = document.getElementById("element-form");
        form.reset();
        form.elements.element_type.value = state.tool;
        form.elements.latitude.value = event.latlng.lat;
        form.elements.longitude.value = event.latlng.lng;
        const titles = { pole: "Novo poste", cto: "Nova CTO", splice_box: "Nova CEO" };
        document.getElementById("element-dialog-title").textContent = titles[state.tool] || "Novo elemento";
        elementDialog.showModal();
    });

    document.getElementById("collapse-sidebar").onclick = () => {
        sidebar.classList.toggle("collapsed");
        setTimeout(() => map.invalidateSize(), 220);
    };
    projectSelect.onchange = async () => {
        state.projectId = projectSelect.value || null;
        clearTool();
        updateTools();
        try {
            await loadStructure(true);
            notify(state.projectId ? "Projeto carregado. Escolha uma ferramenta para editar." : "Selecione um projeto.");
        } catch (error) { notify(error.message, true); }
    };
    document.querySelectorAll(".tool-button").forEach((button) => { button.onclick = () => setTool(button.dataset.tool); });
    document.querySelectorAll(".dialog-close").forEach((button) => { button.onclick = () => button.closest("dialog").close(); });
    document.getElementById("new-project-button").onclick = () => {
        if (!canEdit) return window.location.assign("/admin/login/?next=/mapa/");
        document.getElementById("project-form").reset();
        projectDialog.showModal();
    };
    document.getElementById("project-form").onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        try {
            const data = await api("/api/map/projects/", { method: "POST", body: JSON.stringify(payload) });
            projectDialog.close();
            await loadProjects(data.project.id);
            await loadStructure();
            notify("Projeto criado. Agora você pode adicionar a estrutura.");
        } catch (error) { notify(error.message, true); }
    };
    document.getElementById("element-form").onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        payload.project = state.projectId;
        payload.enabled = true;
        try {
            await api("/api/map/elements/create/", { method: "POST", body: JSON.stringify(payload) });
            elementDialog.close();
            clearTool();
            await loadStructure();
            notify("Elemento adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
    };
    document.getElementById("finish-drawing").onclick = () => {
        if (state.cableCoordinates.length < 2) return notify("O cabo precisa de pelo menos dois pontos.", true);
        cableDialog.showModal();
    };
    document.getElementById("cancel-drawing").onclick = () => { clearTool(); notify("Desenho cancelado."); };
    document.getElementById("cable-form").onsubmit = async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.target));
        payload.project_id = state.projectId;
        payload.coordinates = state.cableCoordinates;
        payload.generate_fibers = Boolean(payload.cable_model_id);
        try {
            await api("/api/map/cables/create/", { method: "POST", body: JSON.stringify(payload) });
            cableDialog.close();
            clearTool();
            await loadStructure();
            notify("Cabo adicionado ao projeto.");
        } catch (error) { notify(error.message, true); }
    };
    document.getElementById("import-button").onclick = () => document.getElementById("import-file").click();
    document.getElementById("import-file").onchange = async (event) => {
        const file = event.target.files[0];
        if (!file || !state.projectId) return;
        const formData = new FormData();
        formData.append("file", file);
        notify(`Importando ${file.name}...`);
        try {
            const data = await api(`/api/map/projects/${state.projectId}/import/`, { method: "POST", body: formData });
            await loadStructure(true);
            notify(`Importação concluída: ${data.imported.elements} pontos e ${data.imported.routes} rotas.`);
        } catch (error) { notify(error.message, true); }
        event.target.value = "";
    };

    [["structure", structureLayer], ["online", clientLayers.online], ["offline", clientLayers.offline], ["unknown", clientLayers.unknown]].forEach(([name, layer]) => {
        document.getElementById(`layer-${name}`).onchange = (event) => {
            if (event.target.checked) layer.addTo(map); else map.removeLayer(layer);
        };
    });

    Promise.all([
        loadProjects(),
        loadClients(),
        api("/api/map/cable-models/").then((data) => {
            const select = document.querySelector('#cable-form [name="cable_model_id"]');
            data.models.forEach((model) => {
                const option = document.createElement("option");
                option.value = model.id;
                option.textContent = `${model.name} · ${model.fiber_count} fibras`;
                select.appendChild(option);
            });
        }),
    ]).then(() => {
        updateTools();
        notify(canEdit ? "Selecione ou crie um projeto." : "Visualização ativa. Entre como administrador para editar.");
    }).catch((error) => notify(error.message, true));
})();
