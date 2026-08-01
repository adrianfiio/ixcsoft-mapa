(function () {
    "use strict";

    const dialog = document.getElementById("unifilar-dialog");
    const content = document.getElementById("unifilar-content");
    if (!dialog || !content) return;

    let enhancedGraph = null;
    let currentZoom = 0.7;
    let autoFit = false;
    let resizeObserver = null;
    let saveTimer = null;
    let fullscreenFallback = false;

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (item) return decodeURIComponent(item.split("=")[1]);
        return document.querySelector("[name='csrfmiddlewaretoken']")?.value
            || document.querySelector("meta[name='csrf-token']")?.content
            || "";
    }

    async function api(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.detail || `HTTP ${response.status}`);
        return data;
    }

    function elementId() {
        return dialog.dataset.elementId || "";
    }

    function clamp(value, minimum, maximum) {
        return Math.min(maximum, Math.max(minimum, Number(value)));
    }

    async function toggleFullscreen() {
        const button = content.querySelector("[data-fusion-fullscreen]");
        try {
            if (document.fullscreenElement === dialog) {
                await document.exitFullscreen();
                return;
            }
            if (dialog.requestFullscreen) {
                await dialog.requestFullscreen();
                return;
            }
        } catch (_error) {
            // O fallback CSS abaixo mantém a função disponível mesmo quando o
            // navegador bloqueia a Fullscreen API.
        }
        fullscreenFallback = !fullscreenFallback;
        dialog.classList.toggle("is-fullscreen", fullscreenFallback);
        if (button) button.setAttribute("aria-pressed", String(fullscreenFallback));
        syncFullscreenButton();
    }

    function syncFullscreenButton() {
        const active = document.fullscreenElement === dialog || fullscreenFallback;
        dialog.classList.toggle("is-fullscreen", active);
        const button = content.querySelector("[data-fusion-fullscreen]");
        if (button) {
            button.setAttribute("aria-pressed", String(active));
            button.classList.toggle("active", active);
            button.textContent = active ? "Desmaximizar" : "Tela cheia";
        }
        window.setTimeout(() => {
            if (autoFit) fitGraph(false);
            else refreshLinks();
        }, 60);
    }

    function parseScale(node) {
        const match = String(node?.style.transform || "").match(/scale\(([^)]+)\)/);
        return match ? Number(match[1]) : 1;
    }

    function graphParts() {
        const graph = content.querySelector(".optical-graph");
        const nodes = graph?.querySelector(".graph-nodes");
        return { graph, nodes };
    }

    function refreshLinks() {
        requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
        window.setTimeout(() => window.dispatchEvent(new Event("resize")), 90);
    }

    function applyZoom(value, persist = false) {
        const { graph, nodes } = graphParts();
        if (!graph || !nodes) return;
        currentZoom = clamp(value, 0.4, 1.6);
        nodes.style.transform = `scale(${currentZoom})`;
        nodes.style.transformOrigin = "top left";
        graph.style.setProperty("--fusion-zoom", currentZoom);
        const output = content.querySelector("[data-fusion-zoom-output]");
        const slider = content.querySelector("[data-fusion-zoom-range]");
        if (output) output.value = `${Math.round(currentZoom * 100)}%`;
        if (slider) slider.value = String(Math.round(currentZoom * 100));
        refreshLinks();
        if (persist) scheduleSave({ zoom: currentZoom });
    }

    function nodeBounds(nodes) {
        const rows = [...nodes.querySelectorAll(".graph-node")];
        if (!rows.length) return { width: nodes.scrollWidth || 1, height: nodes.scrollHeight || 1 };
        let maxX = 1;
        let maxY = 1;
        rows.forEach((node) => {
            const x = Number.parseFloat(node.style.left) || 0;
            const y = Number.parseFloat(node.style.top) || 0;
            maxX = Math.max(maxX, x + node.offsetWidth);
            maxY = Math.max(maxY, y + node.offsetHeight);
        });
        return { width: maxX + 36, height: maxY + 36 };
    }

    function fitGraph(persist = true) {
        const { graph, nodes } = graphParts();
        if (!graph || !nodes) return;
        const bounds = nodeBounds(nodes);
        const availableWidth = Math.max(260, graph.clientWidth - 48);
        const availableHeight = Math.max(260, graph.clientHeight - 48);
        const fitted = clamp(Math.min(availableWidth / bounds.width, availableHeight / bounds.height), 0.4, 1.15);
        applyZoom(fitted, persist);
    }

    function placeColumn(items, x, startY = 32, gap = 26) {
        let y = startY;
        items.forEach((node) => {
            node.style.left = `${Math.round(x)}px`;
            node.style.top = `${Math.round(y)}px`;
            y += node.offsetHeight + gap;
        });
        return y;
    }

    function organizeGraph() {
        const { graph, nodes } = graphParts();
        if (!graph || !nodes) return;
        const cables = [...nodes.querySelectorAll(".fiber-cable-node")]
            .sort((a, b) => (Number.parseFloat(a.style.top) || 0) - (Number.parseFloat(b.style.top) || 0));
        const splitters = [...nodes.querySelectorAll(".graph-splitter-node")]
            .sort((a, b) => (Number.parseFloat(a.style.top) || 0) - (Number.parseFloat(b.style.top) || 0));
        if (!cables.length && !splitters.length) return;

        const canvasWidth = Math.max(1050, Math.round(graph.clientWidth / Math.max(currentZoom, 0.4)) - 48);
        const cableWidth = Math.max(230, ...cables.map((node) => node.offsetWidth || 0));
        const splitterWidth = Math.max(220, ...splitters.map((node) => node.offsetWidth || 0));
        const rawXs = cables.map((node) => Number.parseFloat(node.style.left) || 0);
        const minX = Math.min(...rawXs, 0);
        const maxX = Math.max(...rawXs, 0);
        const midpoint = (minX + maxX) / 2;
        let left = cables.filter((node) => (Number.parseFloat(node.style.left) || 0) <= midpoint);
        let right = cables.filter((node) => !left.includes(node));
        if (!right.length && cables.length > 1) {
            const half = Math.ceil(cables.length / 2);
            left = cables.slice(0, half);
            right = cables.slice(half);
        }

        const leftBottom = placeColumn(left, 34);
        const rightBottom = placeColumn(right, canvasWidth - cableWidth - 34);
        const centerX = Math.max(cableWidth + 90, Math.round((canvasWidth - splitterWidth) / 2));
        const splitterBottom = placeColumn(splitters, centerX, 48, 32);
        const canvasHeight = Math.max(620, leftBottom, rightBottom, splitterBottom) + 36;
        nodes.style.width = `${canvasWidth}px`;
        nodes.style.minWidth = `${canvasWidth}px`;
        nodes.style.height = `${canvasHeight}px`;
        nodes.style.minHeight = `${canvasHeight}px`;

        const positions = {};
        nodes.querySelectorAll(".graph-node[data-node-key]").forEach((node) => {
            positions[node.dataset.nodeKey] = {
                x: Math.round(Number.parseFloat(node.style.left) || 0),
                y: Math.round(Number.parseFloat(node.style.top) || 0),
            };
        });
        scheduleSave({ positions, zoom: currentZoom });
        refreshLinks();
    }

    async function saveLayoutPatch(patch) {
        const id = elementId();
        if (!id) return;
        const data = await api(`/api/map/elements/${id}/layout/`);
        const layout = { ...(data.layout || {}) };
        if (patch.positions) Object.assign(layout, patch.positions);
        if (patch.zoom !== undefined) layout.zoom = patch.zoom;
        await api(`/api/map/elements/${id}/layout/`, {
            method: "PATCH",
            body: JSON.stringify({ layout }),
        });
    }

    function scheduleSave(patch) {
        window.clearTimeout(saveTimer);
        saveTimer = window.setTimeout(() => {
            saveLayoutPatch(patch).catch(() => {});
        }, 220);
    }

    function modernToolbar() {
        const old = content.querySelector(".unifilar-zoom");
        if (!old || old.dataset.v06 === "true") return;
        old.dataset.v06 = "true";
        old.classList.add("fusion-toolbar");
        old.innerHTML = `
            <button type="button" data-fusion-zoom="out" title="Diminuir zoom" aria-label="Diminuir zoom">−</button>
            <input data-fusion-zoom-range type="range" min="40" max="160" step="5" value="70" aria-label="Zoom das fusões">
            <output data-fusion-zoom-output>70%</output>
            <button type="button" data-fusion-zoom="in" title="Aumentar zoom" aria-label="Aumentar zoom">+</button>
            <button type="button" data-fusion-zoom="70">70%</button>
            <button type="button" data-fusion-organize>Organizar</button>
            <button type="button" data-fusion-fit>Ajustar</button>
            <button type="button" data-fusion-auto aria-pressed="false">Auto</button>
            <button type="button" data-fusion-fullscreen aria-pressed="false">Tela cheia</button>`;

        old.querySelector('[data-fusion-zoom="out"]').onclick = () => applyZoom(currentZoom - 0.1, true);
        old.querySelector('[data-fusion-zoom="in"]').onclick = () => applyZoom(currentZoom + 0.1, true);
        old.querySelector('[data-fusion-zoom="70"]').onclick = () => applyZoom(0.7, true);
        old.querySelector("[data-fusion-organize]").onclick = () => organizeGraph();
        old.querySelector("[data-fusion-fit]").onclick = () => fitGraph(true);
        old.querySelector("[data-fusion-zoom-range]").oninput = (event) => applyZoom(Number(event.target.value) / 100, false);
        old.querySelector("[data-fusion-zoom-range]").onchange = () => scheduleSave({ zoom: currentZoom });
        old.querySelector("[data-fusion-auto]").onclick = (event) => {
            autoFit = !autoFit;
            event.currentTarget.setAttribute("aria-pressed", String(autoFit));
            event.currentTarget.classList.toggle("active", autoFit);
            if (autoFit) fitGraph(true);
        };
        old.querySelector("[data-fusion-fullscreen]").onclick = () => toggleFullscreen();
        syncFullscreenButton();
    }

    function bindPassingCableCuts() {
        content.querySelectorAll("[data-cut-passing-cable]").forEach((button) => {
            if (button.dataset.bound === "true") return;
            button.dataset.bound = "true";
            button.addEventListener("click", async (event) => {
                event.preventDefault();
                event.stopPropagation();
                const cableId = button.dataset.cutPassingCable;
                if (!cableId || !elementId()) return;
                if (!confirm("Cortar este cabo nesta caixa e criar dois segmentos? Faça isso antes de criar fusões.")) return;
                button.disabled = true;
                button.textContent = "Cortando...";
                try {
                    await api(`/api/map/elements/${elementId()}/cables/${cableId}/cut/`, {
                        method: "POST",
                        body: JSON.stringify({ max_distance_m: 60 }),
                    });
                    await window.networkMap?.loadStructure?.(false);
                    await window.networkMap?.showUnifilar?.(elementId());
                } catch (error) {
                    alert(error.message);
                    button.disabled = false;
                    button.textContent = "Cortar na caixa";
                }
            });
        });
    }

    function bindCtrlWheelZoom(graph) {
        if (!graph || graph.dataset.ctrlWheelZoom === "true") return;
        graph.dataset.ctrlWheelZoom = "true";
        graph.addEventListener("wheel", (event) => {
            if (!event.ctrlKey && !event.metaKey) return;
            event.preventDefault();
            autoFit = false;
            const autoButton = content.querySelector("[data-fusion-auto]");
            if (autoButton) {
                autoButton.classList.remove("active");
                autoButton.setAttribute("aria-pressed", "false");
            }
            const direction = event.deltaY < 0 ? 1 : -1;
            applyZoom(currentZoom + direction * 0.08, false);
            scheduleSave({ zoom: currentZoom });
        }, { passive: false });
    }

    function enhance() {
        if (!dialog.open) return;
        const { graph, nodes } = graphParts();
        if (!graph || !nodes || nodes === enhancedGraph) return;
        enhancedGraph = nodes;
        modernToolbar();
        bindPassingCableCuts();
        const existing = parseScale(nodes);
        currentZoom = existing >= 0.65 ? existing : 0.7;
        applyZoom(currentZoom, false);
        graph.classList.add("fusion-v06");
        bindCtrlWheelZoom(graph);

        resizeObserver?.disconnect();
        resizeObserver = new ResizeObserver(() => {
            if (autoFit) fitGraph(false);
            else refreshLinks();
        });
        resizeObserver.observe(graph);
    }

    const observer = new MutationObserver(() => requestAnimationFrame(enhance));
    observer.observe(content, { childList: true, subtree: true });
    document.addEventListener("fullscreenchange", syncFullscreenButton);
    dialog.addEventListener("close", () => {
        enhancedGraph = null;
        resizeObserver?.disconnect();
        fullscreenFallback = false;
        dialog.classList.remove("is-fullscreen");
        if (document.fullscreenElement === dialog) document.exitFullscreen().catch(() => {});
    });
    dialog.addEventListener("toggle", enhance);
}());
