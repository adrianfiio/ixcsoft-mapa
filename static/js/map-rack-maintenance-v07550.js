(function (global) {
    "use strict";

    const VERSION = "0.75.50";
    const state = {
        generation: 0,
        observer: null,
        resizeObserver: null,
        uplinks: new Map(),
        pendingUplinks: new Map(),
        uplinkFailures: new Map(),
        renderedUplinks: new WeakMap(),
        serviceDialog: null,
        uplinkDialog: null,
        pan: null,
        enhanceTimer: 0,
        physicalTimer: 0,
        enhancing: false,
        rerun: false,
        lastAutoKey: "",
        lastAutoAt: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];
    const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function rootNode() { return qs("#map-master-container"); }
    function canvasNode(root = rootNode()) { return qs(".master-canvas", root); }
    function scrollNode(root = rootNode()) { return qs(".master-canvas-scroll", root); }
    function isRack(root = rootNode()) {
        if (!root) return false;
        if (root.classList.contains("v07542-physical-rack")) return true;
        const dialog = qs("#container-dialog");
        return [root.dataset.elementType, root.dataset.containerType, dialog?.dataset.elementType, dialog?.dataset.containerType]
            .map((value) => String(value || "").toLowerCase())
            .some((value) => value === "rack" || value.includes("rack"));
    }
    function elementId(root = rootNode()) {
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }
    function equipmentId(node) { return Number(node?.dataset.equipmentNode || node?.dataset.equipmentId || 0); }
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

    function refreshContainer(id = elementId()) {
        state.uplinks.clear();
        return global.mapMasterSuite?.openContainerWorkspace?.(id);
    }

    // ------------------------------------------------------------------
    // Pan/zoom único do Rack. Clique esquerdo move, roda altera apenas zoom.
    // ------------------------------------------------------------------

    function readView(canvas = canvasNode()) {
        if (!canvas) return { scale: 1, tx: 0, ty: 0 };
        const transform = getComputedStyle(canvas).transform;
        if (transform && transform !== "none" && global.DOMMatrixReadOnly) {
            const matrix = new DOMMatrixReadOnly(transform);
            return { scale: matrix.a || 1, tx: matrix.e || 0, ty: matrix.f || 0 };
        }
        return { scale: Number(canvas.dataset.v0741Scale || 1) || 1, tx: 0, ty: 0 };
    }

    function applyView(view, canvas = canvasNode()) {
        if (!canvas) return;
        canvas.style.transformOrigin = "0 0";
        canvas.style.transform = `translate(${view.tx}px, ${view.ty}px) scale(${view.scale})`;
        canvas.dataset.v0741Scale = String(view.scale);
        const output = qs("[data-canvas-zoom-value]", rootNode());
        if (output) output.textContent = `${Math.round(view.scale * 100)}%`;
        document.dispatchEvent(new CustomEvent("map:rack-viewport-changed", { detail: view }));
    }

    function interactivePanTarget(target) {
        if (!(target instanceof Element)) return true;
        return Boolean(target.closest([
            "button", "a", "input", "select", "textarea", "dialog", "[contenteditable='true']",
            ".master-node-port", "[data-port-id]", ".master-cable-node",
            ".master-canvas-node > header", ".v07542-rack-toolbar", ".map-canvas-zoom-v0741",
            ".v07545-service-slot", ".v07547-uplink-slot", ".v07549-uplink-slot",
        ].join(",")));
    }

    function installNavigation() {
        if (global.__mapRackNavigationV07550) return;
        global.__mapRackNavigationV07550 = true;

        global.addEventListener("wheel", (event) => {
            const scroll = event.target instanceof Element ? event.target.closest(".master-canvas-scroll") : null;
            if (!scroll || !isRack()) return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const canvas = canvasNode();
            const before = readView(canvas);
            const scale = clamp(before.scale + (event.deltaY < 0 ? 0.08 : -0.08), 0.20, 2.20);
            const rect = scroll.getBoundingClientRect();
            const cursorX = event.clientX - rect.left;
            const cursorY = event.clientY - rect.top;
            const worldX = (cursorX - before.tx) / before.scale;
            const worldY = (cursorY - before.ty) / before.scale;
            applyView({ scale, tx: cursorX - worldX * scale, ty: cursorY - worldY * scale }, canvas);
        }, { capture: true, passive: false });

        global.addEventListener("pointerdown", (event) => {
            const scroll = event.target instanceof Element ? event.target.closest(".master-canvas-scroll") : null;
            if (!scroll || !isRack()) return;
            if (event.button === 1) {
                // O botão central deixa de ser gesto de navegação.
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                return;
            }
            if (event.button !== 0 || interactivePanTarget(event.target)) return;
            const view = readView(canvasNode());
            state.pan = {
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                tx: view.tx,
                ty: view.ty,
                scale: view.scale,
                moved: false,
                scroll,
            };
            event.stopPropagation();
            event.stopImmediatePropagation();
            scroll.setPointerCapture?.(event.pointerId);
        }, true);

        global.addEventListener("pointermove", (event) => {
            const pan = state.pan;
            if (!pan || event.pointerId !== pan.pointerId) return;
            const dx = event.clientX - pan.startX;
            const dy = event.clientY - pan.startY;
            if (!pan.moved && Math.hypot(dx, dy) < 3) return;
            pan.moved = true;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            pan.scroll.classList.add("v07550-is-panning");
            applyView({ scale: pan.scale, tx: pan.tx + dx, ty: pan.ty + dy });
        }, true);

        const finishPan = (event) => {
            const pan = state.pan;
            if (!pan || event.pointerId !== pan.pointerId) return;
            if (pan.moved) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
            pan.scroll.classList.remove("v07550-is-panning");
            state.pan = null;
        };
        global.addEventListener("pointerup", finishPan, true);
        global.addEventListener("pointercancel", finishPan, true);
        global.addEventListener("auxclick", (event) => {
            if (event.button === 1 && event.target instanceof Element && event.target.closest(".master-canvas-scroll") && isRack()) {
                event.preventDefault();
            }
        }, true);
    }

    // ------------------------------------------------------------------
    // Placas de serviço: clique comum em vazio, botão direito em instalado.
    // O editor permanece aberto depois da instalação e mostra potência por PON.
    // ------------------------------------------------------------------

    function serviceUrl(id, oltId) { return `/api/map/v07548/elements/${id}/olt/${oltId}/editor/`; }
    function chassisUrl(id, oltId) { return `/api/map/v07547/elements/${id}/olt/${oltId}/chassis/`; }
    function uplinkUrl(id, oltId) { return `/api/map/v07549/elements/${id}/olt/${oltId}/uplinks/`; }

    function ensureServiceDialog() {
        if (state.serviceDialog?.isConnected) return state.serviceDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-service-card-v07549";
        dialog.className = "v07549-dialog v07549-service-dialog";
        document.body.appendChild(dialog);
        state.serviceDialog = dialog;
        return dialog;
    }

    async function loadServiceSlot(id, oltId, slotNumber) {
        const data = await request(serviceUrl(id, oltId));
        return { data, slot: data.slots.find((item) => Number(item.slot) === Number(slotNumber)) };
    }

    function servicePowerRows(card) {
        if (!card?.ports?.length) return '<p class="v07549-empty-help">Salve a placa para criar as PONs e informar a potência.</p>';
        return `<section class="v07549-port-power"><header><div><strong>Potência manual por PON</strong><small>Usada quando a OLT não possui coleta SNMP ativa.</small></div></header><div>${card.ports.map((port) => `<label data-power-port="${port.id}"><span>PON ${port.number}${port.linked ? " · ligada" : ""}</span><input type="number" step="0.01" min="-50" max="20" value="${port.tx_power_dbm ?? ""}" placeholder="dBm"><button type="button" data-trace-port="${port.id}">Caminho</button></label>`).join("")}</div></section>`;
    }

    async function renderServiceDialog(id, oltId, slotNumber) {
        const { data, slot } = await loadServiceSlot(id, oltId, slotNumber);
        if (!slot) throw new Error(`Slot S${slotNumber} não encontrado no chassi.`);
        const card = slot.card;
        const dialog = ensureServiceDialog();
        dialog.dataset.elementId = String(id);
        dialog.dataset.oltId = String(oltId);
        dialog.dataset.slot = String(slotNumber);
        dialog.innerHTML = `<form><header><div><small>PLACA DE SERVIÇO · S${slotNumber}</small><h2>${card ? "Editar placa" : "Adicionar placa"}</h2><p>${card ? `${card.ports.length} PON(s) · o editor continuará aberto após salvar` : "O slot está vazio."}</p></div><button type="button" data-close>×</button></header><div class="v07549-dialog-body"><div class="v07549-form-grid"><label>Nome<input name="name" maxlength="100" value="${escapeHtml(card?.name || `Placa ${slotNumber}`)}"></label><label>Modelo<input name="model" maxlength="120" value="${escapeHtml(card?.model || "")}" placeholder="Ex.: GPUF, HSUB"></label><label>Tecnologia<select name="technology"><option value="gpon" ${!card || card.technology === "gpon" ? "selected" : ""}>GPON</option><option value="xgpon" ${card?.technology === "xgpon" ? "selected" : ""}>XG-PON</option><option value="xgspon" ${card?.technology === "xgspon" ? "selected" : ""}>XGS-PON</option></select></label><label>Portas PON<input name="pon_count" type="number" min="1" max="32" value="${card?.ports.length || 16}"></label></div>${servicePowerRows(card)}<p data-status></p></div><footer>${card ? '<button type="button" class="danger" data-remove>Remover placa</button>' : ""}<span></span><button type="button" data-close>Fechar</button><button type="submit" class="primary">${card ? "Salvar placa e potências" : "Instalar placa"}</button></footer></form>`;
        qsa("[data-close]", dialog).forEach((button) => { button.onclick = () => dialog.close(); });
        qsa("[data-trace-port]", dialog).forEach((button) => {
            button.onclick = () => global.mapRackIntegrityV07548?.tracePort?.(id, oltId, Number(button.dataset.tracePort));
        });
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando placa…";
            try {
                const fd = new FormData(form);
                await request(chassisUrl(id, oltId), {
                    method: "POST",
                    body: JSON.stringify({
                        action: "install_card",
                        slot: slotNumber,
                        name: fd.get("name"),
                        model: fd.get("model"),
                        technology: fd.get("technology"),
                        pon_count: Number(fd.get("pon_count") || 0),
                    }),
                });
                const powers = {};
                qsa("[data-power-port]", dialog).forEach((row) => {
                    powers[row.dataset.powerPort] = qs("input", row)?.value || "";
                });
                if (Object.keys(powers).length) {
                    await request(serviceUrl(id, oltId), {
                        method: "PATCH",
                        body: JSON.stringify({ port_tx_power_dbm: powers }),
                    });
                }
                await refreshContainer(id);
                await renderServiceDialog(id, oltId, slotNumber);
                notify(`Placa do slot S${slotNumber} atualizada.`);
            } catch (error) { status.textContent = error.message; }
        };
        qs("[data-remove]", dialog)?.addEventListener("click", async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Removendo placa…";
            try {
                await request(chassisUrl(id, oltId), {
                    method: "POST",
                    body: JSON.stringify({ action: "remove_card", slot: slotNumber }),
                });
                await refreshContainer(id);
                await renderServiceDialog(id, oltId, slotNumber);
            } catch (error) { status.textContent = error.message; }
        });
        if (!dialog.open) dialog.showModal();
    }

    function openServiceFromNode(slotElement) {
        const node = slotElement.closest('.master-canvas-node[data-equipment-type="olt"]');
        const id = elementId();
        const oltId = equipmentId(node);
        const slot = Number(slotElement.dataset.slot || 0);
        if (!id || !oltId || !slot) return;
        renderServiceDialog(id, oltId, slot).catch((error) => notify(error.message, true));
    }

    // ------------------------------------------------------------------
    // Placas de uplink e portas físicas por slot.
    // ------------------------------------------------------------------

    async function loadUplinks(id, oltId, force = false) {
        const key = `${id}:${oltId}`;
        const now = Date.now();
        const cached = state.uplinks.get(key);
        if (!force && cached && now - cached.at < 30000) return cached.data;
        const failed = state.uplinkFailures.get(key);
        if (!force && failed && now < failed.retryAt) return failed.data;
        if (state.pendingUplinks.has(key)) return state.pendingUplinks.get(key);

        const pending = request(uplinkUrl(id, oltId))
            .then((data) => {
                state.uplinks.set(key, { at: Date.now(), data });
                state.uplinkFailures.delete(key);
                return data;
            })
            .catch((error) => {
                const fallback = cached?.data || {
                    uplink_slot_count: 0,
                    uplink_slots: [],
                    load_error: error.message || "Falha ao carregar uplinks.",
                };
                state.uplinkFailures.set(key, {
                    retryAt: Date.now() + 5000,
                    data: fallback,
                    error,
                });
                return fallback;
            })
            .finally(() => state.pendingUplinks.delete(key));
        state.pendingUplinks.set(key, pending);
        return pending;
    }

    function invalidateUplinks(id, oltId) {
        const key = `${id}:${oltId}`;
        state.uplinks.delete(key);
        state.uplinkFailures.delete(key);
    }

    function ensureUplinkDialog() {
        if (state.uplinkDialog?.isConnected) return state.uplinkDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-uplink-card-v07549";
        dialog.className = "v07549-dialog v07549-uplink-dialog";
        document.body.appendChild(dialog);
        state.uplinkDialog = dialog;
        return dialog;
    }

    function portTypeOptions(value) {
        const rows = [
            ["rj45_1g", "RJ45 1G"],
            ["sfp_1g", "SFP 1G"],
            ["sfp_plus_10g", "SFP+ 10G"],
        ];
        return rows.map(([key, label]) => `<option value="${key}" ${key === value ? "selected" : ""}>${label}</option>`).join("");
    }

    function renderUplinkPortFields(dialog, types) {
        const holder = qs("[data-uplink-port-fields]", dialog);
        const quantity = clamp(Number(qs('[name="port_count"]', dialog)?.value || 1), 1, 32);
        const next = Array.from({ length: quantity }, (_, index) => types[index] || "sfp_plus_10g");
        holder.innerHTML = next.map((type, index) => `<label><span>Porta ${index + 1}</span><select data-uplink-port-type>${portTypeOptions(type)}</select></label>`).join("");
    }

    async function renderUplinkDialog(id, oltId, slotNumber) {
        const data = await loadUplinks(id, oltId, true);
        const slot = data.uplink_slots.find((item) => Number(item.slot) === Number(slotNumber));
        if (!slot) throw new Error(`Slot U${slotNumber} não encontrado.`);
        const card = slot.card;
        const currentTypes = card?.ports?.map((port) => port.port_type) || ["sfp_plus_10g"];
        const dialog = ensureUplinkDialog();
        dialog.innerHTML = `<form><header><div><small>PLACA DE UPLINK · U${slotNumber}</small><h2>${card ? "Editar uplink" : "Adicionar uplink"}</h2><p>Defina o modelo e o tipo físico de cada porta.</p></div><button type="button" data-close>×</button></header><div class="v07549-dialog-body"><div class="v07549-form-grid"><label>Modelo da placa<input name="model" maxlength="120" value="${escapeHtml(card?.model || "")}" placeholder="Ex.: HU1A"></label><label>Quantidade de portas<input name="port_count" type="number" min="1" max="32" value="${currentTypes.length}"></label></div><section class="v07549-uplink-port-fields"><header><strong>Tipos das portas</strong><small>RJ45/SFP 1G ficam verdes quando ligados; SFP+ 10G fica azul.</small></header><div data-uplink-port-fields></div></section><p data-status></p></div><footer>${card ? '<button type="button" class="danger" data-remove>Remover placa</button>' : ""}<span></span><button type="button" data-close>Fechar</button><button type="submit" class="primary">Salvar uplink</button></footer></form>`;
        renderUplinkPortFields(dialog, currentTypes);
        qs('[name="port_count"]', dialog).oninput = () => {
            const types = qsa("[data-uplink-port-type]", dialog).map((select) => select.value);
            renderUplinkPortFields(dialog, types);
        };
        qsa("[data-close]", dialog).forEach((button) => { button.onclick = () => dialog.close(); });
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando uplink…";
            try {
                await request(uplinkUrl(id, oltId), {
                    method: "POST",
                    body: JSON.stringify({
                        action: "save_uplink_card",
                        slot: slotNumber,
                        model: qs('[name="model"]', dialog).value,
                        port_types: qsa("[data-uplink-port-type]", dialog).map((select) => select.value),
                    }),
                });
                await refreshContainer(id);
                invalidateUplinks(id, oltId);
                await renderUplinkDialog(id, oltId, slotNumber);
                notify(`Placa de uplink U${slotNumber} atualizada.`);
            } catch (error) { status.textContent = error.message; }
        };
        qs("[data-remove]", dialog)?.addEventListener("click", async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Removendo uplink…";
            try {
                await request(uplinkUrl(id, oltId), {
                    method: "POST",
                    body: JSON.stringify({ action: "remove_uplink_card", slot: slotNumber }),
                });
                await refreshContainer(id);
                invalidateUplinks(id, oltId);
                await renderUplinkDialog(id, oltId, slotNumber);
            } catch (error) { status.textContent = error.message; }
        });
        if (!dialog.open) dialog.showModal();
    }

    function fallbackUplinkPort(port) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "master-node-port v07549-uplink-port";
        button.dataset.portId = String(port.id);
        button.dataset.portType = port.port_type;
        button.dataset.portRole = "front";
        button.innerHTML = `<span>${port.index}</span><i></i>`;
        return button;
    }

    function takeUplinkPort(node, port) {
        const button = qs(`.master-node-port[data-port-id="${port.id}"]`, node) || fallbackUplinkPort(port);
        button.classList.add("v07549-uplink-port", `is-${port.port_type.replaceAll("_", "-")}`);
        button.classList.toggle("is-linked", Boolean(port.linked));
        button.dataset.portRole = "front";
        button.dataset.linkId = port.link_id || "";
        button.title = `${port.port_type_label} · porta ${port.index}${port.linked ? " · ligada" : " · livre"}`;
        const label = qs("span", button);
        if (label) label.textContent = String(port.index);
        return button;
    }

    function renderUplinkBank(node, data) {
        if (!node?.isConnected) return;
        if (data?.load_error) {
            node.dataset.uplinkLoadError = data.load_error;
            const existing = qs(".v07549-uplink-bank", node);
            if (existing) existing.title = `Uplinks temporariamente indisponíveis: ${data.load_error}`;
            return;
        }
        delete node.dataset.uplinkLoadError;
        const signature = JSON.stringify({
            count: data.uplink_slot_count || 0,
            slots: (data.uplink_slots || []).map((slot) => ({
                slot: slot.slot,
                empty: slot.empty,
                model: slot.card?.model || "",
                ports: (slot.card?.ports || []).map((port) => [port.id, port.port_type, Boolean(port.linked)]),
            })),
        });
        if (state.renderedUplinks.get(node) === signature && qs(".v07549-uplink-bank", node)) return;

        qsa(".v07547-uplink-bank, .v07549-uplink-bank", node).forEach((item) => item.remove());
        const face = qs(".v07545-olt-face", node);
        const serviceSlots = qs(".v07545-chassis-slots", face);
        if (!face || !serviceSlots || !data.uplink_slot_count) {
            state.renderedUplinks.set(node, signature);
            return;
        }
        const bank = document.createElement("section");
        bank.className = "v07549-uplink-bank";
        bank.dataset.generatedBy = "v07550";
        bank.innerHTML = `<header><div><strong>SLOTS DE UPLINK</strong><small>Clique no slot vazio; botão direito edita uma placa instalada.</small></div><span>${data.uplink_slot_count} slot(s)</span></header><div class="v07549-uplink-slots"></div>`;
        const holder = qs(".v07549-uplink-slots", bank);
        (data.uplink_slots || []).forEach((slot) => {
            const cell = document.createElement("article");
            cell.className = `v07549-uplink-slot ${slot.empty ? "is-empty" : "is-installed"}`;
            cell.dataset.uplinkSlot = String(slot.slot);
            if (slot.empty) {
                cell.innerHTML = `<strong>U${slot.slot}</strong><span>Slot de uplink vazio</span><small>Clique para adicionar</small>`;
            } else {
                cell.innerHTML = `<header><div><strong>U${slot.slot} · ${escapeHtml(slot.card.model)}</strong><small>${slot.card.ports.length} porta(s)</small></div></header><div class="v07549-uplink-ports"></div>`;
                const ports = qs(".v07549-uplink-ports", cell);
                slot.card.ports.forEach((port) => ports.appendChild(takeUplinkPort(node, port)));
            }
            holder.appendChild(cell);
        });
        face.insertBefore(bank, serviceSlots);
        state.renderedUplinks.set(node, signature);
    }

    async function enhanceOlt(node, generation) {
        const id = elementId();
        const oltId = equipmentId(node);
        if (!id || !oltId) return;
        const data = await loadUplinks(id, oltId, false);
        if (generation !== state.generation || !node.isConnected) return;
        renderUplinkBank(node, data);
    }

    // ------------------------------------------------------------------
    // DIO: frente pela cor do conector, traseira vermelha/laranja e pontos separados.
    // ------------------------------------------------------------------

    async function enhanceDio(node, generation) {
        const id = elementId();
        const dioId = equipmentId(node);
        if (!id || !dioId) return;
        if (node.dataset.dioEnhancedV07550 === "1") return;
        const data = await request(`/api/map/v07539/elements/${id}/dio/${dioId}/dual-face/`);
        if (generation !== state.generation || !node.isConnected) return;
        const connector = data.dio.connector_type === "sc_upc" ? "sc-upc" : "sc-apc";
        node.dataset.connectorV07549 = connector;
        data.ports.forEach((row) => {
            const pair = qs(`[data-port-pair="${row.id}"]`, node);
            const front = qs(`[data-port-id="${row.id}"][data-port-role="front"]`, node);
            const rear = qs(`[data-port-id="${row.id}"][data-port-role="rear"]`, node);
            pair?.classList.toggle("has-front-v07549", Boolean(row.front));
            pair?.classList.toggle("has-rear-v07549", Boolean(row.rear));
            pair?.classList.toggle("rear-free-v07549", !row.rear);
            front?.classList.add("v07549-dio-front", `is-${connector}`);
            rear?.classList.add("v07549-dio-rear");
            front?.setAttribute("title", `${row.label} · frente ${data.dio.connector_type_label || "SC/APC"}${row.front ? " · ligada" : " · livre"}`);
            rear?.setAttribute("title", `${row.label} · traseira${row.rear ? ` · ${row.rear.cable || "fundida"}` : " · sem fusão"}`);
        });
        node.dataset.dioEnhancedV07550 = "1";
    }

    // ------------------------------------------------------------------
    // Rack físico: realinha vazio e evita sobreposição após render assíncrono.
    // ------------------------------------------------------------------

    function syncEmptyAppearance() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        root.classList.toggle("v07549-empty-aligned", root.classList.contains("v07548-rack-empty"));
        const backdrop = qs(".tower-structure-backdrop-v0750", root);
        backdrop?.classList.add("rack", "v07549-rack-backdrop");
    }

    function overlapPairs(nodes) {
        const pairs = [];
        for (let index = 0; index < nodes.length; index += 1) {
            const first = nodes[index].getBoundingClientRect();
            for (let secondIndex = index + 1; secondIndex < nodes.length; secondIndex += 1) {
                const second = nodes[secondIndex].getBoundingClientRect();
                const overlaps = first.left < second.right - 4 && first.right > second.left + 4
                    && first.top < second.bottom - 4 && first.bottom > second.top + 4;
                if (overlaps) pairs.push([nodes[index], nodes[secondIndex]]);
            }
        }
        return pairs;
    }

    function ensurePhysicalFlow() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        const nodes = qsa(".master-canvas-node[data-equipment-node]", root)
            .filter((node) => !node.hidden && getComputedStyle(node).display !== "none");
        const pairs = overlapPairs(nodes);
        if (!pairs.length) {
            state.lastAutoKey = "";
            return;
        }
        const key = pairs.map(([a, b]) => `${equipmentId(a)}:${equipmentId(b)}`).sort().join("|");
        const now = Date.now();
        if (key && (key !== state.lastAutoKey || now - state.lastAutoAt > 2500)) {
            state.lastAutoKey = key;
            state.lastAutoAt = now;
            global.mapRackPhysicalV07542?.autoOrganize?.();
        }
    }

    function installResizeObserver() {
        if (state.resizeObserver) return;
        state.resizeObserver = new ResizeObserver(() => {
            global.clearTimeout(state.physicalTimer);
            state.physicalTimer = global.setTimeout(ensurePhysicalFlow, 180);
        });
    }

    function observeEquipment() {
        installResizeObserver();
        qsa(".master-canvas-node[data-equipment-node]", rootNode()).forEach((node) => {
            if (node.dataset.resizeObservedV07549 === "1") return;
            node.dataset.resizeObservedV07549 = "1";
            state.resizeObserver.observe(node);
        });
    }

    // ------------------------------------------------------------------
    // Eventos e ciclo de render.
    // ------------------------------------------------------------------

    function installSlotEvents() {
        global.addEventListener("click", (event) => {
            const target = event.target instanceof Element ? event.target : null;
            if (!target || !isRack()) return;
            const emptyService = target.closest(".v07545-service-slot.is-empty");
            if (emptyService) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                openServiceFromNode(emptyService);
                return;
            }
            const emptyUplink = target.closest(".v07549-uplink-slot.is-empty");
            if (emptyUplink) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                const node = emptyUplink.closest('.master-canvas-node[data-equipment-type="olt"]');
                renderUplinkDialog(elementId(), equipmentId(node), Number(emptyUplink.dataset.uplinkSlot)).catch((error) => notify(error.message, true));
            }
        }, true);

        global.addEventListener("contextmenu", (event) => {
            const target = event.target instanceof Element ? event.target : null;
            if (!target || !isRack()) return;
            const service = target.closest(".v07545-service-slot");
            if (service) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                openServiceFromNode(service);
                return;
            }
            const uplink = target.closest(".v07549-uplink-slot");
            if (uplink) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                const node = uplink.closest('.master-canvas-node[data-equipment-type="olt"]');
                renderUplinkDialog(elementId(), equipmentId(node), Number(uplink.dataset.uplinkSlot)).catch((error) => notify(error.message, true));
            }
        }, true);
    }

    async function enhance() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        if (state.enhancing) {
            state.rerun = true;
            return;
        }
        state.enhancing = true;
        const generation = ++state.generation;
        try {
            syncEmptyAppearance();
            observeEquipment();
            const oltNodes = qsa('.master-canvas-node[data-equipment-type="olt"]', root);
            const dioNodes = qsa('.master-canvas-node[data-equipment-type="dio"]', root);
            await Promise.all([
                ...oltNodes.map((node) => enhanceOlt(node, generation)),
                ...dioNodes.map((node) => enhanceDio(node, generation)),
            ]);
            global.clearTimeout(state.physicalTimer);
            state.physicalTimer = global.setTimeout(ensurePhysicalFlow, 180);
        } finally {
            state.enhancing = false;
            if (state.rerun) {
                state.rerun = false;
                scheduleEnhance(120);
            }
        }
    }

    function scheduleEnhance(delay = 40) {
        global.clearTimeout(state.enhanceTimer);
        state.enhanceTimer = global.setTimeout(() => {
            state.enhanceTimer = 0;
            enhance().catch((error) => console.error("MAP v0.75.50:", error));
        }, delay);
    }

    function touchesEquipment(node) {
        if (!(node instanceof Element)) return false;
        if (node.dataset.generatedBy === "v07550") return false;
        return node.matches?.("#map-master-container, .master-canvas-node[data-equipment-node]")
            || Boolean(node.querySelector?.(".master-canvas-node[data-equipment-node]"));
    }

    function installObserver() {
        if (state.observer) return;
        state.observer = new MutationObserver((records) => {
            const relevant = records.some((record) =>
                [...record.addedNodes, ...record.removedNodes].some(touchesEquipment)
            );
            if (relevant) scheduleEnhance(80);
        });
        state.observer.observe(document.body, { childList: true, subtree: true });
    }

    function init() {
        installNavigation();
        installSlotEvents();
        installObserver();
        document.addEventListener("map:container-rendered", scheduleEnhance);
        document.addEventListener("map:container-opening", scheduleEnhance);
        global.addEventListener("resize", () => scheduleEnhance(120));
        scheduleEnhance(0);
    }

    global.mapRackMaintenanceV07550 = Object.freeze({
        version: VERSION,
        refresh: () => scheduleEnhance(0),
        invalidateUplinks,
        openServiceCard: renderServiceDialog,
        openUplinkCard: renderUplinkDialog,
    });

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})(window);
