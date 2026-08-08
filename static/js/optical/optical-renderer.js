(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    const stateApi = () => namespace.state;

    const NODE = {
        ctoCableWidth: 168,
        distributionCableWidth: 176,
        cableHeader: 48,
        fiberSize: 13,
        fiberGap: 7,
        distributionFiberPitch: 17,
        splitterWidth: 178,
        splitterPortGap: 24,
    };

    function cableMetrics(session) {
        // MAP v0.75.39: CTO, CEO e CDO compartilham o mesmo idioma visual:
        // cabos verticais e uma fibra por linha. As portas de atendimento da
        // CTO continuam no painel lateral, separadas da fibra física.
        return stateApi().isOpticalBox(session)
            ? {
                width: stateApi().isDistributionBox(session) ? NODE.distributionCableWidth : NODE.ctoCableWidth,
                columns: 1,
                maxFibers: 576,
                vertical: true,
            }
            : { width: NODE.ctoCableWidth, columns: 6, maxFibers: 576, vertical: false };
    }

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

    function visibleFibers(session, cable) {
        return (cable.fibers || []).slice(0, cableMetrics(session).maxFibers);
    }

    function cableNodeHeight(session, cable) {
        const metrics = cableMetrics(session);
        const count = visibleFibers(session, cable).length;
        if (metrics.vertical) return NODE.cableHeader + 22 + Math.max(1, count) * NODE.distributionFiberPitch;
        const rows = Math.max(1, Math.ceil(count / metrics.columns));
        return NODE.cableHeader + 36 + rows * (NODE.fiberSize + NODE.fiberGap);
    }

    function cableTopologyRelation(session, cable) {
        if (Number(cable.destination_id) === Number(session.elementId)) return "input";
        if (Number(cable.origin_id) === Number(session.elementId)) return "output";
        if (cable.requires_cut) return "cut";
        if (String(cable.relation_action || "").toLowerCase() === "pass") return "pass";
        return "unknown";
    }

    function cableSide(session, cable, index) {
        if (stateApi().isOpticalBox(session)) {
            const saved = session.layout.nodes[`cable:${cable.id}`];
            if (saved && Number.isFinite(Number(saved.x))) return Number(saved.x) < 560 ? "left" : "right";
            const relation = cableTopologyRelation(session, cable);
            if (relation === "input") return "left";
            if (relation === "output") return "right";
            return index % 2 === 0 ? "left" : "right";
        }
        if (Number(cable.destination_id) === Number(session.elementId)) return "left";
        if (Number(cable.origin_id) === Number(session.elementId)) return "right";
        return index % 2 === 0 ? "left" : "right";
    }

    function defaultCablePosition(session, cable, index, list) {
        const side = cableSide(session, cable, index);
        let y = 54;
        list.slice(0, index).forEach((previous, previousIndex) => {
            if (cableSide(session, previous, previousIndex) === side) {
                y += cableNodeHeight(session, previous) + 30;
            }
        });
        if (stateApi().isOpticalBox(session)) return { x: side === "left" ? 62 : 866, y };
        return { x: side === "left" ? 58 : 1010, y };
    }

    function splitterHeight(splitter) {
        return 82 + Math.max(1, splitter.output_ports || splitter.ports?.length || 1) * NODE.splitterPortGap;
    }

    function defaultSplitterPosition(index, splitters, session = null) {
        let y = 90;
        splitters.slice(0, index).forEach((previous) => { y += splitterHeight(previous) + 36; });
        return { x: session && stateApi().isOpticalBox(session) ? 476 : 526, y };
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
        const metrics = cableMetrics(session);
        const key = `cable:${cable.id}`;
        const node = ensureNode(session, key, defaultCablePosition(session, cable, index, list));
        const height = cableNodeHeight(session, cable);
        const selected = Number(session.selection.cableId) === Number(cable.id);
        const side = cableSide(session, cable, index);
        ctx.save();
        roundedRect(ctx, node.x, node.y, metrics.width, height, 13);
        ctx.fillStyle = "#0b1a2b";
        ctx.fill();
        ctx.lineWidth = selected ? 3 : 1.5;
        ctx.strokeStyle = selected ? "#42d6b5" : side === "left" ? "#3e6d98" : "#3f8b73";
        ctx.stroke();
        roundedRect(ctx, node.x + 1, node.y + 1, metrics.width - 2, NODE.cableHeader, 12);
        ctx.fillStyle = side === "left" ? "#132a43" : "#123229";
        ctx.fill();
        ctx.fillStyle = "#f4f8ff";
        ctx.font = "700 12px system-ui";
        ctx.fillText(truncate(cable.name || `Cabo ${cable.id}`, stateApi().isDistributionBox(session) ? 17 : 21), node.x + 11, node.y + 18);
        ctx.fillStyle = "#91a8c3";
        ctx.font = "10px system-ui";
        const topology = cableTopologyRelation(session, cable);
        const relation = topology === "cut" ? "passagem · cortar"
            : topology === "pass" ? "passagem"
            : topology === "input" ? "entrada"
            : topology === "output" ? "saída"
            : side === "left" ? "entrada visual" : "saída visual";
        ctx.fillText(`${(cable.fibers || []).length} FO · ${relation}`, node.x + 11, node.y + 34);

        const fibers = visibleFibers(session, cable);
        if (metrics.vertical) {
            const rightSide = side === "right";
            const trunkX = rightSide ? node.x + 18 : node.x + metrics.width - 18;
            const endpointX = rightSide ? node.x : node.x + metrics.width;
            const numberX = rightSide ? node.x + 18 : node.x + metrics.width - 18;
            ctx.beginPath();
            ctx.moveTo(trunkX, node.y + NODE.cableHeader + 8);
            ctx.lineTo(trunkX, node.y + height - 10);
            ctx.strokeStyle = "rgba(66, 214, 181, .72)";
            ctx.lineWidth = 3;
            ctx.stroke();
            fibers.forEach((fiber, fiberIndex) => {
                const point = {
                    x: endpointX,
                    y: node.y + NODE.cableHeader + 18 + fiberIndex * NODE.distributionFiberPitch,
                };
                ctx.fillStyle = "#dceaf7";
                ctx.font = "700 8px system-ui";
                ctx.textAlign = rightSide ? "left" : "right";
                ctx.fillText(String(fiber.number), rightSide ? numberX + 13 : numberX - 13, point.y + 3);
                ctx.textAlign = "left";
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
        } else {
            const cellWidth = (metrics.width - 26) / metrics.columns;
            fibers.forEach((fiber, fiberIndex) => {
                const col = fiberIndex % metrics.columns;
                const row = Math.floor(fiberIndex / metrics.columns);
                const point = {
                    x: node.x + 13 + cellWidth * col + cellWidth / 2,
                    y: node.y + 58 + row * (NODE.fiberSize + NODE.fiberGap) + NODE.fiberSize / 2,
                };
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
        }
        if ((cable.fibers || []).length > fibers.length) {
            ctx.fillStyle = "#91a8c3";
            ctx.font = "9px system-ui";
            ctx.fillText(`+${cable.fibers.length - fibers.length} fibras no painel`, node.x + 11, node.y + height - 8);
        }
        hitboxes.unshift({ type: "cable", id: cable.id, key, x: node.x, y: node.y, width: metrics.width, height });
        ctx.restore();
    }

    function drawSplitter(ctx, session, splitter, index, splitters, hitboxes, endpointPoints) {
        const key = `splitter:${splitter.id}`;
        const node = ensureNode(session, key, defaultSplitterPosition(index, splitters, session));
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

    function distancePointToSegment(point, a, b) {
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const lengthSquared = dx * dx + dy * dy;
        if (!lengthSquared) return Math.hypot(point.x - a.x, point.y - a.y);
        const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / lengthSquared));
        return Math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy));
    }

    function cubicPoint(start, c1, c2, end, t) {
        const mt = 1 - t;
        return {
            x: mt ** 3 * start.x + 3 * mt ** 2 * t * c1.x + 3 * mt * t ** 2 * c2.x + t ** 3 * end.x,
            y: mt ** 3 * start.y + 3 * mt ** 2 * t * c1.y + 3 * mt * t ** 2 * c2.y + t ** 3 * end.y,
        };
    }

    function autoCurveSamples(start, end) {
        const direction = end.x >= start.x ? 1 : -1;
        const bend = Math.max(42, Math.abs(end.x - start.x) * 0.38);
        const c1 = { x: start.x + bend * direction, y: start.y };
        const c2 = { x: end.x - bend * direction, y: end.y };
        return Array.from({ length: 31 }, (_, index) => cubicPoint(start, c1, c2, end, index / 30));
    }

    function orthogonalPoints(start, end, waypoints = []) {
        if (!waypoints.length) {
            const middleX = (start.x + end.x) / 2;
            return [start, { x: middleX, y: start.y }, { x: middleX, y: end.y }, end];
        }
        const result = [start];
        waypoints.forEach((point) => {
            const previous = result[result.length - 1];
            result.push({ x: point.x, y: previous.y }, { x: point.x, y: point.y });
        });
        const previous = result[result.length - 1];
        result.push({ x: end.x, y: previous.y }, end);
        return result.filter((item, index, list) => index === 0 || item.x !== list[index - 1].x || item.y !== list[index - 1].y);
    }

    function smoothManualSamples(points) {
        if (points.length < 3) return points;
        const samples = [points[0]];
        for (let index = 0; index < points.length - 1; index += 1) {
            const start = points[index];
            const end = points[index + 1];
            const previous = points[Math.max(0, index - 1)];
            const next = points[Math.min(points.length - 1, index + 2)];
            const c1 = { x: start.x + (end.x - previous.x) / 6, y: start.y + (end.y - previous.y) / 6 };
            const c2 = { x: end.x - (next.x - start.x) / 6, y: end.y - (next.y - start.y) / 6 };
            for (let step = 1; step <= 12; step += 1) samples.push(cubicPoint(start, c1, c2, end, step / 12));
        }
        return samples;
    }

    function linkSamples(route, start, end) {
        if (route.style === "straight") return [start, end];
        if (route.mode === "manual" && route.points.length) {
            const points = [start, ...route.points, end];
            if (route.style === "orthogonal") return orthogonalPoints(start, end, route.points);
            return smoothManualSamples(points);
        }
        if (route.style === "orthogonal") return orthogonalPoints(start, end);
        return autoCurveSamples(start, end);
    }

    function linkPaint(ctx, start, end, colors) {
        const first = colors?.[0] || "#8fb4d8";
        const second = colors?.[1] || first;
        if (first.toLowerCase() === second.toLowerCase()) return first;
        const gradient = ctx.createLinearGradient(start.x, start.y, end.x, end.y);
        gradient.addColorStop(0, first);
        gradient.addColorStop(0.48, first);
        gradient.addColorStop(0.52, second);
        gradient.addColorStop(1, second);
        return gradient;
    }

    function drawSampledLink(ctx, samples, paint, width, dashed) {
        if (samples.length < 2) return;
        ctx.save();
        if (dashed) ctx.setLineDash([7, 5]);
        ctx.strokeStyle = paint;
        ctx.lineWidth = width;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(samples[0].x, samples[0].y);
        samples.slice(1).forEach((point) => ctx.lineTo(point.x, point.y));
        ctx.stroke();
        ctx.restore();
    }

    function drawSavedLinks(ctx, session, endpointPoints, linkHits, hitboxes) {
        stateApi().savedLinks(session).forEach((link) => {
            const start = endpointPoints.get(stateApi().endpointKey(link.start));
            const end = endpointPoints.get(stateApi().endpointKey(link.end));
            if (!start || !end) return;
            const route = stateApi().linkRoute(session, link.id);
            const samples = linkSamples(route, start, end);
            const selected = session.selection.linkId === link.id || session.editingLinkId === link.id;
            drawSampledLink(ctx, samples, linkPaint(ctx, start, end, link.colors), selected ? 4.4 : 2.7, link.dashed);
            if (selected) {
                drawSampledLink(ctx, samples, "rgba(248, 225, 108, .24)", 8.5, false);
                drawSampledLink(ctx, samples, linkPaint(ctx, start, end, link.colors), 3.2, link.dashed);
            }
            const xs = samples.map((item) => item.x);
            const ys = samples.map((item) => item.y);
            linkHits.push({
                type: "link",
                id: link.id,
                link,
                samples,
                x: Math.min(...xs) - 10,
                y: Math.min(...ys) - 10,
                width: Math.max(...xs) - Math.min(...xs) + 20,
                height: Math.max(...ys) - Math.min(...ys) + 20,
            });
            if (session.editingLinkId === link.id && route.mode === "manual") {
                route.points.forEach((point, pointIndex) => {
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(point.x, point.y, 7, 0, Math.PI * 2);
                    ctx.fillStyle = "#f8e16c";
                    ctx.fill();
                    ctx.strokeStyle = "#171200";
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    ctx.restore();
                    hitboxes.push({
                        type: "link-handle",
                        id: link.id,
                        link,
                        pointIndex,
                        x: point.x - 12,
                        y: point.y - 12,
                        width: 24,
                        height: 24,
                    });
                });
            }
        });
    }

    function drawDraft(ctx, session, endpointPoints) {
        const draft = session.connectionDraft;
        if (!draft?.start || !draft.currentWorld) return;
        const start = endpointPoints.get(stateApi().endpointKey(draft.start));
        if (!start) return;
        const samples = autoCurveSamples(start, draft.currentWorld);
        drawSampledLink(ctx, samples, "#f8e16c", 2.5, true);
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
        if (stateApi().isOpticalBox(session)) drawDistributionDivider(ctx, width / zoom, height / zoom);
        const hitboxes = [];
        const linkHits = [];
        const endpointPoints = new Map();
        const cables = session.optical.cables || [];
        cables.forEach((cable, index) => drawCable(ctx, session, cable, index, cables, hitboxes, endpointPoints));
        const splitters = stateApi().splitters(session);
        splitters.forEach((splitter, index) => drawSplitter(ctx, session, splitter, index, splitters, hitboxes, endpointPoints));
        drawSavedLinks(ctx, session, endpointPoints, linkHits, hitboxes);
        drawDraft(ctx, session, endpointPoints);
        drawNotes(ctx, session, hitboxes);
        ctx.restore();
        session.renderCache = { hitboxes, linkHits, endpointPoints, width, height };
        session.renderVersion += 1;
    }


    function drawDistributionDivider(ctx, width, height) {
        // MAP_V076_REMOVE_FIXED_DIVIDER_LINE: o traço tracejado fixo aqui não
        // representava nenhuma fibra/conexão real -- era desenhado sempre,
        // independente dos dados. Mantemos só os rótulos de orientação
        // (Entrada/chegada, Saída/distribuição); as conexões reais continuam
        // desenhadas por drawSavedLinks/drawDraft, sem nenhuma mudança aqui.
        const dividerX = 560;
        ctx.save();
        ctx.fillStyle = "rgba(215, 233, 247, .9)";
        ctx.font = "700 11px system-ui";
        ctx.textAlign = "center";
        ctx.fillText("ENTRADA / CHEGADA", dividerX - 126, 24);
        ctx.fillText("SAÍDA / DISTRIBUIÇÃO", dividerX + 126, 24);
        ctx.textAlign = "left";
        ctx.restore();
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

    function hitTestLinkHandle(session, screenPoint) {
        const hit = hitTest(session, screenPoint);
        return hit?.type === "link-handle" ? hit : null;
    }

    function hitTestLink(session, screenPoint) {
        const point = screenToWorld(session, screenPoint);
        const threshold = 10 / Math.max(0.35, session.layout.viewport.zoom);
        const hits = session.renderCache?.linkHits || [];
        return [...hits].reverse().find((hit) => {
            if (point.x < hit.x || point.x > hit.x + hit.width || point.y < hit.y || point.y > hit.y + hit.height) return false;
            return hit.samples.some((sample, index) => (
                index > 0 && distancePointToSegment(point, hit.samples[index - 1], sample) <= threshold
            ));
        }) || null;
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

    function linkEndpointPositions(session, linkId) {
        const link = stateApi().linkById(session, linkId);
        const points = session.renderCache?.endpointPoints;
        if (!link || !points) return null;
        const start = points.get(stateApi().endpointKey(link.start));
        const end = points.get(stateApi().endpointKey(link.end));
        return start && end ? { link, start, end } : null;
    }

    function ensureManualRoute(session, linkId) {
        const positions = linkEndpointPositions(session, linkId);
        if (!positions) return null;
        const route = stateApi().linkRoute(session, linkId);
        if (!route.points.length) {
            const thirdX = positions.start.x + (positions.end.x - positions.start.x) / 3;
            const twoThirdX = positions.start.x + (positions.end.x - positions.start.x) * 2 / 3;
            route.points = [
                { x: thirdX, y: positions.start.y },
                { x: twoThirdX, y: positions.end.y },
            ];
        }
        route.mode = "manual";
        session.editingLinkId = String(linkId);
        session.selection.linkId = String(linkId);
        render(session);
        return route;
    }

    function autoRoute(session, linkId) {
        const route = stateApi().linkRoute(session, linkId);
        route.mode = "auto";
        route.points = [];
        if (session.editingLinkId === String(linkId)) session.editingLinkId = null;
        render(session);
    }

    function setLinkStyle(session, linkId, style) {
        const route = stateApi().linkRoute(session, linkId);
        route.style = ["curve", "orthogonal", "straight"].includes(style) ? style : "curve";
        if (route.style === "straight") {
            route.mode = "auto";
            route.points = [];
            if (session.editingLinkId === String(linkId)) session.editingLinkId = null;
        }
        render(session);
    }

    function insertLinkPoint(session, linkId, worldPoint) {
        const positions = linkEndpointPositions(session, linkId);
        if (!positions) return -1;
        const route = ensureManualRoute(session, linkId);
        const chain = [positions.start, ...route.points, positions.end];
        let bestIndex = 0;
        let bestDistance = Infinity;
        for (let index = 1; index < chain.length; index += 1) {
            const distance = distancePointToSegment(worldPoint, chain[index - 1], chain[index]);
            if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = index - 1;
            }
        }
        route.points.splice(bestIndex, 0, { x: worldPoint.x, y: worldPoint.y });
        render(session);
        return bestIndex;
    }

    function moveLinkPoint(session, linkId, pointIndex, screenPoint) {
        const route = stateApi().linkRoute(session, linkId);
        if (!route.points[pointIndex]) return;
        route.mode = "manual";
        route.points[pointIndex] = screenToWorld(session, screenPoint);
    }

    function removeLinkPoint(session, linkId, pointIndex) {
        const route = stateApi().linkRoute(session, linkId);
        route.points.splice(pointIndex, 1);
        if (!route.points.length) route.mode = "auto";
        render(session);
    }

    function organizeVertical(session) {
        session.layout.nodes = {};
        const cables = session.optical.cables || [];
        cables.forEach((cable, index) => {
            session.layout.nodes[`cable:${cable.id}`] = defaultCablePosition(session, cable, index, cables);
        });
        const splitters = stateApi().splitters(session);
        splitters.forEach((splitter, index) => {
            session.layout.nodes[`splitter:${splitter.id}`] = defaultSplitterPosition(index, splitters, session);
        });
        render(session);
    }

    function fitView(session) {
        render(session);
        const boxes = (session.renderCache?.hitboxes || []).filter((box) => !["endpoint", "link-handle"].includes(box.type));
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
        hitTestLink,
        hitTestLinkHandle,
        moveNode,
        moveLinkPoint,
        insertLinkPoint,
        removeLinkPoint,
        ensureManualRoute,
        autoRoute,
        setLinkStyle,
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
