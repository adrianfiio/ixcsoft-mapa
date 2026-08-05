(function (global) {
    "use strict";

    const VERSION = "0.75.44";
    const state = {
        root: null,
        canvas: null,
        scroll: null,
        svg: null,
        data: null,
        frame: 0,
        generation: 0,
        pan: null,
        hardware: new Map(),
        dialog: null,
        createObserver: null,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function csrfToken() {
        const row = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
        return row ? decodeURIComponent(row.split("=")[1]) : qs("[name='csrfmiddlewaretoken']")?.value || "";
    }

    async function request(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function notify(message, error = false) {
        global.networkMap?.notify?.(message, error);
    }

    function canEdit() {
        return document.body.dataset.canEdit === "true";
    }

    function currentElementId() {
        const dialog = qs("#container-dialog");
        return Number(state.root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }

    function currentKind() {
        const direct = String(
            state.root?.dataset.containerKindV07542
            || state.root?.dataset.containerKindV07541
            || state.root?.dataset.containerKindV07540
            || "",
        ).toLowerCase();
        if (direct) return direct;
        const dialog = qs("#container-dialog");
        const values = [dialog?.dataset.containerType, dialog?.dataset.elementType, dialog?.dataset.containerName]
            .map((value) => String(value || "").toLowerCase());
        if (values.some((value) => value === "rack" || value.includes("rack"))) return "rack";
        if (values.some((value) => value === "tower" || value.includes("torre"))) return "tower";
        return "";
    }

    function equipmentId(node) {
        return Number(node?.dataset.equipmentNode || node?.dataset.equipmentId || 0);
    }

    function ensureDialog() {
        if (state.dialog?.isConnected) return state.dialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-rack-hardware-v07544";
        dialog.className = "v07544-dialog";
        dialog.innerHTML = '<form><header><div><small data-kicker>HARDWARE DA OLT</small><h2 data-title></h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div data-body></div></form>';
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
        state.dialog = dialog;
        return dialog;
    }

    function showDialog({ title, subtitle = "", kicker = "HARDWARE DA OLT", body = "" }) {
        const dialog = ensureDialog();
        qs("[data-title]", dialog).textContent = title;
        qs("[data-subtitle]", dialog).textContent = subtitle;
        qs("[data-kicker]", dialog).textContent = kicker;
        qs("[data-body]", dialog).innerHTML = body;
        if (!dialog.open) dialog.showModal();
        return dialog;
    }

    function hardwareUrl(elementId, oltId) {
        return `/api/map/v07544/elements/${Number(elementId)}/olt/${Number(oltId)}/hardware/`;
    }

    async function loadHardware(elementId, oltId, force = false) {
        const key = `${elementId}:${oltId}`;
        if (!force && state.hardware.has(key)) return state.hardware.get(key);
        const data = await request(hardwareUrl(elementId, oltId));
        state.hardware.set(key, data);
        return data;
    }

    async function refreshContainer(elementId = currentElementId()) {
        state.hardware.clear();
        if (elementId && global.mapMasterSuite?.openContainerWorkspace) {
            await global.mapMasterSuite.openContainerWorkspace(elementId);
        }
        global.setTimeout(schedule, 120);
    }

    function technologyLabel(value) {
        return ({ gpon: "GPON", xgpon: "XG-PON", xgspon: "XGS-PON" })[value] || "GPON";
    }

    function createGroupRows(container, count, values = []) {
        container.innerHTML = "";
        for (let index = 0; index < count; index += 1) {
            const current = values[index] || {};
            const row = document.createElement("div");
            row.className = "v07544-uplink-create-row";
            row.dataset.uplinkGroupRow = String(index + 1);
            row.innerHTML = `<label>Nome<input data-group-name value="${escapeHtml(current.name || `Uplink ${index + 1}`)}" maxlength="100"></label><label>Portas<input data-group-count type="number" min="1" max="16" value="${Number(current.port_count || 1)}"></label><label>Tipo<select data-group-type><option value="rj45_1g" ${current.port_type === "rj45_1g" ? "selected" : ""}>RJ45 1G</option><option value="sfp_1g" ${!current.port_type || current.port_type === "sfp_1g" ? "selected" : ""}>SFP 1G</option><option value="sfp_plus_10g" ${current.port_type === "sfp_plus_10g" ? "selected" : ""}>SFP+ 10G</option></select></label>`;
            container.appendChild(row);
        }
        if (!count) container.innerHTML = '<p class="v07544-no-uplink">Nenhum uplink será criado. Nada de portas fantasmas, enfim.</p>';
    }

    function readCreateGroups(form) {
        return qsa("[data-uplink-group-row]", form).map((row, index) => ({
            id: `uplink-${index + 1}`,
            name: qs("[data-group-name]", row).value.trim() || `Uplink ${index + 1}`,
            port_count: Number(qs("[data-group-count]", row).value || 0),
            port_type: qs("[data-group-type]", row).value,
        }));
    }

    function enhanceCreateForm() {
        const dialog = qs("#map-v07539-modal");
        const form = qs("form[data-create-equipment]", dialog);
        if (!form) return;
        const type = qs("[data-create-type]", form)?.value;
        const oldConfig = qs("[data-v07544-olt-create]", form);
        if (type !== "olt") {
            oldConfig?.remove();
            return;
        }
        const cardCount = qs('[name="card_count"]', form);
        const ponsPerCard = qs('[name="pons_per_card"]', form);
        if (cardCount && Number(cardCount.value || 0) <= 0) cardCount.value = "4";
        if (ponsPerCard && Number(ponsPerCard.value || 0) <= 0) ponsPerCard.value = "16";
        if (oldConfig) return;
        const config = document.createElement("section");
        config.dataset.v07544OltCreate = "1";
        config.className = "v07544-olt-create";
        config.innerHTML = `<header><div><strong>UPLINKS DA OLT</strong><small>Defina os grupos agora. Zero grupos cria a OLT sem uplinks.</small></div><label>Grupos<input data-uplink-group-total type="number" min="0" max="16" value="0"></label></header><div data-uplink-group-list></div>`;
        const fields = qs("[data-create-fields]", form);
        (fields || form).appendChild(config);
        const total = qs("[data-uplink-group-total]", config);
        const list = qs("[data-uplink-group-list]", config);
        const render = () => {
            const previous = readCreateGroups(form);
            createGroupRows(list, clamp(Number(total.value || 0), 0, 16), previous);
        };
        total.addEventListener("input", render);
        render();
    }

    function installCreateObserver() {
        const dialog = qs("#map-v07539-modal");
        if (!dialog || dialog.dataset.v07544Observed === "1") return;
        dialog.dataset.v07544Observed = "1";
        state.createObserver?.disconnect();
        state.createObserver = new MutationObserver(() => global.queueMicrotask(enhanceCreateForm));
        state.createObserver.observe(dialog, { childList: true, subtree: true });
        enhanceCreateForm();
    }

    async function submitOltCreation(form) {
        const elementId = currentElementId();
        if (!elementId) throw new Error("Rack não identificado.");
        const payload = Object.fromEntries(new FormData(form));
        payload.equipment_type = "olt";
        payload.enabled = Boolean(qs('[name="enabled"]', form)?.checked);
        payload.card_count = Number(qs('[name="card_count"]', form)?.value || 0);
        payload.pons_per_card = Number(qs('[name="pons_per_card"]', form)?.value || 0);
        payload.uplink_groups = readCreateGroups(form);
        await request(`/api/map/v07544/elements/${elementId}/equipment/`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        form.closest("dialog")?.close();
        await refreshContainer(elementId);
        notify("OLT criada com a estrutura exata de placas, PONs e uplinks.");
    }

    function installCreationInterception() {
        document.addEventListener("click", (event) => {
            if (!(event.target instanceof Element)) return;
            const trigger = event.target.closest("[data-container-add], [data-add-equipment]");
            if (!trigger) return;
            global.setTimeout(installCreateObserver, 0);
            global.setTimeout(enhanceCreateForm, 40);
        }, true);
        document.addEventListener("change", (event) => {
            if (event.target?.matches?.("[data-create-type]")) global.setTimeout(enhanceCreateForm, 0);
        });
        document.addEventListener("submit", (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement) || !form.matches("[data-create-equipment]")) return;
            if (qs("[data-create-type]", form)?.value !== "olt") return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const status = qs("[data-form-status]", form);
            if (status) status.textContent = "Criando OLT…";
            submitOltCreation(form).catch((error) => {
                if (status) {
                    status.textContent = error.message;
                    status.classList.add("error");
                } else notify(error.message, true);
            });
        }, true);
    }

    function openCardEditor(node, card) {
        if (!canEdit()) return;
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        const dialog = showDialog({
            title: `Editar placa S${card.slot}`,
            subtitle: `${card.ports.length} portas PON`,
            kicker: "PLACA DE SERVIÇO",
            body: `<div class="v07544-form-grid"><label>Nome<input name="name" value="${escapeHtml(card.name)}" maxlength="100"></label><label>Modelo<input name="model" value="${escapeHtml(card.model)}" maxlength="100"></label><label>Tecnologia<select name="technology"><option value="gpon" ${card.technology === "gpon" ? "selected" : ""}>GPON</option><option value="xgpon" ${card.technology === "xgpon" ? "selected" : ""}>XG-PON</option><option value="xgspon" ${card.technology === "xgspon" ? "selected" : ""}>XGS-PON</option></select></label></div><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>Salvar</button></footer>`,
        });
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("[data-save]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando…";
            try {
                await request(hardwareUrl(elementId, oltId), {
                    method: "POST",
                    body: JSON.stringify({
                        action: "save_card",
                        card_id: card.id,
                        name: qs('[name="name"]', dialog).value,
                        model: qs('[name="model"]', dialog).value,
                        technology: qs('[name="technology"]', dialog).value,
                    }),
                });
                dialog.close();
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
    }

    function openUplinkConfiguration(node, hardware) {
        if (!canEdit()) return;
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        const dialog = showDialog({
            title: "Configurar uplinks",
            subtitle: "Cada grupo possui sua quantidade de portas e um tipo físico explícito.",
            kicker: "UPLINKS DA OLT",
            body: `<section class="v07544-olt-create"><header><div><strong>GRUPOS DE UPLINK</strong><small>Use zero para remover os grupos explícitos.</small></div><label>Grupos<input data-uplink-group-total type="number" min="0" max="16" value="${hardware.uplink_groups.length}"></label></header><div data-uplink-group-list></div></section><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>Aplicar configuração</button></footer>`,
        });
        const list = qs("[data-uplink-group-list]", dialog);
        const total = qs("[data-uplink-group-total]", dialog);
        createGroupRows(list, hardware.uplink_groups.length, hardware.uplink_groups.map((group) => ({
            name: group.name,
            port_count: group.ports.length,
            port_type: group.port_type,
        })));
        total.addEventListener("input", () => {
            const previous = qsa("[data-uplink-group-row]", dialog).map((row) => ({
                name: qs("[data-group-name]", row).value,
                port_count: qs("[data-group-count]", row).value,
                port_type: qs("[data-group-type]", row).value,
            }));
            createGroupRows(list, clamp(Number(total.value || 0), 0, 16), previous);
        });
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("[data-save]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            const groups = qsa("[data-uplink-group-row]", dialog).map((row, index) => ({
                id: `uplink-${index + 1}`,
                name: qs("[data-group-name]", row).value,
                port_count: Number(qs("[data-group-count]", row).value || 0),
                port_type: qs("[data-group-type]", row).value,
            }));
            status.textContent = "Aplicando…";
            try {
                await request(hardwareUrl(elementId, oltId), {
                    method: "POST",
                    body: JSON.stringify({ action: "replace_uplink_groups", uplink_groups: groups }),
                });
                dialog.close();
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
    }

    function collectOriginalPorts(node) {
        const result = new Map();
        qsa(".master-node-port[data-port-id]", node).forEach((button) => {
            const id = Number(button.dataset.portId || 0);
            if (id && !result.has(id)) result.set(id, button);
        });
        return result;
    }

    function fallbackPort(port) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "master-node-port v07544-fallback-port";
        button.dataset.portId = String(port.id);
        button.dataset.portType = port.port_type;
        button.dataset.portRole = "front";
        button.dataset.linkId = port.link_id || "";
        button.innerHTML = `<i></i><span>${port.number}</span>`;
        button.title = `${port.label} · ${port.port_type_label}`;
        return button;
    }

    function takePort(portMap, port) {
        const button = portMap.get(Number(port.id)) || fallbackPort(port);
        button.classList.add("v07544-hardware-port");
        button.dataset.linkId = port.link_id || "";
        button.dataset.portRole = "front";
        button.title = `${port.label} · ${port.port_type_label}`;
        const span = qs("span", button);
        if (span) span.textContent = String(port.number);
        portMap.delete(Number(port.id));
        return button;
    }

    function cleanupLegacyOlt(node) {
        qsa(":scope > .v07543-olt-bottom-grid, :scope > .v07543-olt-organizer, :scope > .v07544-olt-face", node).forEach((item) => item.remove());
        qsa(".v07543-card-profile", node).forEach((item) => item.remove());
    }

    function renderOltFace(node, hardware) {
        const portMap = collectOriginalPorts(node);
        cleanupLegacyOlt(node);
        qsa(".master-olt-slot-v07510, .master-node-ports", node).forEach((legacy) => legacy.classList.add("v07544-legacy-hidden"));
        const face = document.createElement("section");
        face.className = "v07544-olt-face";
        const service = document.createElement("div");
        service.className = "v07544-service-stack";
        hardware.cards.forEach((card) => {
            const section = document.createElement("section");
            section.className = "v07544-service-card";
            section.dataset.cardId = String(card.id);
            section.innerHTML = `<header><div><strong>S${card.slot} · ${escapeHtml(card.name)}</strong><small>${technologyLabel(card.technology)}${card.model ? ` · ${escapeHtml(card.model)}` : ""}</small></div><span>${card.ports.length} PON</span></header><div class="v07544-pon-grid"></div>`;
            const grid = qs(".v07544-pon-grid", section);
            card.ports.forEach((port) => grid.appendChild(takePort(portMap, port)));
            section.addEventListener("contextmenu", (event) => {
                if (event.target.closest(".master-node-port")) return;
                event.preventDefault();
                event.stopPropagation();
                openCardEditor(node, card);
            });
            service.appendChild(section);
            const organizer = document.createElement("div");
            organizer.className = "v07544-card-organizer";
            organizer.dataset.v07544CardOrganizer = String(card.id);
            organizer.innerHTML = `<i></i><span>ORGANIZADOR · S${card.slot}</span><i></i>`;
            service.appendChild(organizer);
        });
        const uplinks = document.createElement("aside");
        uplinks.className = "v07544-uplink-stack";
        uplinks.innerHTML = `<header><div><strong>UPLINKS</strong><small>Somente grupos definidos no cadastro</small></div>${canEdit() ? '<button type="button" data-configure-uplinks>Configurar</button>' : ""}</header>`;
        const groups = document.createElement("div");
        groups.className = "v07544-uplink-groups";
        hardware.uplink_groups.forEach((group) => {
            const section = document.createElement("section");
            section.className = "v07544-uplink-group";
            section.dataset.uplinkGroup = group.id;
            section.innerHTML = `<header><strong>${escapeHtml(group.name)}</strong><small>${escapeHtml(group.port_type_label)} · ${group.ports.length} porta(s)</small></header><div></div>`;
            const body = qs(":scope > div", section);
            group.ports.forEach((port) => body.appendChild(takePort(portMap, port)));
            groups.appendChild(section);
            const organizer = document.createElement("div");
            organizer.className = "v07544-uplink-organizer";
            organizer.dataset.v07544UplinkOrganizer = group.id;
            organizer.innerHTML = `<i></i><span>ORGANIZADOR · ${escapeHtml(group.name)}</span><i></i>`;
            groups.appendChild(organizer);
        });
        if (!hardware.uplink_groups.length) groups.innerHTML = '<p class="v07544-empty-uplinks">OLT sem uplinks definidos.</p>';
        uplinks.appendChild(groups);
        qs("[data-configure-uplinks]", uplinks)?.addEventListener("click", (event) => {
            event.stopPropagation();
            openUplinkConfiguration(node, hardware);
        });
        face.append(service, uplinks);
        node.appendChild(face);
        node.classList.add("v07544-olt-hardware");
        node.dataset.v07544SlotCount = String(hardware.cards.length);
    }

    async function enhanceOlt(node, generation) {
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        if (!elementId || !oltId) return;
        const hardware = await loadHardware(elementId, oltId, true);
        if (generation !== state.generation || !node.isConnected) return;
        renderOltFace(node, hardware);
        global.setTimeout(() => global.mapRackPhysicalV07542?.refresh?.(), 0);
    }

    function enhanceDio(node) {
        qsa(".v07542-dio-organizer, .v07543-dio-organizer, .v07544-dio-organizer", node).forEach((item) => item.remove());
        qsa(".v07539-dio-cavity", node).forEach((cavity, index) => {
            const organizer = document.createElement("div");
            organizer.className = "v07544-dio-organizer";
            organizer.dataset.cavityIndexV07544 = String(index);
            organizer.innerHTML = `<i></i><span>ORGANIZADOR ÓPTICO · CAVIDADE ${index + 1}</span><i></i>`;
            cavity.after(organizer);
        });
        node.classList.add("v07544-dio-routing");
    }

    function hideRedundantToolbarActions(root) {
        qsa("[data-container-lines]", root).forEach((button) => { button.hidden = true; });
        qsa("button", qs("#container-dialog") || root).forEach((button) => {
            const label = button.textContent.replace(/\s+/g, " ").trim().toLowerCase();
            if (label === "ligar portas" || label === "editar linhas") button.hidden = true;
        });
    }

    function readView() {
        const canvas = state.canvas;
        if (!canvas) return { scale: 1, tx: 0, ty: 0 };
        const transform = getComputedStyle(canvas).transform;
        if (transform && transform !== "none" && global.DOMMatrixReadOnly) {
            const matrix = new DOMMatrixReadOnly(transform);
            return { scale: matrix.a || 1, tx: matrix.e || 0, ty: matrix.f || 0 };
        }
        return { scale: Number(canvas.dataset.v0741Scale || 1) || 1, tx: 0, ty: 0 };
    }

    function applyView(view) {
        if (!state.canvas) return;
        state.canvas.style.transformOrigin = "0 0";
        state.canvas.style.transform = `translate(${view.tx}px, ${view.ty}px) scale(${view.scale})`;
        state.canvas.dataset.v0741Scale = String(view.scale);
        const output = qs("[data-canvas-zoom-value]", state.root);
        if (output) output.textContent = `${Math.round(view.scale * 100)}%`;
        scheduleRedraw();
    }

    function emptyPanTarget(target) {
        if (!(target instanceof Element)) return false;
        return !target.closest(".master-canvas-node, .master-cable-node, button, a, input, select, textarea, dialog, .map-canvas-zoom-v0741, .v07542-rack-toolbar, .master-container-commandbar-v0741");
    }

    function installNavigation(scroll) {
        if (!scroll || scroll.dataset.navigationV07544 === "1") return;
        scroll.dataset.navigationV07544 = "1";
        scroll.classList.add("v07544-navigation-enabled");
        scroll.addEventListener("wheel", (event) => {
            if (currentKind() !== "rack") return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const before = readView();
            const scale = clamp(before.scale + (event.deltaY < 0 ? 0.08 : -0.08), 0.24, 1.8);
            const rect = scroll.getBoundingClientRect();
            const cursorX = event.clientX - rect.left;
            const cursorY = event.clientY - rect.top;
            const worldX = (cursorX - before.tx) / before.scale;
            const worldY = (cursorY - before.ty) / before.scale;
            applyView({
                scale,
                tx: cursorX - worldX * scale,
                ty: cursorY - worldY * scale,
            });
        }, { passive: false, capture: true });
        scroll.addEventListener("pointerdown", (event) => {
            if (currentKind() !== "rack" || event.button !== 0 || !emptyPanTarget(event.target)) return;
            event.preventDefault();
            event.stopPropagation();
            scroll.setPointerCapture?.(event.pointerId);
            const view = readView();
            state.pan = {
                pointerId: event.pointerId,
                x: event.clientX,
                y: event.clientY,
                tx: view.tx,
                ty: view.ty,
                scale: view.scale,
            };
            scroll.classList.add("is-panning-v07544");
        }, true);
        scroll.addEventListener("pointermove", (event) => {
            const pan = state.pan;
            if (!pan || event.pointerId !== pan.pointerId) return;
            applyView({
                scale: pan.scale,
                tx: pan.tx + event.clientX - pan.x,
                ty: pan.ty + event.clientY - pan.y,
            });
        }, true);
        const finish = (event) => {
            if (!state.pan || (event.pointerId != null && event.pointerId !== state.pan.pointerId)) return;
            state.pan = null;
            scroll.classList.remove("is-panning-v07544");
        };
        scroll.addEventListener("pointerup", finish, true);
        scroll.addEventListener("pointercancel", finish, true);
    }

    function ensureSvg(canvas) {
        let svg = qs("svg[data-rack-links-v07544]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07544 = "1";
            svg.classList.add("v07544-rack-links");
            canvas.prepend(svg);
        }
        state.svg = svg;
        return svg;
    }

    function centerInCanvas(element) {
        const canvas = state.canvas;
        let x = element.offsetWidth / 2;
        let y = element.offsetHeight / 2;
        let current = element;
        while (current && current !== canvas) {
            x += current.offsetLeft || 0;
            y += current.offsetTop || 0;
            current = current.offsetParent;
        }
        return { x, y };
    }

    function sidePoint(element, side) {
        const center = centerInCanvas(element);
        return { x: center.x + (side === "left" ? -element.offsetWidth / 2 : element.offsetWidth / 2), y: center.y };
    }

    function svgPath(svg, d, className, attributes = {}) {
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d);
        path.setAttribute("class", className);
        Object.entries(attributes).forEach(([key, value]) => path.setAttribute(key, String(value)));
        svg.appendChild(path);
        return path;
    }

    function organizerForPort(port) {
        const card = port.closest(".v07544-service-card");
        if (card) {
            const organizer = card.nextElementSibling;
            if (organizer?.classList.contains("v07544-card-organizer")) return centerInCanvas(organizer);
        }
        const group = port.closest(".v07544-uplink-group");
        if (group) {
            const organizer = group.nextElementSibling;
            if (organizer?.classList.contains("v07544-uplink-organizer")) return centerInCanvas(organizer);
        }
        const dio = port.closest('[data-equipment-type="dio"]');
        if (dio) {
            const cavity = port.closest(".v07539-dio-cavity");
            const organizer = cavity?.nextElementSibling;
            if (organizer?.classList.contains("v07544-dio-organizer")) return centerInCanvas(organizer);
        }
        const equipment = port.closest(".v07542-rack-mounted");
        if (!equipment) return centerInCanvas(port);
        const center = centerInCanvas(equipment);
        const organizers = qsa(".v07542-rack-organizer", state.canvas).map((node) => ({ node, point: centerInCanvas(node) }));
        if (!organizers.length) return center;
        const bottom = center.y + equipment.offsetHeight / 2;
        return organizers.sort((a, b) => Math.abs(a.point.y - bottom) - Math.abs(b.point.y - bottom))[0].point;
    }

    function ductX(start, end) {
        const left = qs(".v07542-duct.left", state.canvas);
        const right = qs(".v07542-duct.right", state.canvas);
        if (!left || !right) return (start.x + end.x) / 2;
        const leftX = centerInCanvas(left).x;
        const rightX = centerInCanvas(right).x;
        const leftCost = Math.abs(start.x - leftX) + Math.abs(end.x - leftX);
        const rightCost = Math.abs(start.x - rightX) + Math.abs(end.x - rightX);
        return leftCost <= rightCost ? leftX : rightX;
    }

    function drawFrontLinks(svg) {
        const groups = new Map();
        qsa('.master-canvas-node:not([hidden]) .master-node-port[data-link-id]:not([data-link-id=""])', state.canvas).forEach((port) => {
            if (port.dataset.portRole === "rear" || port.closest(".v07544-legacy-hidden")) return;
            const linkId = String(port.dataset.linkId || "");
            if (!groups.has(linkId)) groups.set(linkId, []);
            groups.get(linkId).push(port);
        });
        [...groups.entries()].forEach(([linkId, ports]) => {
            const unique = [...new Set(ports)];
            if (unique.length < 2) return;
            const start = centerInCanvas(unique[0]);
            const end = centerInCanvas(unique[1]);
            const startOrganizer = organizerForPort(unique[0]);
            const endOrganizer = organizerForPort(unique[1]);
            const channel = ductX(start, end);
            svgPath(svg, `M ${start.x} ${start.y} V ${startOrganizer.y} H ${channel} V ${endOrganizer.y} H ${end.x} V ${end.y}`, "v07544-front-link", { "data-link-id": linkId });
        });
    }

    function linkedCableIds(dioNode) {
        return String(dioNode.dataset.linkedCableIdsV07537 || dioNode.dataset.linkedCableIdsV07538 || "")
            .split(",").map(Number).filter(Boolean);
    }

    function drawRearTrunks(svg) {
        const cables = new Map();
        qsa(".master-cable-node[data-cable-node], .master-cable-node[data-cable-node-id]", state.canvas).forEach((node) => {
            const id = Number(node.dataset.cableNode || node.dataset.cableNodeId || 0);
            if (id && !cables.has(id)) cables.set(id, node);
        });
        const targets = new Map();
        qsa('.master-canvas-node[data-equipment-type="dio"]', state.canvas).forEach((dio) => {
            const cavities = qsa(".v07539-dio-cavity", dio);
            linkedCableIds(dio).forEach((cableId, index) => {
                const cavity = cavities[index % Math.max(1, cavities.length)] || dio;
                const organizer = cavity.nextElementSibling?.classList?.contains("v07544-dio-organizer") ? cavity.nextElementSibling : cavity;
                if (!targets.has(cableId)) targets.set(cableId, []);
                targets.get(cableId).push({ cavity, organizer });
            });
        });
        [...targets.entries()].forEach(([cableId, rows], index) => {
            const cable = cables.get(cableId);
            if (!cable) return;
            const anchor = qs("[data-rack-cable-anchor-v07538]", cable) || cable;
            const start = centerInCanvas(anchor);
            const frame = qs("[data-rack-frame-v07542]", state.canvas);
            if (!frame) return;
            const frameCenter = centerInCanvas(frame);
            const useLeft = start.x < frameCenter.x;
            const duct = qs(`.v07542-duct.${useLeft ? "left" : "right"}`, state.canvas);
            const spineX = centerInCanvas(duct).x + (useLeft ? 8 + index * 2 : -8 - index * 2);
            const points = rows.map(({ cavity, organizer }) => ({
                organizer: centerInCanvas(organizer),
                target: sidePoint(cavity, useLeft ? "left" : "right"),
            })).sort((a, b) => a.organizer.y - b.organizer.y);
            if (!points.length) return;
            svgPath(svg, `M ${start.x} ${start.y} H ${spineX} V ${points[0].organizer.y}`, "v07544-rear-trunk", { "data-cable-id": cableId });
            const lastY = points[points.length - 1].organizer.y;
            if (lastY !== points[0].organizer.y) svgPath(svg, `M ${spineX} ${points[0].organizer.y} V ${lastY}`, "v07544-rear-trunk", { "data-cable-id": cableId });
            points.forEach((point) => svgPath(svg, `M ${spineX} ${point.organizer.y} H ${point.target.x} V ${point.target.y}`, "v07544-rear-branch", { "data-cable-id": cableId }));
        });
    }

    function redraw() {
        if (!state.canvas || currentKind() !== "rack") return;
        const svg = ensureSvg(state.canvas);
        const width = Math.max(state.canvas.scrollWidth, 1600);
        const height = Math.max(state.canvas.scrollHeight, 900);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.style.width = `${width}px`;
        svg.style.height = `${height}px`;
        svg.innerHTML = "";
        drawFrontLinks(svg);
        drawRearTrunks(svg);
    }

    function scheduleRedraw() {
        if (state.frame) return;
        state.frame = global.requestAnimationFrame(() => {
            state.frame = 0;
            redraw();
        });
    }

    async function enhance(data = null, generation = 0) {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        if (!root || !dialog?.open) return;
        state.root = root;
        state.data = data || state.data;
        if (currentKind() !== "rack") return;
        state.canvas = qs(".master-canvas", root);
        state.scroll = qs(".master-canvas-scroll", root);
        if (!state.canvas || !state.scroll) return;
        hideRedundantToolbarActions(root);
        installNavigation(state.scroll);
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach(enhanceDio);
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="olt"]', root).map((node) => enhanceOlt(node, generation).catch((error) => {
            node.dataset.v07544HardwareError = error.message;
            console.error("MAP v0.75.44 OLT:", error);
        })));
        if (generation !== state.generation) return;
        scheduleRedraw();
        global.setTimeout(scheduleRedraw, 180);
    }

    function schedule(data = null) {
        if (data) state.data = data;
        const generation = ++state.generation;
        global.requestAnimationFrame(() => enhance(state.data, generation).catch((error) => console.error("MAP v0.75.44:", error)));
    }

    function init() {
        installCreationInterception();
        document.addEventListener("map:container-rendered", (event) => schedule(event.detail?.data || null));
        document.addEventListener("map:container-opening", () => global.setTimeout(schedule, 150));
        global.addEventListener("resize", scheduleRedraw);
        global.setTimeout(schedule, 900);
        global.mapRackHardwareV07544 = Object.freeze({ version: VERSION, refresh: schedule, redraw: scheduleRedraw });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
