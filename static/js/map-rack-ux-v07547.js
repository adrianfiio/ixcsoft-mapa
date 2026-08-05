(function (global) {
    "use strict";

    const VERSION = "0.75.47";
    const state = {
        gesture: null,
        observer: null,
        hardware: new Map(),
        generation: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];
    const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

    function rootNode() {
        return qs("#map-master-container");
    }

    function scrollNode(root = rootNode()) {
        return qs(".master-canvas-scroll", root);
    }

    function canvasNode(root = rootNode()) {
        return qs(".master-canvas", root);
    }

    function currentElementId(root = rootNode()) {
        const dialog = qs("#container-dialog");
        return Number(
            root?.dataset.elementId
            || dialog?.dataset.elementId
            || dialog?.dataset.containerId
            || 0,
        );
    }

    function equipmentId(node) {
        return Number(node?.dataset.equipmentNode || node?.dataset.equipmentId || 0);
    }

    function isRack(root = rootNode()) {
        if (!root) return false;
        if (root.classList.contains("v07542-physical-rack")) return true;
        const dialog = qs("#container-dialog");
        const values = [
            root.dataset.elementType,
            root.dataset.containerType,
            dialog?.dataset.elementType,
            dialog?.dataset.containerType,
            dialog?.dataset.kind,
        ].map((value) => String(value || "").toLowerCase());
        return values.some((value) => value === "rack" || value.includes("rack"));
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

    function readView(canvas = canvasNode()) {
        if (!canvas) return { scale: 1, tx: 0, ty: 0 };
        const transform = getComputedStyle(canvas).transform;
        if (transform && transform !== "none" && global.DOMMatrixReadOnly) {
            const matrix = new global.DOMMatrixReadOnly(transform);
            return {
                scale: Number.isFinite(matrix.a) && matrix.a > 0 ? matrix.a : 1,
                tx: Number.isFinite(matrix.e) ? matrix.e : 0,
                ty: Number.isFinite(matrix.f) ? matrix.f : 0,
            };
        }
        return {
            scale: Number(canvas.dataset.v0741Scale || 1) || 1,
            tx: Number(canvas.dataset.v07547Tx || canvas.dataset.v07546Tx || 0) || 0,
            ty: Number(canvas.dataset.v07547Ty || canvas.dataset.v07546Ty || 0) || 0,
        };
    }

    function applyView(root, view) {
        const canvas = canvasNode(root);
        if (!canvas) return;
        const normalized = {
            scale: clamp(Number(view.scale) || 1, 0.18, 2.4),
            tx: Number(view.tx) || 0,
            ty: Number(view.ty) || 0,
        };
        canvas.style.transformOrigin = "0 0";
        canvas.style.transform = `translate(${normalized.tx}px, ${normalized.ty}px) scale(${normalized.scale})`;
        canvas.style.willChange = "transform";
        canvas.dataset.v0741Scale = String(normalized.scale);
        canvas.dataset.v07546Tx = String(normalized.tx);
        canvas.dataset.v07546Ty = String(normalized.ty);
        canvas.dataset.v07547Tx = String(normalized.tx);
        canvas.dataset.v07547Ty = String(normalized.ty);
        const output = qs("[data-canvas-zoom-value]", root);
        if (output) output.textContent = `${Math.round(normalized.scale * 100)}%`;
        root.dispatchEvent(new CustomEvent("map:rack-viewport-changed", { detail: normalized }));
    }

    function zoomAround(root, event) {
        const scroll = scrollNode(root);
        const canvas = canvasNode(root);
        if (!scroll || !canvas) return;
        const before = readView(canvas);
        const scale = clamp(before.scale + (event.deltaY < 0 ? 0.1 : -0.1), 0.18, 2.4);
        const rect = scroll.getBoundingClientRect();
        const cursorX = event.clientX - rect.left;
        const cursorY = event.clientY - rect.top;
        const worldX = (cursorX - before.tx) / before.scale;
        const worldY = (cursorY - before.ty) / before.scale;
        applyView(root, {
            scale,
            tx: cursorX - worldX * scale,
            ty: cursorY - worldY * scale,
        });
    }

    function interactiveTarget(target) {
        if (!(target instanceof Element)) return true;
        return Boolean(target.closest([
            "button",
            "a",
            "input",
            "select",
            "textarea",
            "dialog",
            "[contenteditable='true']",
            "[data-port-id]",
            ".master-node-port",
            "[data-rack-cable-anchor-v07538]",
            ".map-canvas-zoom-v0741",
            ".v07542-rack-toolbar",
            ".master-container-commandbar-v0741",
            ".v07542-rack-mounted > header",
            ".v07545-service-slot.is-empty",
        ].join(",")));
    }

    function beginPan(event) {
        const root = rootNode();
        const scroll = scrollNode(root);
        if (!root || !scroll || !isRack(root) || !scroll.contains(event.target)) return;
        if (![0, 1].includes(event.button)) return;
        if (interactiveTarget(event.target)) return;

        const view = readView(canvasNode(root));
        state.gesture = {
            root,
            scroll,
            pointerId: event.pointerId,
            button: event.button,
            startX: event.clientX,
            startY: event.clientY,
            tx: view.tx,
            ty: view.ty,
            scale: view.scale,
            active: event.button === 1,
        };

        // Bloqueia os controladores antigos antes que alcancem o scroll.
        event.stopPropagation();
        event.stopImmediatePropagation();
        scroll.setPointerCapture?.(event.pointerId);
        if (state.gesture.active) {
            event.preventDefault();
            scroll.classList.add("is-panning-v07547");
        }
    }

    function movePan(event) {
        const gesture = state.gesture;
        if (!gesture || event.pointerId !== gesture.pointerId) return;
        const dx = event.clientX - gesture.startX;
        const dy = event.clientY - gesture.startY;
        if (!gesture.active && Math.hypot(dx, dy) < 3) return;
        if (!gesture.active) {
            gesture.active = true;
            gesture.scroll.classList.add("is-panning-v07547");
        }
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        applyView(gesture.root, {
            scale: gesture.scale,
            tx: gesture.tx + dx,
            ty: gesture.ty + dy,
        });
    }

    function finishPan(event) {
        const gesture = state.gesture;
        if (!gesture || (event?.pointerId != null && event.pointerId !== gesture.pointerId)) return;
        if (gesture.active) {
            event?.preventDefault?.();
            event?.stopPropagation?.();
        }
        gesture.scroll.classList.remove("is-panning-v07547");
        gesture.scroll.releasePointerCapture?.(gesture.pointerId);
        state.gesture = null;
    }

    function interceptWheel(event) {
        const root = rootNode();
        const scroll = scrollNode(root);
        if (!root || !scroll || !isRack(root) || !scroll.contains(event.target)) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        zoomAround(root, event);
    }

    function oltFieldsHtml() {
        return `<div class="v07547-equipment-grid">
            <label>Nome<input name="name" required maxlength="120"></label>
            <label>Fabricante<input name="vendor" maxlength="100"></label>
            <label>Modelo do chassi<input name="model" maxlength="120" placeholder="Ex.: AN5516-06"></label>
            <label>IP de gerência<input name="management_ip" placeholder="192.168.0.10"></label>
            <label>Disposição das placas<select name="chassis_orientation"><option value="vertical">Placas verticais · lado a lado</option><option value="horizontal">Placas horizontais · uma sobre a outra</option></select></label>
            <label>Slots de placas de serviço<input name="service_slot_count" type="number" min="1" max="32" value="4"></label>
            <label>Slots de uplink<input name="uplink_slot_count" type="number" min="0" max="16" value="0"></label>
        </div><p class="v07547-form-hint">Os slots nascem vazios. As portas PON são definidas somente quando uma placa de serviço for instalada.</p>`;
    }

    function patchRackEquipmentDialog() {
        const dialog = qs("#map-rack-equipment-v07542");
        const form = qs("[data-rack-equipment-form-v07542]", dialog);
        if (!dialog || !form) return;
        const type = qs("[data-type-v07542]", form);
        const fields = qs("[data-fields-v07542]", form);
        if (!type || !fields) return;

        // A lista física do Rack não aceita PTO nem o genérico Outro.
        qsa('option[value="pto"], option[value="other"]', type).forEach((option) => option.remove());
        if (type.value === "olt") {
            if (fields.dataset.v07547OltFields !== "1") {
                fields.dataset.v07547OltFields = "1";
                fields.innerHTML = oltFieldsHtml();
            }
        } else {
            delete fields.dataset.v07547OltFields;
        }
    }

    async function submitOlt(event, form) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const status = qs("[data-status-v07542]", form);
        if (status) {
            status.textContent = "Criando chassi da OLT…";
            status.classList.remove("error");
        }
        const elementId = currentElementId();
        if (!elementId) {
            if (status) status.textContent = "Rack não identificado.";
            return;
        }
        const payload = Object.fromEntries(new FormData(form));
        payload.equipment_type = "olt";
        payload.enabled = true;
        payload.provisioning_mode = "manual";
        payload.chassis_model = payload.model || "";
        payload.service_slot_count = Number(payload.service_slot_count || 0);
        payload.uplink_slot_count = Number(payload.uplink_slot_count || 0);
        try {
            await request(`/api/map/v07547/elements/${elementId}/equipment/`, {
                method: "POST",
                body: JSON.stringify(payload),
            });
            form.closest("dialog")?.close();
            notify("OLT criada com slots vazios de serviço e uplink.");
            await global.mapMasterSuite?.openContainerWorkspace?.(elementId);
            scheduleEnhance();
        } catch (error) {
            if (status) {
                status.textContent = error.message;
                status.classList.add("error");
            } else notify(error.message, true);
        }
    }

    function interceptRackDialogSubmit(event) {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.matches("[data-rack-equipment-form-v07542]")) return;
        const type = qs("[data-type-v07542]", form)?.value;
        if (type !== "olt") return;
        submitOlt(event, form);
    }

    function hideRackPaletteItems() {
        if (!isRack()) return;
        const scope = qs("#container-dialog") || rootNode() || document;
        qsa("button, a, [role='menuitem']", scope).forEach((item) => {
            const text = item.textContent.replace(/\s+/g, " ").trim();
            if (/^(PTO|Outro)(?:\s|$)/i.test(text)) {
                item.hidden = true;
                item.dataset.hiddenRackV07547 = "1";
            }
        });
    }

    function hardwareUrl(elementId, oltId) {
        return `/api/map/v07547/elements/${Number(elementId)}/olt/${Number(oltId)}/chassis/`;
    }

    async function loadHardware(elementId, oltId, force = false) {
        const key = `${elementId}:${oltId}`;
        if (!force && state.hardware.has(key)) return state.hardware.get(key);
        const data = await request(hardwareUrl(elementId, oltId));
        state.hardware.set(key, data);
        return data;
    }

    function decoratePonPorts(node) {
        qsa(".v07545-pon-grid .master-node-port[data-port-id]", node).forEach((port) => {
            port.classList.add("v07547-pon-port");
            const label = qs("span", port);
            if (label) {
                label.classList.add("v07547-pon-number");
                label.textContent = String(Number(label.textContent) || label.textContent.trim());
            }
            const point = qs("i", port);
            point?.classList.add("v07547-pon-point");
        });
    }

    function renderUplinkSlots(node, hardware) {
        qs(".v07547-uplink-bank", node)?.remove();
        const face = qs(".v07545-olt-face", node);
        if (!face) return;
        const count = Number(hardware?.chassis?.uplink_slot_count || 0);
        const serviceCount = Number(hardware?.chassis?.service_slot_count || hardware?.chassis?.slot_count || 0);
        const headerBadge = qs(":scope > header > span", face);
        if (headerBadge) headerBadge.textContent = `${serviceCount} serviço · ${count} uplink`;
        if (!count) return;

        const bank = document.createElement("section");
        bank.className = "v07547-uplink-bank";
        bank.innerHTML = `<header><div><strong>SLOTS DE UPLINK</strong><small>Reservados no chassi. As placas de uplink serão implementadas depois.</small></div><span>${count} slot(s)</span></header><div class="v07547-uplink-slots"></div>`;
        const slots = qs(".v07547-uplink-slots", bank);
        hardware.uplink_slots.forEach((slot) => {
            const cell = document.createElement("div");
            cell.className = "v07547-uplink-slot is-empty";
            cell.innerHTML = `<strong>U${slot.slot}</strong><span>Slot de uplink vazio</span>`;
            slots.appendChild(cell);
        });
        face.appendChild(bank);
    }

    async function enhanceOltNode(node, generation) {
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        if (!elementId || !oltId) return;
        const hardware = await loadHardware(elementId, oltId, true);
        if (generation !== state.generation || !node.isConnected) return;
        decoratePonPorts(node);
        renderUplinkSlots(node, hardware);
    }

    async function enhance() {
        const root = rootNode();
        if (!root || !isRack(root)) return;
        const generation = ++state.generation;
        patchRackEquipmentDialog();
        hideRackPaletteItems();
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="olt"]', root).map((node) => (
            enhanceOltNode(node, generation).catch((error) => {
                node.dataset.v07547Error = error.message;
                console.error("MAP v0.75.47 OLT:", error);
            })
        )));
    }

    function scheduleEnhance() {
        global.requestAnimationFrame(() => enhance().catch((error) => console.error("MAP v0.75.47:", error)));
        global.setTimeout(() => enhance().catch(() => {}), 160);
        global.setTimeout(() => enhance().catch(() => {}), 520);
    }

    function installObserver() {
        if (state.observer) return;
        state.observer = new MutationObserver(() => {
            patchRackEquipmentDialog();
            hideRackPaletteItems();
        });
        state.observer.observe(document.body, { childList: true, subtree: true });
    }

    function init() {
        installObserver();
        document.addEventListener("wheel", interceptWheel, { capture: true, passive: false });
        document.addEventListener("pointerdown", beginPan, true);
        document.addEventListener("pointermove", movePan, true);
        document.addEventListener("pointerup", finishPan, true);
        document.addEventListener("pointercancel", finishPan, true);
        document.addEventListener("submit", interceptRackDialogSubmit, true);
        document.addEventListener("change", (event) => {
            if (event.target?.matches?.("[data-type-v07542]")) global.queueMicrotask(patchRackEquipmentDialog);
        }, true);
        document.addEventListener("click", () => global.setTimeout(() => {
            patchRackEquipmentDialog();
            hideRackPaletteItems();
        }, 0), true);
        document.addEventListener("map:container-opening", scheduleEnhance);
        document.addEventListener("map:container-rendered", scheduleEnhance);
        global.addEventListener("blur", () => finishPan(null));
        scheduleEnhance();
    }

    global.mapRackUxV07547 = Object.freeze({
        version: VERSION,
        refresh: scheduleEnhance,
        getView: () => readView(canvasNode()),
    });

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})(window);
