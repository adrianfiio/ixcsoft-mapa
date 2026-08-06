(function (global) {
    "use strict";

    const VERSION = "0.75.46";
    const installedScrolls = new WeakSet();
    const state = {
        gesture: null,
        suppressClickUntil: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];
    const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

    function rootNode() {
        return qs("#map-master-container");
    }

    function canvasNode(root = rootNode()) {
        return qs(".master-canvas", root);
    }

    function scrollNode(root = rootNode()) {
        return qs(".master-canvas-scroll", root);
    }

    function isRack(root = rootNode()) {
        if (!root) return false;
        if (root.classList.contains("v07542-physical-rack")) return true;
        const dialog = qs("#container-dialog");
        const values = [
            root.dataset.elementType,
            root.dataset.containerType,
            dialog?.dataset.elementType,
            dialog?.dataset.containerType,
            dialog?.dataset.kind,
        ].map((value) => String(value || "").toLowerCase());
        if (values.some((value) => value === "rack" || value.includes("rack"))) return true;
        const title = [
            qs("[data-container-title]", dialog)?.textContent,
            qs("h1", dialog)?.textContent,
            qs("h2", dialog)?.textContent,
        ].join(" ").toLowerCase();
        return title.includes("rack");
    }

    function readView(canvas) {
        if (!canvas) return { scale: 1, tx: 0, ty: 0 };
        const transform = getComputedStyle(canvas).transform;
        if (transform && transform !== "none" && global.DOMMatrixReadOnly) {
            const matrix = new global.DOMMatrixReadOnly(transform);
            return {
                scale: Number.isFinite(matrix.a) && matrix.a > 0 ? matrix.a : 1,
                tx: Number.isFinite(matrix.e) ? matrix.e : 0,
                ty: Number.isFinite(matrix.f) ? matrix.f : 0,
            };
        }
        return {
            scale: Number(canvas.dataset.v0741Scale || 1) || 1,
            tx: Number(canvas.dataset.v07546Tx || 0) || 0,
            ty: Number(canvas.dataset.v07546Ty || 0) || 0,
        };
    }

    function applyView(root, view) {
        const canvas = canvasNode(root);
        if (!canvas) return;
        const normalized = {
            scale: clamp(Number(view.scale) || 1, 0.18, 2.4),
            tx: Number(view.tx) || 0,
            ty: Number(view.ty) || 0,
        };
        canvas.style.transformOrigin = "0 0";
        canvas.style.transform = `translate(${normalized.tx}px, ${normalized.ty}px) scale(${normalized.scale})`;
        canvas.style.willChange = "transform";
        canvas.dataset.v0741Scale = String(normalized.scale);
        canvas.dataset.v07546Tx = String(normalized.tx);
        canvas.dataset.v07546Ty = String(normalized.ty);
        const output = qs("[data-canvas-zoom-value]", root);
        if (output) output.textContent = `${Math.round(normalized.scale * 100)}%`;
        root.dispatchEvent(new CustomEvent("map:rack-viewport-changed", { detail: normalized }));
    }

    function zoomAround(root, clientX, clientY, nextScale) {
        const scroll = scrollNode(root);
        const canvas = canvasNode(root);
        if (!scroll || !canvas) return;
        const before = readView(canvas);
        const scale = clamp(nextScale, 0.18, 2.4);
        const rect = scroll.getBoundingClientRect();
        const cursorX = clientX - rect.left;
        const cursorY = clientY - rect.top;
        const worldX = (cursorX - before.tx) / before.scale;
        const worldY = (cursorY - before.ty) / before.scale;
        applyView(root, {
            scale,
            tx: cursorX - worldX * scale,
            ty: cursorY - worldY * scale,
        });
    }

    function worldRect(node, canvas) {
        let x = 0;
        let y = 0;
        let current = node;
        while (current && current !== canvas) {
            x += current.offsetLeft || 0;
            y += current.offsetTop || 0;
            current = current.offsetParent;
        }
        return {
            x,
            y,
            width: Math.max(1, node.offsetWidth || 0),
            height: Math.max(1, node.offsetHeight || 0),
        };
    }

    function contentBounds(canvas) {
        const candidates = qsa([
            "[data-rack-frame-v07542]",
            ".master-canvas-node:not([hidden])",
            ".master-cable-node:not([hidden])",
            ".v07542-rack-organizer",
        ].join(","), canvas).filter((node) => node.offsetWidth > 0 && node.offsetHeight > 0);
        if (!candidates.length) {
            return { x: 0, y: 0, width: Math.max(canvas.scrollWidth, 1), height: Math.max(canvas.scrollHeight, 1) };
        }
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        candidates.forEach((node) => {
            const rect = worldRect(node, canvas);
            minX = Math.min(minX, rect.x);
            minY = Math.min(minY, rect.y);
            maxX = Math.max(maxX, rect.x + rect.width);
            maxY = Math.max(maxY, rect.y + rect.height);
        });
        return {
            x: minX,
            y: minY,
            width: Math.max(1, maxX - minX),
            height: Math.max(1, maxY - minY),
        };
    }

    function fitView(root) {
        const scroll = scrollNode(root);
        const canvas = canvasNode(root);
        if (!scroll || !canvas) return;
        const bounds = contentBounds(canvas);
        const padding = 54;
        const availableWidth = Math.max(120, scroll.clientWidth - padding * 2);
        const availableHeight = Math.max(120, scroll.clientHeight - padding * 2);
        const scale = clamp(Math.min(availableWidth / bounds.width, availableHeight / bounds.height, 1), 0.18, 1);
        applyView(root, {
            scale,
            tx: Math.round((scroll.clientWidth - bounds.width * scale) / 2 - bounds.x * scale),
            ty: Math.round((scroll.clientHeight - bounds.height * scale) / 2 - bounds.y * scale),
        });
    }

    function blockedPrimaryTarget(target) {
        if (!(target instanceof Element)) return true;
        // MAP_V07555_PAN_FIX: mesma correção do v07552 — "dialog" batia no
        // próprio #container-dialog que envolve todo o canvas (ancestral via
        // closest()), não um modal aninhado, bloqueando o pan sempre.
        return Boolean(target.closest([
            "button",
            "a",
            "input",
            "select",
            "textarea",
            "[contenteditable='true']",
            "[data-port-id]",
            ".master-node-port",
            ".v07545-pon-port",
            "[data-rack-cable-anchor-v07538]",
            ".map-canvas-zoom-v0741",
            ".v07542-rack-toolbar",
            ".master-container-commandbar-v0741",
            ".v07542-rack-mounted > header",
        ].join(",")));
    }

    function beginPan(event, scroll, root) {
        if (!isRack(root) || ![0, 1].includes(event.button)) return;
        if (event.button === 0 && blockedPrimaryTarget(event.target)) return;
        if (event.button === 1 && event.target instanceof Element && event.target.closest("input, select, textarea, dialog")) return;
        const canvas = canvasNode(root);
        if (!canvas) return;
        const view = readView(canvas);
        state.gesture = {
            root,
            scroll,
            pointerId: event.pointerId,
            button: event.button,
            startX: event.clientX,
            startY: event.clientY,
            tx: view.tx,
            ty: view.ty,
            scale: view.scale,
            active: event.button === 1,
        };
        scroll.setPointerCapture?.(event.pointerId);
        if (state.gesture.active) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            scroll.classList.add("is-panning-v07546");
        }
    }

    function movePan(event) {
        const gesture = state.gesture;
        if (!gesture || event.pointerId !== gesture.pointerId) return;
        const dx = event.clientX - gesture.startX;
        const dy = event.clientY - gesture.startY;
        if (!gesture.active && Math.hypot(dx, dy) < 4) return;
        if (!gesture.active) {
            gesture.active = true;
            gesture.scroll.classList.add("is-panning-v07546");
        }
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        applyView(gesture.root, {
            scale: gesture.scale,
            tx: gesture.tx + dx,
            ty: gesture.ty + dy,
        });
    }

    function finishPan(event) {
        const gesture = state.gesture;
        if (!gesture || (event?.pointerId != null && event.pointerId !== gesture.pointerId)) return;
        if (gesture.active) {
            event?.preventDefault?.();
            event?.stopPropagation?.();
            state.suppressClickUntil = performance.now() + 180;
        }
        gesture.scroll.classList.remove("is-panning-v07546");
        gesture.scroll.releasePointerCapture?.(gesture.pointerId);
        state.gesture = null;
    }

    function install(scroll) {
        if (!scroll || installedScrolls.has(scroll)) return;
        installedScrolls.add(scroll);
        scroll.dataset.navigationV07546 = "1";
        scroll.classList.add("v07546-navigation-enabled");

        scroll.addEventListener("wheel", (event) => {
            const root = rootNode();
            if (!root || !isRack(root)) return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const view = readView(canvasNode(root));
            const step = event.deltaY < 0 ? 0.1 : -0.1;
            zoomAround(root, event.clientX, event.clientY, view.scale + step);
        }, { capture: true, passive: false });

        scroll.addEventListener("pointerdown", (event) => beginPan(event, scroll, rootNode()), true);
    }

    function interceptZoomButtons(event) {
        const button = event.target instanceof Element
            ? event.target.closest("[data-canvas-zoom-in], [data-canvas-zoom-out], [data-canvas-zoom-fit]")
            : null;
        const root = rootNode();
        if (!button || !root || !root.contains(button) || !isRack(root)) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        if (button.matches("[data-canvas-zoom-fit]")) {
            fitView(root);
            return;
        }
        const scroll = scrollNode(root);
        const canvas = canvasNode(root);
        if (!scroll || !canvas) return;
        const rect = scroll.getBoundingClientRect();
        const view = readView(canvas);
        zoomAround(
            root,
            rect.left + rect.width / 2,
            rect.top + rect.height / 2,
            view.scale + (button.matches("[data-canvas-zoom-in]") ? 0.1 : -0.1),
        );
    }

    function suppressClickAfterPan(event) {
        if (performance.now() > state.suppressClickUntil) return;
        const scroll = scrollNode();
        if (!scroll || !(event.target instanceof Node) || !scroll.contains(event.target)) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
    }

    function ensure() {
        const root = rootNode();
        const scroll = scrollNode(root);
        if (!root || !scroll) return;
        install(scroll);
    }

    function scheduleEnsure() {
        global.requestAnimationFrame(ensure);
        global.setTimeout(ensure, 80);
        global.setTimeout(ensure, 260);
    }

    function init() {
        document.addEventListener("map:container-opening", scheduleEnsure);
        document.addEventListener("map:container-rendered", scheduleEnsure);
        document.addEventListener("click", interceptZoomButtons, true);
        document.addEventListener("click", suppressClickAfterPan, true);
        global.addEventListener("pointermove", movePan, true);
        global.addEventListener("pointerup", finishPan, true);
        global.addEventListener("pointercancel", finishPan, true);
        global.addEventListener("blur", () => finishPan(null));
        scheduleEnsure();
    }

    // O sinal existe antes dos runtimes v0.75.42 e v0.75.45 carregarem.
    global.mapRackViewportV07546 = Object.freeze({
        version: VERSION,
        ensure,
        fit: () => fitView(rootNode()),
        getView: () => readView(canvasNode()),
    });

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})(window);
