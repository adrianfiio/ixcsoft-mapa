(function (global) {
    "use strict";

    const VERSION = "0.75.41";
    const state = {
        data: null,
        root: null,
        canvas: null,
        scroll: null,
        frame: null,
        svg: null,
        frameId: 0,
        scrollTarget: null,
        currentKind: "unknown",
        layout: null,
        preferences: {},
        preferencesElementId: 0,
        drag: null,
        saveTimer: 0,
        enhanceGeneration: 0,
        toolbar: null,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

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

    function number(value, fallback = 0) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function currentElementId(root = state.root) {
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }

    function detectKind(data, root) {
        const values = [
            data?.element?.type,
            data?.element?.element_type,
            data?.container?.type,
            data?.container_type,
            data?.element_type,
            root?.dataset?.elementType,
            qs("#container-dialog")?.dataset?.elementType,
            qs("#container-dialog")?.dataset?.containerType,
        ].map((value) => String(value || "").toLowerCase());
        if (values.some((value) => value === "tower" || value.includes("torre"))) return "tower";
        if (values.some((value) => value === "rack" || value.includes("rack"))) return "rack";
        const heading = [
            qs("#container-dialog h1")?.textContent,
            qs("#container-dialog h2")?.textContent,
            qs("#container-dialog [data-container-title]")?.textContent,
        ].join(" ").toLowerCase();
        if (heading.includes("torre")) return "tower";
        if (heading.includes("rack")) return "rack";
        return "unknown";
    }

    function dedupeInside(node, selector, canonicalAttribute) {
        const rows = qsa(selector, node);
        if (!rows.length) return null;
        const first = rows[0];
        rows.slice(1).forEach((item) => item.remove());
        if (canonicalAttribute) first.setAttribute(canonicalAttribute, "1");
        return first;
    }

    function normalizeGeneratedControls(root) {
        qsa(".master-cable-node", root).forEach((node) => {
            dedupeInside(
                node,
                "[data-rack-cable-summary-v07538], [data-rack-cable-summary-v07537], .map-rack-cable-summary-v07538",
                "data-rack-cable-summary-v07538",
            );
        });
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach((node) => {
            dedupeInside(
                node,
                "[data-dio-cable-target-v07538], [data-dio-cable-target-v07537], .map-dio-cable-target-v07538",
                "data-dio-cable-target-v07538",
            );
            dedupeInside(
                qs(":scope > header", node) || node,
                "[data-open-dio-fusions-v07538], [data-open-dio-fusions-v07537], .map-open-dio-fusions-v07538",
                "data-open-dio-fusions-v07538",
            );
        });
    }

    function uniqueCableNodes(root) {
        const seen = new Map();
        const unique = [];
        qsa(".master-cable-node[data-cable-node], .master-cable-node[data-cable-node-id]", root).forEach((node) => {
            const id = Number(node.dataset.cableNode || node.dataset.cableNodeId || 0);
            if (!id) {
                unique.push(node);
                return;
            }
            if (seen.has(id)) {
                node.dataset.v07541DuplicateCable = "1";
                node.remove();
                return;
            }
            seen.set(id, node);
            unique.push(node);
        });
        return unique;
    }

    function equipmentRows(data, root) {
        const byId = new Map((data?.equipment || []).map((item) => [Number(item.id), item]));
        const seen = new Set();
        const rows = [];
        qsa(".master-canvas-node[data-equipment-node]", root).forEach((node) => {
            const id = Number(node.dataset.equipmentNode || 0);
            if (id && seen.has(id)) {
                node.dataset.v07541DuplicateEquipment = "1";
                node.remove();
                return;
            }
            if (id) seen.add(id);
            rows.push({ node, id, item: byId.get(id) || { id, type: node.dataset.equipmentType, metadata: {} } });
        });
        return rows;
    }

    function defaultHeightUnits(type) {
        return ({
            olt: 4,
            dio: 3,
            switch: 1,
            router: 1,
            firewall: 1,
            server: 2,
            pto: 1,
            onu: 1,
            access_point: 1,
            ptp: 1,
        })[String(type || "").toLowerCase()] || 1;
    }

    function rowHeightUnits(row, unitHeight) {
        const metadata = row.item?.metadata || {};
        const configured = number(metadata.height_units || row.item?.height_units, 0);
        const measuredPixels = Math.max(44, row.node.scrollHeight || row.node.offsetHeight || 44);
        const measured = Math.max(1, Math.ceil((measuredPixels + 10) / unitHeight));
        return Math.max(defaultHeightUnits(row.item?.type || row.node.dataset.equipmentType), configured, measured);
    }

    function explicitRackUnit(row) {
        const metadata = row.item?.metadata || {};
        return number(
            metadata.rack_unit
            || metadata.rack_position
            || metadata.position_u
            || row.item?.rack_unit
            || row.item?.position_u,
            0,
        );
    }

    function preferredRackUnit(row) {
        const saved = state.preferences?.[String(row.id)];
        return number(saved?.unit, 0) || explicitRackUnit(row);
    }

    function priority(row) {
        return ({ olt: 1, dio: 2, switch: 3, router: 4, firewall: 5, server: 6, pto: 7, onu: 8 })[
            String(row.item?.type || row.node.dataset.equipmentType || "").toLowerCase()
        ] || 20;
    }

    function rangeIsFree(assignments, unit, height, units, excludedId = null) {
        if (unit < 1 || unit + height - 1 > units) return false;
        for (const [equipmentId, placement] of assignments.entries()) {
            if (String(equipmentId) === String(excludedId)) continue;
            const start = placement.unit;
            const end = placement.unit + placement.height - 1;
            const candidateEnd = unit + height - 1;
            if (unit <= end && candidateEnd >= start) return false;
        }
        return true;
    }

    function findNearestAvailableUnit(preferred, height, units, assignments, excludedId = null) {
        const bounded = Math.max(1, Math.min(number(preferred, 1), Math.max(1, units - height + 1)));
        if (rangeIsFree(assignments, bounded, height, units, excludedId)) return bounded;
        for (let distance = 1; distance <= units; distance += 1) {
            const above = bounded + distance;
            const below = bounded - distance;
            if (rangeIsFree(assignments, above, height, units, excludedId)) return above;
            if (rangeIsFree(assignments, below, height, units, excludedId)) return below;
        }
        return null;
    }

    function prepareEquipmentMeasurement(rows, geometry) {
        const width = geometry.width - geometry.duct * 2 - 48;
        rows.forEach((row) => {
            row.node.classList.add("v07541-rack-mounted");
            row.node.classList.remove("v07541-drag-locked");
            row.node.style.width = `${width}px`;
            row.node.style.minHeight = "0";
            row.node.style.height = "auto";
            row.node.style.maxHeight = "none";
        });
        // Leitura síncrona força o navegador a recalcular o tamanho final já com a largura do Rack.
        rows.forEach((row) => void row.node.offsetHeight);
    }

    function buildAssignments(rows, data, unitHeight) {
        const configuredUnits = number(
            data?.element?.metadata?.rack_units
            || data?.element?.metadata?.rack_height_units
            || data?.rack_units,
            0,
        );
        rows.forEach((row) => {
            row.heightUnits = rowHeightUnits(row, unitHeight);
            row.preferredUnit = preferredRackUnit(row);
        });
        const maxPreferred = rows.reduce((max, row) => Math.max(max, row.preferredUnit ? row.preferredUnit + row.heightUnits - 1 : 0), 0);
        const naturalUnits = rows.reduce((total, row) => total + row.heightUnits, 4) + Math.max(0, rows.length - 1);
        const units = Math.max(12, Math.min(96, Math.max(configuredUnits || 42, maxPreferred, naturalUnits)));
        const assignments = new Map();

        rows.filter((row) => row.preferredUnit > 0)
            .sort((a, b) => b.preferredUnit - a.preferredUnit || priority(a) - priority(b) || a.id - b.id)
            .forEach((row) => {
                const unit = findNearestAvailableUnit(row.preferredUnit, row.heightUnits, units, assignments);
                if (unit != null) assignments.set(row.id, { unit, height: row.heightUnits });
            });

        rows.filter((row) => !assignments.has(row.id))
            .sort((a, b) => priority(a) - priority(b) || a.id - b.id)
            .forEach((row) => {
                let unit = null;
                for (let top = units; top >= row.heightUnits; top -= 1) {
                    const candidate = top - row.heightUnits + 1;
                    if (rangeIsFree(assignments, candidate, row.heightUnits, units)) { unit = candidate; break; }
                }
                if (unit == null) unit = findNearestAvailableUnit(1, row.heightUnits, units, assignments);
                if (unit != null) assignments.set(row.id, { unit, height: row.heightUnits });
            });

        return { units, assignments };
    }

    function ensureFrame(canvas, units, geometry) {
        let frame = qs("[data-rack-frame-v07541]", canvas);
        if (!frame) {
            frame = document.createElement("section");
            frame.dataset.rackFrameV07541 = "1";
            frame.className = "v07541-rack-frame";
            canvas.prepend(frame);
        }
        frame.style.left = `${geometry.x}px`;
        frame.style.top = `${geometry.y}px`;
        frame.style.width = `${geometry.width}px`;
        frame.style.height = `${geometry.header + units * geometry.unitHeight + 24}px`;
        frame.innerHTML = `
            <header><strong>RACK FÍSICO</strong><span>${units}U · arraste pelo cabeçalho · snap em U</span></header>
            <aside class="v07541-duct left"><b>CALHA</b></aside>
            <aside class="v07541-duct right"><b>CALHA</b></aside>
            <div class="v07541-rear-spine"><span>TRASEIRA · CABOS EXTERNOS</span></div>
            <div class="v07541-rack-units">${Array.from({ length: units }, (_, index) => {
                const unit = units - index;
                return `<div style="height:${geometry.unitHeight}px"><span>U${unit}</span><i></i></div>`;
            }).join("")}</div>`;
        state.frame = frame;
        return frame;
    }

    function ensureToolbar(canvas, geometry) {
        let toolbar = qs("[data-rack-toolbar-v07541]", canvas);
        if (!toolbar) {
            toolbar = document.createElement("div");
            toolbar.dataset.rackToolbarV07541 = "1";
            toolbar.className = "v07541-rack-toolbar";
            toolbar.innerHTML = '<span>Arraste equipamentos pelo cabeçalho</span><button type="button" data-rack-auto-v07541>Auto organizar</button>';
            canvas.appendChild(toolbar);
            qs("[data-rack-auto-v07541]", toolbar).addEventListener("click", autoOrganizeRack);
        }
        toolbar.style.left = `${geometry.x + geometry.width - 250}px`;
        toolbar.style.top = `${Math.max(4, geometry.y - 32)}px`;
        state.toolbar = toolbar;
        return toolbar;
    }

    function ensureSvg(canvas) {
        let svg = qs("svg[data-rack-links-v07541]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07541 = "1";
            svg.classList.add("v07541-rack-links");
            canvas.prepend(svg);
        }
        state.svg = svg;
        return svg;
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

    function path(svg, d, className, attributes = {}) {
        const node = document.createElementNS("http://www.w3.org/2000/svg", "path");
        node.setAttribute("d", d);
        node.setAttribute("class", className);
        Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
        svg.appendChild(node);
        return node;
    }

    function drawFrontLinks(svg, canvas, geometry) {
        const groups = new Map();
        qsa('.master-canvas-node:not([hidden]) .master-node-port[data-link-id]:not([data-link-id=""])', canvas).forEach((port) => {
            if (port.dataset.portRole === "rear") return;
            const linkId = String(port.dataset.linkId || "");
            if (!linkId) return;
            if (!groups.has(linkId)) groups.set(linkId, []);
            groups.get(linkId).push(port);
        });
        [...groups.entries()].forEach(([linkId, ports], index) => {
            const unique = [...new Set(ports)];
            if (unique.length < 2) return;
            const start = centerInCanvas(unique[0], canvas);
            const end = centerInCanvas(unique[1], canvas);
            const leftX = geometry.x + geometry.duct / 2 + 5 + (index % 6) * 3;
            const rightX = geometry.x + geometry.width - geometry.duct / 2 - 5 - (index % 6) * 3;
            const leftCost = Math.abs(start.x - leftX) + Math.abs(end.x - leftX);
            const rightCost = Math.abs(start.x - rightX) + Math.abs(end.x - rightX);
            const ductX = leftCost <= rightCost ? leftX : rightX;
            path(svg, `M ${start.x} ${start.y} H ${ductX} V ${end.y} H ${end.x}`, "v07541-front-link", { "data-link-id": linkId });
            [start, end].forEach((point) => {
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", point.x); dot.setAttribute("cy", point.y); dot.setAttribute("r", 3.2);
                dot.setAttribute("class", "v07541-port-dot");
                svg.appendChild(dot);
            });
        });
    }

    function linkedCableIds(dioNode) {
        return String(dioNode.dataset.linkedCableIdsV07537 || dioNode.dataset.linkedCableIdsV07538 || "")
            .split(",")
            .map((value) => Number(value))
            .filter(Boolean);
    }

    function drawRearCableTrunks(svg, canvas, cableNodes, geometry) {
        const byCable = new Map(cableNodes.map((node) => [Number(node.dataset.cableNode || node.dataset.cableNodeId || 0), node]));
        const targets = new Map();
        qsa('.master-canvas-node[data-equipment-type="dio"]', canvas).forEach((dioNode) => {
            const endpoint = qs("[data-dio-cable-target-v07538], [data-dio-cable-target-v07537], [data-port-role='rear'][data-port-id]", dioNode);
            if (!endpoint) return;
            linkedCableIds(dioNode).forEach((cableId) => {
                if (!targets.has(cableId)) targets.set(cableId, []);
                targets.get(cableId).push(endpoint);
            });
        });
        [...targets.entries()].forEach(([cableId, endpoints], index) => {
            const cableNode = byCable.get(cableId);
            if (!cableNode) return;
            const anchor = qs("[data-rack-cable-anchor-v07538]", cableNode) || cableNode;
            const start = centerInCanvas(anchor, canvas);
            const points = endpoints.map((endpoint) => centerInCanvas(endpoint, canvas)).sort((a, b) => a.y - b.y);
            if (!points.length) return;
            const useLeft = start.x < geometry.x + geometry.width / 2;
            const spineX = useLeft
                ? geometry.x + geometry.duct / 2 + 10 + (index % 5) * 3
                : geometry.x + geometry.width - geometry.duct / 2 - 10 - (index % 5) * 3;
            const firstY = points[0].y;
            const lastY = points[points.length - 1].y;
            path(svg, `M ${start.x} ${start.y} H ${spineX} V ${firstY}`, "v07541-rear-trunk", { "data-cable-id": cableId });
            if (lastY !== firstY) path(svg, `M ${spineX} ${firstY} V ${lastY}`, "v07541-rear-trunk", { "data-cable-id": cableId });
            points.forEach((point) => path(svg, `M ${spineX} ${point.y} H ${point.x}`, "v07541-rear-branch", { "data-cable-id": cableId }));
        });
    }

    function placementTop(placement, geometry, units) {
        return geometry.y + geometry.header + (units - (placement.unit + placement.height - 1)) * geometry.unitHeight + 2;
    }

    function placeEquipment(rows, assignments, geometry, units) {
        rows.forEach((row) => {
            const placement = assignments.get(row.id);
            if (!placement) return;
            row.node.classList.add("v07541-rack-mounted");
            row.node.classList.remove("v07541-drag-locked");
            row.node.dataset.rackUnitV07541 = String(placement.unit);
            row.node.dataset.rackHeightV07541 = String(placement.height);
            row.node.style.left = `${geometry.x + geometry.duct + 24}px`;
            row.node.style.top = `${placementTop(placement, geometry, units)}px`;
            row.node.style.width = `${geometry.width - geometry.duct * 2 - 48}px`;
            row.node.style.minHeight = `${Math.max(44, placement.height * geometry.unitHeight - 4)}px`;
            row.node.style.height = "auto";
            row.node.style.maxHeight = "none";
            let badge = qs("[data-rack-u-badge-v07541]", row.node);
            if (!badge) {
                badge = document.createElement("span");
                badge.dataset.rackUBadgeV07541 = "1";
                badge.className = "v07541-rack-u-badge";
                (qs(":scope > header", row.node) || row.node).appendChild(badge);
            }
            badge.textContent = placement.height > 1
                ? `U${placement.unit}–U${placement.unit + placement.height - 1}`
                : `U${placement.unit}`;
        });
    }

    function placeCables(cableNodes, data, geometry, units) {
        const byId = new Map((data?.cables || []).map((item) => [Number(item.id), item]));
        const left = [];
        const right = [];
        cableNodes.forEach((node) => {
            const id = Number(node.dataset.cableNode || node.dataset.cableNodeId || 0);
            const item = byId.get(id) || {};
            const relation = String(item.relation || node.dataset.cableSide || "input").toLowerCase();
            (relation === "output" || relation === "right" ? right : left).push({ node, id, item });
        });
        const place = (rows, side) => rows.forEach((row, index) => {
            row.node.classList.add("v07541-external-cable", "v07541-drag-locked");
            row.node.dataset.externalSideV07541 = side;
            row.node.style.left = `${side === "left" ? geometry.x - 270 : geometry.x + geometry.width + 38}px`;
            row.node.style.top = `${geometry.y + 70 + index * 118}px`;
            row.node.style.width = "230px";
        });
        place(left, "left");
        place(right, "right");
        return [...left, ...right].map((row) => row.node);
    }

    function redraw() {
        if (!state.root || !state.canvas || state.currentKind !== "rack" || !state.layout) return;
        const { geometry, units, cableNodes } = state.layout;
        const svg = ensureSvg(state.canvas);
        const width = Math.max(
            state.canvas.scrollWidth,
            geometry.x + geometry.width + 330,
            ...cableNodes.map((node) => (number(node.style.left) + node.offsetWidth + 40)),
        );
        const height = Math.max(state.canvas.scrollHeight, geometry.y + geometry.header + units * geometry.unitHeight + 70);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.style.width = `${width}px`;
        svg.style.height = `${height}px`;
        svg.innerHTML = "";
        drawFrontLinks(svg, state.canvas, geometry);
        drawRearCableTrunks(svg, state.canvas, cableNodes, geometry);
    }

    function scheduleRedraw() {
        if (state.frameId) return;
        state.frameId = global.requestAnimationFrame(() => {
            state.frameId = 0;
            redraw();
        });
    }

    function attachScroll(scroll) {
        if (state.scrollTarget === scroll) return;
        state.scrollTarget?.removeEventListener("scroll", scheduleRedraw);
        state.scrollTarget = scroll;
        scroll?.addEventListener("scroll", scheduleRedraw, { passive: true });
    }

    function resetPhysicalMode(root) {
        root.classList.remove("v07541-physical-rack");
        qs("[data-rack-frame-v07541]", root)?.remove();
        qs("[data-rack-links-v07541]", root)?.remove();
        qs("[data-rack-toolbar-v07541]", root)?.remove();
        qsa(".v07541-rack-mounted, .v07541-external-cable", root).forEach((node) => {
            node.classList.remove("v07541-rack-mounted", "v07541-external-cable", "v07541-drag-locked");
            node.style.removeProperty("min-height");
            node.style.removeProperty("height");
            node.style.removeProperty("max-height");
            node.style.removeProperty("width");
            node.style.removeProperty("left");
            node.style.removeProperty("top");
        });
        state.layout = null;
    }

    async function loadPreferences(elementId) {
        if (!elementId) return {};
        if (state.preferencesElementId === elementId) return state.preferences;
        try {
            const data = await request(`/api/map/v07539/elements/${elementId}/layout/`);
            state.preferences = data.layout?.rack_units_v07541 || {};
        } catch (_error) {
            state.preferences = {};
        }
        state.preferencesElementId = elementId;
        return state.preferences;
    }

    function schedulePreferenceSave() {
        global.clearTimeout(state.saveTimer);
        state.saveTimer = global.setTimeout(async () => {
            const elementId = currentElementId();
            if (!elementId) return;
            try {
                await request(`/api/map/v07539/elements/${elementId}/layout/`, {
                    method: "PATCH",
                    body: JSON.stringify({ layout: { rack_units_v07541: state.preferences } }),
                });
            } catch (error) {
                global.networkMap?.notify?.(`Não foi possível salvar a posição no Rack: ${error.message}`, true);
            }
        }, 180);
    }

    function autoOrganizeRack(event) {
        event?.preventDefault?.();
        event?.stopPropagation?.();
        state.preferences = {};
        schedulePreferenceSave();
        schedule(state.data);
        global.networkMap?.notify?.("Equipamentos reorganizados automaticamente no Rack.");
    }

    async function applyPhysicalRack(root, data, normalizedCableNodes = null, generation = 0) {
        const canvas = qs(".master-canvas", root);
        const scroll = qs(".master-canvas-scroll", root);
        if (!canvas) return;
        const elementId = currentElementId(root);
        await loadPreferences(elementId);
        if (generation && generation !== state.enhanceGeneration) return;
        state.canvas = canvas;
        state.scroll = scroll;
        attachScroll(scroll);
        root.classList.add("v07541-physical-rack");
        const available = Math.max(900, Math.min(1120, number(scroll?.clientWidth, 1100) - 120));
        const geometry = { x: 300, y: 48, width: available, duct: 52, header: 50, unitHeight: 62 };
        const rows = equipmentRows(data, root);
        prepareEquipmentMeasurement(rows, geometry);
        const { units, assignments } = buildAssignments(rows, data, geometry.unitHeight);
        ensureFrame(canvas, units, geometry);
        ensureToolbar(canvas, geometry);
        placeEquipment(rows, assignments, geometry, units);
        const cableNodes = placeCables(normalizedCableNodes || uniqueCableNodes(root), data, geometry, units);
        canvas.style.minWidth = `${geometry.x + geometry.width + 330}px`;
        canvas.style.minHeight = `${geometry.y + geometry.header + units * geometry.unitHeight + 90}px`;
        state.layout = { geometry, units, assignments, rows, cableNodes };
        scheduleRedraw();
    }

    async function enhance(eventData = null, generation = 0) {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        if (!root || !dialog?.open) return;
        const data = eventData || state.data || {};
        state.data = data;
        state.root = root;
        normalizeGeneratedControls(root);
        const normalizedCableNodes = uniqueCableNodes(root);
        const kind = detectKind(data, root);
        state.currentKind = kind;
        root.dataset.containerKindV07541 = kind;
        if (kind === "rack") await applyPhysicalRack(root, data, normalizedCableNodes, generation);
        else resetPhysicalMode(root);
    }

    function schedule(eventData = null) {
        if (eventData) state.data = eventData;
        const generation = ++state.enhanceGeneration;
        global.requestAnimationFrame(() => {
            enhance(state.data, generation).catch((error) => console.error("MAP v0.75.41 Rack:", error));
        });
    }

    function rackUnitFromPointer(clientY, placement) {
        const { geometry, units } = state.layout;
        const canvasRect = state.canvas.getBoundingClientRect();
        const scale = number(state.canvas.dataset.v0741Scale, 1) || 1;
        const canvasY = (clientY - canvasRect.top) / scale;
        const topIndex = Math.round((canvasY - geometry.y - geometry.header - 2) / geometry.unitHeight);
        return units - topIndex - placement.height + 1;
    }

    function updateDragPreview(event) {
        const drag = state.drag;
        if (!drag || event.pointerId !== drag.pointerId || !state.layout) return;
        const preferred = rackUnitFromPointer(event.clientY, drag.original);
        const unit = findNearestAvailableUnit(
            preferred,
            drag.original.height,
            state.layout.units,
            state.layout.assignments,
            drag.equipmentId,
        );
        if (unit == null) return;
        drag.previewUnit = unit;
        drag.node.style.top = `${placementTop({ unit, height: drag.original.height }, state.layout.geometry, state.layout.units)}px`;
        const badge = qs("[data-rack-u-badge-v07541]", drag.node);
        if (badge) badge.textContent = drag.original.height > 1 ? `U${unit}–U${unit + drag.original.height - 1}` : `U${unit}`;
        scheduleRedraw();
    }

    function finishRackDrag(event, cancelled = false) {
        const drag = state.drag;
        if (!drag || (event?.pointerId != null && event.pointerId !== drag.pointerId)) return;
        global.removeEventListener("pointermove", updateDragPreview, true);
        global.removeEventListener("pointerup", finishRackDrag, true);
        global.removeEventListener("pointercancel", cancelRackDrag, true);
        drag.node.classList.remove("is-dragging-v07541");
        const unit = cancelled ? drag.original.unit : (drag.previewUnit ?? drag.original.unit);
        state.layout.assignments.set(drag.equipmentId, { unit, height: drag.original.height });
        state.preferences[String(drag.equipmentId)] = { unit };
        placeEquipment(state.layout.rows, state.layout.assignments, state.layout.geometry, state.layout.units);
        state.drag = null;
        schedulePreferenceSave();
        scheduleRedraw();
    }

    function cancelRackDrag(event) {
        finishRackDrag(event, true);
    }

    function startRackDrag(event) {
        const target = event.target;
        const root = qs("#map-master-container.v07541-physical-rack");
        if (!(target instanceof Element) || !root || !root.contains(target)) return;
        if (target.closest("button, a, input, select, textarea, [data-port-id], [data-rack-cable-anchor-v07538]")) return;
        const header = target.closest(".v07541-rack-mounted > header");
        const node = header?.closest(".v07541-rack-mounted");
        const equipmentId = Number(node?.dataset.equipmentNode || 0);
        const placement = state.layout?.assignments?.get(equipmentId);
        if (!header || !node || !equipmentId || !placement) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        header.setPointerCapture?.(event.pointerId);
        state.drag = {
            pointerId: event.pointerId,
            equipmentId,
            node,
            original: { ...placement },
            previewUnit: placement.unit,
        };
        node.classList.add("is-dragging-v07541");
        global.addEventListener("pointermove", updateDragPreview, true);
        global.addEventListener("pointerup", finishRackDrag, true);
        global.addEventListener("pointercancel", cancelRackDrag, true);
    }

    function init() {
        document.addEventListener("map:container-rendered", (event) => schedule(event.detail?.data || null));
        document.addEventListener("map:container-opening", () => global.setTimeout(() => schedule(), 120));
        document.addEventListener("pointerdown", startRackDrag, true);
        global.addEventListener("resize", scheduleRedraw);
        global.setTimeout(() => schedule(), 800);
        const api = Object.freeze({
            version: VERSION,
            refresh: () => schedule(),
            normalizeDuplicates: () => normalizeGeneratedControls(qs("#map-master-container")),
            autoOrganize: autoOrganizeRack,
        });
        global.mapRackPhysicalV07541 = api;
        global.mapRackPhysicalV07540 = api;
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
