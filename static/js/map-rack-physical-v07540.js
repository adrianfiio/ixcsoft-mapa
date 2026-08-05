(function (global) {
    "use strict";

    const VERSION = "0.75.40";
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
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

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
                node.dataset.v07540DuplicateCable = "1";
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
        return qsa(".master-canvas-node[data-equipment-node]", root).map((node) => {
            const id = Number(node.dataset.equipmentNode || 0);
            return { node, id, item: byId.get(id) || { id, type: node.dataset.equipmentType, metadata: {} } };
        });
    }

    function defaultHeightUnits(type) {
        return ({
            olt: 6,
            dio: 4,
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
        const measured = Math.max(1, Math.ceil(Math.max(40, row.node.scrollHeight || row.node.offsetHeight || 40) / unitHeight));
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

    function priority(row) {
        return ({ olt: 1, dio: 2, switch: 3, router: 4, firewall: 5, server: 6, pto: 7, onu: 8 })[
            String(row.item?.type || row.node.dataset.equipmentType || "").toLowerCase()
        ] || 20;
    }

    function buildAssignments(rows, data, unitHeight) {
        const configuredUnits = number(
            data?.element?.metadata?.rack_units
            || data?.element?.metadata?.rack_height_units
            || data?.rack_units,
            0,
        );
        rows.forEach((row) => { row.heightUnits = rowHeightUnits(row, unitHeight); row.explicitUnit = explicitRackUnit(row); });
        const maxExplicit = rows.reduce((max, row) => Math.max(max, row.explicitUnit ? row.explicitUnit + row.heightUnits - 1 : 0), 0);
        const naturalUnits = rows.reduce((total, row) => total + row.heightUnits + 1, 4);
        const units = Math.max(12, Math.min(48, Math.max(configuredUnits, maxExplicit, naturalUnits)));
        const occupied = new Set();
        const assignments = new Map();

        const claim = (row, start) => {
            const safeStart = Math.max(1, Math.min(start, Math.max(1, units - row.heightUnits + 1)));
            for (let current = safeStart; current < safeStart + row.heightUnits; current += 1) occupied.add(current);
            assignments.set(row.id, { unit: safeStart, height: row.heightUnits });
        };

        rows.filter((row) => row.explicitUnit > 0).sort((a, b) => b.explicitUnit - a.explicitUnit).forEach((row) => claim(row, row.explicitUnit));
        rows.filter((row) => !row.explicitUnit).sort((a, b) => priority(a) - priority(b) || a.id - b.id).forEach((row) => {
            let selected = 1;
            for (let top = units; top >= row.heightUnits; top -= 1) {
                const start = top - row.heightUnits + 1;
                let free = true;
                for (let current = start; current <= top; current += 1) {
                    if (occupied.has(current)) { free = false; break; }
                }
                if (free) { selected = start; break; }
            }
            claim(row, selected);
        });
        return { units, assignments };
    }

    function ensureFrame(canvas, units, geometry) {
        let frame = qs("[data-rack-frame-v07540]", canvas);
        if (!frame) {
            frame = document.createElement("section");
            frame.dataset.rackFrameV07540 = "1";
            frame.className = "v07540-rack-frame";
            canvas.prepend(frame);
        }
        frame.style.left = `${geometry.x}px`;
        frame.style.top = `${geometry.y}px`;
        frame.style.width = `${geometry.width}px`;
        frame.style.height = `${geometry.header + units * geometry.unitHeight + 24}px`;
        frame.innerHTML = `
            <header><strong>RACK FÍSICO</strong><span>${units}U · equipamentos travados</span></header>
            <aside class="v07540-duct left"><b>CALHA</b></aside>
            <aside class="v07540-duct right"><b>CALHA</b></aside>
            <div class="v07540-rear-spine"><span>TRASEIRA · CABOS EXTERNOS</span></div>
            <div class="v07540-rack-units">${Array.from({ length: units }, (_, index) => {
                const unit = units - index;
                return `<div style="height:${geometry.unitHeight}px"><span>U${unit}</span><i></i></div>`;
            }).join("")}</div>`;
        state.frame = frame;
        return frame;
    }

    function ensureSvg(canvas) {
        let svg = qs("svg[data-rack-links-v07540]", canvas);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.dataset.rackLinksV07540 = "1";
            svg.classList.add("v07540-rack-links");
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
            path(svg, `M ${start.x} ${start.y} H ${ductX} V ${end.y} H ${end.x}`, "v07540-front-link", { "data-link-id": linkId });
            [start, end].forEach((point) => {
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", point.x); dot.setAttribute("cy", point.y); dot.setAttribute("r", 3.2);
                dot.setAttribute("class", "v07540-port-dot");
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
            path(svg, `M ${start.x} ${start.y} H ${spineX} V ${firstY}`, "v07540-rear-trunk", { "data-cable-id": cableId });
            if (lastY !== firstY) path(svg, `M ${spineX} ${firstY} V ${lastY}`, "v07540-rear-trunk", { "data-cable-id": cableId });
            points.forEach((point) => path(svg, `M ${spineX} ${point.y} H ${point.x}`, "v07540-rear-branch", { "data-cable-id": cableId }));
        });
    }

    function placeEquipment(rows, assignments, geometry, units) {
        rows.forEach((row) => {
            const placement = assignments.get(row.id);
            if (!placement) return;
            const top = geometry.y + geometry.header + (units - (placement.unit + placement.height - 1)) * geometry.unitHeight + 2;
            row.node.classList.add("v07540-rack-mounted", "v07540-drag-locked");
            row.node.dataset.rackUnitV07540 = String(placement.unit);
            row.node.dataset.rackHeightV07540 = String(placement.height);
            row.node.style.left = `${geometry.x + geometry.duct + 24}px`;
            row.node.style.top = `${top}px`;
            row.node.style.width = `${geometry.width - geometry.duct * 2 - 48}px`;
            row.node.style.minHeight = `${Math.max(44, placement.height * geometry.unitHeight - 4)}px`;
            let badge = qs("[data-rack-u-badge-v07540]", row.node);
            if (!badge) {
                badge = document.createElement("span");
                badge.dataset.rackUBadgeV07540 = "1";
                badge.className = "v07540-rack-u-badge";
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
            row.node.classList.add("v07540-external-cable", "v07540-drag-locked");
            row.node.dataset.externalSideV07540 = side;
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
        root.classList.remove("v07540-physical-rack");
        qs("[data-rack-frame-v07540]", root)?.remove();
        qs("[data-rack-links-v07540]", root)?.remove();
        qsa(".v07540-rack-mounted, .v07540-external-cable", root).forEach((node) => {
            node.classList.remove("v07540-rack-mounted", "v07540-external-cable", "v07540-drag-locked");
            node.style.removeProperty("min-height");
            node.style.removeProperty("width");
        });
        state.layout = null;
    }

    function applyPhysicalRack(root, data, normalizedCableNodes = null) {
        const canvas = qs(".master-canvas", root);
        const scroll = qs(".master-canvas-scroll", root);
        if (!canvas) return;
        state.canvas = canvas;
        state.scroll = scroll;
        attachScroll(scroll);
        root.classList.add("v07540-physical-rack");
        const geometry = { x: 330, y: 38, width: 820, duct: 48, header: 48, unitHeight: 56 };
        const rows = equipmentRows(data, root);
        const { units, assignments } = buildAssignments(rows, data, geometry.unitHeight);
        ensureFrame(canvas, units, geometry);
        placeEquipment(rows, assignments, geometry, units);
        const cableNodes = placeCables(normalizedCableNodes || uniqueCableNodes(root), data, geometry, units);
        canvas.style.minWidth = `${geometry.x + geometry.width + 330}px`;
        canvas.style.minHeight = `${geometry.y + geometry.header + units * geometry.unitHeight + 90}px`;
        state.layout = { geometry, units, assignments, cableNodes };
        scheduleRedraw();
    }

    function enhance(eventData = null) {
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
        root.dataset.containerKindV07540 = kind;
        if (kind === "rack") applyPhysicalRack(root, data, normalizedCableNodes);
        else resetPhysicalMode(root);
    }

    function schedule(eventData = null) {
        if (eventData) state.data = eventData;
        global.requestAnimationFrame(() => enhance(state.data));
    }

    function lockDrag(event) {
        const root = qs("#map-master-container.v07540-physical-rack");
        if (!root || !event.target.closest(root)) return;
        if (event.target.closest("button, a, input, select, textarea, [data-port-id], [data-rack-cable-anchor-v07538]")) return;
        const handle = event.target.closest(".master-canvas-node > header, .master-cable-node > header, .drag-grip");
        if (!handle) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    function init() {
        document.addEventListener("map:container-rendered", (event) => schedule(event.detail?.data || null));
        document.addEventListener("map:container-opening", () => global.setTimeout(() => schedule(), 120));
        document.addEventListener("pointerdown", lockDrag, true);
        global.addEventListener("resize", scheduleRedraw);
        global.setTimeout(() => schedule(), 800);
        global.mapRackPhysicalV07540 = Object.freeze({
            version: VERSION,
            refresh: () => schedule(),
            normalizeDuplicates: () => normalizeGeneratedControls(qs("#map-master-container")),
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
