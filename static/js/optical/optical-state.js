(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};

    function subtypeLabel(element) {
        if (element.element_type === "cto") return "CTO";
        return String(element.element_subtype || element.metadata?.import_subtype || "ceo").toLowerCase() === "cdo"
            ? "CDO"
            : "CEO";
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
                version: 1,
                viewport: { zoom: 1, panX: 0, panY: 0 },
                nodes: {},
                notes: [],
            },
            selection: {
                cableId: null,
                fiberA: null,
                fiberB: null,
                trayId: null,
                splitterId: null,
                splitterPortId: null,
                cascadePortId: null,
            },
            mode: "select",
            status: "",
            statusError: false,
            dragging: null,
            saveTimer: null,
            renderVersion: 0,
            initialFitDone: false,
            mutating: false,
        };
    }

    function normalizeLayout(raw) {
        const source = raw && typeof raw === "object" ? raw : {};
        const viewport = source.viewport && typeof source.viewport === "object" ? source.viewport : {};
        const nodes = source.nodes && typeof source.nodes === "object" ? source.nodes : {};
        const notes = Array.isArray(source.notes) ? source.notes : [];
        return {
            version: 1,
            viewport: {
                zoom: clampNumber(viewport.zoom, 0.4, 2.4, 1),
                panX: clampNumber(viewport.panX, -5000, 5000, 0),
                panY: clampNumber(viewport.panY, -5000, 5000, 0),
            },
            nodes: Object.fromEntries(Object.entries(nodes).filter(([, value]) => (
                value && Number.isFinite(Number(value.x)) && Number.isFinite(Number(value.y))
            )).map(([key, value]) => [key, { x: Number(value.x), y: Number(value.y) }])),
            notes: notes.filter((item) => item && typeof item.text === "string").map((item) => ({
                id: String(item.id || `note-${Math.random().toString(36).slice(2)}`),
                x: clampNumber(item.x, -5000, 5000, 0),
                y: clampNumber(item.y, -5000, 5000, 0),
                text: item.text.slice(0, 240),
            })),
        };
    }

    function hydrate(session, payload) {
        session.payload = payload;
        session.element = payload.element;
        session.optical = payload.optical || session.optical;
        session.cableState = payload.cableState || session.cableState;
        session.servicePorts = payload.servicePorts;
        session.layout = normalizeLayout(payload.layout);
        const trays = payload.element.splice_box?.trays || [];
        session.selection.trayId = trays[0]?.id || null;
        session.selection.splitterId = trays.flatMap((tray) => tray.splitters || [])[0]?.id || null;
        session.selection.cableId = session.optical.cables[0]?.id || null;
        return session;
    }

    function clampNumber(value, min, max, fallback) {
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
    }

    function fiberById(session, fiberId) {
        const id = Number(fiberId);
        for (const cable of session.optical.cables || []) {
            const fiber = (cable.fibers || []).find((item) => Number(item.id) === id);
            if (fiber) return { ...fiber, cableId: cable.id, cableName: cable.name };
        }
        return null;
    }

    function cableById(session, cableId) {
        return (session.optical.cables || []).find((item) => Number(item.id) === Number(cableId)) || null;
    }

    function trays(session) {
        return session.element?.splice_box?.trays || [];
    }

    function splitters(session) {
        return trays(session).flatMap((tray) => (tray.splitters || []).map((splitter) => ({
            ...splitter,
            trayId: tray.id,
            trayName: tray.name || `Bandeja ${tray.number}`,
        })));
    }

    function splitterById(session, splitterId) {
        return splitters(session).find((item) => Number(item.id) === Number(splitterId)) || null;
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

    function dispose(session) {
        if (!session || session.disposed) return;
        session.disposed = true;
        session.controller.abort();
        if (session.saveTimer) clearTimeout(session.saveTimer);
        session.resizeObserver?.disconnect();
        session.root?.remove();
        document.body.classList.remove("ixc-optical-workspace-open");
    }

    namespace.state = Object.freeze({
        createSession,
        hydrate,
        normalizeLayout,
        subtypeLabel,
        fiberById,
        cableById,
        trays,
        splitters,
        splitterById,
        isFiberUsed,
        dispose,
    });
})(window);
