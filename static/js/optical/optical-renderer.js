(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    const stateApi = () => namespace.state;

    const NODE = {
        cableWidth: 168,
        cableHeader: 42,
        fiberSize: 13,
        fiberGap: 7,
        fiberColumns: 6,
        splitterWidth: 178,
        splitterPortGap: 24,
    };

    function ensureNode(session, key, fallback) {
        if (!session.layout.nodes[key]) session.layout.nodes[key] = { ...fallback };
        return session.layout.nodes[key];
    }

    function worldToScreen(session, point) {
        const { zoom, panX, panY } = session.layout.viewport;
        return { x: point.x * zoom + panX, y: point.y * zoom + panY };
    }

    function screenToWorld(session, point) {
        const { zoom, panX, panY } = session.layout.viewport;
        return { x: (point.x - panX) / zoom, y: (point.y - panY) / zoom };
    }

    function roundedRect(ctx, x, y, width, height, radius) {
        const r = Math.min(radius, width / 2, height / 2);
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + width, y, x + width, y + height, r);
        ctx.arcTo(x + width, y + height, x, y + height, r);
        ctx.arcTo(x, y + height, x, y, r);
        ctx.arcTo(x, y, x + width, y, r);
        ctx.closePath();
    }

    function fitCanvas(session) {
        const canvas = session.canvas;
        if (!canvas) return null;
        const bounds = canvas.getBoundingClientRect();
        const ratio = Math.max(1, Math.min(global.devicePixelRatio || 1, 2));
        const width = Math.max(320, Math.floor(bounds.width));
        const height = Math.max(320, Math.floor(bounds.height));
        if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
            canvas.width = width * ratio;
            canvas.height = height * ratio;
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        return { ctx, width, height };
    }

    function visibleFibers(cable) {
        return (cable.fibers || []).slice(0, 576);
    }

    function cableNodeHeight(cable) {
        const count = visibleFibers(cable).length;
        const rows = Math.max(1, Math.ceil(count / NODE.fiberColumns));
        return NODE.cableHeader + 36 + rows * (NODE.fiberSize + NODE.fiberGap);
    }

    function cableSide(session, cable, index) {
        if (Number(cable.destination_id) === Number(session.elementId)) return "left";
        if (Number(cable.origin_id) === Number(session.elementId)) return "right";
        return index % 2 === 0 ? "left" : "right";
    }

    function defaultCablePosition(session, cable, index, list) {
        const side = cableSide(session, cable, index);
        let y = 50;
        list.slice(0, index).forEach((previous, previousIndex) => {
            if (cableSide(session, previous, previousIndex) === side) y += cableNodeHeight(previous) + 34;
        });
        return { x: side === "left" ? 50 : 1010, y };
    }

    function splitterHeight(splitter) {
        return 82 + Math.max(1, splitter.output_ports || splitter.ports?.length || 1) * NODE.splitterPortGap;
    }

    function defaultSplitterPosition(index, splitters) {
        let y = 90;
        splitters.slice(0, index).forEach((previous) => { y += splitterHeight(previous) + 36; });
        return { x: 530, y };
    }

    function endpointSelected(session, endpoint) {
        return stateApi().endpointKey(session.selection.pendingEndpoint) === stateApi().endpointKey(endpoint);
    }

    function drawEndpoint(ctx, point, endpoint, session, occupied, color, hitboxes, endpointPoints) {
        const selected = endpointSelected(session, endpoint);
        ctx.save();
        ctx.beginPath();
        ctx.arc(point.x, point.y, selected ? 8 : occupied ? 6.5 : 5.5, 0, Math.PI * 2);
        ctx.fillStyle = occupied ? color : "#07111e";
        ctx.fill();
        ctx.lineWidth = selected ? 3 : 2;
        ctx.strokeStyle = selected ? "#f8e16c" : color;
        ctx.stroke();
        if (selected) {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 12, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(248, 225, 108, .42)";
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        ctx.restore();
        const key = stateApi().endpointKey(endpoint);
        endpointPoints.set(key, point);
        hitboxes.push({ type: "endpoint", endpoint, x: point.x - 11, y: point.y - 11, width: 22, height: 22 });
    }

    function drawCable(ctx, session, cable, index, list, hitboxes, endpointPoints) {
        const key = `cable:${cable.id}`;
        const node = ensureNode(session, key, defaultCablePosition(session, cable, index, list));
        const height = cableNodeHeight(cable);
        const selected = Number(session.selection.cableId) === Number(cable.id);
        const side = cableSide(session, cable, index);
        ctx.save();
        roundedRect(ctx, node.x, node.y, NODE.cableWidth, height, 13);
        ctx.fillStyle = "#0b1a2b";
        ctx.fill();
        ctx.lineWidth = selected ? 3 : 1.5;
        ctx.strokeStyle = selected ? "#42d6b5" : side === "left" ? "#3e6d98" : "#3f8b73";
        ctx.stroke();
        roundedRect(ctx, node.x + 1, node.y + 1, NODE.cableWidth - 2, NODE.cableHeader, 12);
        ctx.fillStyle = side === "left" ? "#132a43" : "#123229";
        ctx.fill();
        ctx.fillStyle = "#f4f8ff";
        ctx.font = "700 12px system-ui";
        ctx.fillText(truncate(cable.name || `Cabo ${cable.id}`, 21), node.x + 11, node.y + 18);
        ctx.fillStyle = "#91a8c3";
        ctx.font = "10px system-ui";
        const relation = cable.requires_cut ? "passagem · cortar" : cable.relation_action === "pass" ? "passagem" : side === "left" ? "entrada" : "saída";
        ctx.fillText(`${(cable.fibers || []).length} FO · ${relation}`, node.x + 11, node.y + 34);

        const fibers = visibleFibers(cable);
        fibers.forEach((fiber, fiberIndex) => {
            const col = fiberIndex % NODE.fiberColumns;
            const row = Math.floor(fiberIndex / NODE.fiberColumns);
            const x = node.x + 13 + col * (NODE.fiberSize + NODE.fiberGap + 8);
            const y = node.y + 58 + row * (NODE.fiberSize + NODE.fiberGap);
            const point = { x: x + NODE.fiberSize / 2, y: y + NODE.fiberSize / 2 };
            drawEndpoint(
                ctx,
                point,
                { kind: "fiber", id: Number(fiber.id) },
                session,
                stateApi().isFiberUsed(session, fiber.id),
                fiber.color_hex || "#8fb4d8",
                hitboxes,
                endpointPoints,
            );
        });
        if ((cable.fibers || []).length > fibers.length) {
            ctx.fillStyle = "#91a8c3";
            ctx.font = "9px system-ui";
            ctx.fillText(`+${cable.fibers.length - fibers.length} fibras disponíveis no painel`, node.x + 11, node.y + height - 8);
        }
        hitboxes.unshift({ type: "cable", id: cable.id, key, x: node.x, y: node.y, width: NODE.cableWidth, height });
        ctx.restore();
    }

    function drawSplitter(ctx, session, splitter, index, splitters, hitboxes, endpointPoints) {
        const key = `splitter:${splitter.id}`;
        const node = ensureNode(session, key, defaultSplitterPosition(index, splitters));
        const height = splitterHeight(splitter);
        const selected = Number(session.selection.splitterId) === Number(splitter.id);
        ctx.save();
        roundedRect(ctx, node.x, node.y, NODE.splitterWidth, height, 13);
        ctx.fillStyle = "#10253d";
        ctx.fill();
        ctx.strokeStyle = selected ? "#42d6b5" : "#41698e";
        ctx.lineWidth = selected ? 3 : 1.5;
        ctx.stroke();
        ctx.fillStyle = "#d9e8f8";
        ctx.font = "700 12px system-ui";
        ctx.fillText(`Splitter ${splitter.ratio}`, node.x + 13, node.y + 22);
        ctx.fillStyle = "#8da7c3";
        ctx.font = "10px system-ui";
        ctx.fillText(`${splitter.output_ports || splitter.ports?.length || 0} saída(s)`, node.x + 13, node.y + 40);

        const input = { x: node.x, y: node.y + 61 };
        drawEndpoint(
            ctx,
            input,
            { kind: "splitter-input", id: Number(splitter.id) },
            session,
            Boolean(splitter.input_fiber_id || splitter.input_splitter_port_id),
            "#42d6b5",
            hitboxes,
            endpointPoints,
        );
        (splitter.ports || []).forEach((port, portIndex) => {
            const point = { x: node.x + NODE.splitterWidth, y: node.y + 66 + portIndex * NODE.splitterPortGap };
            drawEndpoint(
                ctx,
                point,
                { kind: "splitter-output", id: Number(port.id), splitterId: Number(splitter.id) },
                session,
                stateApi().endpointOccupied(session, { kind: "splitter-output", id: port.id }),
                "#6fb7ff",
                hitboxes,
                endpointPoints,
            );
            ctx.fillStyle = "#a9bdd3";
            ctx.font = "9px system-ui";
            ctx.textAlign = "right";
            ctx.fillText(`P${port.number}`, point.x - 11, point.y + 3);
            ctx.textAlign = "left";
        });
        hitboxes.unshift({ type: "splitter", id: splitter.id, key, x: node.x, y: node.y, width: NODE.splitterWidth, height });
        ctx.restore();
    }

    function drawLink(ctx, start, end, color, width = 2, dashed = false) {
        if (!start || !end) return;
        ctx.save();
        if (dashed) ctx.setLineDash([7, 5]);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        const direction = end.x >= start.x ? 1 : -1;
        const bend = Math.max(42, Math.abs(end.x - start.x) * 0.38);
        ctx.bezierCurveTo(start.x + bend * direction, start.y, end.x - bend * direction, end.y, end.x, end.y);
        ctx.stroke();
        ctx.restore();
    }

    function drawSavedLinks(ctx, session, endpointPoints) {
        (session.optical.splices || []).forEach((splice) => {
            drawLink(
                ctx,
                endpointPoints.get(`fiber:${Number(splice.input_fiber_id)}`),
                endpointPoints.get(`fiber:${Number(splice.output_fiber_id)}`),
                "#ffca5c",
                2.5,
            );
        });
        (session.optical.splitter_links || []).forEach((splitter) => {
            const input = endpointPoints.get(`splitter-input:${Number(splitter.splitter_id)}`);
            if (splitter.input_fiber_id) {
                drawLink(ctx, endpointPoints.get(`fiber:${Number(splitter.input_fiber_id)}`), input, "#42d6b5", 2.5);
            } else if (splitter.input_splitter_port_id) {
                drawLink(ctx, endpointPoints.get(`splitter-output:${Number(splitter.input_splitter_port_id)}`), input, "#9b8cff", 2.4, true);
            }
            (splitter.ports || []).forEach((port) => {
                if (!port.output_fiber_id) return;
                drawLink(
                    ctx,
                    endpointPoints.get(`splitter-output:${Number(port.id)}`),
                    endpointPoints.get(`fiber:${Number(port.output_fiber_id)}`),
                    "#6fb7ff",
                    2.3,
                );
            });
        });
    }

    function drawDraft(ctx, session, endpointPoints) {
        const draft = session.connectionDraft;
        if (!draft?.start || !draft.currentWorld) return;
        const start = endpointPoints.get(stateApi().endpointKey(draft.start));
        if (!start) return;
        drawLink(ctx, start, draft.currentWorld, "#f8e16c", 2.5, true);
        ctx.beginPath();
        ctx.arc(draft.currentWorld.x, draft.currentWorld.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = "#f8e16c";
        ctx.fill();
    }

    function drawNotes(ctx, session, hitboxes) {
        ctx.font = "11px system-ui";
        (session.layout.notes || []).forEach((note) => {
            const width = 210;
            const lines = wrapText(ctx, note.text, width - 22);
            const height = 32 + lines.length * 16;
            roundedRect(ctx, note.x, note.y, width, height, 11);
            ctx.fillStyle = "rgba(64, 50, 18, .96)";
            ctx.fill();
            ctx.strokeStyle = "#d6a93e";
            ctx.stroke();
            ctx.fillStyle = "#ffe9a8";
            lines.forEach((line, index) => ctx.fillText(line, note.x + 11, note.y + 23 + index * 16));
            hitboxes.unshift({ type: "note", id: note.id, key: `note:${note.id}`, x: note.x, y: note.y, width, height });
        });
    }

    function render(session) {
        if (session.disposed || !session.canvas) return;
        const fitted = fitCanvas(session);
        if (!fitted) return;
        const { ctx, width, height } = fitted;
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#06111d";
        ctx.fillRect(0, 0, width, height);
        ctx.save();
        const { zoom, panX, panY } = session.layout.viewport;
        ctx.translate(panX, panY);
        ctx.scale(zoom, zoom);
        drawGrid(ctx, width / zoom, height / zoom, panX / zoom, panY / zoom);
        const hitboxes = [];
        const endpointPoints = new Map();
        const cables = session.optical.cables || [];
        cables.forEach((cable, index) => drawCable(ctx, session, cable, index, cables, hitboxes, endpointPoints));
        const splitters = stateApi().splitters(session);
        splitters.forEach((splitter, index) => drawSplitter(ctx, session, splitter, index, splitters, hitboxes, endpointPoints));
        drawSavedLinks(ctx, session, endpointPoints);
        drawDraft(ctx, session, endpointPoints);
        drawNotes(ctx, session, hitboxes);
        ctx.restore();
        session.renderCache = { hitboxes, endpointPoints, width, height };
        session.renderVersion += 1;
    }

    function drawGrid(ctx, width, height, offsetX, offsetY) {
        const size = 28;
        ctx.save();
        ctx.strokeStyle = "rgba(92, 128, 164, .10)";
        ctx.lineWidth = 1;
        const startX = Math.floor(-offsetX / size) * size - size;
        const startY = Math.floor(-offsetY / size) * size - size;
        for (let x = startX; x < width - offsetX + size; x += size) {
            ctx.beginPath();
            ctx.moveTo(x, -offsetY - size);
            ctx.lineTo(x, height - offsetY + size);
            ctx.stroke();
        }
        for (let y = startY; y < height - offsetY + size; y += size) {
            ctx.beginPath();
            ctx.moveTo(-offsetX - size, y);
            ctx.lineTo(width - offsetX + size, y);
            ctx.stroke();
        }
        ctx.restore();
    }

    function hitTest(session, screenPoint) {
        const point = screenToWorld(session, screenPoint);
        const boxes = session.renderCache?.hitboxes || [];
        return [...boxes].reverse().find((box) => (
            point.x >= box.x && point.x <= box.x + box.width
            && point.y >= box.y && point.y <= box.y + box.height
        )) || null;
    }

    function hitTestEndpoint(session, screenPoint) {
        const hit = hitTest(session, screenPoint);
        return hit?.type === "endpoint" ? hit.endpoint : null;
    }

    function moveNode(session, hitbox, screenPoint, offset) {
        const point = screenToWorld(session, screenPoint);
        if (hitbox.type === "note") {
            const note = session.layout.notes.find((item) => item.id === hitbox.id);
            if (note) {
                note.x = point.x - offset.x;
                note.y = point.y - offset.y;
            }
            return;
        }
        session.layout.nodes[hitbox.key] = { x: point.x - offset.x, y: point.y - offset.y };
    }

    function organizeVertical(session) {
        session.layout.nodes = {};
        const cables = session.optical.cables || [];
        cables.forEach((cable, index) => {
            session.layout.nodes[`cable:${cable.id}`] = defaultCablePosition(session, cable, index, cables);
        });
        const splitters = stateApi().splitters(session);
        splitters.forEach((splitter, index) => {
            session.layout.nodes[`splitter:${splitter.id}`] = defaultSplitterPosition(index, splitters);
        });
        render(session);
    }

    function fitView(session) {
        render(session);
        const boxes = (session.renderCache?.hitboxes || []).filter((box) => box.type !== "endpoint");
        if (!boxes.length || !session.canvas) {
            session.layout.viewport = { zoom: 1, panX: 0, panY: 0 };
            render(session);
            return;
        }
        const minX = Math.min(...boxes.map((box) => box.x));
        const minY = Math.min(...boxes.map((box) => box.y));
        const maxX = Math.max(...boxes.map((box) => box.x + box.width));
        const maxY = Math.max(...boxes.map((box) => box.y + box.height));
        const rect = session.canvas.getBoundingClientRect();
        const padding = 46;
        const contentWidth = Math.max(1, maxX - minX);
        const contentHeight = Math.max(1, maxY - minY);
        const zoom = Math.max(0.35, Math.min(1.25,
            (Math.max(320, rect.width) - padding * 2) / contentWidth,
            (Math.max(320, rect.height) - padding * 2) / contentHeight,
        ));
        session.layout.viewport = {
            zoom,
            panX: padding - minX * zoom,
            panY: padding - minY * zoom,
        };
        render(session);
    }

    function resetView(session) {
        fitView(session);
    }

    function zoomAt(session, screenPoint, factor) {
        const viewport = session.layout.viewport;
        const before = screenToWorld(session, screenPoint);
        viewport.zoom = Math.max(0.35, Math.min(2.6, viewport.zoom * factor));
        viewport.panX = screenPoint.x - before.x * viewport.zoom;
        viewport.panY = screenPoint.y - before.y * viewport.zoom;
        render(session);
    }

    function setConnectionDraft(session, start, currentWorld) {
        session.connectionDraft = { start, currentWorld };
        render(session);
    }

    function clearConnectionDraft(session) {
        session.connectionDraft = null;
        render(session);
    }

    function wrapText(ctx, text, maxWidth) {
        const words = String(text || "").split(/\s+/);
        const lines = [];
        let line = "";
        words.forEach((word) => {
            const candidate = line ? `${line} ${word}` : word;
            if (ctx.measureText(candidate).width > maxWidth && line) {
                lines.push(line);
                line = word;
            } else {
                line = candidate;
            }
        });
        if (line) lines.push(line);
        return lines.slice(0, 14);
    }

    function truncate(value, max) {
        const text = String(value || "");
        return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
    }

    namespace.renderer = Object.freeze({
        render,
        hitTest,
        hitTestEndpoint,
        moveNode,
        screenToWorld,
        worldToScreen,
        resetView,
        fitView,
        zoomAt,
        organizeVertical,
        setConnectionDraft,
        clearConnectionDraft,
    });
})(window);
