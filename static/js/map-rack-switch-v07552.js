(function (global) {
    "use strict";

    const VERSION = "0.75.52";
    const CACHE_MS = 30000;
    const SPEED_CLASSES = ["is-speed-1g", "is-speed-10g", "is-speed-25g", "is-speed-40g", "is-speed-100g"];
    const LINK_SPEED_CLASSES = ["speed-1g", "speed-10g", "speed-25g", "speed-40g", "speed-100g"];
    const CONNECTORS = [
        ["rj45", "RJ45"],
        ["sfp", "SFP"],
        ["sfp_plus", "SFP+"],
        ["xfp", "XFP"],
        ["qsfp_plus", "QSFP+"],
    ];
    const SPEEDS = [1, 10, 25, 40, 100];
    const state = {
        cache: new Map(),
        pending: new Map(),
        linkSpeeds: new Map(),
        rendered: new WeakMap(),
        dialog: null,
        observer: null,
        svgObservers: new WeakMap(),
        enhanceTimer: 0,
        forceEnhance: false,
        generation: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function rootNode() { return qs("#map-master-container"); }
    function elementId() {
        const root = rootNode();
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }
    function canEdit() { return document.body.dataset.canEdit === "true"; }
    function csrfToken() {
        const row = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
        return row ? decodeURIComponent(row.split("=")[1]) : qs("[name='csrfmiddlewaretoken']")?.value || "";
    }
    function notify(message, error = false) { global.networkMap?.notify?.(message, error); }

    async function request(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function hardwareUrl(containerId, switchId) {
        return `/api/map/v07551/elements/${Number(containerId)}/switch/${Number(switchId)}/hardware/`;
    }

    async function loadSwitch(containerId, switchId, force = false) {
        const key = `${containerId}:${switchId}`;
        const cached = state.cache.get(key);
        if (!force && cached && Date.now() - cached.at < CACHE_MS) return cached.data;
        if (state.pending.has(key)) return state.pending.get(key);
        const pending = request(hardwareUrl(containerId, switchId))
            .then((data) => {
                state.cache.set(key, { at: Date.now(), data });
                return data;
            })
            .finally(() => state.pending.delete(key));
        state.pending.set(key, pending);
        return pending;
    }

    function invalidateSwitch(containerId, switchId) {
        state.cache.delete(`${containerId}:${switchId}`);
    }

    function speedClass(value) {
        const number = Number(value);
        return ({ 1: "speed-1g", 10: "speed-10g", 25: "speed-25g", 40: "speed-40g", 100: "speed-100g" })[number] || "";
    }

    function portSpeedClass(value) {
        const valueClass = speedClass(value);
        return valueClass ? `is-${valueClass}` : "";
    }

    function connectorOptions(value) {
        return CONNECTORS.map(([key, label]) =>
            `<option value="${key}" ${key === value ? "selected" : ""}>${label}</option>`
        ).join("");
    }

    function speedOptions(value) {
        return SPEEDS.map((speed) =>
            `<option value="${speed}" ${Number(value) === speed ? "selected" : ""}>${speed} Gbps</option>`
        ).join("");
    }

    function linkTitle(port) {
        const configured = `${port.speed_gbps} Gbps`;
        if (!port.linked) {
            return `${port.name} · ${port.connector_type_label} · ${configured} · livre`;
        }
        const effective = port.effective_speed_gbps == null ? "não informada" : `${port.effective_speed_gbps} Gbps`;
        const remote = port.remote_equipment
            ? `${port.remote_equipment}${port.remote_port ? ` · ${port.remote_port}` : ""}`
            : "destino externo";
        return `${port.name} · ${port.connector_type_label} · configurada ${configured} · link ${effective} · ${remote}`;
    }

    function takePortButton(node, port, existing = null) {
        let button = existing || qs(`.master-node-port[data-port-id="${port.id}"]`, node);
        if (!button) {
            button = document.createElement("button");
            button.type = "button";
            button.className = "master-node-port";
            button.dataset.portId = String(port.id);
            button.dataset.portRole = "front";
            button.dataset.linkId = port.link_id || "";
            button.innerHTML = "<span></span><i></i>";
        }
        button.classList.remove("left", "right", ...SPEED_CLASSES);
        button.classList.add("v07552-switch-port");
        button.classList.toggle("is-linked", Boolean(port.linked));
        button.classList.toggle("used", Boolean(port.linked));
        const currentSpeedClass = port.linked ? portSpeedClass(port.effective_speed_gbps) : "";
        if (currentSpeedClass) button.classList.add(currentSpeedClass);
        button.dataset.portRole = "front";
        button.dataset.portType = port.port_type;
        button.dataset.connectorType = port.connector_type;
        button.dataset.connectorLabel = port.connector_type_label;
        button.dataset.speedGbps = String(port.speed_gbps);
        button.dataset.effectiveSpeedGbps = port.effective_speed_gbps == null ? "" : String(port.effective_speed_gbps);
        button.dataset.linkId = port.link_id || "";
        button.title = linkTitle(port);
        button.setAttribute("aria-label", linkTitle(port));
        const label = qs("span", button);
        if (label) label.textContent = port.name;
        return button;
    }

    function registerLinkSpeeds(data) {
        (data.ports || []).forEach((port) => {
            if (!port.link_id) return;
            const value = port.speed_class || speedClass(port.effective_speed_gbps);
            if (value) state.linkSpeeds.set(String(port.link_id), value);
            else state.linkSpeeds.delete(String(port.link_id));
        });
    }

    function applyLinkColors(root = rootNode()) {
        if (!root) return;
        qsa("[data-master-link], .v07542-front-link[data-link-id]", root).forEach((path) => {
            path.classList.remove(...LINK_SPEED_CLASSES);
            const linkId = String(path.dataset.masterLink || path.dataset.linkId || "");
            const value = state.linkSpeeds.get(linkId);
            if (value) path.classList.add(value);
        });
    }

    function observeLinkSvg(root = rootNode()) {
        if (!root) return;
        qsa(".master-canvas-links, .v07542-rack-links", root).forEach((svg) => {
            if (state.svgObservers.has(svg)) return;
            const observer = new MutationObserver(() => {
                // Somente reaplica classes em caminhos já renderizados. Nunca
                // busca dados, evitando repetir o desastre observer → fetch.
                applyLinkColors(root);
            });
            observer.observe(svg, { childList: true, subtree: true });
            state.svgObservers.set(svg, observer);
        });
    }

    function renderSwitchFace(node, data) {
        if (!node?.isConnected) return;
        const signature = JSON.stringify((data.ports || []).map((port) => [
            port.id,
            port.name,
            port.connector_type,
            port.speed_gbps,
            port.link_id,
            port.effective_speed_gbps,
        ]));
        if (state.rendered.get(node) === signature && qs(".v07552-switch-face", node)) {
            registerLinkSpeeds(data);
            applyLinkColors();
            return;
        }

        const oldFace = qs(".v07552-switch-face", node);
        const legacy = qs(":scope > .master-node-ports", node);
        const buttons = new Map(
            qsa(".master-node-port[data-port-id]", node).map((button) => [Number(button.dataset.portId), button])
        );
        oldFace?.remove();
        const face = document.createElement("section");
        face.className = "v07552-switch-face";
        face.dataset.portCount = String(data.ports.length);
        face.dataset.generatedBy = "v07552";
        face.innerHTML = `<header><div><strong>${escapeHtml(data.equipment.vendor || "Switch")} ${escapeHtml(data.equipment.model || "")}</strong><small>${data.ports.length} porta(s) · conectores e velocidades individuais</small></div>${canEdit() ? `<button type="button" data-v07552-switch-edit="${data.equipment.id}">Editar portas</button>` : ""}</header><div class="v07552-switch-ports"></div>`;
        const holder = qs(".v07552-switch-ports", face);
        if ([8, 12, 16].includes(data.ports.length)) {
            holder.classList.add("is-single-row");
            holder.style.setProperty("--port-count", String(data.ports.length));
        }
        data.ports.forEach((port) => {
            const existing = buttons.get(Number(port.id)) || null;
            holder.appendChild(takePortButton(node, port, existing));
        });
        // MAP_V07564_SWITCH_ORGANIZER_DIVIDER: barra visual dividindo a
        // grade de portas ao meio (a pedido do usuário -- só estética,
        // não cria um tipo de porta "uplink"/"serviço" novo nem mexe nos
        // dados, diferente do organizador real que a OLT já tem).
        if (data.ports.length > 1) {
            const divider = document.createElement("div");
            divider.className = "v07564-switch-half-divider";
            divider.setAttribute("aria-hidden", "true");
            holder.appendChild(divider);
        }
        legacy?.remove();
        const nodeHeader = qs(":scope > header", node);
        if (nodeHeader?.nextSibling) node.insertBefore(face, nodeHeader.nextSibling);
        else node.appendChild(face);
        registerLinkSpeeds(data);
        state.rendered.set(node, signature);
        applyLinkColors();
    }

    async function enhanceSwitchNode(node, generation, force) {
        const containerId = elementId();
        const switchId = Number(node.dataset.equipmentNode || node.dataset.equipmentId || 0);
        if (!containerId || !switchId) return;
        try {
            const data = await loadSwitch(containerId, switchId, force);
            if (generation !== state.generation || !node.isConnected) return;
            renderSwitchFace(node, data);
        } catch (error) {
            node.dataset.switchErrorV07552 = error.message;
            const face = qs(".v07552-switch-face", node);
            if (face) face.title = `Falha ao carregar portas do Switch: ${error.message}`;
        }
    }

    async function enhanceAll(force = false) {
        const root = rootNode();
        if (!root || !qs("#container-dialog")?.open) return;
        const generation = ++state.generation;
        observeLinkSvg(root);
        const nodes = qsa('.master-canvas-node[data-equipment-type="switch"]', root);
        await Promise.all(nodes.map((node) => enhanceSwitchNode(node, generation, force)));
        if (generation === state.generation) applyLinkColors(root);
    }

    function scheduleEnhance(force = false, delay = 35) {
        state.forceEnhance = state.forceEnhance || force;
        global.clearTimeout(state.enhanceTimer);
        state.enhanceTimer = global.setTimeout(() => {
            const nextForce = state.forceEnhance;
            state.forceEnhance = false;
            state.enhanceTimer = 0;
            enhanceAll(nextForce).catch((error) => console.error("MAP v0.75.52:", error));
        }, delay);
    }

    function ensurePortCount(select) {
        if (!select) return;
        if (!qsa("option", select).some((option) => Number(option.value) === 16)) {
            const option = document.createElement("option");
            option.value = "16";
            option.textContent = "16 portas";
            const before = qsa("option", select).find((item) => Number(item.value) > 16);
            if (before) select.insertBefore(option, before);
            else select.appendChild(option);
        }
    }

    function enhanceCreateForms() {
        const physical = qs("#map-rack-equipment-v07542");
        if (physical) {
            const type = qs("[data-type-v07542]", physical)?.value;
            if (type === "switch") ensurePortCount(qs('[name="port_count"]', physical));
        }
        const generic = qs("[data-create-equipment]");
        if (!generic) return;
        const type = qs("[data-create-type]", generic)?.value;
        const fields = qs("[data-create-fields]", generic);
        if (type !== "switch" || !fields) return;
        let row = qs("[data-v07552-switch-count]", fields);
        if (!row) {
            row = document.createElement("label");
            row.dataset.v07552SwitchCount = "1";
            row.innerHTML = `Quantidade de portas<select name="port_count">${[4, 8, 12, 16, 24, 48].map((count) => `<option value="${count}" ${count === 24 ? "selected" : ""}>${count} portas</option>`).join("")}</select>`;
            const grid = qs(".v07539-form-grid", fields) || fields;
            grid.appendChild(row);
        }
        ensurePortCount(qs('[name="port_count"]', row));
    }

    function ensureDialog() {
        if (state.dialog?.isConnected) return state.dialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-switch-editor-v07552";
        dialog.className = "v07552-switch-dialog";
        document.body.appendChild(dialog);
        state.dialog = dialog;
        return dialog;
    }

    function editorRows(data) {
        return data.ports.map((port, index) => `<tr data-v07552-port-row="${port.id}">
            <td><b>${index + 1}</b><input type="hidden" name="order" value="${index + 1}"></td>
            <td><input name="name" maxlength="100" value="${escapeHtml(port.name)}" title="${escapeHtml(port.name)}" required></td>
            <td><select name="connector_type">${connectorOptions(port.connector_type)}</select></td>
            <td><select name="speed_gbps">${speedOptions(port.speed_gbps)}</select></td>
            <td><span class="v07552-link-state ${port.linked ? "is-linked" : ""} ${port.linked ? portSpeedClass(port.effective_speed_gbps) : ""}">${port.linked ? `${port.effective_speed_gbps || "?"}G · ${escapeHtml(port.remote_equipment || "ligada")}` : "Livre"}</span></td>
        </tr>`).join("");
    }

    function installEditorEvents(dialog, containerId, switchId) {
        qsa("[data-close]", dialog).forEach((button) => { button.onclick = () => dialog.close(); });
        qs("[data-apply-range]", dialog).onclick = () => {
            const start = Math.max(1, Number(qs('[name="range_start"]', dialog).value || 1));
            const end = Math.max(start, Number(qs('[name="range_end"]', dialog).value || start));
            const connector = qs('[name="range_connector"]', dialog).value;
            const speed = qs('[name="range_speed"]', dialog).value;
            qsa("[data-v07552-port-row]", dialog).forEach((row, index) => {
                const position = index + 1;
                if (position < start || position > end) return;
                qs('[name="connector_type"]', row).value = connector;
                qs('[name="speed_gbps"]', row).value = speed;
            });
        };
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando portas…";
            const ports = qsa("[data-v07552-port-row]", dialog).map((row, index) => ({
                id: Number(row.dataset.v07552PortRow),
                order: index + 1,
                name: qs('[name="name"]', row).value,
                connector_type: qs('[name="connector_type"]', row).value,
                speed_gbps: Number(qs('[name="speed_gbps"]', row).value),
            }));
            try {
                await request(hardwareUrl(containerId, switchId), {
                    method: "PATCH",
                    body: JSON.stringify({ action: "save_ports", ports }),
                });
                invalidateSwitch(containerId, switchId);
                await global.mapMasterSuite?.openContainerWorkspace?.(containerId);
                const refreshed = await loadSwitch(containerId, switchId, true);
                renderEditor(dialog, containerId, switchId, refreshed);
                notify("Portas do Switch atualizadas.");
            } catch (error) {
                status.textContent = error.message;
            }
        };
    }

    function renderEditor(dialog, containerId, switchId, data) {
        const lastPort = Math.max(1, data.ports.length);
        dialog.innerHTML = `<form><header><div><small>SWITCH · MAP v${VERSION}</small><h2>${escapeHtml(data.equipment.name)}</h2><p>Edite nome, conector e velocidade sem apagar ligações existentes.</p></div><button type="button" data-close aria-label="Fechar">×</button></header><section class="v07552-bulk-editor"><strong>Aplicar em intervalo</strong><label>Da porta<input name="range_start" type="number" min="1" max="${lastPort}" value="1"></label><label>Até<input name="range_end" type="number" min="1" max="${lastPort}" value="${lastPort}"></label><label>Conector<select name="range_connector">${connectorOptions("rj45")}</select></label><label>Velocidade<select name="range_speed">${speedOptions(1)}</select></label><button type="button" data-apply-range>Aplicar</button></section><div class="v07552-port-table-wrap"><table><thead><tr><th>#</th><th>Nome da porta</th><th>Conector</th><th>Velocidade</th><th>Ligação</th></tr></thead><tbody>${editorRows(data)}</tbody></table></div><p data-status></p><footer><button type="button" data-close>Fechar</button><button type="submit" class="primary">Salvar portas</button></footer></form>`;
        installEditorEvents(dialog, containerId, switchId);
        if (!dialog.open) dialog.showModal();
    }

    async function openSwitchEditor(containerId, switchId) {
        if (!canEdit()) return;
        const data = await loadSwitch(containerId, switchId, true);
        renderEditor(ensureDialog(), containerId, switchId, data);
    }

    function switchIdFromEditButton(button) {
        if (button.dataset.v07552SwitchEdit) return Number(button.dataset.v07552SwitchEdit);
        const node = button.closest('.master-canvas-node[data-equipment-type="switch"]');
        if (node) return Number(node.dataset.equipmentNode || 0);
        const row = button.closest('[data-equipment-type="switch"][data-equipment-id]');
        return Number(row?.dataset.equipmentId || 0);
    }

    function installCaptureHandlers() {
        global.addEventListener("click", (event) => {
            const edit = event.target instanceof Element
                ? event.target.closest("[data-v07552-switch-edit], [data-node-edit], [data-edit-equipment]")
                : null;
            const switchId = edit ? switchIdFromEditButton(edit) : 0;
            if (switchId && qs("#container-dialog")?.open) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                openSwitchEditor(elementId(), switchId).catch((error) => notify(error.message, true));
                return;
            }
            const add = event.target instanceof Element
                ? event.target.closest("[data-v07539-add-equipment], [data-container-add], [data-add-equipment]")
                : null;
            if (add) global.setTimeout(enhanceCreateForms, 0);
        }, true);
        global.addEventListener("change", (event) => {
            if (!(event.target instanceof Element)) return;
            if (event.target.matches("[data-create-type], [data-type-v07542]")) {
                global.setTimeout(enhanceCreateForms, 0);
            }
        }, true);
    }

    function installObserver() {
        if (state.observer) return;
        state.observer = new MutationObserver((records) => {
            const createFormChanged = records.some((record) =>
                [...record.addedNodes].some((node) => node instanceof Element && (
                    node.matches?.("[data-create-equipment], #map-rack-equipment-v07542")
                    || node.querySelector?.("[data-create-equipment], #map-rack-equipment-v07542")
                ))
            );
            if (createFormChanged) global.setTimeout(enhanceCreateForms, 0);
        });
        state.observer.observe(document.body, { childList: true, subtree: true });
    }

    function init() {
        installCaptureHandlers();
        installObserver();
        document.addEventListener("map:container-rendered", () => scheduleEnhance(true));
        document.addEventListener("map:container-opening", () => scheduleEnhance(true));
        document.addEventListener("map:node-moved", () => applyLinkColors());
        global.addEventListener("resize", () => applyLinkColors());
        enhanceCreateForms();
        scheduleEnhance(false, 0);
    }

    function registerLinkSpeed(linkId, value) {
        if (!linkId) return;
        if (value) state.linkSpeeds.set(String(linkId), value);
        else state.linkSpeeds.delete(String(linkId));
        applyLinkColors();
    }

    document.addEventListener("map:link-speed-v07552", (event) => {
        registerLinkSpeed(event.detail?.linkId, event.detail?.speedClass);
    });

    global.mapRackSwitchV07552 = Object.freeze({
        version: VERSION,
        refresh: () => scheduleEnhance(true, 0),
        invalidate: invalidateSwitch,
        openEditor: openSwitchEditor,
        applyLinkColors,
        registerLinkSpeed,
    });

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
