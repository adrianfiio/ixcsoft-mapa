(function () {
    "use strict";

    const VERSION = "0.75.12";
    const state = {
        containerId: "",
        containerData: null,
        layout: null,
        selectedLinkId: "",
        tooltip: null,
        ptpLayer: null,
        ptpLinks: [],
        ptpDialog: null,
        resizeObserver: null,
        routeFrame: 0,
        gpsMarker: null,
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return cookie ? decodeURIComponent(cookie.split("=")[1]) : qs("[name='csrfmiddlewaretoken']")?.value || "";
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

    function notify(message, error = false) {
        if (window.networkMap?.notify) return window.networkMap.notify(message, error);
        console[error ? "error" : "info"](message);
    }

    function containerRoot() {
        return qs("#map-master-container");
    }

    function canvasElement() {
        return qs("#map-master-container .master-canvas");
    }

    function svgElement() {
        return qs("#map-master-container .master-canvas-links");
    }

    function currentContainerId() {
        return String(qs("#container-dialog")?.dataset.elementId || state.containerId || "");
    }

    function currentProjectId() {
        return String(qs("#project-select")?.value || "");
    }

    function parseTransform(element) {
        const inline = element?.style.transform || "";
        const match = inline.match(/translate\(\s*(-?[\d.]+)px\s*,\s*(-?[\d.]+)px\s*\)/);
        if (match) return { x: Number(match[1]), y: Number(match[2]) };
        const matrix = getComputedStyle(element).transform;
        if (matrix && matrix !== "none") {
            const values = matrix.match(/matrix\(([^)]+)\)/)?.[1].split(",").map(Number);
            if (values?.length === 6) return { x: values[4], y: values[5] };
        }
        return { x: 0, y: 0 };
    }

    function canvasScale() {
        return Number(canvasElement()?.dataset.v0741Scale || 1) || 1;
    }

    function pointInCanvas(element, side = "center") {
        const canvas = canvasElement();
        if (!canvas || !element) return null;
        const target = qs("i", element) || element;
        const canvasRect = canvas.getBoundingClientRect();
        const rect = target.getBoundingClientRect();
        const scale = canvasScale();
        let x = rect.left + rect.width / 2;
        if (side === "left") x = rect.left;
        if (side === "right") x = rect.right;
        return {
            x: (x - canvasRect.left) / scale,
            y: (rect.top + rect.height / 2 - canvasRect.top) / scale,
        };
    }

    function portButton(portId, role = "front") {
        const canvas = canvasElement();
        return qs(`[data-port-id="${portId}"][data-port-role="${role}"]`, canvas)
            || qs(`[data-port-id="${portId}"]`, canvas);
    }

    function fiberButton(fiberId) {
        return qs(`[data-cable-fiber="${fiberId}"]`, canvasElement());
    }

    function endpointForLink(link) {
        const destinationRole = !link.source_port_id && (link.cable_id || link.cable_fiber_id) ? "rear" : "front";
        const destinationButton = portButton(link.destination_port_id, destinationRole);
        const destination = pointInCanvas(destinationButton);
        let sourceButton = null;
        let source = null;
        if (link.source_port_id) {
            sourceButton = portButton(link.source_port_id, "front");
            source = pointInCanvas(sourceButton);
        } else if (link.cable_fiber_id) {
            sourceButton = fiberButton(link.cable_fiber_id);
            const cableNode = sourceButton?.closest("[data-cable-node]");
            const sideRight = cableNode?.classList.contains("side-right-v0758");
            source = pointInCanvas(sourceButton, sideRight ? "left" : "right");
        }
        if (!source && destination) {
            const saved = state.layout?.externalLinks?.[String(link.id)];
            source = saved || { x: 24, y: destination.y };
        }
        return { source, destination, sourceButton, destinationButton };
    }

    function distance(a, b) {
        return Math.hypot(b.x - a.x, b.y - a.y);
    }

    function manualRouteIsUsable(points, start, end) {
        if (!Array.isArray(points) || !points.length || points.length > 16) return false;
        const all = [start, ...points, end];
        if (all.some((point) => !Number.isFinite(Number(point?.x)) || !Number.isFinite(Number(point?.y)))) return false;
        const direct = Math.max(80, distance(start, end));
        const total = all.slice(1).reduce((sum, point, index) => sum + distance(all[index], point), 0);
        const minX = Math.min(start.x, end.x) - 700;
        const maxX = Math.max(start.x, end.x) + 700;
        const minY = Math.min(start.y, end.y) - 700;
        const maxY = Math.max(start.y, end.y) + 700;
        return total <= direct * 5 + 900
            && points.every((point) => point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY);
    }

    function roundedPolyline(points, radius = 12) {
        if (!points.length) return "";
        if (points.length === 1) return `M${points[0].x},${points[0].y}`;
        let path = `M${points[0].x},${points[0].y}`;
        for (let index = 1; index < points.length - 1; index += 1) {
            const previous = points[index - 1];
            const current = points[index];
            const next = points[index + 1];
            const beforeDistance = Math.max(1, distance(previous, current));
            const afterDistance = Math.max(1, distance(current, next));
            const localRadius = Math.min(radius, beforeDistance / 2, afterDistance / 2);
            const before = {
                x: current.x + (previous.x - current.x) * (localRadius / beforeDistance),
                y: current.y + (previous.y - current.y) * (localRadius / beforeDistance),
            };
            const after = {
                x: current.x + (next.x - current.x) * (localRadius / afterDistance),
                y: current.y + (next.y - current.y) * (localRadius / afterDistance),
            };
            path += ` L${before.x},${before.y} Q${current.x},${current.y} ${after.x},${after.y}`;
        }
        const last = points.at(-1);
        return `${path} L${last.x},${last.y}`;
    }

    function autoRoute(link, endpoints) {
        const { source, destination, sourceButton, destinationButton } = endpoints;
        const lane = (Number(link.id) % 7) * 9;
        const sourceNode = sourceButton?.closest("[data-equipment-node], [data-cable-node]");
        const destinationNode = destinationButton?.closest("[data-equipment-node]");
        const sourceType = sourceNode?.dataset.equipmentType || "";
        const destinationType = destinationNode?.dataset.equipmentType || "";
        const oltToDio = sourceType === "olt" && destinationType === "dio";

        if (oltToDio) {
            const canvas = canvasElement();
            const canvasRect = canvas.getBoundingClientRect();
            const scale = canvasScale();
            const board = sourceButton.closest(".master-olt-slot-v07510, .master-olt-board-v07512");
            const boardRect = board?.getBoundingClientRect();
            const sourceNodeRect = sourceNode?.getBoundingClientRect();
            const guideY = boardRect
                ? (boardRect.bottom - canvasRect.top) / scale + 20 + lane / 3
                : source.y + 32 + lane / 3;
            const rightChannel = Math.max(
                source.x,
                destination.x,
                sourceNodeRect ? (sourceNodeRect.right - canvasRect.left) / scale : source.x,
            ) + 48 + lane;
            return [
                source,
                { x: source.x, y: guideY },
                { x: rightChannel, y: guideY },
                { x: rightChannel, y: destination.y },
                destination,
            ];
        }

        const horizontalDirection = destination.x >= source.x ? 1 : -1;
        const offset = 36 + lane;
        const firstX = source.x + horizontalDirection * offset;
        const lastX = destination.x - horizontalDirection * offset;
        const middleY = source.y + (destination.y - source.y) / 2;
        if (Math.abs(destination.x - source.x) > 180) {
            return [source, { x: firstX, y: source.y }, { x: firstX, y: middleY }, { x: lastX, y: middleY }, { x: lastX, y: destination.y }, destination];
        }
        const middleX = source.x + (destination.x - source.x) / 2 + lane;
        return [source, { x: middleX, y: source.y }, { x: middleX, y: destination.y }, destination];
    }

    function routePoints(link) {
        const endpoints = endpointForLink(link);
        if (!endpoints.source || !endpoints.destination) return null;
        const manual = state.layout?.routes?.[String(link.id)] || [];
        if (manualRouteIsUsable(manual, endpoints.source, endpoints.destination)) {
            return { points: [endpoints.source, ...manual, endpoints.destination], endpoints, manual: true };
        }
        return { points: autoRoute(link, endpoints), endpoints, manual: false };
    }

    function connectorKind(link) {
        const equipmentByPort = new Map();
        (state.containerData?.equipment || []).forEach((equipment) => {
            (equipment.ports || []).forEach((port) => equipmentByPort.set(String(port.id), equipment));
        });
        const equipment = equipmentByPort.get(String(link.destination_port_id));
        const destinationPort = (equipment?.ports || []).find((port) => String(port.id) === String(link.destination_port_id));
        const raw = String(
            destinationPort?.type
            || equipment?.connector_type
            || equipment?.metadata?.pon_connector
            || "",
        ).toLowerCase().replace("/", "_");
        if (raw.includes("apc")) return "apc";
        if (raw.includes("upc")) return "upc";
        return "";
    }

    function ensureSvgElement(tag, className, linkId) {
        const svg = svgElement();
        let element = qs(`${tag}.${className}[data-v07512-link="${linkId}"]`, svg);
        if (!element) {
            element = document.createElementNS("http://www.w3.org/2000/svg", tag);
            element.classList.add(className);
            element.dataset.v07512Link = String(linkId);
            svg.appendChild(element);
        }
        return element;
    }

    function nearestSegmentIndex(points, point) {
        let bestIndex = 0;
        let bestDistance = Infinity;
        for (let index = 0; index < points.length - 1; index += 1) {
            const a = points[index];
            const b = points[index + 1];
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const lengthSquared = dx * dx + dy * dy || 1;
            const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / lengthSquared));
            const projection = { x: a.x + t * dx, y: a.y + t * dy };
            const currentDistance = distance(projection, point);
            if (currentDistance < bestDistance) {
                bestDistance = currentDistance;
                bestIndex = index;
            }
        }
        return bestIndex;
    }

    async function saveLayout() {
        const id = currentContainerId();
        if (!id || !state.layout) return;
        await request(`/api/map/elements/${id}/container-layout-v3/`, {
            method: "PATCH",
            body: JSON.stringify({ layout: state.layout }),
        });
    }

    function renderPluginHandles() {
        const svg = svgElement();
        if (!svg) return;
        qsa(".master-link-handle-v07512", svg).forEach((element) => element.remove());
        if (!state.selectedLinkId) return;
        const points = state.layout?.routes?.[String(state.selectedLinkId)] || [];
        points.forEach((point, index) => {
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.classList.add("master-link-handle-v07512");
            circle.setAttribute("cx", point.x);
            circle.setAttribute("cy", point.y);
            circle.setAttribute("r", "8");
            circle.addEventListener("pointerdown", (event) => {
                event.preventDefault();
                event.stopPropagation();
                const move = (moveEvent) => {
                    const rect = svg.getBoundingClientRect();
                    const scale = canvasScale();
                    point.x = (moveEvent.clientX - rect.left) / scale;
                    point.y = (moveEvent.clientY - rect.top) / scale;
                    circle.setAttribute("cx", point.x);
                    circle.setAttribute("cy", point.y);
                    rewriteLinks();
                };
                const up = async () => {
                    window.removeEventListener("pointermove", move);
                    await saveLayout().catch((error) => notify(error.message, true));
                };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", up, { once: true });
            });
            circle.addEventListener("contextmenu", async (event) => {
                event.preventDefault();
                points.splice(index, 1);
                await saveLayout();
                rewriteLinks();
            });
            svg.appendChild(circle);
        });
    }

    function linkById(id) {
        return (state.containerData?.links || []).find((link) => String(link.id) === String(id));
    }

    function bindHitPath(hit, link, route) {
        hit.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            state.selectedLinkId = String(link.id);
            qsa("[data-master-link]", svgElement()).forEach((path) => path.classList.toggle("selected", String(path.dataset.masterLink) === state.selectedLinkId));
            renderPluginHandles();
        };
        hit.ondblclick = async (event) => {
            event.preventDefault();
            event.stopPropagation();
            const svg = svgElement();
            const rect = svg.getBoundingClientRect();
            const scale = canvasScale();
            const point = { x: (event.clientX - rect.left) / scale, y: (event.clientY - rect.top) / scale };
            const manual = state.layout.routes[String(link.id)] || [];
            const currentPoints = [route.endpoints.source, ...manual, route.endpoints.destination];
            const insertAfter = nearestSegmentIndex(currentPoints, point);
            manual.splice(Math.max(0, insertAfter), 0, point);
            state.layout.routes[String(link.id)] = manual;
            state.selectedLinkId = String(link.id);
            await saveLayout();
            rewriteLinks();
            notify("Ponto de dobra criado exatamente no local do duplo clique.");
        };
        hit.oncontextmenu = async (event) => {
            event.preventDefault();
            event.stopPropagation();
            const accepted = window.mapV0758?.confirmAction
                ? await window.mapV0758.confirmAction({ title: "Excluir ligação", message: "A ligação será removida.", confirmLabel: "Excluir", danger: true })
                : window.confirm("Excluir esta ligação?");
            if (!accepted) return;
            await request(`/api/map/elements/${currentContainerId()}/equipment-links/${link.id}/`, { method: "DELETE" });
            await refreshContainer();
        };
    }

    function rewriteLinks() {
        cancelAnimationFrame(state.routeFrame);
        state.routeFrame = requestAnimationFrame(() => {
            const svg = svgElement();
            if (!svg || !state.containerData || !state.layout) return;
            qsa("[data-v07512-link]", svg).forEach((element) => element.remove());
            (state.containerData.links || []).forEach((link) => {
                const route = routePoints(link);
                if (!route) return;
                const d = roundedPolyline(route.points, 11);
                const visible = qs(`[data-master-link="${link.id}"]`, svg);
                if (visible) {
                    visible.setAttribute("d", d);
                    visible.style.strokeLinejoin = "round";
                    visible.style.strokeLinecap = "round";
                }
                const hit = ensureSvgElement("path", "master-link-hit-v07512", link.id);
                hit.setAttribute("d", d);
                bindHitPath(hit, link, route);

                const kind = connectorKind(link);
                if (kind && route.endpoints.destination) {
                    const connector = ensureSvgElement("rect", `master-link-connector-${kind}-v07512`, link.id);
                    connector.setAttribute("x", route.endpoints.destination.x - 6);
                    connector.setAttribute("y", route.endpoints.destination.y - 5);
                    connector.setAttribute("width", "12");
                    connector.setAttribute("height", "10");
                    connector.setAttribute("rx", "2");
                }
            });
            renderPluginHandles();
        });
    }

    function ensureTooltip() {
        if (state.tooltip) return state.tooltip;
        const tooltip = document.createElement("div");
        tooltip.id = "map-v07512-port-tooltip";
        tooltip.hidden = true;
        document.body.appendChild(tooltip);
        state.tooltip = tooltip;
        return tooltip;
    }

    function linkedTargetForPort(portId) {
        const link = (state.containerData?.links || []).find((item) => String(item.source_port_id) === String(portId) || String(item.destination_port_id) === String(portId));
        if (!link) return "";
        return String(link.source_port_id) === String(portId) ? link.destination : link.source;
    }

    function equipmentForPort(portId) {
        return (state.containerData?.equipment || []).find((equipment) => (equipment.ports || []).some((port) => String(port.id) === String(portId)));
    }

    function portData(portId) {
        const equipment = equipmentForPort(portId);
        const port = (equipment?.ports || []).find((item) => String(item.id) === String(portId));
        return { equipment, port };
    }

    function decoratePorts() {
        const root = containerRoot();
        if (!root || !state.containerData) return;
        qsa("[data-port-id]", root).forEach((button) => {
            const { equipment, port } = portData(button.dataset.portId);
            if (!port) return;
            button.dataset.v07512Label = `${equipment.name} · ${port.label}`;
            button.dataset.v07512Connected = linkedTargetForPort(port.id);
            button.dataset.v07512EquipmentType = equipment.type || "";
            button.dataset.v07512Connector = equipment.connector_type || equipment.metadata?.pon_connector || port.type || "";
            button.classList.add("master-port-hit-v07512");
        });
    }

    function compatible(first, candidate) {
        if (!first || !candidate || first === candidate) return false;
        const firstType = first.dataset.portType || "";
        const candidateType = candidate.dataset.portType || "";
        const optical = new Set(["pon", "dio", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "qsfp_plus_40g", "qsfp28_100g", "sc_apc", "sc_upc", "lc"]);
        const copper = new Set(["rj45_100m", "rj45_1g", "rj45_2g5"]);
        if (firstType === "wireless" || candidateType === "wireless") return firstType === candidateType;
        if (optical.has(firstType) && optical.has(candidateType)) return true;
        return copper.has(firstType) && copper.has(candidateType);
    }

    function refreshCompatibleHighlights() {
        const root = containerRoot();
        if (!root) return;
        const selected = qs("[data-port-id].selected", root);
        qsa("[data-port-id]", root).forEach((button) => {
            const isCompatible = Boolean(selected && compatible(selected, button) && !button.dataset.linkId);
            button.classList.toggle("port-compatible-v07512", isCompatible);
            button.classList.toggle("port-incompatible-v07512", Boolean(selected && button !== selected && !isCompatible));
        });
    }

    function addOltBoardGuides() {
        const root = containerRoot();
        qsa(".master-olt-slot-v07510", root).forEach((slot) => {
            const kind = String(slot.dataset.slotKind || "").toLowerCase();
            const isPon = kind === "pon" || kind === "gpon" || qsa('[data-port-type="pon"]', slot).length > 0;
            slot.classList.toggle("master-olt-board-v07512", isPon);
            if (!isPon || slot.nextElementSibling?.classList.contains("master-olt-cable-guide-v07512")) return;
            const guide = document.createElement("div");
            guide.className = "master-olt-cable-guide-v07512";
            guide.setAttribute("aria-hidden", "true");
            slot.after(guide);
        });
    }

    function injectRefreshButtons() {
        const root = containerRoot();
        qsa("[data-equipment-node]", root).forEach((node) => {
            const actions = qs(".master-node-actions", node);
            if (!actions || qs("[data-refresh-node-v07512]", actions)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.refreshNodeV07512 = node.dataset.equipmentNode;
            button.title = "Atualizar este equipamento no editor";
            button.setAttribute("aria-label", "Atualizar equipamento");
            button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 6v5h-5M4 18v-5h5"></path><path d="M6.1 9A7 7 0 0 1 18 6l2 5M17.9 15A7 7 0 0 1 6 18l-2-5"></path></svg>';
            actions.prepend(button);
        });
    }

    async function loadContainerSnapshot(data = null) {
        const id = currentContainerId();
        if (!id) return;
        state.containerId = id;
        const [equipment, layout] = await Promise.all([
            data ? Promise.resolve(data) : request(`/api/map/elements/${id}/equipment/`),
            request(`/api/map/elements/${id}/container-layout-v3/`).catch(() => ({ layout: {} })),
        ]);
        state.containerData = equipment;
        state.layout = { positions: {}, cablePositions: {}, routes: {}, notes: [], ...(layout.layout || {}) };
        state.layout.routes ||= {};
        state.layout.notes ||= [];
    }

    async function enhanceContainer(data = null) {
        if (!currentContainerId() || !containerRoot()) return;
        await loadContainerSnapshot(data).catch((error) => notify(error.message, true));
        addOltBoardGuides();
        decoratePorts();
        injectRefreshButtons();
        rewriteLinks();
        if (state.resizeObserver) state.resizeObserver.disconnect();
        if (window.ResizeObserver) {
            state.resizeObserver = new ResizeObserver(() => rewriteLinks());
            const canvas = canvasElement();
            if (canvas) state.resizeObserver.observe(canvas);
        }
    }

    async function refreshContainer() {
        const id = currentContainerId();
        if (!id) return;
        await window.mapMasterSuite?.openContainerWorkspace?.(id);
        await enhanceContainer();
    }

    async function editNote(index) {
        await loadContainerSnapshot();
        const note = state.layout.notes[index];
        if (!note) return;
        const text = window.mapV0758?.editLongText
            ? await window.mapV0758.editLongText({ title: "Editar nota técnica", label: "Texto", value: note.text || "" })
            : window.prompt("Editar nota técnica", note.text || "");
        if (text === null || text === undefined || !String(text).trim()) return;
        note.text = String(text).trim();
        await saveLayout();
        await refreshContainer();
    }

    async function deleteNote(index) {
        await loadContainerSnapshot();
        if (!state.layout.notes[index]) return;
        const accepted = window.mapV0758?.confirmAction
            ? await window.mapV0758.confirmAction({ title: "Excluir nota", message: "A nota será removida do Canvas.", confirmLabel: "Excluir", danger: true })
            : window.confirm("Excluir esta nota?");
        if (!accepted) return;
        state.layout.notes.splice(index, 1);
        await saveLayout();
        await refreshContainer();
    }

    function beginNoteDrag(event, noteNode) {
        if (event.button !== 0 || event.target.closest("button")) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const index = Number(noteNode.dataset.canvasNote);
        const start = parseTransform(noteNode);
        const scale = canvasScale();
        const origin = { x: event.clientX, y: event.clientY };
        noteNode.classList.add("dragging-v07512");
        const move = (moveEvent) => {
            const x = start.x + (moveEvent.clientX - origin.x) / scale;
            const y = start.y + (moveEvent.clientY - origin.y) / scale;
            noteNode.style.transform = `translate(${x}px,${y}px)`;
            noteNode.dataset.v07512X = String(x);
            noteNode.dataset.v07512Y = String(y);
        };
        const up = async () => {
            window.removeEventListener("pointermove", move);
            noteNode.classList.remove("dragging-v07512");
            await loadContainerSnapshot();
            const note = state.layout.notes[index];
            if (note) {
                const current = parseTransform(noteNode);
                note.x = Math.round(current.x);
                note.y = Math.round(current.y);
                await saveLayout();
            }
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up, { once: true });
    }

    function selectedFiberButton() {
        return qs("#map-master-container .master-cable-fiber.selected");
    }

    function directDropTarget(button) {
        const { equipment, port } = portData(button.dataset.portId);
        if (!equipment || !port) return false;
        // O conector TRASEIRO do DIO não é interceptado aqui: o fluxo base
        // selectContainerPort() continua recebendo qualquer fibra de cabo
        // selecionada e cria a fusão traseira normal. Esta extensão cuida
        // somente das terminações diretas especiais de DROP em PTO/ONU.
        if (equipment.type === "pto") return true;
        return equipment.type === "onu" && port.type === "pon";
    }

    async function terminateDropDirectly(event, button) {
        const fiber = selectedFiberButton();
        if (!fiber || !directDropTarget(button)) return false;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const { equipment } = portData(button.dataset.portId);
        const connector = String(equipment.connector_type || equipment.metadata?.pon_connector || "sc_apc").toLowerCase().replace("/", "_");
        await request(`/api/map/elements/${currentContainerId()}/equipment-links/`, {
            method: "POST",
            body: JSON.stringify({
                cable_fiber_id: Number(fiber.dataset.cableFiber),
                destination_port_id: Number(button.dataset.portId),
                termination_method: "direct_connector",
                connector_type: connector,
            }),
        });
        notify("DROP terminado diretamente na porta óptica.");
        await refreshContainer();
        return true;
    }

    function ensurePtpDialog() {
        if (state.ptpDialog) return state.ptpDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-v07512-ptp-dialog";
        dialog.className = "map-v07512-ptp-dialog";
        dialog.innerHTML = `
            <form>
                <header><div><strong>Ligar PTP entre torres</strong><small>Escolha a torre e o rádio wireless do outro lado.</small></div><button type="button" data-close>×</button></header>
                <label>Torre de destino<select name="tower_id" required></select></label>
                <label>Equipamento / porta wireless<select name="destination_port_id" required></select></label>
                <p data-status></p>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Criar enlace PTP</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        state.ptpDialog = dialog;
        return dialog;
    }

    async function openPtpWizard(sourcePortId) {
        const accepted = window.mapV0758?.confirmAction
            ? await window.mapV0758.confirmAction({ title: "Ligar PTP?", message: "Deseja criar um enlace wireless entre esta torre e outra torre?", confirmLabel: "Sim, escolher destino", cancelLabel: "Não" })
            : window.confirm("Ligar PTP entre esta torre e outra torre?");
        if (!accepted) return;
        const data = await request(`/api/map/ptp-links/candidates/?source_port_id=${encodeURIComponent(sourcePortId)}`);
        if (!data.candidates.length) return notify("Nenhuma porta wireless livre foi encontrada em outra torre deste projeto.", true);
        const dialog = ensurePtpDialog();
        const form = dialog.querySelector("form");
        const towerSelect = form.elements.tower_id;
        const targetSelect = form.elements.destination_port_id;
        const towers = [...new Map(data.candidates.map((row) => [String(row.tower_id), row.tower_name])).entries()];
        towerSelect.innerHTML = towers.map(([id, name]) => `<option value="${id}">${name}</option>`).join("");
        const renderTargets = () => {
            const rows = data.candidates.filter((row) => String(row.tower_id) === String(towerSelect.value));
            targetSelect.innerHTML = rows.map((row) => `<option value="${row.port_id}">${row.equipment_name} · ${row.port_label}</option>`).join("");
        };
        towerSelect.onchange = renderTargets;
        renderTargets();
        form.onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request("/api/map/ptp-links/", {
                    method: "POST",
                    body: JSON.stringify({ source_port_id: Number(sourcePortId), destination_port_id: Number(targetSelect.value) }),
                });
                dialog.close();
                notify("Enlace PTP criado. A linha tracejada foi adicionada ao mapa.");
                await refreshPtpLayer();
                await refreshContainer();
            } catch (error) {
                qs("[data-status]", dialog).textContent = error.message;
            }
        };
        dialog.showModal();
    }

    async function wirelessPortAction(event, button) {
        if (button.dataset.portType !== "wireless") return false;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        const current = state.ptpLinks.find((link) => String(link.source.port_id) === String(button.dataset.portId) || String(link.destination.port_id) === String(button.dataset.portId));
        if (current) {
            const accepted = window.mapV0758?.confirmAction
                ? await window.mapV0758.confirmAction({ title: "Enlace PTP existente", message: `${current.source.tower_name} ↔ ${current.destination.tower_name}. Deseja remover?`, confirmLabel: "Remover enlace", danger: true })
                : window.confirm("Remover enlace PTP existente?");
            if (accepted) {
                await request(`/api/map/ptp-links/${current.id}/`, { method: "DELETE" });
                await refreshPtpLayer();
                await refreshContainer();
            }
            return true;
        }
        await openPtpWizard(button.dataset.portId);
        return true;
    }

    async function refreshPtpLayer() {
        const projectId = currentProjectId();
        const map = window.networkMap?.map;
        if (!projectId || !map || !window.L) return;
        if (!state.ptpLayer) state.ptpLayer = L.layerGroup().addTo(map);
        state.ptpLayer.clearLayers();
        const data = await request(`/api/map/ptp-links/?project_id=${encodeURIComponent(projectId)}`);
        state.ptpLinks = data.links || [];
        state.ptpLinks.forEach((link) => {
            const line = L.polyline(
                [[link.source.latitude, link.source.longitude], [link.destination.latitude, link.destination.longitude]],
                { color: "#f59e0b", weight: 2, opacity: .92, dashArray: "8 8", lineCap: "round", className: "map-ptp-link-v07512" },
            );
            line.bindTooltip(`${link.source.tower_name} ↔ ${link.destination.tower_name}<br>${link.source.equipment_name} ↔ ${link.destination.equipment_name}`, { sticky: true, className: "map-ptp-tooltip-v07512" });
            const remove = document.body.dataset.canEdit === "true"
                ? `<br><button type="button" data-delete-ptp-link="${link.id}">Remover enlace</button>` : "";
            line.bindPopup(`<strong>Enlace PTP</strong><br>${link.source.tower_name} ↔ ${link.destination.tower_name}<br>${link.source.equipment_name} · ${link.source.port_label}<br>${link.destination.equipment_name} · ${link.destination.port_label}${remove}`);
            line.on("popupopen", () => {
                const button = document.querySelector(`[data-delete-ptp-link="${link.id}"]`);
                if (button) button.onclick = async () => {
                    await request(`/api/map/ptp-links/${link.id}/`, { method: "DELETE" });
                    map.closePopup();
                    await refreshPtpLayer();
                };
            });
            line.addTo(state.ptpLayer);
        });
    }

    function parseCoordinates(value) {
        const values = String(value || "").trim().match(/[-+]?\d{1,3}(?:[.,]\d+)?/g);
        if (!values || values.length !== 2) return null;
        const latitude = Number(values[0].replace(",", "."));
        const longitude = Number(values[1].replace(",", "."));
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
        return { latitude, longitude };
    }

    function focusCoordinates(coordinates) {
        const map = window.networkMap?.map;
        if (!map) return;
        map.setView([coordinates.latitude, coordinates.longitude], 20);
        if (state.gpsMarker) map.removeLayer(state.gpsMarker);
        state.gpsMarker = L.circleMarker([coordinates.latitude, coordinates.longitude], {
            radius: 9,
            color: "#ffffff",
            weight: 2,
            fillColor: "#06b6d4",
            fillOpacity: 1,
        }).addTo(map).bindTooltip(`${coordinates.latitude.toFixed(7)}, ${coordinates.longitude.toFixed(7)}`, { permanent: false }).openTooltip();
        qs("#map-search-results").hidden = true;
        notify("Coordenadas localizadas no mapa.");
    }

    function interceptCoordinateSearch(event) {
        const query = qs("#map-search-query")?.value;
        const coordinates = parseCoordinates(query);
        if (!coordinates) return false;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        focusCoordinates(coordinates);
        return true;
    }

    function installGlobalListeners() {
        document.addEventListener("map:container-rendered", (event) => {
            if (!currentContainerId()) return;
            window.setTimeout(() => enhanceContainer(event.detail?.data || null), 0);
        });
        document.addEventListener("map:container-opening", () => window.setTimeout(() => enhanceContainer(), 40));

        document.addEventListener("mouseover", (event) => {
            const button = event.target.closest?.("#map-master-container [data-port-id]");
            if (!button) return;
            const tooltip = ensureTooltip();
            const connected = button.dataset.v07512Connected;
            tooltip.innerHTML = `<strong>${button.dataset.v07512Label || button.textContent.trim()}</strong><span class="${connected ? "occupied" : "free"}">${connected ? `🔗 Ligado a: ${connected}` : "✅ Status: Livre"}</span>`;
            tooltip.hidden = false;
        });
        document.addEventListener("mousemove", (event) => {
            if (!state.tooltip || state.tooltip.hidden) return;
            state.tooltip.style.left = `${event.clientX + 16}px`;
            state.tooltip.style.top = `${event.clientY + 16}px`;
        });
        document.addEventListener("mouseout", (event) => {
            if (!event.target.closest?.("#map-master-container [data-port-id]")) return;
            if (state.tooltip) state.tooltip.hidden = true;
        });

        document.addEventListener("pointerdown", (event) => {
            const note = event.target.closest?.("#map-master-container .master-canvas-note");
            if (note) beginNoteDrag(event, note);
        }, true);
        document.addEventListener("click", async (event) => {
            const refresh = event.target.closest?.("[data-refresh-node-v07512]");
            if (refresh) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                await refreshContainer();
                notify("Equipamento atualizado dentro do editor.");
                return;
            }
            const edit = event.target.closest?.("#map-master-container [data-edit-note]");
            if (edit) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                await editNote(Number(edit.dataset.editNote));
                return;
            }
            const remove = event.target.closest?.("#map-master-container [data-delete-note]");
            if (remove) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                await deleteNote(Number(remove.dataset.deleteNote));
                return;
            }
            const port = event.target.closest?.("#map-master-container [data-port-id]");
            if (port) {
                if (await wirelessPortAction(event, port)) return;
                if (await terminateDropDirectly(event, port)) return;
                window.setTimeout(refreshCompatibleHighlights, 0);
            }
        }, true);

        const searchButton = qs("#map-search-button");
        searchButton?.addEventListener("click", (event) => interceptCoordinateSearch(event), true);
        qs("#map-search-query")?.addEventListener("keydown", (event) => {
            if (event.key === "Enter") interceptCoordinateSearch(event);
        }, true);
        qs("#map-search-mode")?.addEventListener("change", () => {
            const input = qs("#map-search-query");
            if (input) input.placeholder = "Endereço, equipamento ou -24.45, -50.75";
        });
        qs("#project-select")?.addEventListener("change", () => window.setTimeout(() => refreshPtpLayer().catch((error) => notify(error.message, true)), 120));
        window.addEventListener("resize", rewriteLinks);
        window.addEventListener("pointerup", () => window.setTimeout(rewriteLinks, 20));
    }

    async function init() {
        for (let attempt = 0; attempt < 100 && (!window.networkMap || !window.mapMasterSuite); attempt += 1) {
            await new Promise((resolve) => window.setTimeout(resolve, 50));
        }
        installGlobalListeners();
        await refreshPtpLayer().catch(() => {});
        window.mapV07512 = {
            version: VERSION,
            enhanceContainer,
            refreshPtpLayer,
            parseCoordinates,
            rewriteLinks,
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
