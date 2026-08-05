(function (global) {
    "use strict";

    const VERSION = "0.75.45";
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
        dialog.id = "map-rack-chassis-v07545";
        dialog.className = "v07545-dialog";
        dialog.innerHTML = '<form><header><div><small data-kicker>CHASSI DA OLT</small><h2 data-title></h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div data-body></div></form>';
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
        state.dialog = dialog;
        return dialog;
    }

    function showDialog({ title, subtitle = "", kicker = "CHASSI DA OLT", body = "" }) {
        const dialog = ensureDialog();
        qs("[data-title]", dialog).textContent = title;
        qs("[data-subtitle]", dialog).textContent = subtitle;
        qs("[data-kicker]", dialog).textContent = kicker;
        qs("[data-body]", dialog).innerHTML = body;
        if (!dialog.open) dialog.showModal();
        return dialog;
    }

    function chassisUrl(elementId, oltId) {
        return `/api/map/v07545/elements/${Number(elementId)}/olt/${Number(oltId)}/chassis/`;
    }

    async function loadHardware(elementId, oltId, force = false) {
        const key = `${elementId}:${oltId}`;
        if (!force && state.hardware.has(key)) return state.hardware.get(key);
        const data = await request(chassisUrl(elementId, oltId));
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

    function setLegacyCreateFields(form, hidden) {
        ["card_count", "pons_per_card", "model"].forEach((name) => {
            const field = qs(`[name="${name}"]`, form);
            const wrapper = field?.closest("label, .field, .form-field, [data-field]");
            if (wrapper) wrapper.hidden = hidden;
            if (hidden && field && name !== "model") field.value = "0";
        });
        if (hidden) qsa("[data-v07544-olt-create], [data-v07543-olt-create]", form).forEach((node) => node.remove());
    }

    function enhanceCreateForm() {
        const dialog = qs("#map-v07539-modal");
        const form = qs("form[data-create-equipment]", dialog);
        if (!form) return;
        const type = qs("[data-create-type]", form)?.value;
        const old = qs("[data-v07545-olt-create]", form);
        if (type !== "olt") {
            old?.remove();
            setLegacyCreateFields(form, false);
            return;
        }
        setLegacyCreateFields(form, true);
        if (old) return;
        const config = document.createElement("section");
        config.dataset.v07545OltCreate = "1";
        config.className = "v07545-olt-create";
        config.innerHTML = `
            <header><div><strong>MODELO FÍSICO DO CHASSI</strong><small>Os slots nascem vazios. Instale cada placa depois pelo próprio slot.</small></div></header>
            <div class="v07545-create-grid">
                <label>Modelo do chassi<input data-chassis-model maxlength="120" placeholder="Ex.: AN5516-06"></label>
                <label>Disposição das placas<select data-chassis-orientation><option value="vertical">Placas verticais · lado a lado</option><option value="horizontal">Placas horizontais · uma sobre a outra</option></select></label>
                <label>Slots de serviço<input data-service-slot-count type="number" min="1" max="16" value="4"></label>
            </div>`;
        const fields = qs("[data-create-fields]", form);
        (fields || form).appendChild(config);
    }

    function installCreateObserver() {
        const dialog = qs("#map-v07539-modal");
        if (!dialog || dialog.dataset.v07545Observed === "1") return;
        dialog.dataset.v07545Observed = "1";
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
        payload.chassis_model = qs("[data-chassis-model]", form)?.value.trim() || payload.model || "";
        payload.model = payload.chassis_model;
        payload.chassis_orientation = qs("[data-chassis-orientation]", form)?.value || "vertical";
        payload.service_slot_count = Number(qs("[data-service-slot-count]", form)?.value || 0);
        await request(`/api/map/v07545/elements/${elementId}/equipment/`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        form.closest("dialog")?.close();
        await refreshContainer(elementId);
        notify("OLT criada com slots vazios. Agora instale as placas nos slots desejados.");
    }

    function installCreationInterception() {
        document.addEventListener("click", (event) => {
            if (!(event.target instanceof Element)) return;
            if (event.target.closest("[data-container-add], [data-add-equipment], button")) {
                global.setTimeout(installCreateObserver, 0);
                global.setTimeout(enhanceCreateForm, 40);
            }
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
            if (status) status.textContent = "Criando chassi…";
            submitOltCreation(form).catch((error) => {
                if (status) {
                    status.textContent = error.message;
                    status.classList.add("error");
                } else notify(error.message, true);
            });
        }, true);
    }

    function openSlotEditor(node, slotRow) {
        if (!canEdit()) return;
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        const card = slotRow.card;
        const dialog = showDialog({
            title: card ? `Editar placa do slot S${slotRow.slot}` : `Adicionar placa no slot S${slotRow.slot}`,
            subtitle: card ? `${card.ports.length} porta(s) PON instaladas` : "O slot está vazio.",
            kicker: "PLACA DE SERVIÇO",
            body: `<div class="v07545-form-grid">
                <label>Nome<input name="name" value="${escapeHtml(card?.name || `Placa ${slotRow.slot}`)}" maxlength="100"></label>
                <label>Modelo da placa<input name="model" value="${escapeHtml(card?.model || "")}" maxlength="120" placeholder="Ex.: HSUB, GPUF, XGHD"></label>
                <label>Tecnologia<select name="technology"><option value="gpon" ${!card || card.technology === "gpon" ? "selected" : ""}>GPON</option><option value="xgpon" ${card?.technology === "xgpon" ? "selected" : ""}>XG-PON</option><option value="xgspon" ${card?.technology === "xgspon" ? "selected" : ""}>XGS-PON</option></select></label>
                <label>Portas PON<input name="pon_count" type="number" min="1" max="32" value="${Number(card?.ports.length || 16)}"></label>
            </div><p data-status></p><footer>${card ? '<button type="button" class="danger" data-remove>Remover placa</button>' : ""}<span></span><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>${card ? "Salvar placa" : "Instalar placa"}</button></footer>`,
        });
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("[data-save]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando…";
            status.classList.remove("error");
            try {
                await request(chassisUrl(elementId, oltId), {
                    method: "POST",
                    body: JSON.stringify({
                        action: "install_card",
                        slot: slotRow.slot,
                        name: qs('[name="name"]', dialog).value,
                        model: qs('[name="model"]', dialog).value,
                        technology: qs('[name="technology"]', dialog).value,
                        pon_count: Number(qs('[name="pon_count"]', dialog).value || 0),
                    }),
                });
                dialog.close();
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
        qs("[data-remove]", dialog)?.addEventListener("click", async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Removendo…";
            status.classList.remove("error");
            try {
                await request(chassisUrl(elementId, oltId), {
                    method: "POST",
                    body: JSON.stringify({ action: "remove_card", slot: slotRow.slot }),
                });
                dialog.close();
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        });
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
        button.className = "master-node-port v07545-fallback-port";
        button.dataset.portId = String(port.id);
        button.dataset.portType = port.port_type;
        button.dataset.portRole = "front";
        button.dataset.linkId = port.link_id || "";
        button.innerHTML = `<i></i><span>${port.number}</span>`;
        return button;
    }

    function takePort(portMap, port) {
        const button = portMap.get(Number(port.id)) || fallbackPort(port);
        button.classList.add("v07545-hardware-port");
        button.dataset.linkId = port.link_id || "";
        button.dataset.portRole = "front";
        button.title = `${port.label} · ${port.port_type_label}`;
        const span = qs("span", button);
        if (span) span.textContent = String(port.number);
        portMap.delete(Number(port.id));
        return button;
    }

    function cleanupLegacyOlt(node) {
        qsa(":scope > .v07543-olt-bottom-grid, :scope > .v07543-olt-organizer, :scope > .v07544-olt-face, :scope > .v07545-olt-face", node).forEach((item) => item.remove());
        qsa(".v07543-card-profile", node).forEach((item) => item.remove());
    }

    function bindSlotActions(node, slotElement, slotRow) {
        const open = (event) => {
            if (event.target.closest(".master-node-port, button, a, input, select")) return;
            event.preventDefault();
            event.stopPropagation();
            openSlotEditor(node, slotRow);
        };
        slotElement.addEventListener("dblclick", open);
        slotElement.addEventListener("contextmenu", open);
    }

    function renderInstalledSlot(node, slotRow, portMap, orientation) {
        const card = slotRow.card;
        const section = document.createElement("section");
        section.className = `v07545-service-slot is-installed is-${orientation}`;
        section.dataset.slot = String(slotRow.slot);
        section.dataset.cardId = String(card.id);
        section.innerHTML = `<header><div><strong>S${slotRow.slot} · ${escapeHtml(card.name)}</strong><small>${technologyLabel(card.technology)}${card.model ? ` · ${escapeHtml(card.model)}` : ""}</small></div><span>${card.ports.length} PON</span></header><div class="v07545-pon-grid"></div>`;
        const grid = qs(".v07545-pon-grid", section);
        card.ports.forEach((port) => grid.appendChild(takePort(portMap, port)));
        bindSlotActions(node, section, slotRow);
        return section;
    }

    function renderEmptySlot(node, slotRow, orientation) {
        const section = document.createElement("section");
        section.className = `v07545-service-slot is-empty is-${orientation}`;
        section.dataset.slot = String(slotRow.slot);
        section.innerHTML = `<div><strong>S${slotRow.slot}</strong><span>Slot vazio</span><small>Duplo clique ou botão direito para adicionar placa</small></div>`;
        bindSlotActions(node, section, slotRow);
        return section;
    }

    function renderOltFace(node, hardware) {
        const portMap = collectOriginalPorts(node);
        cleanupLegacyOlt(node);
        qsa(".master-olt-slot-v07510, .master-node-ports", node).forEach((legacy) => legacy.classList.add("v07545-legacy-hidden"));
        const orientation = hardware.chassis.orientation === "vertical" ? "vertical" : "horizontal";
        const face = document.createElement("section");
        face.className = `v07545-olt-face is-${orientation}`;
        face.innerHTML = `<header><div><strong>${escapeHtml(hardware.chassis.chassis_model || hardware.equipment.model || "Chassi OLT")}</strong><small>${orientation === "vertical" ? "Placas verticais · lado a lado" : "Placas horizontais · uma sobre a outra"}</small></div><span>${hardware.chassis.slot_count} slot(s) de serviço</span></header><div class="v07545-chassis-slots"></div>`;
        const slots = qs(".v07545-chassis-slots", face);
        slots.style.setProperty("--v07545-slot-count", String(hardware.chassis.slot_count));
        hardware.slots.forEach((slotRow) => {
            const slot = slotRow.empty
                ? renderEmptySlot(node, slotRow, orientation)
                : renderInstalledSlot(node, slotRow, portMap, orientation);
            slots.appendChild(slot);
            const organizer = document.createElement("div");
            organizer.className = "v07545-slot-organizer";
            organizer.dataset.v07545SlotOrganizer = String(slotRow.slot);
            organizer.innerHTML = `<i></i><span>ORGANIZADOR · S${slotRow.slot}</span><i></i>`;
            slots.appendChild(organizer);
        });
        node.appendChild(face);
        node.classList.add("v07545-olt-chassis");
        node.dataset.v07545Orientation = orientation;
        node.dataset.v07545SlotCount = String(hardware.chassis.slot_count);
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
        qsa(".v07542-dio-organizer, .v07543-dio-organizer, .v07544-dio-organizer, .v07545-dio-organizer", node).forEach((item) => item.remove());
        qsa(".v07539-dio-cavity", node).forEach((cavity, index) => {
            const organizer = document.createElement("div");
            organizer.className = "v07545-dio-organizer";
            organizer.dataset.cavityIndexV07545 = String(index);
            organizer.innerHTML = `<i></i><span>ORGANIZADOR ÓPTICO · CAVIDADE ${index + 1}</span><i></i>`;
            cavity.after(organizer);
        });
        node.classList.add("v07545-dio-routing");
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

    function panAllowed(target, button) {
        if (!(target instanceof Element)) return false;
        if (button === 1) return !target.closest("input, select, textarea, dialog");
        return !target.closest(".master-canvas-node, .master-cable-node, button, a, input, select, textarea, dialog, .map-canvas-zoom-v0741, .v07542-rack-toolbar, .master-container-commandbar-v0741");
    }

    function installNavigation(scroll) {
        if (!scroll || scroll.dataset.navigationV07545 === "1") return;
        scroll.dataset.navigationV07545 = "1";
        scroll.classList.add("v07545-navigation-enabled");
        scroll.addEventListener("wheel", (event) => {
            if (currentKind() !== "rack") return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const before = readView();
            const scale = clamp(before.scale + (event.deltaY < 0 ? 0.08 : -0.08), 0.22, 1.8);
            const rect = scroll.getBoundingClientRect();
            const cursorX = event.clientX - rect.left;
            const cursorY = event.clientY - rect.top;
            const worldX = (cursorX - before.tx) / before.scale;
            const worldY = (cursorY - before.ty) / before.scale;
            applyView({ scale, tx: cursorX - worldX * scale, ty: cursorY - worldY * scale });
        }, { passive: false, capture: true });

        scroll.addEventListener("pointerdown", (event) => {
            if (currentKind() !== "rack" || ![0, 1].includes(event.button) || !panAllowed(event.target, event.button)) return;
            event.preventDefault();
            event.stopPropagation();
            const view = readView();
            state.pan = {
                pointerId: event.pointerId,
                x: event.clientX,
                y: event.clientY,
                tx: view.tx,
                ty: view.ty,
                scale: view.scale,
            };
            scroll.setPointerCapture?.(event.pointerId);
            scroll.classList.add("is-panning-v07545");
        }, true);

        const move = (event) => {
            const pan = state.pan;
            if (!pan || event.pointerId !== pan.pointerId) return;
            event.preventDefault();
            applyView({
                scale: pan.scale,
                tx: pan.tx + event.clientX - pan.x,
                ty: pan.ty + event.clientY - pan.y,
            });
        };
        const finish = (event) => {
            if (!state.pan || event.pointerId !== state.pan.pointerId) return;
            state.pan = null;
            scroll.classList.remove("is-panning-v07545");
        };
        global.addEventListener("pointermove", move, true);
        global.addEventListener("pointerup", finish, true);
        global.addEventListener("pointercancel", finish, true);
    }

    function ensureSvg(canvas) {
        let svg = qs("svg[data-rack-links-v07545]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07545 = "1";
            svg.classList.add("v07545-rack-links");
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
        const slot = port.closest(".v07545-service-slot");
        if (slot) {
            const organizer = slot.nextElementSibling;
            if (organizer?.classList.contains("v07545-slot-organizer")) return centerInCanvas(organizer);
        }
        const dio = port.closest('[data-equipment-type="dio"]');
        if (dio) {
            const cavity = port.closest(".v07539-dio-cavity");
            const organizer = cavity?.nextElementSibling;
            if (organizer?.classList.contains("v07545-dio-organizer")) return centerInCanvas(organizer);
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
            if (port.dataset.portRole === "rear" || port.closest(".v07545-legacy-hidden")) return;
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
            svgPath(svg, `M ${start.x} ${start.y} V ${startOrganizer.y} H ${channel} V ${endOrganizer.y} H ${end.x} V ${end.y}`, "v07545-front-link", { "data-link-id": linkId });
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
                const organizer = cavity.nextElementSibling?.classList?.contains("v07545-dio-organizer") ? cavity.nextElementSibling : cavity;
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
            if (!duct) return;
            const spineX = centerInCanvas(duct).x + (useLeft ? 8 + index * 2 : -8 - index * 2);
            const points = rows.map(({ cavity, organizer }) => ({
                organizer: centerInCanvas(organizer),
                target: sidePoint(cavity, useLeft ? "left" : "right"),
            })).sort((a, b) => a.organizer.y - b.organizer.y);
            if (!points.length) return;
            svgPath(svg, `M ${start.x} ${start.y} H ${spineX} V ${points[0].organizer.y}`, "v07545-rear-trunk", { "data-cable-id": cableId });
            const lastY = points[points.length - 1].organizer.y;
            if (lastY !== points[0].organizer.y) svgPath(svg, `M ${spineX} ${points[0].organizer.y} V ${lastY}`, "v07545-rear-trunk", { "data-cable-id": cableId });
            points.forEach((point) => svgPath(svg, `M ${spineX} ${point.organizer.y} H ${point.target.x} V ${point.target.y}`, "v07545-rear-branch", { "data-cable-id": cableId }));
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
            node.dataset.v07545HardwareError = error.message;
            console.error("MAP v0.75.45 OLT:", error);
        })));
        if (generation !== state.generation) return;
        scheduleRedraw();
        global.setTimeout(scheduleRedraw, 180);
    }

    function schedule(data = null) {
        if (data) state.data = data;
        const generation = ++state.generation;
        global.requestAnimationFrame(() => enhance(state.data, generation).catch((error) => console.error("MAP v0.75.45:", error)));
    }

    function init() {
        installCreationInterception();
        document.addEventListener("map:container-rendered", (event) => schedule(event.detail?.data || null));
        document.addEventListener("map:container-opening", () => global.setTimeout(schedule, 150));
        global.addEventListener("resize", scheduleRedraw);
        global.setTimeout(schedule, 900);
        global.mapRackChassisV07545 = Object.freeze({ version: VERSION, refresh: schedule, redraw: scheduleRedraw });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
