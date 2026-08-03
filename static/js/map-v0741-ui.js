(function () {
    "use strict";

    const VERSION = "0.74.1";
    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
    const canvasViews = new WeakMap();
    let resizingCanvas = false;

    function svg(name) {
        const icons = {
            equipment: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M8 8h8M8 12h8M8 16h5"></path></svg>',
            canvas: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="8" cy="10" r="2"></circle><circle cx="16" cy="14" r="2"></circle><path d="M10 10h3a3 3 0 0 1 3 3"></path></svg>',
            fiber: '<svg viewBox="0 0 24 24"><path d="M3 12h5m8 0h5"></path><circle cx="10" cy="12" r="2"></circle><circle cx="14" cy="12" r="2"></circle><path d="M10 8V5m4 3V5m-4 11v3m4-3v3"></path></svg>',
            add: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"></path></svg>',
            organize: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect></svg>',
            lines: '<svg viewBox="0 0 24 24"><circle cx="5" cy="18" r="2"></circle><circle cx="19" cy="6" r="2"></circle><path d="M7 18h4a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3"></path></svg>',
            more: '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"></circle><circle cx="12" cy="12" r="1.5"></circle><circle cx="19" cy="12" r="1.5"></circle></svg>',
            fullscreen: '<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"></path></svg>',
            print: '<svg viewBox="0 0 24 24"><path d="M7 8V3h10v5M7 17h10v4H7z"></path><rect x="3" y="8" width="18" height="10" rx="2"></rect></svg>',
            qr: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect><path d="M14 14h3v3h-3zm4 4h3v3h-3zm0-4h3v2h-3zm-4 5h2v2h-2z"></path></svg>',
            close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"></path></svg>',
            fit: '<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"></path><path d="M9 9h6v6H9z"></path></svg>',
            plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"></path></svg>',
            minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"></path></svg>',
            matrix: '<svg viewBox="0 0 24 24"><path d="M4 5h16M4 12h16M4 19h16M8 3v18M16 3v18"></path></svg>',
            export: '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4"></path><path d="M5 17v4h14v-4"></path></svg>',
            save: '<svg viewBox="0 0 24 24"><path d="M5 3h12l2 2v16H5z"></path><path d="M8 3v6h8V3M8 17h8"></path></svg>',
            models: '<svg viewBox="0 0 24 24"><path d="m12 3 9 5-9 5-9-5 9-5Z"></path><path d="m3 13 9 5 9-5"></path></svg>',
        };
        return icons[name] || icons.more;
    }

    function decorateButton(button, iconName, fallbackLabel) {
        if (!button) return;
        if (button.dataset.v0741Icon === "1" && qs(".v0741-button-icon", button)) return;
        button.dataset.v0741Icon = "1";
        const text = button.textContent.trim() || fallbackLabel || "Ação";
        const icon = document.createElement("span");
        icon.className = "v0741-button-icon";
        icon.innerHTML = svg(iconName);
        const label = document.createElement("span");
        label.className = "v0741-button-label";
        label.textContent = text;
        button.replaceChildren(icon, label);
        button.title ||= text;
        button.setAttribute("aria-label", text);
    }

    function decorateContainer(root) {
        if (!root) return;
        const tabs = qs(".master-container-tabs", root);
        const toolbar = qs(".master-container-toolbar", root);
        if (!tabs || !toolbar) return;

        if (!qs(".master-container-commandbar-v0741", root)) {
            const bar = document.createElement("div");
            bar.className = "master-container-commandbar-v0741";
            root.insertBefore(bar, tabs);
            bar.append(tabs, toolbar);
        }

        const buttons = [
            ['[data-tab="equipment"]', "equipment", "Equipamentos"],
            ['[data-tab="canvas"]', "canvas", "Canvas 2D"],
            ['[data-tab="fibers"]', "fiber", "Fibras e terminações"],
            ['[data-tab="matrix"]', "matrix", "Matriz de manobra"],
            ['[data-tab="models"]', "models", "YAML / modelos"],
            ["[data-container-add]", "add", "Equipamento"],
            ["[data-container-organize]", "organize", "Organizar"],
            ["[data-container-lines]", "lines", "Editar linhas"],
            ["[data-container-export]", "export", "Exportar PNG"],
            ["[data-container-revision]", "save", "Salvar versão"],
            ["[data-container-more-toggle]", "more", "Mais"],
            ["[data-container-fullscreen]", "fullscreen", "Tela cheia"],
        ];
        buttons.forEach(([selector, iconName, label]) => decorateButton(qs(selector, root), iconName, label));

        const moreMenu = qs(".master-container-more-menu", root);
        if (moreMenu) qsa("button", moreMenu).forEach((button) => {
            if (button.matches('[data-tab="matrix"]')) decorateButton(button, "matrix", "Matriz de manobra");
            else if (button.matches('[data-tab="models"]')) decorateButton(button, "models", "YAML / modelos");
            else if (button.matches("[data-container-export]")) decorateButton(button, "export", "Exportar PNG");
            else if (button.matches("[data-container-revision]")) decorateButton(button, "save", "Salvar versão");
        });
        installCanvasControls(root);
    }

    function viewState(root) {
        if (!canvasViews.has(root)) canvasViews.set(root, { scale: 1, fitted: false, userZoom: false, tx: 0, ty: 0 });
        return canvasViews.get(root);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function canvasBounds(root) {
        const nodes = qsa(".master-canvas-node, .master-cable-node", root);
        if (!nodes.length) return null;
        let minX = Infinity;
        let minY = Infinity;
        let maxX = 0;
        let maxY = 0;
        nodes.forEach((node) => {
            const x = Number(node.dataset.posX || 0);
            const y = Number(node.dataset.posY || 0);
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x + Math.max(node.offsetWidth, 190));
            maxY = Math.max(maxY, y + Math.max(node.offsetHeight, 88));
        });
        return { minX, minY, maxX, maxY, width: Math.max(1, maxX - minX), height: Math.max(1, maxY - minY) };
    }

    function applyCanvasView(root, scale, { userZoom = false } = {}) {
        const viewport = qs(".master-canvas-scroll", root);
        const canvas = qs(".master-canvas", root);
        const bounds = canvasBounds(root);
        if (!viewport || !canvas || !bounds || !viewport.clientWidth || !viewport.clientHeight) return;

        const state = viewState(root);
        const nextScale = clamp(scale, 0.32, 1.6);
        const padding = 34;
        const contentWidth = bounds.width * nextScale;
        const contentHeight = bounds.height * nextScale;
        const tx = Math.round((viewport.clientWidth - contentWidth) / 2 - bounds.minX * nextScale);
        const ty = Math.round((viewport.clientHeight - contentHeight) / 2 - bounds.minY * nextScale);

        state.scale = nextScale;
        state.tx = tx;
        state.ty = ty;
        state.userZoom = userZoom;
        canvas.style.transformOrigin = "0 0";
        canvas.style.transform = `translate(${tx}px, ${ty}px) scale(${nextScale})`;
        canvas.dataset.v0741Scale = String(nextScale);
        viewport.dataset.v0741Fitted = "true";
        const output = qs("[data-canvas-zoom-value]", root);
        if (output) output.textContent = `${Math.round(nextScale * 100)}%`;
        viewport.style.setProperty("--v0741-canvas-padding", `${padding}px`);
    }

    function clearCanvasView(root) {
        const canvas = qs(".master-canvas", root);
        if (!canvas) return;
        canvas.style.removeProperty("transform");
        canvas.style.removeProperty("transform-origin");
    }


    function redrawCanvasAtNativeScale(root) {
        if (!root) return;
        clearCanvasView(root);
        resizingCanvas = true;
        try {
            window.dispatchEvent(new Event("resize"));
        } finally {
            resizingCanvas = false;
        }
    }

    function fitCanvas(root, { force = false } = {}) {
        const viewport = qs(".master-canvas-scroll", root);
        const bounds = canvasBounds(root);
        const state = viewState(root);
        if (!viewport || !bounds || (!force && state.userZoom)) return;
        const padding = 54;
        const availableWidth = Math.max(120, viewport.clientWidth - padding);
        const availableHeight = Math.max(120, viewport.clientHeight - padding);
        const scale = clamp(Math.min(availableWidth / bounds.width, availableHeight / bounds.height, 1), 0.32, 1);
        state.fitted = true;
        applyCanvasView(root, scale, { userZoom: false });
    }

    function installCanvasControls(root) {
        const panel = qs('[data-panel="canvas"]', root);
        const viewport = qs(".master-canvas-scroll", root);
        if (!panel || !viewport) return;
        let controls = qs(".map-canvas-zoom-v0741", panel);
        if (!controls) {
            controls = document.createElement("div");
            controls.className = "map-canvas-zoom-v0741";
            controls.innerHTML = `
                <button type="button" data-canvas-zoom-out title="Diminuir zoom">${svg("minus")}</button>
                <output data-canvas-zoom-value>100%</output>
                <button type="button" data-canvas-zoom-in title="Aumentar zoom">${svg("plus")}</button>
                <button type="button" data-canvas-zoom-fit title="Ajustar todos os equipamentos">${svg("fit")}<span>Ajustar</span></button>`;
            panel.appendChild(controls);
            qs("[data-canvas-zoom-out]", controls).onclick = () => {
                const state = viewState(root);
                applyCanvasView(root, state.scale - 0.1, { userZoom: true });
            };
            qs("[data-canvas-zoom-in]", controls).onclick = () => {
                const state = viewState(root);
                applyCanvasView(root, state.scale + 0.1, { userZoom: true });
            };
            qs("[data-canvas-zoom-fit]", controls).onclick = () => fitCanvas(root, { force: true });
            viewport.addEventListener("wheel", (event) => {
                if (!event.ctrlKey) return;
                event.preventDefault();
                const state = viewState(root);
                applyCanvasView(root, state.scale + (event.deltaY < 0 ? 0.08 : -0.08), { userZoom: true });
            }, { passive: false });
            viewport.addEventListener("pointerdown", (event) => {
                if (event.button !== 1) return;
                event.preventDefault();
                const canvas = qs(".master-canvas", root);
                const state = viewState(root);
                const origin = { x: event.clientX, y: event.clientY, tx: state.tx || 0, ty: state.ty || 0 };
                viewport.classList.add("canvas-panning-v0752");
                const move = (moveEvent) => {
                    state.tx = origin.tx + moveEvent.clientX - origin.x;
                    state.ty = origin.ty + moveEvent.clientY - origin.y;
                    canvas.style.transformOrigin = "0 0";
                    canvas.style.transform = `translate(${state.tx}px, ${state.ty}px) scale(${state.scale || 1})`;
                };
                const up = () => {
                    viewport.classList.remove("canvas-panning-v0752");
                    window.removeEventListener("pointermove", move);
                };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", up, { once: true });
            });
        }
        window.setTimeout(() => fitCanvas(root), 40);
        window.setTimeout(() => fitCanvas(root), 180);
    }

    function normalizeSidebar() {
        const sidebar = qs("#map-sidebar");
        if (!sidebar) return;
        sidebar.scrollLeft = 0;
        const content = qs(".sidebar-content", sidebar);
        if (content) content.scrollLeft = 0;
        const message = qs("#editor-message", sidebar);
        if (!message || message.dataset.v0741Observed === "1") return;
        message.dataset.v0741Observed = "1";
        let last = message.textContent.trim();
        new MutationObserver(() => {
            const current = message.textContent.trim();
            const collapsed = sidebar.classList.contains("v072-collapsed");
            if (collapsed && current && current !== last && !/^carregando/i.test(current)) showFloatingStatus(current, message.classList.contains("error"));
            last = current;
        }).observe(message, { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    }

    function showFloatingStatus(text, error = false) {
        let toast = qs("#map-status-toast-v0741");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "map-status-toast-v0741";
            toast.className = "map-status-toast-v0741";
            document.body.appendChild(toast);
        }
        toast.textContent = text;
        toast.classList.toggle("error", error);
        toast.classList.add("show");
        window.clearTimeout(toast._timer);
        toast._timer = window.setTimeout(() => toast.classList.remove("show"), 3200);
    }

    function syncCancelButton() {
        const cancel = qs("#map-toolbar-v072 [data-v0722-cancel]");
        if (!cancel) return;
        const drawingBar = qs("#drawing-bar");
        const contextual = Boolean(drawingBar && !drawingBar.hidden);
        const active = document.body.classList.contains("map-tool-active-v0722");
        cancel.hidden = !active || contextual;
        cancel.classList.toggle("v0741-suppressed", contextual);
    }

    function installCancelCoordinator() {
        const drawingBar = qs("#drawing-bar");
        if (drawingBar && drawingBar.dataset.v0741Observed !== "1") {
            drawingBar.dataset.v0741Observed = "1";
            new MutationObserver(syncCancelButton).observe(drawingBar, { attributes: true, attributeFilter: ["hidden", "class"] });
        }
        if (document.body.dataset.v0741CancelObserved !== "1") {
            document.body.dataset.v0741CancelObserved = "1";
            new MutationObserver(syncCancelButton).observe(document.body, { attributes: true, attributeFilter: ["class"] });
            document.addEventListener("click", () => window.setTimeout(syncCancelButton, 0), true);
        }
        syncCancelButton();
    }

    function normalizeAssetSheet() {
        const dialog = qs("#map-master-asset-sheet");
        if (!dialog) return;
        const print = qs("[data-print]", dialog);
        const qr = qs("[data-qr]", dialog);
        const close = qs("[data-close]", dialog);
        decorateButton(print, "print", "Imprimir / PDF");
        decorateButton(qr, "qr", "QR Code");
        decorateButton(close, "close", "Fechar");

        qsa(".master-sheet-definition > div", dialog).forEach((row) => {
            if (qs(":scope > dd > .master-sheet-definition, :scope > dd > .master-sheet-list", row)) row.classList.add("has-nested-value-v0741");
        });
        qsa(".master-sheet-definition .master-sheet-definition", dialog).forEach((nested) => nested.classList.add("nested-definition-v0741"));

        const grid = qs(".master-sheet-grid", dialog);
        const lifecycle = qs(".master-lifecycle-editor", dialog);
        if (grid && lifecycle && lifecycle.parentElement !== grid) {
            lifecycle.classList.add("master-sheet-card", "full", "v0741-lifecycle-card");
            grid.appendChild(lifecycle);
        }
    }

    function installAssetSheetObserver() {
        const install = () => {
            const dialog = qs("#map-master-asset-sheet");
            if (!dialog || dialog.dataset.v0741Observed === "1") return;
            dialog.dataset.v0741Observed = "1";
            new MutationObserver(() => window.requestAnimationFrame(normalizeAssetSheet)).observe(dialog, { childList: true, subtree: true, attributes: true, attributeFilter: ["open"] });
            dialog.addEventListener("close", () => dialog.scrollTo?.(0, 0));
            normalizeAssetSheet();
        };
        install();
        window.setTimeout(install, 500);
        window.setTimeout(install, 1600);
    }

    function refreshUi(event) {
        const root = qs("#map-master-container");
        if (root) {
            decorateContainer(root);
            if (!event?.detail?.root || event.detail.root.closest?.("#map-master-container") || event.detail.root === root) {
                redrawCanvasAtNativeScale(root);
                window.setTimeout(() => fitCanvas(root), 30);
            }
        }
        normalizeSidebar();
        installCancelCoordinator();
        normalizeAssetSheet();
    }

    function init() {
        document.body.classList.add("map-ui-v0741");
        normalizeSidebar();
        installCancelCoordinator();
        installAssetSheetObserver();
        document.addEventListener("map:container-rendered", refreshUi);
        document.addEventListener("click", (event) => {
            if (!event.target.closest("#map-master-container [data-container-lines], #map-master-container [data-container-fullscreen]")) return;
            window.setTimeout(() => decorateContainer(qs("#map-master-container")), 0);
        });
        window.addEventListener("resize", () => {
            if (resizingCanvas) return;
            const root = qs("#map-master-container");
            if (!root) return;
            const state = viewState(root);
            clearCanvasView(root);
            window.setTimeout(() => {
                if (state.userZoom) applyCanvasView(root, state.scale, { userZoom: true });
                else fitCanvas(root, { force: true });
            }, 60);
        }, true);
        window.setTimeout(refreshUi, 300);
        window.setTimeout(refreshUi, 900);
        window.setTimeout(refreshUi, 1800);
        window.mapUiV0741 = { version: VERSION, fitCanvas: () => fitCanvas(qs("#map-master-container"), { force: true }) };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
