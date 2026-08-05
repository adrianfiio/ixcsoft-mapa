(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    const stateApi = () => namespace.state;

    const NODE = {
        cableWidth: 184,
        cableHeader: 30,
        fiberSize: 12,
        fiberGap: 5,
        splitterWidth: 156,
        splitterPortGap: 19,
        trayPadding: 26,
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

    function cableNodeHeight(cable) {
        const count = Math.min((cable.fibers || []).length, 288);
        const rows = Math.max(1, Math.ceil(count / 12));
        return NODE.cableHeader + 30 + rows * (NODE.fiberSize + NODE.fiberGap);
    }

    function defaultCablePosition(index, count, canvasHeight) {
        const left = index % 2 === 0;
        const row = Math.floor(index / 2);
        const rows = Math.max(1, Math.ceil(count / 2));
        const spacing = Math.max(130, (Math.max(canvasHeight, 620) - 100) / rows);
        return { x: left ? 50 : 860, y: 50 + row * spacing };
    }

    function defaultSplitterPosition(index, trayIndex) {
        return { x: 410 + (index % 2) * 210, y: 120 + trayIndex * 240 + Math.floor(index / 2) * 170 };
    }

    function drawCable(ctx, session, cable, index, total, viewportHeight, hitboxes, fiberPoints) {
        const key = `cable:${cable.id}`;
        const node = ensureNode(session, key, defaultCablePosition(index, total, viewportHeight));
        const height = cableNodeHeight(cable);
        const selected = Number(session.selection.cableId) === Number(cable.id);
        ctx.save();
        roundedRect(ctx, node.x, node.y, NODE.cableWidth, height, 12);
        ctx.fillStyle = "#0d1b2c";
        ctx.fill();
        ctx.lineWidth = selected ? 3 : 1.5;
        ctx.strokeStyle = selected ? "#42d6b5" : "#35506d";
        ctx.stroke();
        ctx.fillStyle = "#132842";
        roundedRect(ctx, node.x + 1, node.y + 1, NODE.cableWidth - 2, NODE.cableHeader, 11);
        ctx.fill();
        ctx.fillStyle = "#f4f8ff";
        ctx.font = "600 13px system-ui";
        ctx.fillText(truncate(cable.name || `Cabo ${cable.id}`, 22), node.x + 12, node.y + 20);
        ctx.fillStyle = "#91a8c3";
        ctx.font = "11px system-ui";
        const relation = cable.requires_cut ? "passagem · corte necessário" : cable.relation_action === "pass" ? "passagem" : "conectado";
        ctx.fillText(`${(cable.fibers || []).length} fibras · ${relation}`, node.x + 12, node.y + 47);

        const visibleFibers = (cable.fibers || []).slice(0, 288);
        visibleFibers.forEach((fiber, fiberIndex) => {
            const col = fiberIndex % 12;
            const row = Math.floor(fiberIndex / 12);
            const x = node.x + 12 + col * (NODE.fiberSize + NODE.fiberGap);
            const y = node.y + 60 + row * (NODE.fiberSize + NODE.fiberGap);
            const used = stateApi().isFiberUsed(session, fiber.id);
            ctx.beginPath();
            ctx.arc(x + NODE.fiberSize / 2, y + NODE.fiberSize / 2, NODE.fiberSize / 2, 0, Math.PI * 2);
            ctx.fillStyle = fiber.color_hex || "#a8b1bd";
            ctx.fill();
            ctx.lineWidth = used ? 2 : 1;
            ctx.strokeStyle = used ? "#ffca5c" : "#08111d";
            ctx.stroke();
            fiberPoints.set(Number(fiber.id), { x: x + NODE.fiberSize / 2, y: y + NODE.fiberSize / 2 });
        });
        if ((cable.fibers || []).length > 288) {
            ctx.fillStyle = "#91a8c3";
            ctx.font = "10px system-ui";
            ctx.fillText(`+${cable.fibers.length - 288} fibras no painel`, node.x + 12, node.y + height - 8);
        }
        hitboxes.push({ type: "cable", id: cable.id, key, x: node.x, y: node.y, width: NODE.cableWidth, height });
        ctx.restore();
    }

    function drawTray(ctx, session, tray, trayIndex, hitboxes, splitterPoints) {
        const splitters = (tray.splitters || []).map((item, index) => ({ item, index }));
        const positions = splitters.map(({ item, index }) => ensureNode(
            session,
            `splitter:${item.id}`,
            defaultSplitterPosition(index, trayIndex),
        ));
        const minX = Math.min(...positions.map((p) => p.x), 360) - NODE.trayPadding;
        const minY = Math.min(...positions.map((p) => p.y), 80 + trayIndex * 240) - 44;
        const maxX = Math.max(...positions.map((p) => p.x + NODE.splitterWidth), 720) + NODE.trayPadding;
        const maxY = Math.max(...positions.map((p, index) => p.y + splitterHeight(splitters[index]?.item)), 220 + trayIndex * 240) + NODE.trayPadding;
        ctx.save();
        ctx.setLineDash([8, 7]);
        roundedRect(ctx, minX, minY, maxX - minX, maxY - minY, 18);
        ctx.fillStyle = "rgba(18, 36, 58, 0.48)";
        ctx.fill();
        ctx.strokeStyle = "#385a7d";
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#bcd0e8";
        ctx.font = "600 12px system-ui";
        ctx.fillText(`${tray.name || `Bandeja ${tray.number}`} · ${tray.splice_count || 0} fusões`, minX + 14, minY + 23);
        ctx.restore();
        splitters.forEach(({ item, index }) => drawSplitter(ctx, session, item, tray, index, trayIndex, hitboxes, splitterPoints));
    }

    function splitterHeight(splitter) {
        return 72 + Math.max(1, splitter.output_ports || splitter.ports?.length || 1) * NODE.splitterPortGap;
    }

    function drawSplitter(ctx, session, splitter, tray, index, trayIndex, hitboxes, splitterPoints) {
        const key = `splitter:${splitter.id}`;
        const node = ensureNode(session, key, defaultSplitterPosition(index, trayIndex));
        const height = splitterHeight(splitter);
        const selected = Number(session.selection.splitterId) === Number(splitter.id);
        ctx.save();
        roundedRect(ctx, node.x, node.y, NODE.splitterWidth, height, 12);
        ctx.fillStyle = "#10253d";
        ctx.fill();
        ctx.strokeStyle = selected ? "#42d6b5" : "#41698e";
        ctx.lineWidth = selected ? 3 : 1.5;
        ctx.stroke();
        ctx.fillStyle = "#d9e8f8";
        ctx.font = "700 12px system-ui";
        ctx.fillText(`Splitter ${splitter.ratio}`, node.x + 12, node.y + 22);
        ctx.fillStyle = "#8da7c3";
        ctx.font = "10px system-ui";
        ctx.fillText(tray.name || `Bandeja ${tray.number}`, node.x + 12, node.y + 40);

        const input = { x: node.x, y: node.y + 55 };
        drawPort(ctx, input, "#42d6b5", Boolean(splitter.input_fiber_id || splitter.input_splitter_port_id));
        splitterPoints.set(`splitter-input:${splitter.id}`, input);
        (splitter.ports || []).forEach((port, portIndex) => {
            const point = { x: node.x + NODE.splitterWidth, y: node.y + 60 + portIndex * NODE.splitterPortGap };
            drawPort(ctx, point, "#6fb7ff", Boolean(port.output_fiber_id));
            ctx.fillStyle = "#a9bdd3";
            ctx.font = "9px system-ui";
            ctx.textAlign = "right";
            ctx.fillText(String(port.number), point.x - 10, point.y + 3);
            ctx.textAlign = "left";
            splitterPoints.set(`splitter-port:${port.id}`, point);
        });
        hitboxes.push({ type: "splitter", id: splitter.id, key, x: node.x, y: node.y, width: NODE.splitterWidth, height });
        ctx.restore();
    }

    function drawPort(ctx, point, color, occupied) {
        ctx.beginPath();
        ctx.arc(point.x, point.y, occupied ? 6 : 5, 0, Math.PI * 2);
        ctx.fillStyle = occupied ? color : "#0a1421";
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    function drawLink(ctx, start, end, color, width = 2, dashed = false) {
        if (!start || !end) return;
        ctx.save();
        if (dashed) ctx.setLineDash([7, 5]);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        const bend = Math.max(40, Math.abs(end.x - start.x) * 0.42);
        ctx.bezierCurveTo(start.x + bend, start.y, end.x - bend, end.y, end.x, end.y);
        ctx.stroke();
        ctx.restore();
    }

    function drawLinks(ctx, session, fiberPoints, splitterPoints) {
        (session.optical.splices || []).forEach((splice) => {
            drawLink(
                ctx,
                fiberPoints.get(Number(splice.input_fiber_id)),
                fiberPoints.get(Number(splice.output_fiber_id)),
                "#ffca5c",
                2.4,
            );
        });
        (session.optical.splitter_links || []).forEach((splitter) => {
            const inputPoint = splitterPoints.get(`splitter-input:${splitter.splitter_id}`);
            if (splitter.input_fiber_id) {
                drawLink(ctx, fiberPoints.get(Number(splitter.input_fiber_id)), inputPoint, "#42d6b5", 2.4);
            } else if (splitter.input_splitter_port_id) {
                drawLink(
                    ctx,
                    splitterPoints.get(`splitter-port:${splitter.input_splitter_port_id}`),
                    inputPoint,
                    "#9b8cff",
                    2.3,
                    true,
                );
            }
            (splitter.ports || []).forEach((port) => {
                if (!port.output_fiber_id) return;
                drawLink(
                    ctx,
                    splitterPoints.get(`splitter-port:${port.id}`),
                    fiberPoints.get(Number(port.output_fiber_id)),
                    "#6fb7ff",
                    2.2,
                );
            });
        });
    }

    function drawNotes(ctx, session, hitboxes) {
        (session.layout.notes || []).forEach((note) => {
            const width = 190;
            const lines = wrapText(ctx, note.text, width - 20);
            const height = 28 + lines.length * 16;
            roundedRect(ctx, note.x, note.y, width, height, 10);
            ctx.fillStyle = "rgba(68, 53, 18, 0.96)";
            ctx.fill();
            ctx.strokeStyle = "#d6a93e";
            ctx.stroke();
            ctx.fillStyle = "#ffe9a8";
            ctx.font = "11px system-ui";
            lines.forEach((line, index) => ctx.fillText(line, note.x + 10, note.y + 22 + index * 16));
            hitboxes.push({ type: "note", id: note.id, key: `note:${note.id}`, x: note.x, y: note.y, width, height });
        });
    }

    function render(session) {
        if (session.disposed || !session.canvas) return;
        const fitted = fitCanvas(session);
        if (!fitted) return;
        const { ctx, width, height } = fitted;
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#07111e";
        ctx.fillRect(0, 0, width, height);
        ctx.save();
        const { zoom, panX, panY } = session.layout.viewport;
        ctx.translate(panX, panY);
        ctx.scale(zoom, zoom);
        drawGrid(ctx, width / zoom, height / zoom, panX / zoom, panY / zoom);
        const hitboxes = [];
        const fiberPoints = new Map();
        const splitterPoints = new Map();
        (session.optical.cables || []).forEach((cable, index, list) => {
            drawCable(ctx, session, cable, index, list.length, height / zoom, hitboxes, fiberPoints);
        });
        stateApi().trays(session).forEach((tray, trayIndex) => {
            drawTray(ctx, session, tray, trayIndex, hitboxes, splitterPoints);
        });
        drawLinks(ctx, session, fiberPoints, splitterPoints);
        drawNotes(ctx, session, hitboxes);
        ctx.restore();
        session.renderCache = { hitboxes, fiberPoints, splitterPoints, width, height };
        session.renderVersion += 1;
    }

    function drawGrid(ctx, width, height, offsetX, offsetY) {
        const size = 28;
        ctx.save();
        ctx.strokeStyle = "rgba(92, 128, 164, 0.10)";
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
        session.layout.nodes[hitbox.key] = {
            x: point.x - offset.x,
            y: point.y - offset.y,
        };
    }

    function fitView(session) {
        render(session);
        const boxes = session.renderCache?.hitboxes || [];
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
        const padding = 42;
        const contentWidth = Math.max(1, maxX - minX);
        const contentHeight = Math.max(1, maxY - minY);
        const zoom = Math.max(0.4, Math.min(1.25,
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
        viewport.zoom = Math.max(0.4, Math.min(2.4, viewport.zoom * factor));
        viewport.panX = screenPoint.x - before.x * viewport.zoom;
        viewport.panY = screenPoint.y - before.y * viewport.zoom;
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
        return lines.slice(0, 8);
    }

    function truncate(value, max) {
        const text = String(value || "");
        return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
    }

    namespace.renderer = Object.freeze({
        render,
        hitTest,
        moveNode,
        screenToWorld,
        worldToScreen,
        resetView,
        fitView,
        zoomAt,
    });
})(window);
