(function (global) {
    "use strict";

    const VERSION = "0.75.35";
    const WIDTH_MIN = 190;
    const WIDTH_MAX = 620;
    const DEFAULT_WIDTH = 280;
    let redrawFrame = 0;

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function root() {
        return qs("#map-master-container");
    }

    function dialog() {
        return qs("#container-dialog");
    }

    function elementId() {
        const container = root();
        const shell = dialog();
        return String(
            container?.dataset.elementId
            || shell?.dataset.elementId
            || shell?.dataset.containerId
            || "unknown"
        );
    }

    function storageKey(cableId) {
        return `ixcsoft-map-v07535:cable-width:${elementId()}:${cableId}`;
    }

    function readWidth(cableId) {
        try {
            const value = Number(global.localStorage.getItem(storageKey(cableId)) || 0);
            return Number.isFinite(value) && value >= WIDTH_MIN && value <= WIDTH_MAX ? value : 0;
        } catch (_error) {
            return 0;
        }
    }

    function saveWidth(cableId, width) {
        try { global.localStorage.setItem(storageKey(cableId), String(Math.round(width))); } catch (_error) {}
    }

    function clearWidth(cableId) {
        try { global.localStorage.removeItem(storageKey(cableId)); } catch (_error) {}
    }

    function requestLinkRedraw() {
        if (redrawFrame) return;
        redrawFrame = global.requestAnimationFrame(() => {
            redrawFrame = 0;
            global.dispatchEvent(new Event("resize"));
        });
    }

    function applyCableWidth(node, width) {
        const bounded = Math.max(WIDTH_MIN, Math.min(WIDTH_MAX, Number(width) || DEFAULT_WIDTH));
        node.style.setProperty("--map-cable-width-v07535", `${bounded}px`);
        node.dataset.cableWidthV07535 = String(Math.round(bounded));
        requestLinkRedraw();
        return bounded;
    }

    function installCableControls(node) {
        const cableId = String(node.dataset.cableNode || node.dataset.cableNodeId || "");
        if (!cableId) return;
        node.classList.add("map-cable-resizable-v07535");
        const saved = readWidth(cableId);
        if (saved) applyCableWidth(node, saved);

        const header = qs(":scope > header", node);
        if (header && !qs("[data-cable-expand-v07535]", header)) {
            const expand = document.createElement("button");
            expand.type = "button";
            expand.dataset.cableExpandV07535 = "1";
            expand.className = "map-cable-expand-v07535";
            expand.title = "Alternar largura do cabo";
            expand.setAttribute("aria-label", "Alternar largura do cabo");
            expand.textContent = "↔";
            expand.addEventListener("pointerdown", (event) => event.stopPropagation());
            expand.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const current = node.getBoundingClientRect().width;
                const next = current < 390 ? 480 : DEFAULT_WIDTH;
                const applied = applyCableWidth(node, next);
                saveWidth(cableId, applied);
            });
            const arrow = qs(":scope > b", header);
            header.insertBefore(expand, arrow || null);
        }

        if (!qs("[data-cable-resize-v07535]", node)) {
            const grip = document.createElement("span");
            grip.dataset.cableResizeV07535 = "1";
            grip.className = "map-cable-resize-v07535";
            grip.title = "Arraste para aumentar ou reduzir o widget do cabo. Duplo clique restaura.";
            grip.setAttribute("aria-hidden", "true");
            grip.textContent = "⋮⋮";
            grip.addEventListener("dblclick", (event) => {
                event.preventDefault();
                event.stopPropagation();
                clearWidth(cableId);
                node.style.removeProperty("--map-cable-width-v07535");
                node.dataset.cableWidthV07535 = String(DEFAULT_WIDTH);
                requestLinkRedraw();
            });
            grip.addEventListener("pointerdown", (event) => {
                event.preventDefault();
                event.stopPropagation();
                grip.setPointerCapture(event.pointerId);
                document.body.classList.add("map-cable-resizing-v07535");
                const startX = event.clientX;
                const startWidth = node.getBoundingClientRect().width;
                const move = (moveEvent) => {
                    const applied = applyCableWidth(node, startWidth + moveEvent.clientX - startX);
                    node.dataset.pendingCableWidthV07535 = String(applied);
                };
                const finish = () => {
                    grip.removeEventListener("pointermove", move);
                    grip.removeEventListener("pointerup", finish);
                    grip.removeEventListener("pointercancel", finish);
                    document.body.classList.remove("map-cable-resizing-v07535");
                    const width = Number(node.dataset.pendingCableWidthV07535 || node.getBoundingClientRect().width);
                    delete node.dataset.pendingCableWidthV07535;
                    saveWidth(cableId, width);
                    requestLinkRedraw();
                };
                grip.addEventListener("pointermove", move);
                grip.addEventListener("pointerup", finish);
                grip.addEventListener("pointercancel", finish);
            });
            node.appendChild(grip);
        }
    }

    function installDioFlow(node) {
        node.classList.add("map-dio-flow-v07535");
        if (!qs(".map-dio-flow-labels-v07535", node)) {
            const labels = document.createElement("div");
            labels.className = "map-dio-flow-labels-v07535";
            labels.innerHTML = `
                <span><b>ENTRADA</b><small>OLT / equipamento</small></span>
                <i aria-hidden="true">→</i>
                <span><b>SAÍDA</b><small>cabos / rede externa</small></span>`;
            const header = qs(":scope > header", node);
            if (header?.nextSibling) node.insertBefore(labels, header.nextSibling);
            else node.appendChild(labels);
        }
        qsa('[data-port-role="front"], .dio-front', node).forEach((port) => {
            port.classList.add("map-dio-upstream-v07535");
            port.title = `Entrada OLT / equipamento · ${port.textContent.trim()}`;
        });
        qsa('[data-port-role="rear"], .dio-rear', node).forEach((port) => {
            port.classList.add("map-dio-cable-v07535");
            port.title = `Saída para cabo / rede externa · ${port.textContent.trim()}`;
        });
    }

    function enhance() {
        const container = root();
        const shell = dialog();
        if (!container || !shell?.open) return;
        container.classList.add("map-v07535-rack-polish");
        qsa('.master-canvas-node[data-equipment-type="dio"]', container).forEach(installDioFlow);
        qsa(".master-cable-node", container).forEach(installCableControls);
        requestLinkRedraw();
    }

    document.addEventListener("map:container-rendered", () => global.requestAnimationFrame(enhance));
    document.addEventListener("map:container-opening", () => global.setTimeout(enhance, 100));
    global.setTimeout(enhance, 500);

    global.mapRackPolishV07535 = Object.freeze({ version: VERSION, enhance });
})(window);
