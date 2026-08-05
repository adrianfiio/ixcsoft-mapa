(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    const LINK_STYLES = new Set(["curve", "orthogonal", "straight"]);

    function workspaceLabel() {
        return "CAIXA ÓPTICA";
    }

    function createSession(elementId) {
        return {
            id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
            elementId: Number(elementId),
            controller: new AbortController(),
            disposed: false,
            root: null,
            canvas: null,
            resizeObserver: null,
            payload: null,
            element: null,
            optical: { cables: [], splices: [], splitter_links: [] },
            cableState: { cables: [] },
            servicePorts: null,
            layout: {
                version: 3,
                viewport: { zoom: 1, panX: 0, panY: 0 },
                nodes: {},
                links: {},
                notes: [],
            },
            selection: {
                cableId: null,
                splitterId: null,
                pendingEndpoint: null,
                linkId: null,
            },
            expandedCables: new Set(),
            status: "",
            statusError: false,
            dragging: null,
            connectionDraft: null,
            editingLinkId: null,
            contextActions: new Map(),
            contextWorld: null,
            saveTimer: null,
            renderVersion: 0,
            initialFitDone: false,
            mutating: false,
            layoutMigrated: false,
        };
    }

    function clampNumber(value, min, max, fallback) {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
    }

    function normalizePoint(item) {
        if (!item || !Number.isFinite(Number(item.x)) || !Number.isFinite(Number(item.y))) return null;
        return {
            x: clampNumber(item.x, -7000, 7000, 0),
            y: clampNumber(item.y, -7000, 7000, 0),
        };
    }

    function normalizeLinkRoute(value) {
        const source = value && typeof value === "object" ? value : {};
        const style = LINK_STYLES.has(String(source.style || "")) ? String(source.style) : "curve";
        const points = Array.isArray(source.points)
            ? source.points.map(normalizePoint).filter(Boolean).slice(0, 24)
            : [];
        return {
            mode: source.mode === "manual" && points.length ? "manual" : "auto",
            style,
            points,
        };
    }

    function normalizeLayout(raw) {
        const source = raw && typeof raw === "object" ? raw : {};
        const sourceVersion = Number(source.version || 1);
        const viewport = source.viewport && typeof source.viewport === "object" ? source.viewport : {};
        const rawNodes = source.nodes && typeof source.nodes === "object" ? source.nodes : {};
        const rawLinks = source.links && typeof source.links === "object" ? source.links : {};
        const notes = Array.isArray(source.notes) ? source.notes : [];
        const keepNodes = sourceVersion >= 2;
        return {
            version: 3,
            viewport: {
                zoom: clampNumber(viewport.zoom, 0.35, 2.6, 1),
                panX: clampNumber(viewport.panX, -7000, 7000, 0),
                panY: clampNumber(viewport.panY, -7000, 7000, 0),
            },
            nodes: keepNodes
                ? Object.fromEntries(Object.entries(rawNodes).filter(([, value]) => (
                    value && Number.isFinite(Number(value.x)) && Number.isFinite(Number(value.y))
                )).map(([key, value]) => [key, { x: Number(value.x), y: Number(value.y) }]))
                : {},
            links: Object.fromEntries(Object.entries(rawLinks).map(([key, value]) => [
                String(key),
                normalizeLinkRoute(value),
            ])),
            notes: notes.filter((item) => item && typeof item.text === "string").map((item) => ({
                id: String(item.id || `note-${Math.random().toString(36).slice(2)}`),
                x: clampNumber(item.x, -7000, 7000, 0),
                y: clampNumber(item.y, -7000, 7000, 0),
                text: item.text.slice(0, 1200),
            })),
            migratedFromVersion: sourceVersion,
        };
    }

    function hydrate(session, payload) {
        session.payload = payload;
        session.element = payload.element;
        session.optical = payload.optical || session.optical;
        session.cableState = payload.cableState || session.cableState;
        session.servicePorts = payload.servicePorts;
        session.layout = normalizeLayout(payload.layout);
        session.layoutMigrated = Number(session.layout.migratedFromVersion || 1) < 3;
        delete session.layout.migratedFromVersion;
        session.selection.splitterId = splitters(session)[0]?.id || null;
        session.selection.cableId = session.optical.cables[0]?.id || null;
        session.selection.pendingEndpoint = null;
        session.selection.linkId = null;
        session.editingLinkId = null;
        return session;
    }

    function isDistributionBox(session) {
        return session.element?.element_type === "splice_box";
    }

    function fiberById(session, fiberId) {
        const id = Number(fiberId);
        for (const cable of session.optical.cables || []) {
            const fiber = (cable.fibers || []).find((item) => Number(item.id) === id);
            if (fiber) return { ...fiber, cableId: cable.id, cableName: cable.name };
        }
        return null;
    }

    function fiberColor(session, fiberId) {
        return fiberById(session, fiberId)?.color_hex || "#8fb4d8";
    }

    function cableById(session, cableId) {
        return (session.optical.cables || []).find((item) => Number(item.id) === Number(cableId)) || null;
    }

    function internalGroups(session) {
        return session.element?.splice_box?.trays || [];
    }

    function internalGroup(session) {
        return internalGroups(session)[0] || null;
    }

    function splitters(session) {
        return internalGroups(session).flatMap((group) => (group.splitters || []).map((splitter) => ({
            ...splitter,
            internalGroupId: group.id,
        })));
    }

    function splitterById(session, splitterId) {
        return splitters(session).find((item) => Number(item.id) === Number(splitterId)) || null;
    }

    function splitterPortById(session, portId) {
        const id = Number(portId);
        for (const splitter of splitters(session)) {
            const port = (splitter.ports || []).find((item) => Number(item.id) === id);
            if (port) return { ...port, splitterId: splitter.id, splitterRatio: splitter.ratio };
        }
        return null;
    }

    function endpointKey(endpoint) {
        if (!endpoint) return "";
        return `${endpoint.kind}:${Number(endpoint.id)}`;
    }

    function endpointLabel(session, endpoint) {
        if (!endpoint) return "Nenhuma ponta selecionada";
        if (endpoint.kind === "fiber") {
            const fiber = fiberById(session, endpoint.id);
            return fiber
                ? `${fiber.cableName} · fibra ${fiber.number} · ${fiber.color_name || "sem cor"}`
                : `Fibra ${endpoint.id}`;
        }
        if (endpoint.kind === "splitter-input") {
            const splitter = splitterById(session, endpoint.id);
            return `${splitter ? `Splitter ${splitter.ratio}` : "Splitter"} · entrada`;
        }
        if (endpoint.kind === "splitter-output") {
            const port = splitterPortById(session, endpoint.id);
            return port
                ? `Splitter ${port.splitterRatio} · saída ${port.number}`
                : `Saída ${endpoint.id}`;
        }
        return "Ponta óptica";
    }

    function isFiberUsed(session, fiberId) {
        const id = Number(fiberId);
        return (session.optical.splices || []).some((item) => (
            Number(item.input_fiber_id) === id || Number(item.output_fiber_id) === id
        )) || (session.optical.splitter_links || []).some((splitter) => (
            Number(splitter.input_fiber_id) === id
            || (splitter.ports || []).some((port) => Number(port.output_fiber_id) === id)
        ));
    }

    function endpointOccupied(session, endpoint) {
        if (!endpoint) return false;
        if (endpoint.kind === "fiber") return isFiberUsed(session, endpoint.id);
        if (endpoint.kind === "splitter-input") {
            const splitter = splitterById(session, endpoint.id);
            return Boolean(splitter?.input_fiber_id || splitter?.input_splitter_port_id);
        }
        if (endpoint.kind === "splitter-output") {
            const port = splitterPortById(session, endpoint.id);
            const cascaded = (session.optical.splitter_links || []).some((item) => (
                Number(item.input_splitter_port_id) === Number(endpoint.id)
            ));
            return Boolean(port?.output_fiber_id || cascaded);
        }
        return false;
    }

    function savedLinks(session) {
        const links = [];
        (session.optical.splices || []).forEach((splice) => {
            links.push({
                id: `splice:${Number(splice.id)}`,
                type: "splice",
                refId: Number(splice.id),
                label: `${splice.input?.cable || "Cabo"} F${splice.input?.number || ""} ↔ ${splice.output?.cable || "Cabo"} F${splice.output?.number || ""}`,
                start: { kind: "fiber", id: Number(splice.input_fiber_id) },
                end: { kind: "fiber", id: Number(splice.output_fiber_id) },
                colors: [fiberColor(session, splice.input_fiber_id), fiberColor(session, splice.output_fiber_id)],
            });
        });
        (session.optical.splitter_links || []).forEach((splitter) => {
            if (splitter.input_fiber_id) {
                const color = fiberColor(session, splitter.input_fiber_id);
                links.push({
                    id: `splitter-input:${Number(splitter.splitter_id)}`,
                    type: "splitter-input",
                    splitterId: Number(splitter.splitter_id),
                    label: `Fibra F${fiberById(session, splitter.input_fiber_id)?.number || splitter.input_fiber_id} → entrada do splitter`,
                    start: { kind: "fiber", id: Number(splitter.input_fiber_id) },
                    end: { kind: "splitter-input", id: Number(splitter.splitter_id) },
                    colors: [color, color],
                });
            } else if (splitter.input_splitter_port_id) {
                links.push({
                    id: `splitter-cascade:${Number(splitter.splitter_id)}`,
                    type: "splitter-cascade",
                    splitterId: Number(splitter.splitter_id),
                    sourcePortId: Number(splitter.input_splitter_port_id),
                    label: "Cascata entre splitters",
                    start: { kind: "splitter-output", id: Number(splitter.input_splitter_port_id) },
                    end: { kind: "splitter-input", id: Number(splitter.splitter_id) },
                    colors: ["#9b8cff", "#9b8cff"],
                    dashed: true,
                });
            }
            (splitter.ports || []).forEach((port) => {
                if (!port.output_fiber_id) return;
                const color = fiberColor(session, port.output_fiber_id);
                links.push({
                    id: `splitter-output:${Number(port.id)}`,
                    type: "splitter-output",
                    splitterId: Number(splitter.splitter_id),
                    portId: Number(port.id),
                    label: `Saída ${port.number} do splitter → fibra F${fiberById(session, port.output_fiber_id)?.number || port.output_fiber_id}`,
                    start: { kind: "splitter-output", id: Number(port.id) },
                    end: { kind: "fiber", id: Number(port.output_fiber_id) },
                    colors: [color, color],
                });
            });
        });
        return links;
    }

    function linkById(session, linkId) {
        return savedLinks(session).find((item) => item.id === String(linkId)) || null;
    }

    function linkRoute(session, linkId) {
        const key = String(linkId);
        if (!session.layout.links[key]) session.layout.links[key] = normalizeLinkRoute({});
        return session.layout.links[key];
    }

    function removeLinkRoute(session, linkId) {
        delete session.layout.links[String(linkId)];
        if (session.editingLinkId === String(linkId)) session.editingLinkId = null;
        if (session.selection.linkId === String(linkId)) session.selection.linkId = null;
    }

    function dispose(session) {
        if (!session || session.disposed) return;
        session.disposed = true;
        session.controller.abort();
        if (session.saveTimer) clearTimeout(session.saveTimer);
        session.resizeObserver?.disconnect();
        session.contextActions?.clear();
        session.root?.remove();
        document.body.classList.remove("ixc-optical-workspace-open");
    }

    namespace.state = Object.freeze({
        createSession,
        hydrate,
        normalizeLayout,
        normalizeLinkRoute,
        workspaceLabel,
        isDistributionBox,
        fiberById,
        fiberColor,
        cableById,
        internalGroups,
        internalGroup,
        splitters,
        splitterById,
        splitterPortById,
        endpointKey,
        endpointLabel,
        endpointOccupied,
        isFiberUsed,
        savedLinks,
        linkById,
        linkRoute,
        removeLinkRoute,
        dispose,
    });
})(window);
