(function (global) {
    "use strict";

    const VERSION = "0.75.43";
    const state = {
        root: null,
        canvas: null,
        scroll: null,
        svg: null,
        data: null,
        frame: 0,
        pan: null,
        hardware: new Map(),
        dialog: null,
        generation: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

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
        const direct = String(state.root?.dataset.containerKindV07542 || state.root?.dataset.containerKindV07541 || "").toLowerCase();
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
        dialog.id = "map-rack-hardware-v07543";
        dialog.className = "v07543-dialog";
        dialog.innerHTML = '<form><header><div><small data-kicker>HARDWARE ÓPTICO</small><h2 data-title></h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div data-body></div></form>';
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
        state.dialog = dialog;
        return dialog;
    }

    function showDialog({ title, subtitle = "", kicker = "HARDWARE ÓPTICO", body = "" }) {
        const dialog = ensureDialog();
        qs("[data-title]", dialog).textContent = title;
        qs("[data-subtitle]", dialog).textContent = subtitle;
        qs("[data-kicker]", dialog).textContent = kicker;
        qs("[data-body]", dialog).innerHTML = body;
        if (!dialog.open) dialog.showModal();
        return dialog;
    }

    function hardwareUrl(elementId, oltId) {
        return `/api/map/v07543/elements/${Number(elementId)}/olt/${Number(oltId)}/hardware/`;
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

    function openCardEditor(node, card) {
        if (!canEdit()) return;
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        const dialog = showDialog({
            title: `Editar placa S${card.slot}`,
            subtitle: `${card.pon_count} portas de serviço`,
            kicker: "PLACA DE SERVIÇO",
            body: `<div class="v07543-form-grid"><label>Nome da placa<input name="name" value="${escapeHtml(card.name || `Placa ${card.slot}`)}" maxlength="100"></label><label>Modelo<input name="model" value="${escapeHtml(card.model || "")}" maxlength="100" placeholder="Ex.: H901GPHF"></label><label>Tecnologia<select name="technology"><option value="gpon" ${card.technology === "gpon" ? "selected" : ""}>GPON</option><option value="xgpon" ${card.technology === "xgpon" ? "selected" : ""}>XG-PON</option><option value="xgspon" ${card.technology === "xgspon" ? "selected" : ""}>XGS-PON</option></select></label></div><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>Salvar placa</button></footer>`,
        });
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("[data-save]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando placa…";
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
                notify("Placa de serviço atualizada.");
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
    }

    function openUplinkEditor(node, hardware, port = null) {
        if (!canEdit()) return;
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        const options = hardware.uplink_types.map((item) => `<option value="${escapeHtml(item.value)}" ${port?.port_type === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("");
        const dialog = showDialog({
            title: port ? `Editar ${port.label}` : "Adicionar uplink",
            subtitle: "Portas de gerência e subida ficam separadas das placas PON.",
            kicker: "UPLINK DA OLT",
            body: `<div class="v07543-form-grid"><label>Identificação<input name="label" value="${escapeHtml(port?.label || "")}" maxlength="100" placeholder="Ex.: Uplink Core 1"></label><label>Tipo físico<select name="port_type">${options}</select></label></div><p data-status></p><footer>${port ? '<button type="button" class="danger" data-delete>Excluir uplink</button>' : ""}<span></span><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>Salvar uplink</button></footer>`,
        });
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        qs("[data-save]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Salvando uplink…";
            try {
                await request(hardwareUrl(elementId, oltId), {
                    method: "POST",
                    body: JSON.stringify({
                        action: "save_uplink",
                        port_id: port?.id || null,
                        label: qs('[name="label"]', dialog).value,
                        port_type: qs('[name="port_type"]', dialog).value,
                    }),
                });
                dialog.close();
                notify(port ? "Uplink atualizado." : "Uplink criado.");
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
        const remove = qs("[data-delete]", dialog);
        if (remove) remove.onclick = async () => {
            const status = qs("[data-status]", dialog);
            status.textContent = "Excluindo uplink…";
            try {
                await request(hardwareUrl(elementId, oltId), {
                    method: "DELETE",
                    body: JSON.stringify({ action: "delete_uplink", port_id: port.id }),
                });
                dialog.close();
                notify("Uplink excluído.");
                await refreshContainer(elementId);
            } catch (error) {
                status.textContent = error.message;
                status.classList.add("error");
            }
        };
    }

    function technologyLabel(value) {
        return ({ gpon: "GPON", xgpon: "XG-PON", xgspon: "XGS-PON" })[value] || "GPON";
    }

    function compactUplinkLabel(port) {
        if (port.port_type === "rj45_1g") return "RJ45";
        if (port.port_type === "sfp_plus_10g") return "SFP+";
        return "SFP";
    }

    function renderUplinkPanel(node, panel, hardware) {
        panel.innerHTML = `<header><div><strong>UPLINKS</strong><small>RJ45 · SFP · SFP+</small></div>${canEdit() ? '<button type="button" data-add-uplink>+ Uplink</button>' : ""}</header><div class="v07543-uplink-grid">${hardware.uplinks.map((port) => `<button type="button" class="master-node-port v07543-uplink-port ${port.linked ? "linked" : ""}" data-port-id="${port.id}" data-port-type="${escapeHtml(port.port_type)}" data-port-role="front" data-link-id="${port.link_id || ""}" title="${escapeHtml(port.label)} · botão direito para editar"><i></i><span>${compactUplinkLabel(port)}</span><b>${port.number}</b></button>`).join("") || '<p>Nenhum uplink cadastrado.</p>'}</div>`;
        const add = qs("[data-add-uplink]", panel);
        if (add) add.onclick = (event) => { event.stopPropagation(); openUplinkEditor(node, hardware); };
        qsa(".v07543-uplink-port", panel).forEach((button) => {
            const port = hardware.uplinks.find((item) => Number(item.id) === Number(button.dataset.portId));
            button.addEventListener("contextmenu", (event) => {
                event.preventDefault();
                event.stopPropagation();
                openUplinkEditor(node, hardware, port);
            });
        });
    }

    function ensureOltBottomGrid(node, slots) {
        let grid = qs(":scope > .v07543-olt-bottom-grid", node);
        if (grid) return { grid, created: false };
        grid = document.createElement("div");
        grid.className = "v07543-olt-bottom-grid";
        const service = document.createElement("div");
        service.className = "v07543-olt-service-tail";
        const uplinks = document.createElement("section");
        uplinks.className = "v07543-olt-uplinks";
        const tail = slots.slice(Math.max(0, slots.length - 2));
        if (tail.length) tail[0].before(grid);
        else node.appendChild(grid);
        tail.forEach((slot) => service.appendChild(slot));
        grid.append(service, uplinks);
        return { grid, created: true };
    }

    async function enhanceOlt(node, generation) {
        const elementId = currentElementId();
        const oltId = equipmentId(node);
        if (!elementId || !oltId) return;
        const hardware = await loadHardware(elementId, oltId);
        if (generation !== state.generation || !node.isConnected) return;
        node.classList.add("v07543-olt-hardware");
        const slots = qsa(".master-olt-slot-v07510", node);
        slots.forEach((slot, index) => {
            const card = hardware.cards[index];
            if (!card) return;
            slot.dataset.cardIdV07543 = String(card.id);
            slot.classList.add("v07543-service-card");
            let badge = qs("[data-card-profile-v07543]", slot);
            if (!badge) {
                badge = document.createElement("span");
                badge.dataset.cardProfileV07543 = "1";
                badge.className = "v07543-card-profile";
                (qs(":scope > header", slot) || slot).appendChild(badge);
            }
            badge.textContent = `${technologyLabel(card.technology)}${card.model ? ` · ${card.model}` : ""}`;
            slot.title = `Botão direito: editar placa S${card.slot}`;
            if (slot.dataset.cardContextV07543 !== "1") {
                slot.dataset.cardContextV07543 = "1";
                slot.addEventListener("contextmenu", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    openCardEditor(node, card);
                });
            }
        });
        const bottom = ensureOltBottomGrid(node, slots);
        renderUplinkPanel(node, qs(".v07543-olt-uplinks", bottom.grid), hardware);
        let organizer = qs(":scope > .v07543-olt-organizer", node);
        if (!organizer) {
            organizer = document.createElement("div");
            organizer.className = "v07543-olt-organizer";
            organizer.innerHTML = "<i></i><span>ORGANIZADOR OLT / UPLINKS</span><i></i>";
            node.appendChild(organizer);
        }
        if (bottom.created) {
            global.setTimeout(() => global.mapRackPhysicalV07542?.refresh?.(), 0);
        }
    }

    function enhanceDio(node) {
        qsa(".v07542-dio-organizer, .v07543-dio-organizer", node).forEach((item) => item.remove());
        qsa(".v07539-dio-cavity", node).forEach((cavity, index) => {
            const organizer = document.createElement("div");
            organizer.className = "v07543-dio-organizer";
            organizer.dataset.cavityIndexV07543 = String(index);
            organizer.innerHTML = `<i></i><span>ORGANIZADOR ÓPTICO · CAVIDADE ${index + 1}</span><i></i>`;
            cavity.after(organizer);
        });
        node.classList.add("v07543-dio-routing");
    }

    function hideRedundantToolbarActions(root) {
        qsa("[data-container-lines]", root).forEach((button) => { button.hidden = true; button.dataset.hiddenV07543 = "1"; });
        qsa("button", qs("#container-dialog") || root).forEach((button) => {
            const label = button.textContent.replace(/\s+/g, " ").trim().toLowerCase();
            if (label === "ligar portas" || label === "editar linhas") {
                button.hidden = true;
                button.dataset.hiddenV07543 = "1";
            }
        });
    }

    function installPan(scroll) {
        if (!scroll || scroll.dataset.panV07543 === "1") return;
        scroll.dataset.panV07543 = "1";
        scroll.classList.add("v07543-pan-enabled");
        scroll.addEventListener("pointerdown", (event) => {
            if (currentKind() !== "rack" || event.button !== 0) return;
            if (!(event.target instanceof Element)) return;
            if (event.target.closest(".master-canvas-node, .master-cable-node, button, a, input, select, textarea, dialog, .map-canvas-zoom-v0741, .v07542-rack-toolbar")) return;
            event.preventDefault();
            event.stopPropagation();
            scroll.setPointerCapture?.(event.pointerId);
            state.pan = {
                pointerId: event.pointerId,
                x: event.clientX,
                y: event.clientY,
                left: scroll.scrollLeft,
                top: scroll.scrollTop,
            };
            scroll.classList.add("is-panning-v07543");
        }, true);
        scroll.addEventListener("pointermove", (event) => {
            const pan = state.pan;
            if (!pan || event.pointerId !== pan.pointerId) return;
            scroll.scrollLeft = pan.left - (event.clientX - pan.x);
            scroll.scrollTop = pan.top - (event.clientY - pan.y);
            scheduleRedraw();
        }, true);
        const finish = (event) => {
            if (!state.pan || (event.pointerId != null && event.pointerId !== state.pan.pointerId)) return;
            state.pan = null;
            scroll.classList.remove("is-panning-v07543");
        };
        scroll.addEventListener("pointerup", finish, true);
        scroll.addEventListener("pointercancel", finish, true);
    }

    function ensureSvg(canvas) {
        let svg = qs("svg[data-rack-links-v07543]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07543 = "1";
            svg.classList.add("v07543-rack-links");
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
        const dio = port.closest('[data-equipment-type="dio"]');
        if (dio) {
            const cavity = port.closest(".v07539-dio-cavity");
            const organizer = cavity?.nextElementSibling?.classList?.contains("v07543-dio-organizer") ? cavity.nextElementSibling : null;
            if (organizer) return centerInCanvas(organizer);
        }
        const olt = port.closest('[data-equipment-type="olt"]');
        if (olt) {
            const organizer = qs(":scope > .v07543-olt-organizer", olt);
            if (organizer) return centerInCanvas(organizer);
        }
        const equipment = port.closest(".v07542-rack-mounted");
        if (!equipment) return centerInCanvas(port);
        const equipmentCenter = centerInCanvas(equipment);
        const equipmentBottom = equipmentCenter.y + equipment.offsetHeight / 2;
        const organizers = qsa(".v07542-rack-organizer", state.canvas).map((node) => ({ node, point: centerInCanvas(node) }));
        if (!organizers.length) return { x: equipmentCenter.x, y: equipmentBottom };
        const below = organizers.filter((item) => item.point.y >= equipmentBottom - 4).sort((a, b) => a.point.y - b.point.y)[0];
        return (below || organizers.sort((a, b) => Math.abs(a.point.y - equipmentBottom) - Math.abs(b.point.y - equipmentBottom))[0]).point;
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
            if (port.dataset.portRole === "rear") return;
            const linkId = String(port.dataset.linkId || "");
            if (!linkId) return;
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
            svgPath(svg, `M ${start.x} ${start.y} V ${startOrganizer.y} H ${channel} V ${endOrganizer.y} H ${end.x} V ${end.y}`, "v07543-front-link", { "data-link-id": linkId });
            [start, end].forEach((point) => {
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", point.x);
                dot.setAttribute("cy", point.y);
                dot.setAttribute("r", 3.2);
                dot.setAttribute("class", "v07543-port-dot");
                svg.appendChild(dot);
            });
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
                const organizer = cavity.nextElementSibling?.classList?.contains("v07543-dio-organizer") ? cavity.nextElementSibling : cavity;
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
            svgPath(svg, `M ${start.x} ${start.y} H ${spineX} V ${points[0].organizer.y}`, "v07543-rear-trunk", { "data-cable-id": cableId });
            const lastY = points[points.length - 1].organizer.y;
            if (lastY !== points[0].organizer.y) svgPath(svg, `M ${spineX} ${points[0].organizer.y} V ${lastY}`, "v07543-rear-trunk", { "data-cable-id": cableId });
            points.forEach((point) => {
                svgPath(svg, `M ${spineX} ${point.organizer.y} H ${point.target.x} V ${point.target.y}`, "v07543-rear-branch", { "data-cable-id": cableId });
            });
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
        installPan(state.scroll);
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach(enhanceDio);
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="olt"]', root).map((node) => enhanceOlt(node, generation).catch((error) => {
            node.dataset.v07543HardwareError = error.message;
        })));
        if (generation !== state.generation) return;
        scheduleRedraw();
        global.setTimeout(scheduleRedraw, 180);
    }

    function schedule(data = null) {
        if (data) state.data = data;
        const generation = ++state.generation;
        global.requestAnimationFrame(() => enhance(state.data, generation).catch((error) => console.error("MAP v0.75.43:", error)));
    }

    function init() {
        document.addEventListener("map:container-rendered", (event) => schedule(event.detail?.data || null));
        document.addEventListener("map:container-opening", () => global.setTimeout(schedule, 150));
        global.addEventListener("resize", scheduleRedraw);
        document.addEventListener("scroll", scheduleRedraw, true);
        global.setTimeout(schedule, 900);
        global.mapRackRoutingV07543 = Object.freeze({ version: VERSION, refresh: schedule, redraw: scheduleRedraw });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
