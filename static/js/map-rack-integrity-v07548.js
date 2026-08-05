(function (global) {
    "use strict";

    const VERSION = "0.75.48";
    const state = {
        observer: null,
        topology: null,
        topologyKey: "",
        frame: 0,
        editor: null,
        cardDialog: null,
        infoDialog: null,
        pathPanel: null,
        pendingLinkRequests: new Map(),
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function rootNode() { return qs("#map-master-container"); }
    function canvasNode(root = rootNode()) { return qs(".master-canvas", root); }
    function scrollNode(root = rootNode()) { return qs(".master-canvas-scroll", root); }
    function currentElementId(root = rootNode()) {
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }
    function equipmentId(node) { return Number(node?.dataset.equipmentNode || node?.dataset.equipmentId || 0); }
    function isRack(root = rootNode()) {
        if (!root) return false;
        if (root.classList.contains("v07542-physical-rack")) return true;
        const dialog = qs("#container-dialog");
        return [root.dataset.elementType, root.dataset.containerType, dialog?.dataset.elementType, dialog?.dataset.containerType]
            .map((value) => String(value || "").toLowerCase())
            .some((value) => value === "rack" || value.includes("rack"));
    }
    function canEdit() { return document.body.dataset.canEdit === "true"; }
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
    function notify(message, error = false) { global.networkMap?.notify?.(message, error); }

    function installRequestGuard() {
        if (global.fetch?.v07548RackGuard) return;
        const originalFetch = global.fetch.bind(global);
        const guardedFetch = function (input, options = {}) {
            const rawUrl = typeof input === "string" ? input : input?.url || "";
            const url = new URL(rawUrl, global.location.href);
            const method = String(options.method || input?.method || "GET").toUpperCase();

            // Rack não é caixa de emenda. Evita chamadas herdadas que só produziriam HTTP 400.
            if (isRack() && method === "GET" && /^\/api\/map\/elements\/\d+\/splices\/?$/.test(url.pathname)) {
                return Promise.resolve(new Response(JSON.stringify({
                    splices: [],
                    links: [],
                    summary: {},
                    ignored_for_rack: true,
                }), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }));
            }

            // Várias camadas legadas ainda podem receber o mesmo gesto de ligação.
            // Compartilha a resposta da primeira escrita em voo em vez de criar 409 duplicado.
            if (isRack() && method === "POST" && /\/api\/map\/elements\/\d+\/equipment-links\/?$/.test(url.pathname)) {
                const body = typeof options.body === "string" ? options.body : "";
                const key = `${url.pathname}|${body}`;
                const pending = state.pendingLinkRequests.get(key);
                if (pending) return pending.then((snapshot) => snapshot());
                const requestPromise = originalFetch(input, options).then(async (response) => {
                    const blob = await response.blob();
                    const headers = [...response.headers.entries()];
                    return () => new Response(blob.slice(0, blob.size, blob.type), {
                        status: response.status,
                        statusText: response.statusText,
                        headers,
                    });
                }).finally(() => state.pendingLinkRequests.delete(key));
                state.pendingLinkRequests.set(key, requestPromise);
                return requestPromise.then((snapshot) => snapshot());
            }
            return originalFetch(input, options);
        };
        guardedFetch.v07548RackGuard = true;
        guardedFetch.originalFetch = originalFetch;
        global.fetch = guardedFetch;
    }

    function refreshContainer(elementId = currentElementId()) {
        state.topology = null;
        state.topologyKey = "";
        return global.mapMasterSuite?.openContainerWorkspace?.(elementId);
    }

    function essentialNodes(root = rootNode()) {
        if (!root) return [];
        return qsa('.master-canvas-node[data-equipment-type="olt"], .master-canvas-node[data-equipment-type="dio"], .master-canvas-node[data-equipment-type="switch"]', root)
            .filter((node) => !node.hidden && node.isConnected && getComputedStyle(node).display !== "none");
    }

    function syncEmptyRack() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        const empty = essentialNodes(root).length === 0;
        root.classList.toggle("v07548-rack-empty", empty);
        const prompt = qs(".tower-empty-v0750", root);
        if (prompt) {
            prompt.hidden = !empty;
            prompt.classList.toggle("v07548-empty-visible", empty);
        }
        qsa(".master-cable-node", root).forEach((node) => { node.setAttribute("aria-hidden", empty ? "true" : "false"); });
    }

    function hideRackPaletteItems() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        const scope = qs("#container-dialog") || root;
        qsa('[data-quick-add="pto"], [data-quick-add="other"]', scope).forEach((node) => { node.hidden = true; node.dataset.hiddenRackV07548 = "1"; });
        qsa("button, a, [role='menuitem']", scope).forEach((node) => {
            const label = String(node.textContent || "").replace(/\s+/g, " ").trim();
            if (/^(PTO|Outro)(?:\s|$)/i.test(label)) {
                node.hidden = true;
                node.dataset.hiddenRackV07548 = "1";
            }
        });
    }

    function oltFieldsHtml() {
        return `<div class="v07548-create-grid">
            <label>Nome<input name="name" required maxlength="120"></label>
            <label>Fabricante<input name="vendor" maxlength="80"></label>
            <label>Modelo do chassi<input name="model" maxlength="120" placeholder="Ex.: AN5516-06"></label>
            <label>IP de gerência<input name="management_ip" placeholder="192.168.0.10"></label>
            <label>Disposição das placas<select name="chassis_orientation"><option value="vertical">Placas verticais · lado a lado</option><option value="horizontal">Placas horizontais · uma sobre a outra</option></select></label>
            <label>Slots de placas de serviço<input name="service_slot_count" type="number" min="1" max="32" value="4"></label>
            <label>Slots de uplink<input name="uplink_slot_count" type="number" min="0" max="16" value="0"></label>
        </div><p class="v07548-hint">A OLT nasce com slots vazios. Cada placa define depois a tecnologia e a quantidade de PONs.</p>`;
    }

    function patchRackCreateForm() {
        const dialog = qs("#map-rack-equipment-v07542");
        const form = qs("[data-rack-equipment-form-v07542]", dialog);
        if (form) {
            const type = qs("[data-type-v07542]", form);
            const fields = qs("[data-fields-v07542]", form);
            qsa('option[value="pto"], option[value="other"]', type).forEach((option) => option.remove());
            if (type?.value === "olt" && fields) {
                if (fields.dataset.v07548Olt !== "1" || fields.querySelector('[name="pons_per_card"], [name="card_count"]')) {
                    fields.dataset.v07548Olt = "1";
                    fields.innerHTML = oltFieldsHtml();
                }
            } else if (fields) {
                delete fields.dataset.v07548Olt;
            }
        }

        const modern = qs("#map-v07539-modal form[data-create-equipment]");
        if (modern) {
            const type = qs("[data-create-type]", modern);
            const fields = qs("[data-create-fields]", modern);
            qsa('option[value="pto"], option[value="other"]', type).forEach((option) => option.remove());
            if (type?.value === "olt" && fields) {
                fields.dataset.v07548Olt = "1";
                fields.innerHTML = oltFieldsHtml();
            }
        }
    }

    async function submitOltCreation(event, form) {
        const type = qs("[data-type-v07542], [data-create-type]", form)?.value;
        if (type !== "olt") return false;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const elementId = currentElementId();
        if (!elementId) return notify("Rack não identificado.", true), true;
        const data = Object.fromEntries(new FormData(form));
        const status = qs("[data-status-v07542], [data-form-status]", form);
        if (status) status.textContent = "Criando chassi…";
        const payload = {
            equipment_type: "olt",
            name: String(data.name || "").trim(),
            vendor: String(data.vendor || "").trim(),
            model: String(data.model || "").trim(),
            chassis_model: String(data.model || "").trim(),
            management_ip: data.management_ip || null,
            provisioning_mode: "manual",
            enabled: true,
            chassis_orientation: data.chassis_orientation || "horizontal",
            service_slot_count: Number(data.service_slot_count || 0),
            uplink_slot_count: Number(data.uplink_slot_count || 0),
        };
        try {
            await request(`/api/map/v07547/elements/${elementId}/equipment/`, { method: "POST", body: JSON.stringify(payload) });
            form.closest("dialog")?.close();
            notify("OLT criada com todos os slots vazios.");
            await refreshContainer(elementId);
            scheduleEnhance();
        } catch (error) {
            if (status) status.textContent = error.message;
            else notify(error.message, true);
        }
        return true;
    }

    function ensureEditorDialog() {
        if (state.editor?.isConnected) return state.editor;
        const dialog = document.createElement("dialog");
        dialog.id = "map-rack-olt-editor-v07548";
        dialog.className = "v07548-dialog v07548-editor";
        dialog.innerHTML = `<form><header><div><small>EDITOR DA OLT</small><h2 data-title>OLT</h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div data-body></div></form>`;
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
        state.editor = dialog;
        return dialog;
    }

    function technologyLabel(value) { return ({ gpon: "GPON", xgpon: "XG-PON", xgspon: "XGS-PON" })[value] || "GPON"; }

    function slotHtml(slot) {
        if (slot.empty) {
            return `<article class="v07548-slot-card is-empty" data-slot="${slot.slot}"><header><div><strong>S${slot.slot}</strong><small>Slot de serviço vazio</small></div><button type="button" data-edit-slot="${slot.slot}">Adicionar placa</button></header></article>`;
        }
        const card = slot.card;
        return `<article class="v07548-slot-card" data-slot="${slot.slot}"><header><div><strong>S${slot.slot} · ${escapeHtml(card.name)}</strong><small>${technologyLabel(card.technology)}${card.model ? ` · ${escapeHtml(card.model)}` : ""}</small></div><button type="button" data-edit-slot="${slot.slot}">Editar placa</button></header><div class="v07548-power-grid">${card.ports.map((port) => `<label data-port-row="${port.id}"><span>PON ${port.number}${port.linked ? " · ligada" : ""}</span><input name="port_power_${port.id}" type="number" step="0.01" min="-50" max="20" value="${port.tx_power_dbm ?? ""}" placeholder="dBm"><button type="button" data-trace-port="${port.id}" title="Ver caminho óptico">Caminho</button></label>`).join("")}</div></article>`;
    }

    async function loadOltEditor(elementId, oltId) {
        return request(`/api/map/v07548/elements/${elementId}/olt/${oltId}/editor/`);
    }

    async function openOltEditor(node) {
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        if (!elementId || !oltId) return;
        const data = await loadOltEditor(elementId, oltId);
        const dialog = ensureEditorDialog();
        qs("[data-title]", dialog).textContent = data.equipment.name;
        qs("[data-subtitle]", dialog).textContent = `${data.slots.length} slot(s) de serviço · ${data.uplink_slots.length} slot(s) de uplink`;
        qs("[data-body]", dialog).innerHTML = `<section class="v07548-editor-body"><div class="v07548-editor-grid">
            <label>Nome<input name="name" value="${escapeHtml(data.equipment.name)}"></label>
            <label>Fabricante<input name="vendor" value="${escapeHtml(data.equipment.vendor || "")}"></label>
            <label>Modelo do chassi<input name="chassis_model" value="${escapeHtml(data.chassis.chassis_model || "")}"></label>
            <label>Serial<input name="serial_number" value="${escapeHtml(data.equipment.serial_number || "")}"></label>
            <label>IP de gerenciamento<input name="management_ip" value="${escapeHtml(data.equipment.management_ip || "")}"></label>
            <label>Provisionamento<select name="provisioning_mode"><option value="manual" ${data.equipment.provisioning_mode !== "snmp" ? "selected" : ""}>Manual</option><option value="snmp" ${data.equipment.provisioning_mode === "snmp" ? "selected" : ""}>SNMP</option></select></label>
            <label>Potência TX padrão (dBm)<input name="tx_power_dbm" type="number" step="0.01" value="${data.equipment.tx_power_dbm ?? ""}"></label>
            <label>Disposição<select name="orientation"><option value="vertical" ${data.chassis.orientation === "vertical" ? "selected" : ""}>Placas verticais</option><option value="horizontal" ${data.chassis.orientation === "horizontal" ? "selected" : ""}>Placas horizontais</option></select></label>
            <label>Slots de serviço<input name="service_slot_count" type="number" min="1" max="32" value="${data.chassis.service_slot_count}"></label>
            <label>Slots de uplink<input name="uplink_slot_count" type="number" min="0" max="16" value="${data.chassis.uplink_slot_count}"></label>
            <label class="wide">Observações<textarea name="description" rows="3">${escapeHtml(data.equipment.description || "")}</textarea></label>
        </div><section class="v07548-slots"><header><div><strong>Placas e potência por PON</strong><small>Sem SNMP, informe manualmente a potência individual.</small></div></header>${data.slots.map(slotHtml).join("")}</section><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary">Salvar OLT</button></footer></section>`;
        const form = qs("form", dialog);
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qsa("[data-edit-slot]", dialog).forEach((button) => button.onclick = () => openCardEditor(elementId, oltId, data.slots.find((item) => item.slot === Number(button.dataset.editSlot))));
        qsa("[data-trace-port]", dialog).forEach((button) => button.onclick = () => tracePort(elementId, oltId, Number(button.dataset.tracePort)));
        form.onsubmit = async (event) => {
            event.preventDefault();
            const fd = new FormData(form);
            const powers = {};
            qsa("[data-port-row]", form).forEach((row) => {
                powers[row.dataset.portRow] = qs("input", row)?.value || "";
            });
            const payload = {
                name: fd.get("name"), vendor: fd.get("vendor"), chassis_model: fd.get("chassis_model"),
                serial_number: fd.get("serial_number"), management_ip: fd.get("management_ip"),
                provisioning_mode: fd.get("provisioning_mode"), tx_power_dbm: fd.get("tx_power_dbm"),
                orientation: fd.get("orientation"), service_slot_count: Number(fd.get("service_slot_count") || 0),
                uplink_slot_count: Number(fd.get("uplink_slot_count") || 0), description: fd.get("description"),
                enabled: true, port_tx_power_dbm: powers,
            };
            const status = qs("[data-status]", form);
            status.textContent = "Salvando…";
            try {
                await request(`/api/map/v07548/elements/${elementId}/olt/${oltId}/editor/`, { method: "PATCH", body: JSON.stringify(payload) });
                dialog.close();
                await refreshContainer(elementId);
                notify("OLT atualizada.");
            } catch (error) { status.textContent = error.message; }
        };
        if (!dialog.open) dialog.showModal();
    }

    function ensureCardDialog() {
        if (state.cardDialog?.isConnected) return state.cardDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-rack-card-editor-v07548";
        dialog.className = "v07548-dialog v07548-card-dialog";
        document.body.appendChild(dialog);
        state.cardDialog = dialog;
        return dialog;
    }

    function openCardEditor(elementId, oltId, slot) {
        const dialog = ensureCardDialog();
        const card = slot.card;
        dialog.innerHTML = `<form><header><div><small>PLACA DE SERVIÇO</small><h2>${card ? "Editar" : "Adicionar"} placa · S${slot.slot}</h2><p>${card ? `${card.ports.length} PON(s)` : "Slot vazio"}</p></div><button type="button" data-close>×</button></header><div class="v07548-card-body"><label>Nome<input name="name" value="${escapeHtml(card?.name || `Placa ${slot.slot}`)}"></label><label>Modelo<input name="model" value="${escapeHtml(card?.model || "")}"></label><label>Tecnologia<select name="technology"><option value="gpon" ${!card || card.technology === "gpon" ? "selected" : ""}>GPON</option><option value="xgpon" ${card?.technology === "xgpon" ? "selected" : ""}>XG-PON</option><option value="xgspon" ${card?.technology === "xgspon" ? "selected" : ""}>XGS-PON</option></select></label><label>Portas PON<input name="pon_count" type="number" min="1" max="32" value="${card?.ports.length || 16}"></label><p data-status></p></div><footer>${card ? '<button type="button" class="danger" data-remove>Remover placa</button>' : ""}<span></span><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary">Salvar placa</button></footer></form>`;
        qs("[data-close]", dialog).onclick = () => dialog.close();
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            const fd = new FormData(event.currentTarget);
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando…";
            try {
                await request(`/api/map/v07547/elements/${elementId}/olt/${oltId}/chassis/`, { method: "POST", body: JSON.stringify({ action: "install_card", slot: slot.slot, name: fd.get("name"), model: fd.get("model"), technology: fd.get("technology"), pon_count: Number(fd.get("pon_count") || 0) }) });
                dialog.close();
                state.editor?.close();
                await refreshContainer(elementId);
                notify(`Placa do slot S${slot.slot} salva.`);
            } catch (error) { status.textContent = error.message; }
        };
        qs("[data-remove]", dialog)?.addEventListener("click", async () => {
            const status = qs("[data-status]", dialog);
            try {
                await request(`/api/map/v07547/elements/${elementId}/olt/${oltId}/chassis/`, { method: "POST", body: JSON.stringify({ action: "remove_card", slot: slot.slot }) });
                dialog.close(); state.editor?.close(); await refreshContainer(elementId);
            } catch (error) { status.textContent = error.message; }
        });
        if (!dialog.open) dialog.showModal();
    }

    function centerInCanvas(element, canvas) {
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

    function ensureTopologySvg(canvas) {
        let svg = qs("svg[data-rack-links-v07548]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07548 = "1";
            svg.classList.add("v07548-rack-links");
            canvas.prepend(svg);
        }
        return svg;
    }

    function drawTopology() {
        const root = rootNode();
        const canvas = canvasNode(root);
        if (!root || !canvas || !isRack(root) || !state.topology) return;
        const svg = ensureTopologySvg(canvas);
        const width = Math.max(canvas.scrollWidth, 1600);
        const height = Math.max(canvas.scrollHeight, 900);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.style.width = `${width}px`; svg.style.height = `${height}px`; svg.innerHTML = "";
        const frame = qs("[data-rack-frame-v07542]", canvas);
        const framePoint = frame ? centerInCanvas(frame, canvas) : { x: 600, y: 300 };
        const leftDuct = qs(".v07542-duct.left", canvas);
        const rightDuct = qs(".v07542-duct.right", canvas);
        state.topology.rear_links.forEach((link, index) => {
            const cable = qs(`.master-cable-node[data-cable-node="${link.cable_id}"], .master-cable-node[data-cable-node-id="${link.cable_id}"]`, canvas);
            const dio = qs(`.master-canvas-node[data-equipment-node="${link.dio_id}"]`, canvas);
            const target = qs(`[data-port-id="${link.dio_port_id}"][data-port-role="rear"]`, dio) || qs(`[data-port-id="${link.dio_port_id}"]`, dio);
            if (!cable || !target) return;
            const anchor = qs("[data-rack-cable-anchor-v07538]", cable) || cable;
            const start = centerInCanvas(anchor, canvas);
            const end = centerInCanvas(target, canvas);
            const useLeft = start.x < framePoint.x;
            const duct = useLeft ? leftDuct : rightDuct;
            const channelX = duct ? centerInCanvas(duct, canvas).x + (useLeft ? 5 + index * 2 : -5 - index * 2) : (start.x + end.x) / 2;
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", `M ${start.x} ${start.y} H ${channelX} V ${end.y} H ${end.x}`);
            path.setAttribute("class", "v07548-rear-link");
            path.dataset.cableId = String(link.cable_id || "");
            path.dataset.dioPortId = String(link.dio_port_id);
            svg.appendChild(path);
        });
    }

    function scheduleDraw() {
        if (state.frame) return;
        state.frame = global.requestAnimationFrame(() => { state.frame = 0; drawTopology(); });
    }

    async function loadTopology(force = false) {
        const elementId = currentElementId();
        if (!elementId) return null;
        const key = String(elementId);
        if (!force && state.topology && state.topologyKey === key) return state.topology;
        state.topology = await request(`/api/map/v07548/elements/${elementId}/rack-topology/`);
        state.topologyKey = key;
        const byDio = new Map();
        state.topology.rear_links.forEach((link) => {
            if (!byDio.has(link.dio_id)) byDio.set(link.dio_id, new Set());
            if (link.cable_id) byDio.get(link.dio_id).add(link.cable_id);
        });
        byDio.forEach((ids, dioId) => {
            const node = qs(`.master-canvas-node[data-equipment-node="${dioId}"]`, rootNode());
            if (node) node.dataset.linkedCableIdsV07538 = [...ids].join(",");
        });
        return state.topology;
    }

    function simplifyDioPorts() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        qsa('.master-canvas-node[data-equipment-type="dio"] .v07539-dio-pair .master-node-port', root).forEach((port) => {
            port.classList.add("v07548-dio-dot-port");
            const label = qs("span", port);
            if (label) label.setAttribute("aria-hidden", "true");
            const point = qs("i", port);
            if (point) point.classList.add("v07548-dio-dot");
        });
    }

    function ensureInfoDialog() {
        if (state.infoDialog?.isConnected) return state.infoDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-dio-port-info-v07548";
        dialog.className = "v07548-dialog v07548-info-dialog";
        document.body.appendChild(dialog);
        state.infoDialog = dialog;
        return dialog;
    }

    async function openDioPortInfo(port) {
        const dio = port.closest('[data-equipment-type="dio"]');
        const elementId = currentElementId();
        const dioId = equipmentId(dio);
        const portId = Number(port.dataset.portId || 0);
        if (!elementId || !dioId || !portId) return;
        const data = await request(`/api/map/v07539/elements/${elementId}/dio/${dioId}/dual-face/`);
        const row = data.ports.find((item) => Number(item.id) === portId);
        if (!row) return;
        const dialog = ensureInfoDialog();
        dialog.innerHTML = `<section><header><div><small>PORTA DO DIO</small><h2>${escapeHtml(row.label)}</h2><p>${escapeHtml(data.dio.name)}</p></div><button type="button" data-close>×</button></header><div class="v07548-info-grid"><article><strong>Frente</strong><span>${row.front ? `${escapeHtml(row.front.source_equipment)} · ${escapeHtml(row.front.source_port)}` : "Livre"}</span></article><article><strong>Traseira</strong><span>${row.rear ? `${escapeHtml(row.rear.cable || "Cabo")} ${row.rear.fiber_number ? `· fibra ${row.rear.fiber_number}` : ""}` : "Livre"}</span></article><article><strong>Estado</strong><span>${escapeHtml(row.state)}</span></article></div></section>`;
        qs("[data-close]", dialog).onclick = () => dialog.close();
        if (!dialog.open) dialog.showModal();
    }

    function ensurePathPanel() {
        if (state.pathPanel?.isConnected) return state.pathPanel;
        const panel = document.createElement("aside");
        panel.id = "map-optical-path-v07548";
        panel.className = "v07548-path-panel";
        document.body.appendChild(panel);
        state.pathPanel = panel;
        return panel;
    }

    function clearTrace() {
        qsa(".v07548-trace-active").forEach((node) => node.classList.remove("v07548-trace-active"));
        qsa("[data-cable-id].v07548-trace-path").forEach((node) => node.classList.remove("v07548-trace-path"));
        state.pathPanel?.remove(); state.pathPanel = null;
    }

    async function tracePort(elementId, oltId, portId) {
        const data = await request(`/api/map/v07548/elements/${elementId}/olt/${oltId}/ports/${portId}/path/`);
        clearTrace();
        qsa(`[data-port-id="${portId}"]`).forEach((node) => node.classList.add("v07548-trace-active"));
        if (data.dio_port_id) qsa(`[data-port-id="${data.dio_port_id}"]`).forEach((node) => node.classList.add("v07548-trace-active"));
        if (data.cable_id) {
            qsa(`[data-cable-node="${data.cable_id}"], [data-cable-node-id="${data.cable_id}"], [data-cable-id="${data.cable_id}"]`).forEach((node) => node.classList.add("v07548-trace-active", "v07548-trace-path"));
        }
        const panel = ensurePathPanel();
        panel.innerHTML = `<header><div><strong>Caminho óptico</strong><small>${data.complete_to_cable ? "OLT → DIO → cabo" : "Caminho parcial"}</small></div><button type="button" data-close>×</button></header><div>${data.segments.map((segment) => `<article><b>${escapeHtml(segment.kind.replaceAll("_", " "))}</b><span>${escapeHtml(segment.equipment || segment.dio || segment.cable || segment.port || segment.dio_port || "")}</span></article>`).join("")}</div><footer><span>TX ${data.tx_power_dbm ?? "—"} dBm</span><span>Perdas ${data.total_known_loss_db} dB</span><strong>Estimado ${data.estimated_power_after_dio_dbm ?? "—"} dBm</strong></footer>`;
        qs("[data-close]", panel).onclick = clearTrace;
        global.dispatchEvent(new CustomEvent("map:optical-path-highlight", { detail: data }));
    }

    function interceptEvents() {
        document.addEventListener("submit", (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) return;
            if (form.matches("[data-rack-equipment-form-v07542], form[data-create-equipment]")) submitOltCreation(event, form);
        }, true);
        document.addEventListener("change", (event) => {
            if (event.target?.matches?.("[data-type-v07542], [data-create-type]")) global.queueMicrotask(patchRackCreateForm);
        }, true);
        document.addEventListener("click", (event) => {
            const target = event.target instanceof Element ? event.target : null;
            if (!target) return;
            const edit = target.closest("[data-node-edit], [data-edit-equipment]");
            const olt = edit?.closest?.('.master-canvas-node[data-equipment-type="olt"]');
            if (edit && olt && isRack()) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                openOltEditor(olt).catch((error) => notify(error.message, true));
                return;
            }
            global.setTimeout(() => { patchRackCreateForm(); hideRackPaletteItems(); syncEmptyRack(); }, 0);
        }, true);
        document.addEventListener("contextmenu", (event) => {
            const port = event.target instanceof Element ? event.target.closest('.master-canvas-node[data-equipment-type="dio"] .master-node-port[data-port-id]') : null;
            if (!port || !isRack()) return;
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            openDioPortInfo(port).catch((error) => notify(error.message, true));
        }, true);
        document.addEventListener("map:container-rendered", scheduleEnhance);
        document.addEventListener("map:container-opening", scheduleEnhance);
        document.addEventListener("map:rack-viewport-changed", scheduleDraw);
        global.addEventListener("resize", scheduleDraw);
    }

    async function enhance() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        patchRackCreateForm();
        hideRackPaletteItems();
        syncEmptyRack();
        simplifyDioPorts();
        await loadTopology(true).catch((error) => console.warn("MAP v0.75.48 topology:", error));
        scheduleDraw();
    }

    function scheduleEnhance() {
        global.requestAnimationFrame(() => enhance().catch((error) => console.error("MAP v0.75.48:", error)));
        global.setTimeout(() => enhance().catch(() => {}), 120);
        global.setTimeout(() => enhance().catch(() => {}), 420);
    }

    function installObserver() {
        if (state.observer) return;
        state.observer = new MutationObserver(() => {
            patchRackCreateForm();
            hideRackPaletteItems();
            syncEmptyRack();
            simplifyDioPorts();
        });
        state.observer.observe(document.body, { childList: true, subtree: true });
    }

    function init() {
        installRequestGuard();
        installObserver();
        interceptEvents();
        scheduleEnhance();
    }

    global.mapRackIntegrityV07548 = Object.freeze({ version: VERSION, refresh: scheduleEnhance, tracePort, clearTrace });
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})(window);
