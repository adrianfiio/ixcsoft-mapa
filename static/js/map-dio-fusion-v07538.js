(function (global) {
    "use strict";

    const VERSION = "0.75.38";
    const state = {
        workspace: null,
        data: null,
        elementId: null,
        dioId: null,
        selectedCableId: null,
        selectedFiberId: null,
        selectedPortId: null,
        busy: false,
        drag: null,
        associations: new Map(),
        redrawFrame: 0,
        loadTokens: new Map(),
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (cookie) return decodeURIComponent(cookie.split("=")[1]);
        return qs("[name='csrfmiddlewaretoken']")?.value || "";
    }

    async function request(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function notify(message, error = false) {
        if (global.networkMap?.notify) global.networkMap.notify(message, error);
    }

    function canEdit() {
        return document.body.dataset.canEdit === "true";
    }

    function masterRoot() {
        return qs("#map-master-container");
    }

    function containerDialog() {
        return qs("#container-dialog");
    }

    function currentElementId() {
        const root = masterRoot();
        const dialog = containerDialog();
        return Number(
            root?.dataset.elementId
            || dialog?.dataset.elementId
            || dialog?.dataset.containerId
            || 0
        );
    }

    function endpointUrl(elementId, dioId) {
        return `/api/map/elements/${Number(elementId)}/dio/${Number(dioId)}/fusion-matrix-v07537/`;
    }

    function cableId(node) {
        return Number(node?.dataset.cableNode || node?.dataset.cableNodeId || 0);
    }

    function dioId(node) {
        return Number(node?.dataset.equipmentNode || node?.dataset.equipmentId || 0);
    }

    function cableFiberCount(node) {
        return Number(node?.dataset.fiberCount || qsa(".master-cable-fiber", node).length || 0);
    }

    function installCableSummary(node) {
        const id = cableId(node);
        if (!id) return;
        node.classList.add("map-rack-cable-compact-v07538");
        let summary = qs("[data-rack-cable-summary-v07538]", node);
        if (!summary) {
            summary = document.createElement("div");
            summary.dataset.rackCableSummaryV07538 = "1";
            summary.className = "map-rack-cable-summary-v07538";
            summary.innerHTML = `
                <button type="button" data-rack-cable-anchor-v07538="${id}" title="Vincular este cabo a um DIO" aria-label="Vincular cabo ao DIO"><i></i></button>
                <span><strong>${cableFiberCount(node)} fibras</strong><small>Arraste o ponto até um DIO</small></span>`;
            node.appendChild(summary);
            const anchor = qs("[data-rack-cable-anchor-v07538]", summary);
            anchor.addEventListener("pointerdown", (event) => startCableDrag(event, node, anchor));
        }
        const name = qs(":scope > header strong", node)?.textContent?.trim() || `Cabo ${id}`;
        const header = qs(":scope > header small", node);
        if (header) header.textContent = `${cableFiberCount(node)} FO`;
        node.dataset.cableDisplayNameV07537 = name;
    }

    function compactPortLabel(port, fallbackIndex) {
        const span = qs("span", port);
        const original = String(span?.textContent || port.title || "").trim();
        if (!port.dataset.fullPortLabelV07537) port.dataset.fullPortLabelV07537 = original;
        const matches = original.match(/(\d+)(?!.*\d)/);
        const number = matches ? Number(matches[1]) : fallbackIndex + 1;
        if (span) span.textContent = String(number);
        port.title = original || `Porta ${number}`;
        port.dataset.compactPortNumberV07537 = String(number);
    }

    function installCompactOlt(node) {
        node.classList.add("map-olt-compact-v07538");
        const header = qs(":scope > header", node);
        if (header && !qs("[data-olt-width-v07538]", header)) {
            const widthButton = document.createElement("button");
            widthButton.type = "button";
            widthButton.dataset.oltWidthV07538 = "1";
            widthButton.className = "map-olt-width-v07538";
            widthButton.title = "Alternar largura da OLT";
            widthButton.textContent = "↔";
            widthButton.addEventListener("pointerdown", (event) => event.stopPropagation());
            widthButton.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const expanded = node.classList.toggle("is-wide-v07538");
                node.style.setProperty("--olt-width-v07538", expanded ? "620px" : "505px");
                requestAssociationRedraw();
            });
            const actions = qs(".master-node-actions", header);
            header.insertBefore(widthButton, actions || null);
        }
        const slots = qsa(".master-olt-slot-v07510", node);
        slots.forEach((slot, slotIndex) => {
            slot.dataset.compactSlotV07537 = String(slotIndex + 1);
            const title = qs(":scope > header strong", slot);
            const original = title?.textContent?.trim() || `Slot ${slotIndex + 1}`;
            if (title) title.textContent = `S${slotIndex + 1}`;
            if (title) title.title = original;
            qsa(".olt-port-v07510, .master-node-port", slot).forEach(compactPortLabel);
        });
    }

    function installDio(node) {
        const id = dioId(node);
        const elementId = currentElementId();
        if (!id || !elementId) return;
        node.classList.add("map-dio-matrix-ready-v07538");
        qsa('[data-port-role="rear"], .dio-rear', node).forEach((port) => {
            port.classList.add("map-dio-port-hidden-v07538");
            port.setAttribute("aria-hidden", "true");
            port.tabIndex = -1;
        });
        let target = qs("[data-dio-cable-target-v07538]", node);
        if (!target) {
            target = document.createElement("button");
            target.type = "button";
            target.dataset.dioCableTargetV07538 = String(id);
            target.className = "map-dio-cable-target-v07538";
            target.innerHTML = '<i></i><span><strong>CABOS</strong><small data-dio-linked-count-v07538>0 vinculados</small></span>';
            target.title = "Arraste um cabo até aqui ou abra a matriz de fusões. A frente do DIO continua livre para OLT.";
            target.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                openWorkspace(elementId, id).catch((error) => notify(error.message, true));
            });
            node.appendChild(target);
        }
        const header = qs(":scope > header", node);
        if (header && !qs("[data-open-dio-fusions-v07538]", header)) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.openDioFusionsV07538 = String(id);
            button.className = "map-open-dio-fusions-v07538";
            button.textContent = "Fusões";
            button.title = "Abrir matriz de fusão do DIO";
            button.addEventListener("pointerdown", (event) => event.stopPropagation());
            button.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                openWorkspace(elementId, id).catch((error) => notify(error.message, true));
            });
            const actions = qs(".master-node-actions", header);
            header.insertBefore(button, actions || null);
        }
        loadAssociation(elementId, id, node);
    }

    function syncAssociationData(elementId, equipmentId, data) {
        const ids = new Set((data.linked_cable_ids || []).map(Number));
        state.associations.set(`${elementId}:${equipmentId}`, ids);
        qsa(`.master-canvas-node[data-equipment-node="${equipmentId}"]`).forEach((node) => {
            node.dataset.dioAssociationLoadedV07537 = "1";
            node.dataset.linkedCableIdsV07537 = [...ids].join(",");
            const count = qs("[data-dio-linked-count-v07538]", node);
            if (count) count.textContent = `${ids.size} vinculado(s)`;
        });
        requestAssociationRedraw();
    }

    async function loadAssociation(elementId, equipmentId, node) {
        const cached = state.associations.get(`${elementId}:${equipmentId}`);
        if (cached && node.dataset.dioAssociationLoadedV07537 === "1") {
            const count = qs("[data-dio-linked-count-v07538]", node);
            if (count) count.textContent = `${cached.size} vinculado(s)`;
            return;
        }
        const key = `${elementId}:${equipmentId}`;
        const token = (state.loadTokens.get(key) || 0) + 1;
        state.loadTokens.set(key, token);
        try {
            const data = await request(endpointUrl(elementId, equipmentId));
            if (state.loadTokens.get(key) !== token || !node.isConnected) return;
            syncAssociationData(elementId, equipmentId, data);
        } catch (error) {
            node.dataset.dioFusionLoadErrorV07537 = error.message;
        }
    }

    function enhance() {
        const root = masterRoot();
        const dialog = containerDialog();
        if (!root || !dialog?.open) return;
        qsa(".master-cable-node", root).forEach(installCableSummary);
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach(installDio);
        qsa('.master-canvas-node[data-equipment-type="olt"], .master-olt-chassis-v07510', root).forEach(installCompactOlt);
        requestAssociationRedraw();
    }

    function dragOverlay() {
        let svg = qs("#map-rack-cable-drag-v07538");
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.id = "map-rack-cable-drag-v07538";
            svg.setAttribute("aria-hidden", "true");
            svg.innerHTML = '<path></path>';
            document.body.appendChild(svg);
        }
        return svg;
    }

    function startCableDrag(event, cableNode, anchor) {
        if (!canEdit()) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const id = cableId(cableNode);
        if (!id) return;
        anchor.setPointerCapture?.(event.pointerId);
        const rect = anchor.getBoundingClientRect();
        state.drag = {
            pointerId: event.pointerId,
            cableId: id,
            cableNode,
            anchor,
            start: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
            clientX: event.clientX,
            clientY: event.clientY,
            frame: 0,
        };
        document.body.classList.add("map-cable-linking-v07538");
        scheduleDragLine(event.clientX, event.clientY);
        global.addEventListener("pointermove", handleDragMove, true);
        global.addEventListener("pointerup", finishCableDrag, true);
        global.addEventListener("pointercancel", cancelCableDrag, true);
    }

    function handleDragMove(event) {
        if (!state.drag || event.pointerId !== state.drag.pointerId) return;
        scheduleDragLine(event.clientX, event.clientY);
        qsa(".map-dio-cable-target-v07538.is-drop-target").forEach((item) => item.classList.remove("is-drop-target"));
        const target = document.elementsFromPoint(event.clientX, event.clientY)
            .map((item) => item.closest?.("[data-dio-cable-target-v07538], .master-canvas-node[data-equipment-type='dio']"))
            .find(Boolean);
        target?.classList.add("is-drop-target");
    }

    async function finishCableDrag(event) {
        if (!state.drag || event.pointerId !== state.drag.pointerId) return;
        const drag = state.drag;
        const target = document.elementsFromPoint(event.clientX, event.clientY)
            .map((item) => item.closest?.("[data-dio-cable-target-v07538], .master-canvas-node[data-equipment-type='dio']"))
            .find(Boolean);
        cancelCableDrag();
        const node = target?.closest?.('.master-canvas-node[data-equipment-type="dio"]') || target;
        const equipmentId = dioId(node) || Number(target?.dataset.dioCableTargetV07537 || 0);
        const elementId = currentElementId();
        if (!equipmentId || !elementId) {
            notify("Solte o cabo sobre a área CABOS de um DIO.", true);
            return;
        }
        try {
            const data = await mutateMatrix(elementId, equipmentId, "attach_cable", { cable_id: drag.cableId });
            syncAssociationData(elementId, equipmentId, data);
            notify("Cabo vinculado ao DIO. Abra Fusões para distribuir as fibras.");
            enhance();
        } catch (error) {
            notify(error.message, true);
        }
    }

    function cancelCableDrag() {
        if (state.drag?.frame) global.cancelAnimationFrame(state.drag.frame);
        state.drag = null;
        document.body.classList.remove("map-cable-linking-v07538");
        qs("#map-rack-cable-drag-v07538")?.remove();
        qsa(".map-dio-cable-target-v07538.is-drop-target").forEach((item) => item.classList.remove("is-drop-target"));
        global.removeEventListener("pointermove", handleDragMove, true);
        global.removeEventListener("pointerup", finishCableDrag, true);
        global.removeEventListener("pointercancel", cancelCableDrag, true);
    }

    function scheduleDragLine(x, y) {
        if (!state.drag) return;
        state.drag.clientX = x;
        state.drag.clientY = y;
        if (state.drag.frame) return;
        state.drag.frame = global.requestAnimationFrame(() => {
            if (!state.drag) return;
            state.drag.frame = 0;
            updateDragLine(state.drag.clientX, state.drag.clientY);
        });
    }

    function updateDragLine(x, y) {
        if (!state.drag) return;
        const svg = dragOverlay();
        const start = state.drag.start;
        const direction = x >= start.x ? 1 : -1;
        const dx = Math.max(54, Math.abs(x - start.x) * 0.34);
        const midX = start.x + direction * dx;
        qs("path", svg).setAttribute(
            "d",
            `M ${start.x} ${start.y} C ${midX} ${start.y}, ${x - direction * dx} ${y}, ${x} ${y}`,
        );
    }

    function center(rect) {
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    }

    function associationSvg() {
        const panel = qs("#map-master-container [data-panel='canvas']") || masterRoot();
        if (!panel) return null;
        let svg = qs(".map-rack-association-links-v07538", panel);
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.classList.add("map-rack-association-links-v07538");
            svg.setAttribute("aria-hidden", "true");
            panel.appendChild(svg);
        }
        return svg;
    }

    function requestAssociationRedraw() {
        if (state.redrawFrame) return;
        state.redrawFrame = global.requestAnimationFrame(() => {
            state.redrawFrame = 0;
            drawAssociations();
        });
    }

    function drawAssociations() {
        const svg = associationSvg();
        const root = masterRoot();
        if (!svg || !root) return;
        const svgRect = svg.getBoundingClientRect();
        const width = Math.max(1, svgRect.width);
        const height = Math.max(1, svgRect.height);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        const paths = [];
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach((dioNode) => {
            const equipmentId = dioId(dioNode);
            const elementId = currentElementId();
            const linked = state.associations.get(`${elementId}:${equipmentId}`) || new Set();
            const target = qs("[data-dio-cable-target-v07538]", dioNode);
            if (!target) return;
            const endRect = target.getBoundingClientRect();
            const end = { x: endRect.left - svgRect.left + endRect.width / 2, y: endRect.top - svgRect.top + endRect.height / 2 };
            linked.forEach((linkedCableId) => {
                const cableNode = qs(`[data-cable-node="${linkedCableId}"], [data-cable-node-id="${linkedCableId}"]`, root);
                const anchor = cableNode && qs("[data-rack-cable-anchor-v07538]", cableNode);
                if (!anchor) return;
                const startRect = anchor.getBoundingClientRect();
                const start = { x: startRect.left - svgRect.left + startRect.width / 2, y: startRect.top - svgRect.top + startRect.height / 2 };
                const bend = Math.max(50, Math.abs(end.x - start.x) * 0.38);
                paths.push(`<path d="M ${start.x} ${start.y} C ${start.x + bend} ${start.y}, ${end.x - bend} ${end.y}, ${end.x} ${end.y}" data-linked-cable="${linkedCableId}" data-linked-dio="${equipmentId}"></path>`);
            });
        });
        svg.innerHTML = paths.join("");
    }

    async function mutateMatrix(elementId, equipmentId, action, payload = {}, method = "POST") {
        return request(endpointUrl(elementId, equipmentId), {
            method,
            body: JSON.stringify({ action, ...payload }),
        });
    }

    function ensureWorkspace() {
        if (state.workspace?.isConnected) return state.workspace;
        const root = document.createElement("div");
        root.className = "map-dio-fusion-workspace-v07538";
        root.innerHTML = `
            <section role="dialog" aria-modal="true" aria-labelledby="map-dio-fusion-title-v07538">
                <header>
                    <div><span>MATRIZ DE FUSÃO</span><h2 id="map-dio-fusion-title-v07538">DIO</h2><p>Clique numa fibra e depois numa porta. A fusão traseira é gravada imediatamente; a frente do DIO continua disponível para a OLT.</p></div>
                    <div class="map-dio-fusion-header-actions-v07538">
                        <button type="button" data-dio-auto-fuse-v07538>⚡ Auto fusão</button>
                        <button type="button" data-dio-close-v07538 aria-label="Fechar">×</button>
                    </div>
                </header>
                <div class="map-dio-fusion-status-v07538" data-dio-status-v07538></div>
                <main data-dio-body-v07538></main>
            </section>
            <div class="map-dio-port-menu-v07538" data-dio-port-menu-v07538 hidden></div>`;
        document.body.appendChild(root);
        root.addEventListener("click", handleWorkspaceClick);
        root.addEventListener("contextmenu", handleWorkspaceContextMenu);
        root.addEventListener("dblclick", handleWorkspaceDoubleClick);
        state.workspace = root;
        return root;
    }

    async function openWorkspace(elementId, equipmentId) {
        const root = ensureWorkspace();
        state.elementId = Number(elementId);
        state.dioId = Number(equipmentId);
        state.data = null;
        state.selectedCableId = null;
        state.selectedFiberId = null;
        state.selectedPortId = null;
        root.classList.add("is-open");
        document.body.classList.add("map-dio-fusion-open-v07538");
        setWorkspaceStatus("Carregando matriz…");
        try {
            state.data = await request(endpointUrl(elementId, equipmentId));
            state.selectedCableId = state.data.linked_cables?.[0]?.id || null;
            renderWorkspace();
            setWorkspaceStatus("Matriz carregada.");
        } catch (error) {
            setWorkspaceStatus(error.message, true);
            throw error;
        }
    }

    function closeWorkspace() {
        state.workspace?.classList.remove("is-open");
        document.body.classList.remove("map-dio-fusion-open-v07538");
        closePortMenu();
        enhance();
    }

    function setWorkspaceStatus(message, error = false) {
        const node = qs("[data-dio-status-v07538]", state.workspace || document);
        if (!node) return;
        node.textContent = message || "";
        node.classList.toggle("is-error", error);
    }

    function selectedCable() {
        return (state.data?.linked_cables || []).find((item) => Number(item.id) === Number(state.selectedCableId)) || null;
    }

    function selectedFiber() {
        const cable = selectedCable();
        return cable?.fibers?.find((item) => Number(item.id) === Number(state.selectedFiberId)) || null;
    }

    function fiberGroups(cable) {
        const groups = new Map();
        (cable?.fibers || []).forEach((fiber) => {
            const number = Number(fiber.tube_number || 1);
            if (!groups.has(number)) groups.set(number, []);
            groups.get(number).push(fiber);
        });
        return [...groups.entries()].sort((a, b) => a[0] - b[0]);
    }

    function renderWorkspace() {
        if (!state.workspace || !state.data) return;
        qs("#map-dio-fusion-title-v07538", state.workspace).textContent = `${state.data.dio.name} · ${state.data.dio.capacity} portas`;
        const body = qs("[data-dio-body-v07538]", state.workspace);
        body.innerHTML = `
            <section class="map-dio-cables-v07538">
                <header><strong>CABOS VINCULADOS</strong><span>${state.data.linked_cables.length}</span><button type="button" data-dio-attach-menu-v07538 ${state.data.available_cables.length ? "" : "disabled"}>+ Vincular</button></header>
                <div>${renderCables()}</div>
            </section>
            <section class="map-dio-selection-v07538">
                <header><strong>SELEÇÃO RÁPIDA</strong></header>
                ${renderSelection()}
            </section>
            <section class="map-dio-ports-v07538">
                <header><strong>PORTAS DO DIO</strong><span>${state.data.summary.fusions}/${state.data.ports.length}</span></header>
                <div>${renderPortGroups()}</div>
            </section>`;
    }

    function renderCables() {
        if (!state.data.linked_cables.length) {
            return '<p class="map-dio-empty-v07538">Nenhum cabo vinculado. Arraste um cabo no Rack até o DIO ou use “Vincular”.</p>';
        }
        return state.data.linked_cables.map((cable) => {
            const active = Number(cable.id) === Number(state.selectedCableId);
            const used = cable.fibers.filter((fiber) => fiber.fusion).length;
            return `<article class="map-dio-cable-card-v07538 ${active ? "is-active" : ""}" data-dio-cable-card-v07538="${cable.id}">
                <header><button type="button" data-dio-select-cable-v07538="${cable.id}"><span>⌁</span><strong>${escapeHtml(cable.name)}</strong><small>${cable.fiber_count} FO · ${used}/${cable.fibers.length}</small></button><button type="button" data-dio-detach-cable-v07538="${cable.id}" title="Desvincular cabo">×</button></header>
                <div class="map-dio-tubes-v07538">${fiberGroups(cable).map(([tubeNumber, fibers]) => `<div class="map-dio-tube-v07538"><b style="--tube-color:${escapeHtml(fibers[0]?.tube_color_hex || "#64748b")}">T${tubeNumber}</b><div>${fibers.map((fiber) => `<button type="button" data-dio-fiber-v07538="${fiber.id}" class="${fiber.fusion ? "is-fused" : ""} ${Number(fiber.id) === Number(state.selectedFiberId) ? "is-selected" : ""}" style="--fiber-color:${escapeHtml(fiber.color_hex || "#94a3b8")}" title="Fibra ${fiber.number} · ${escapeHtml(fiber.color_name)}${fiber.fusion ? ` · DIO ${fiber.fusion.port_number}` : ""}"><i></i><span>${fiber.number}</span></button>`).join("")}</div></div>`).join("")}</div>
            </article>`;
        }).join("");
    }

    function renderSelection() {
        const cable = selectedCable();
        const fiber = selectedFiber();
        const port = state.data.ports.find((item) => Number(item.id) === Number(state.selectedPortId));
        return `<div class="map-dio-selection-card-v07538">
            <div><span>1</span><p><strong>${fiber ? `${escapeHtml(cable.name)} · F${fiber.number}` : "Escolha uma fibra"}</strong><small>${fiber ? escapeHtml(fiber.color_name) : "Clique num círculo do cabo"}</small></p></div>
            <i>→</i>
            <div><span>2</span><p><strong>${port ? `Porta ${port.number}` : "Escolha uma porta"}</strong><small>${port?.fusion ? `${escapeHtml(port.fusion.cable)} F${port.fusion.fiber_number}` : "Clique numa porta livre do DIO"}</small></p></div>
        </div>
        <p class="map-dio-selection-help-v07538">A segunda seleção cria a fusão. Para romper, clique com o botão direito ou dê dois cliques numa porta ocupada.</p>
        <dl><div><dt>Cabos</dt><dd>${state.data.summary.linked_cables}</dd></div><div><dt>Fusões</dt><dd>${state.data.summary.fusions}</dd></div><div><dt>Portas livres</dt><dd>${state.data.summary.free_ports}</dd></div></dl>`;
    }

    function renderPortGroups() {
        const groups = [];
        for (let index = 0; index < state.data.ports.length; index += 12) groups.push(state.data.ports.slice(index, index + 12));
        return groups.map((ports, index) => `<article class="map-dio-port-group-v07538">
            <header><strong>BANDEJA ${index + 1}</strong><small>${ports.filter((port) => port.fusion).length}/${ports.length}</small></header>
            <div>${ports.map((port) => `<button type="button" data-dio-port-v07538="${port.id}" class="${port.fusion ? "is-fused" : ""} ${port.front ? "has-front" : ""} ${Number(port.id) === Number(state.selectedPortId) ? "is-selected" : ""}" style="--fusion-color:${escapeHtml(port.fusion?.color_hex || "#fb6a13")}" title="${port.fusion ? `${escapeHtml(port.fusion.cable)} F${port.fusion.fiber_number}` : `Porta ${port.number} livre`}"><span>${port.number}</span><i></i></button>`).join("")}</div>
        </article>`).join("");
    }

    async function handleWorkspaceClick(event) {
        if (!state.workspace?.classList.contains("is-open")) return;
        closePortMenu();
        if (event.target.closest("[data-dio-close-v07538]")) return closeWorkspace();
        const cableButton = event.target.closest("[data-dio-select-cable-v07538]");
        if (cableButton) {
            state.selectedCableId = Number(cableButton.dataset.dioSelectCableV07538);
            state.selectedFiberId = null;
            renderWorkspace();
            return;
        }
        const fiberButton = event.target.closest("[data-dio-fiber-v07538]");
        if (fiberButton) {
            const fiberId = Number(fiberButton.dataset.dioFiberV07538);
            const cableCard = fiberButton.closest("[data-dio-cable-card-v07538]");
            state.selectedCableId = Number(cableCard.dataset.dioCableCardV07538);
            const fiber = selectedCable()?.fibers.find((item) => Number(item.id) === fiberId);
            if (fiber?.fusion) {
                state.selectedFiberId = fiberId;
                state.selectedPortId = Number(fiber.fusion.port_id);
            } else {
                state.selectedFiberId = state.selectedFiberId === fiberId ? null : fiberId;
            }
            renderWorkspace();
            return;
        }
        const portButton = event.target.closest("[data-dio-port-v07538]");
        if (portButton) {
            const portId = Number(portButton.dataset.dioPortV07538);
            const port = state.data.ports.find((item) => Number(item.id) === portId);
            state.selectedPortId = portId;
            if (!port?.fusion && state.selectedFiberId) await createFusion(portId);
            else renderWorkspace();
            return;
        }
        if (event.target.closest("[data-dio-auto-fuse-v07538]")) return autoFuse();
        const detach = event.target.closest("[data-dio-detach-cable-v07538]");
        if (detach) return detachCable(Number(detach.dataset.dioDetachCableV07538));
        if (event.target.closest("[data-dio-attach-menu-v07538]")) return attachCableDialog();
    }

    async function createFusion(portId) {
        if (state.busy || !state.selectedFiberId) return;
        state.busy = true;
        setWorkspaceStatus("Criando fusão…");
        try {
            state.data = await mutateMatrix(state.elementId, state.dioId, "create_fusion", {
                fiber_id: state.selectedFiberId,
                port_id: portId,
            });
            state.selectedFiberId = null;
            state.selectedPortId = portId;
            renderWorkspace();
            setWorkspaceStatus("Fusão criada.");
        } catch (error) {
            setWorkspaceStatus(error.message, true);
        } finally {
            state.busy = false;
        }
    }

    async function deleteFusion(linkId) {
        if (!linkId || state.busy) return;
        const accepted = await global.IXCMapDialog?.confirm?.({
            title: "Romper fusão",
            message: "A fibra será liberada e a porta do DIO ficará disponível.",
            confirmLabel: "Romper fusão",
            danger: true,
        });
        if (!accepted) return;
        state.busy = true;
        try {
            state.data = await mutateMatrix(state.elementId, state.dioId, "delete_fusion", { link_id: linkId }, "DELETE");
            state.selectedFiberId = null;
            state.selectedPortId = null;
            renderWorkspace();
            setWorkspaceStatus("Fusão rompida.");
        } catch (error) {
            setWorkspaceStatus(error.message, true);
        } finally {
            state.busy = false;
        }
    }

    async function autoFuse() {
        const cable = selectedCable();
        if (!cable) return setWorkspaceStatus("Selecione um cabo para a auto fusão.", true);
        const startPort = state.data.ports.find((item) => Number(item.id) === Number(state.selectedPortId) && !item.fusion)
            || state.data.ports.find((item) => !item.fusion);
        if (!startPort) return setWorkspaceStatus("Não há porta livre no DIO.", true);
        const freeFibers = cable.fibers.filter((fiber) => !fiber.fusion).length;
        const accepted = await global.IXCMapDialog?.confirm?.({
            title: "Auto fusão sequencial",
            message: `${freeFibers} fibra(s) livres de ${cable.name} serão ligadas a partir da porta ${startPort.number}, respeitando a ordem das fibras e portas livres.`,
            confirmLabel: "Executar auto fusão",
        });
        if (!accepted) return;
        state.busy = true;
        setWorkspaceStatus("Executando auto fusão…");
        try {
            state.data = await mutateMatrix(state.elementId, state.dioId, "auto_fuse", {
                cable_id: cable.id,
                start_port_id: startPort.id,
            });
            state.selectedFiberId = null;
            state.selectedPortId = null;
            renderWorkspace();
            setWorkspaceStatus(`${state.data.auto_fused || 0} fusão(ões) criada(s).`);
        } catch (error) {
            setWorkspaceStatus(error.message, true);
        } finally {
            state.busy = false;
        }
    }

    async function attachCableDialog() {
        const options = (state.data.available_cables || []).map((item) => ({
            value: String(item.id),
            label: `${item.name} · ${item.fiber_count} FO`,
        }));
        if (!options.length) return;
        const selected = await global.IXCMapDialog?.prompt?.({
            title: "Vincular cabo ao DIO",
            label: "Cabo disponível",
            options,
            value: options[0].value,
            confirmLabel: "Vincular cabo",
        });
        if (!selected) return;
        try {
            state.data = await mutateMatrix(state.elementId, state.dioId, "attach_cable", { cable_id: Number(selected) });
            syncAssociationData(state.elementId, state.dioId, state.data);
            state.selectedCableId = Number(selected);
            renderWorkspace();
            setWorkspaceStatus("Cabo vinculado.");
            enhance();
        } catch (error) {
            setWorkspaceStatus(error.message, true);
        }
    }

    async function detachCable(cableIdValue) {
        const cable = state.data.linked_cables.find((item) => Number(item.id) === Number(cableIdValue));
        if (!cable) return;
        const accepted = await global.IXCMapDialog?.confirm?.({
            title: "Desvincular cabo",
            message: `Remover ${cable.name} deste DIO? Cabos com fusões não podem ser desvinculados.`,
            confirmLabel: "Desvincular",
            danger: true,
        });
        if (!accepted) return;
        try {
            state.data = await mutateMatrix(state.elementId, state.dioId, "detach_cable", { cable_id: cable.id });
            syncAssociationData(state.elementId, state.dioId, state.data);
            state.selectedCableId = state.data.linked_cables?.[0]?.id || null;
            state.selectedFiberId = null;
            renderWorkspace();
            setWorkspaceStatus("Cabo desvinculado.");
            enhance();
        } catch (error) {
            setWorkspaceStatus(error.message, true);
        }
    }

    function handleWorkspaceContextMenu(event) {
        const portButton = event.target.closest("[data-dio-port-v07538]");
        if (!portButton) return;
        event.preventDefault();
        const portId = Number(portButton.dataset.dioPortV07538);
        const port = state.data?.ports.find((item) => Number(item.id) === portId);
        if (!port?.fusion) return;
        openPortMenu(event.clientX, event.clientY, port);
    }

    function handleWorkspaceDoubleClick(event) {
        const portButton = event.target.closest("[data-dio-port-v07538]");
        if (!portButton) return;
        const port = state.data?.ports.find((item) => Number(item.id) === Number(portButton.dataset.dioPortV07538));
        if (port?.fusion) deleteFusion(port.fusion.id);
    }

    function openPortMenu(x, y, port) {
        const menu = qs("[data-dio-port-menu-v07538]", state.workspace);
        menu.innerHTML = `<button type="button" data-dio-break-fusion-v07538="${port.fusion.id}">Romper fusão</button><small>${escapeHtml(port.fusion.cable)} F${port.fusion.fiber_number} → DIO ${port.number}</small>`;
        menu.hidden = false;
        menu.style.left = `${Math.min(x, global.innerWidth - 230)}px`;
        menu.style.top = `${Math.min(y, global.innerHeight - 110)}px`;
        const button = qs("[data-dio-break-fusion-v07538]", menu);
        button.onclick = () => {
            closePortMenu();
            deleteFusion(Number(button.dataset.dioBreakFusionV07538));
        };
    }

    function closePortMenu() {
        const menu = qs("[data-dio-port-menu-v07538]", state.workspace || document);
        if (menu) menu.hidden = true;
    }

    document.addEventListener("map:container-rendered", () => global.requestAnimationFrame(enhance));
    document.addEventListener("map:container-opening", () => global.setTimeout(enhance, 120));
    global.addEventListener("resize", requestAssociationRedraw);
    document.addEventListener("pointermove", (event) => {
        if (event.buttons) requestAssociationRedraw();
    }, { passive: true });
    document.addEventListener("wheel", requestAssociationRedraw, { passive: true });
    global.setTimeout(enhance, 600);

    global.mapDioFusionV07537 = Object.freeze({
        version: VERSION,
        enhance,
        open: openWorkspace,
        close: closeWorkspace,
    });
})(window);
