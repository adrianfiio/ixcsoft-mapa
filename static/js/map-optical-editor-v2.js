(function () {
    "use strict";

    const mapApi = () => window.networkMap || null;
    const unifilarDialog = document.getElementById("unifilar-dialog");
    const unifilarContent = document.getElementById("unifilar-content");
    const projectSelect = document.getElementById("project-select");
    if (!unifilarDialog || !unifilarContent || !projectSelect) return;

    let insertion = null;
    let lineEditEnabled = false;
    let selectedLinkKey = null;
    let routeLayout = null;
    let routeElementId = null;
    let decoratingSvg = false;
    let enhanceTimer = null;

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (cookie) return decodeURIComponent(cookie.split("=")[1]);
        return document.querySelector("[name='csrfmiddlewaretoken']")?.value
            || document.querySelector("meta[name='csrf-token']")?.content
            || "";
    }

    async function request(path, options = {}) {
        const headers = {
            Accept: "application/json",
            ...(options.headers || {}),
        };
        if (options.body && !(options.body instanceof FormData)) {
            headers["Content-Type"] = headers["Content-Type"] || "application/json";
        }
        if (options.method && options.method !== "GET") {
            headers["X-CSRFToken"] = csrfToken();
        }
        const response = await fetch(path, {
            credentials: "same-origin",
            ...options,
            headers,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = data.detail || data.error || Object.values(data.errors || {}).flat().join(" ");
            throw new Error(detail || `HTTP ${response.status}`);
        }
        return data;
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function notify(message, error = false) {
        if (mapApi()?.notify) mapApi().notify(message, error);
        const status = document.querySelector("#cable-box-insert-v2 [data-box-status]");
        if (status) {
            status.textContent = message || "";
            status.classList.toggle("error", error);
        }
    }

    function flattenCableCoordinates(cable) {
        const geometry = cable?.geometry || {};
        const lines = geometry.type === "MultiLineString"
            ? geometry.coordinates
            : geometry.type === "LineString"
                ? [geometry.coordinates]
                : [];
        return lines.filter((line) => Array.isArray(line) && line.length > 1);
    }

    function nearestCablePoint(latlng, cable) {
        const map = mapApi()?.map;
        if (!map) return latlng;
        const point = map.latLngToLayerPoint(latlng);
        let best = null;
        flattenCableCoordinates(cable).forEach((line) => {
            for (let index = 0; index < line.length - 1; index += 1) {
                const aLatLng = L.latLng(line[index][1], line[index][0]);
                const bLatLng = L.latLng(line[index + 1][1], line[index + 1][0]);
                const a = map.latLngToLayerPoint(aLatLng);
                const b = map.latLngToLayerPoint(bLatLng);
                const vx = b.x - a.x;
                const vy = b.y - a.y;
                const denominator = vx * vx + vy * vy;
                const ratio = denominator === 0 ? 0 : Math.max(0, Math.min(1,
                    ((point.x - a.x) * vx + (point.y - a.y) * vy) / denominator));
                const projected = L.point(a.x + ratio * vx, a.y + ratio * vy);
                const distance = projected.distanceTo(point);
                if (!best || distance < best.distance) {
                    best = { distance, latlng: map.layerPointToLatLng(projected) };
                }
            }
        });
        return best?.latlng || latlng;
    }

    function middleCablePoint(cable) {
        const lines = flattenCableCoordinates(cable);
        const line = lines[0] || [];
        if (!line.length) return mapApi()?.map?.getCenter();
        const coordinate = line[Math.floor((line.length - 1) / 2)];
        return L.latLng(coordinate[1], coordinate[0]);
    }

    function previewIcon(type) {
        const label = type === "cto" ? "CTO" : type === "cdo" ? "CDO" : "CEO";
        return L.divIcon({
            className: "",
            html: `<div class="box-preview-marker ${escapeHtml(type)}"><span>${label}</span></div>`,
            iconSize: [54, 54],
            iconAnchor: [27, 27],
        });
    }

    function removeInsertion() {
        if (!insertion) return;
        const map = mapApi()?.map;
        if (map && insertion.marker) map.removeLayer(insertion.marker);
        insertion.panel?.remove();
        insertion = null;
        document.body.classList.remove("box-insertion-active-v2");
    }

    function makeDraggablePanel(panel) {
        const handle = panel.querySelector("header");
        if (!handle) return;
        handle.addEventListener("pointerdown", (event) => {
            if (event.target.closest("button, input, select")) return;
            const rect = panel.getBoundingClientRect();
            const offsetX = event.clientX - rect.left;
            const offsetY = event.clientY - rect.top;
            handle.setPointerCapture?.(event.pointerId);
            const move = (moveEvent) => {
                panel.style.left = `${Math.max(8, Math.min(window.innerWidth - panel.offsetWidth - 8, moveEvent.clientX - offsetX))}px`;
                panel.style.top = `${Math.max(8, Math.min(window.innerHeight - panel.offsetHeight - 8, moveEvent.clientY - offsetY))}px`;
                panel.style.right = "auto";
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", up);
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        });
    }

    async function loadInsertionData(cableId) {
        const projectId = projectSelect.value;
        if (!projectId) throw new Error("Selecione um projeto antes de inserir a caixa.");
        const [cableData, elements] = await Promise.all([
            request(`/api/map/cables/${cableId}/`),
            request(`/api/map/elements/?project_id=${encodeURIComponent(projectId)}`),
        ]);
        return {
            projectId,
            cable: cableData.cable,
            elements: elements.features || [],
        };
    }

    function syncInsertionFields() {
        if (!insertion) return;
        const panel = insertion.panel;
        const mode = panel.querySelector("[name='box_mode']").value;
        const type = panel.querySelector("[name='box_type']").value;
        panel.querySelector("[data-new-box-fields]").hidden = mode !== "new";
        panel.querySelector("[data-existing-box-fields]").hidden = mode !== "existing";
        panel.querySelector("[data-cto-capacity]").hidden = mode !== "new" || type !== "cto";
        const action = panel.querySelector("[name='box_action']");
        if (type === "cto" && action.value === "pass") action.value = "cut";
        const marker = insertion.marker;
        if (mode === "new") {
            marker.dragging?.enable();
            marker.setIcon(previewIcon(type));
        } else {
            marker.dragging?.disable();
            const selected = panel.querySelector("[name='existing_element_id']").value;
            const feature = insertion.elements.find((item) => String(item.properties?.id) === String(selected));
            if (feature?.geometry?.coordinates) {
                marker.setLatLng([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
                const subtype = String(feature.properties?.subtipo || feature.properties?.element_subtype || "").toLowerCase();
                marker.setIcon(previewIcon(feature.properties?.tipo === "cto" ? "cto" : subtype === "cdo" ? "cdo" : "ceo"));
            }
        }
    }

    async function confirmInsertion() {
        if (!insertion) return;
        const panel = insertion.panel;
        const confirm = panel.querySelector("[data-box-confirm]");
        const mode = panel.querySelector("[name='box_mode']").value;
        const action = panel.querySelector("[name='box_action']").value;
        let elementId = null;
        let createdElementId = null;
        confirm.disabled = true;
        try {
            notify(action === "cut" ? "Salvando a caixa e cortando o cabo..." : "Salvando a passagem do cabo...");
            if (mode === "existing") {
                elementId = panel.querySelector("[name='existing_element_id']").value;
                if (!elementId) throw new Error("Escolha a caixa existente.");
            } else {
                const type = panel.querySelector("[name='box_type']").value;
                const name = panel.querySelector("[name='box_name']").value.trim();
                if (!name) throw new Error("Informe o nome da caixa.");
                const position = insertion.marker.getLatLng();
                const capacity = Number(panel.querySelector("[name='cto_capacity_v2']").value || 8);
                const ratioCapacity = [2, 4, 8, 16, 32, 64].includes(capacity) ? capacity : capacity <= 8 ? 8 : capacity <= 16 ? 16 : capacity <= 32 ? 32 : 64;
                const payload = {
                    project: insertion.projectId,
                    element_type: type === "cto" ? "cto" : "splice_box",
                    element_subtype: type,
                    latitude: position.lat,
                    longitude: position.lng,
                    name,
                    code: panel.querySelector("[name='box_code']").value.trim() || name,
                    description: `Inserida manualmente sobre o cabo ${insertion.cable.name}.`,
                    status: "no_data",
                    enabled: true,
                };
                if (type === "cto") {
                    payload.cto_capacity = capacity;
                    payload.splitter_ratio = `1:${ratioCapacity}`;
                    payload.splitter_ports = capacity;
                }
                const result = await request("/api/map/elements/create/", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });
                elementId = result.element?.id;
                createdElementId = elementId;
                if (!elementId) throw new Error("O servidor não retornou a caixa criada.");
            }

            if (action === "cut") {
                await request(`/api/map/elements/${elementId}/cables/${insertion.cable.id}/cut/`, {
                    method: "POST",
                    body: JSON.stringify({ max_distance_m: 80 }),
                });
            } else {
                await request(`/api/map/elements/${elementId}/cables/${insertion.cable.id}/pass/`, {
                    method: "POST",
                    body: JSON.stringify({ max_distance_m: 80 }),
                });
            }
            removeInsertion();
            await mapApi()?.loadStructure?.(false);
            notify(action === "cut"
                ? "Caixa posicionada e cabo dividido em dois segmentos."
                : "Caixa posicionada e passagem do cabo registrada.");
        } catch (error) {
            if (createdElementId) {
                try {
                    await request(`/api/map/elements/${createdElementId}/`, { method: "DELETE" });
                } catch (_cleanupError) {
                    // A mensagem principal continua sendo a falha da operação.
                }
            }
            notify(error.message, true);
            confirm.disabled = false;
        }
    }

    async function openInsertion(cableId) {
        removeInsertion();
        const data = await loadInsertionData(cableId);
        const map = mapApi()?.map;
        if (!map) throw new Error("Mapa Leaflet indisponível.");
        const popupPoint = map._popup?.getLatLng?.() || middleCablePoint(data.cable);
        const initial = nearestCablePoint(popupPoint, data.cable);
        map.closePopup();

        const existingBoxes = data.elements.filter((feature) => ["cto", "splice_box"].includes(feature.properties?.tipo));
        const panel = document.createElement("section");
        panel.id = "cable-box-insert-v2";
        panel.innerHTML = `
            <header><div><strong>Inserir caixa no cabo</strong><small>${escapeHtml(data.cable.name)}</small></div><button type="button" data-box-close aria-label="Fechar">×</button></header>
            <div class="box-insert-body-v2">
                <label>Operação
                    <select name="box_mode"><option value="new">Criar nova caixa</option><option value="existing">Conectar caixa existente</option></select>
                </label>
                <div data-new-box-fields>
                    <div class="box-insert-grid-v2">
                        <label>Tipo<select name="box_type"><option value="cto">CTO</option><option value="cdo">CDO</option><option value="ceo">CEO</option></select></label>
                        <label data-cto-capacity>Portas da CTO<select name="cto_capacity_v2"><option>8</option><option selected>16</option><option>24</option><option>32</option><option>48</option><option>64</option></select></label>
                    </div>
                    <label>Nome<input name="box_name" maxlength="180" value="CTO-NOVA"></label>
                    <label>Código<input name="box_code" maxlength="100" placeholder="Gerado pelo nome"></label>
                    <p class="box-help-v2">Arraste a prévia sobre o cabo. A posição somente será gravada ao confirmar.</p>
                </div>
                <div data-existing-box-fields hidden>
                    <label>Caixa existente<select name="existing_element_id"><option value="">Escolha a caixa</option>${existingBoxes.map((feature) => {
                        const subtype = String(feature.properties?.subtipo || feature.properties?.element_subtype || "").toLowerCase();
                        const label = feature.properties?.tipo === "cto" ? "CTO" : subtype === "cdo" ? "CDO" : "CEO";
                        return `<option value="${feature.properties.id}">${label} · ${escapeHtml(feature.properties.nome)}</option>`;
                    }).join("")}</select></label>
                    <p class="box-help-v2">A caixa existente não será movida. O cabo será conectado na posição atual dela.</p>
                </div>
                <label>Comportamento
                    <select name="box_action"><option value="cut">Cortar e criar dois segmentos</option><option value="pass">Passagem sem corte</option></select>
                </label>
                <div class="box-status-v2" data-box-status>Posicione a caixa e confirme.</div>
            </div>
            <footer><button type="button" data-box-cancel>Cancelar</button><button type="button" class="primary" data-box-confirm>Salvar e concluir</button></footer>`;
        document.body.appendChild(panel);
        makeDraggablePanel(panel);
        const marker = L.marker(initial, {
            draggable: true,
            zIndexOffset: 2500,
            icon: previewIcon("cto"),
        }).addTo(map);
        insertion = { ...data, panel, marker };
        document.body.classList.add("box-insertion-active-v2");

        marker.on("drag", () => {
            const snapped = nearestCablePoint(marker.getLatLng(), data.cable);
            marker.setLatLng(snapped);
        });
        panel.querySelector("[data-box-close]").onclick = removeInsertion;
        panel.querySelector("[data-box-cancel]").onclick = removeInsertion;
        panel.querySelector("[data-box-confirm]").onclick = confirmInsertion;
        panel.querySelector("[name='box_mode']").onchange = syncInsertionFields;
        panel.querySelector("[name='box_type']").onchange = (event) => {
            const type = event.target.value;
            const name = panel.querySelector("[name='box_name']");
            if (/^(CTO|CDO|CEO)-NOVA$/.test(name.value)) name.value = `${type.toUpperCase()}-NOVA`;
            syncInsertionFields();
        };
        panel.querySelector("[name='existing_element_id']").onchange = syncInsertionFields;
        syncInsertionFields();
        notify("Arraste a caixa sobre o cabo e confirme para salvar.");
    }

    function renameCableInsertionActions() {
        document.querySelectorAll("[data-insert-cable]").forEach((button) => {
            button.textContent = "Inserir caixa";
            button.title = "Criar ou conectar CTO, CDO ou CEO neste cabo";
        });
    }

    const mapRoot = document.getElementById("map");
    if (mapRoot) {
        new MutationObserver(renameCableInsertionActions).observe(mapRoot, { childList: true, subtree: true });
        renameCableInsertionActions();
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-insert-cable]");
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        openInsertion(button.dataset.insertCable).catch((error) => notify(error.message, true));
    }, true);

    // ---------------------------------------------------------------------
    // Editor manual de linhas no diagrama de fusões
    // ---------------------------------------------------------------------

    function linkKey(path) {
        return path?.dataset?.linkType && path?.dataset?.linkId
            ? `${path.dataset.linkType}:${path.dataset.linkId}`
            : "";
    }

    async function loadRouteLayout(force = false) {
        const elementId = unifilarDialog.dataset.elementId || "";
        if (!elementId) return null;
        if (!force && routeLayout && String(routeElementId) === String(elementId)) return routeLayout;
        const data = await request(`/api/map/elements/${elementId}/layout/`);
        routeElementId = elementId;
        routeLayout = data.layout || {};
        routeLayout.manual_link_routes_v2 = routeLayout.manual_link_routes_v2 || {};
        return routeLayout;
    }

    async function saveManualRoutes() {
        const elementId = unifilarDialog.dataset.elementId || "";
        if (!elementId || !routeLayout) return;
        const current = await request(`/api/map/elements/${elementId}/layout/`);
        const layout = {
            ...(current.layout || {}),
            manual_link_routes_v2: routeLayout.manual_link_routes_v2 || {},
        };
        await request(`/api/map/elements/${elementId}/layout/`, {
            method: "PATCH",
            body: JSON.stringify({ layout }),
        });
    }

    function pathEndpoints(path) {
        try {
            const total = path.getTotalLength();
            const start = path.getPointAtLength(0);
            const end = path.getPointAtLength(total);
            return { start: { x: start.x, y: start.y }, end: { x: end.x, y: end.y } };
        } catch (_error) {
            return null;
        }
    }

    function pathData(start, points, end) {
        const rows = [start, ...(points || []), end];
        return rows.map((point, index) => `${index ? "L" : "M"}${Math.round(point.x * 10) / 10},${Math.round(point.y * 10) / 10}`).join(" ");
    }

    function svgPoint(svg, clientX, clientY) {
        const point = svg.createSVGPoint();
        point.x = clientX;
        point.y = clientY;
        const matrix = svg.getScreenCTM();
        return matrix ? point.matrixTransform(matrix.inverse()) : point;
    }

    function closestSegmentIndex(rows, point) {
        let bestIndex = 0;
        let bestDistance = Infinity;
        for (let index = 0; index < rows.length - 1; index += 1) {
            const a = rows[index];
            const b = rows[index + 1];
            const vx = b.x - a.x;
            const vy = b.y - a.y;
            const denominator = vx * vx + vy * vy;
            const ratio = denominator === 0 ? 0 : Math.max(0, Math.min(1,
                ((point.x - a.x) * vx + (point.y - a.y) * vy) / denominator));
            const x = a.x + ratio * vx;
            const y = a.y + ratio * vy;
            const distance = Math.hypot(point.x - x, point.y - y);
            if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = index;
            }
        }
        return bestIndex;
    }

    function selectedRoute() {
        if (!selectedLinkKey || !routeLayout) return null;
        return routeLayout.manual_link_routes_v2?.[selectedLinkKey] || null;
    }

    function refreshRouteToolbar() {
        const toolbar = unifilarContent.querySelector("[data-route-editor-v2]");
        if (!toolbar) return;
        toolbar.classList.toggle("active", lineEditEnabled);
        toolbar.querySelector("[data-route-edit-toggle]").textContent = lineEditEnabled ? "Concluir linhas" : "Editar linhas";
        toolbar.querySelectorAll("[data-route-selected-action]").forEach((button) => {
            button.disabled = !selectedLinkKey;
        });
        const selected = toolbar.querySelector("[data-route-selected-label]");
        if (selected) selected.textContent = selectedLinkKey ? `Ligação ${selectedLinkKey}` : "Clique em uma linha";
    }

    function decorateSvg() {
        if (decoratingSvg || !unifilarDialog.open) return;
        const svg = unifilarContent.querySelector(".optical-links");
        if (!svg) return;
        decoratingSvg = true;
        svg.querySelectorAll(".manual-route-handle-v2").forEach((node) => node.remove());
        const routes = routeLayout?.manual_link_routes_v2 || {};
        svg.querySelectorAll("path[data-link-type][data-link-id]").forEach((path) => {
            const key = linkKey(path);
            if (!path.dataset.autoD) path.dataset.autoD = path.getAttribute("d") || "";
            path.classList.toggle("route-editable-v2", lineEditEnabled);
            path.classList.toggle("route-selected-v2", key === selectedLinkKey);
            const route = routes[key];
            if (route?.points?.length) {
                const endpoints = pathEndpoints(path);
                if (endpoints) path.setAttribute("d", pathData(endpoints.start, route.points, endpoints.end));
            }
        });

        if (lineEditEnabled && selectedLinkKey) {
            const path = [...svg.querySelectorAll("path[data-link-type][data-link-id]")].find((item) => linkKey(item) === selectedLinkKey);
            const route = routes[selectedLinkKey];
            if (path && route?.points) {
                route.points.forEach((point, index) => {
                    const handle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    handle.setAttribute("cx", point.x);
                    handle.setAttribute("cy", point.y);
                    handle.setAttribute("r", 7);
                    handle.classList.add("manual-route-handle-v2");
                    handle.dataset.pointIndex = String(index);
                    handle.addEventListener("pointerdown", (event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        handle.setPointerCapture?.(event.pointerId);
                        const move = (moveEvent) => {
                            const current = svgPoint(svg, moveEvent.clientX, moveEvent.clientY);
                            route.points[index] = { x: current.x, y: current.y };
                            handle.setAttribute("cx", current.x);
                            handle.setAttribute("cy", current.y);
                            const endpoints = pathEndpoints(path);
                            if (endpoints) path.setAttribute("d", pathData(endpoints.start, route.points, endpoints.end));
                        };
                        const up = () => {
                            window.removeEventListener("pointermove", move);
                            window.removeEventListener("pointerup", up);
                            saveManualRoutes().catch((error) => notify(error.message, true));
                        };
                        window.addEventListener("pointermove", move);
                        window.addEventListener("pointerup", up, { once: true });
                    });
                    handle.addEventListener("contextmenu", (event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        route.points.splice(index, 1);
                        saveManualRoutes().then(decorateSvg).catch((error) => notify(error.message, true));
                    });
                    svg.appendChild(handle);
                });
            }
        }
        decoratingSvg = false;
        refreshRouteToolbar();
    }

    function selectPathForEditing(path) {
        const key = linkKey(path);
        if (!key || !routeLayout) return;
        selectedLinkKey = key;
        const routes = routeLayout.manual_link_routes_v2;
        if (!routes[key]) {
            const endpoints = pathEndpoints(path);
            if (endpoints) {
                const middle = (endpoints.start.x + endpoints.end.x) / 2;
                routes[key] = {
                    points: [
                        { x: middle, y: endpoints.start.y },
                        { x: middle, y: endpoints.end.y },
                    ],
                };
            }
        }
        decorateSvg();
    }

    function bindSvgEditor(svg) {
        if (svg.dataset.routeEditorV2 === "true") return;
        svg.dataset.routeEditorV2 = "true";
        svg.addEventListener("click", (event) => {
            if (!lineEditEnabled) return;
            const path = event.target.closest("path[data-link-type][data-link-id]");
            if (!path) return;
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            selectPathForEditing(path);
        }, true);
        svg.addEventListener("dblclick", (event) => {
            if (!lineEditEnabled) return;
            const path = event.target.closest("path[data-link-type][data-link-id]");
            if (!path) return;
            event.preventDefault();
            event.stopPropagation();
            selectPathForEditing(path);
            const route = selectedRoute();
            const endpoints = pathEndpoints(path);
            if (!route || !endpoints) return;
            const point = svgPoint(svg, event.clientX, event.clientY);
            const rows = [endpoints.start, ...route.points, endpoints.end];
            route.points.splice(closestSegmentIndex(rows, point), 0, { x: point.x, y: point.y });
            saveManualRoutes().then(decorateSvg).catch((error) => notify(error.message, true));
        }, true);
    }

    function installRouteToolbar() {
        const toolbarHost = unifilarContent.querySelector(".fusion-toolbar") || unifilarContent.querySelector(".unifilar-zoom");
        if (!toolbarHost || unifilarContent.querySelector("[data-route-editor-v2]")) return;
        const editor = document.createElement("span");
        editor.className = "manual-route-toolbar-v2";
        editor.dataset.routeEditorV2 = "true";
        editor.innerHTML = `
            <button type="button" data-route-edit-toggle>Editar linhas</button>
            <span data-route-selected-label>Clique em uma linha</span>
            <button type="button" data-route-selected-action data-route-orthogonal disabled>Ortogonal</button>
            <button type="button" data-route-selected-action data-route-reset disabled>Automático</button>
            <button type="button" data-route-selected-action data-route-delete disabled>Excluir</button>`;
        toolbarHost.appendChild(editor);
        editor.querySelector("[data-route-edit-toggle]").onclick = () => {
            lineEditEnabled = !lineEditEnabled;
            if (!lineEditEnabled) selectedLinkKey = null;
            decorateSvg();
        };
        editor.querySelector("[data-route-orthogonal]").onclick = () => {
            const svg = unifilarContent.querySelector(".optical-links");
            const path = [...(svg?.querySelectorAll("path[data-link-type][data-link-id]") || [])].find((item) => linkKey(item) === selectedLinkKey);
            const endpoints = pathEndpoints(path);
            if (!path || !endpoints) return;
            const middle = (endpoints.start.x + endpoints.end.x) / 2;
            routeLayout.manual_link_routes_v2[selectedLinkKey] = {
                points: [{ x: middle, y: endpoints.start.y }, { x: middle, y: endpoints.end.y }],
            };
            saveManualRoutes().then(decorateSvg).catch((error) => notify(error.message, true));
        };
        editor.querySelector("[data-route-reset]").onclick = () => {
            delete routeLayout.manual_link_routes_v2[selectedLinkKey];
            selectedLinkKey = null;
            saveManualRoutes().then(() => window.dispatchEvent(new Event("resize"))).catch((error) => notify(error.message, true));
        };
        editor.querySelector("[data-route-delete]").onclick = () => {
            const svg = unifilarContent.querySelector(".optical-links");
            const path = [...(svg?.querySelectorAll("path[data-link-type][data-link-id]") || [])].find((item) => linkKey(item) === selectedLinkKey);
            lineEditEnabled = false;
            selectedLinkKey = null;
            refreshRouteToolbar();
            path?.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        };
        refreshRouteToolbar();
    }

    function makeFusionDialogDraggable() {
        if (unifilarDialog.dataset.draggableV2 === "true") return;
        unifilarDialog.dataset.draggableV2 = "true";
        unifilarDialog.classList.add("fusion-window-v2");
        const header = unifilarDialog.querySelector(":scope > section > header");
        header?.addEventListener("pointerdown", (event) => {
            if (unifilarDialog.classList.contains("is-fullscreen") || document.fullscreenElement === unifilarDialog) return;
            if (event.target.closest("button, input, select")) return;
            const rect = unifilarDialog.getBoundingClientRect();
            const offsetX = event.clientX - rect.left;
            const offsetY = event.clientY - rect.top;
            unifilarDialog.classList.add("fusion-window-moved-v2");
            const move = (moveEvent) => {
                unifilarDialog.style.left = `${Math.max(0, Math.min(window.innerWidth - unifilarDialog.offsetWidth, moveEvent.clientX - offsetX))}px`;
                unifilarDialog.style.top = `${Math.max(0, Math.min(window.innerHeight - unifilarDialog.offsetHeight, moveEvent.clientY - offsetY))}px`;
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", up);
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        });
    }

    async function enhanceFusion() {
        if (!unifilarDialog.open) return;
        makeFusionDialogDraggable();
        await loadRouteLayout(false);
        installRouteToolbar();
        const svg = unifilarContent.querySelector(".optical-links");
        if (svg) {
            bindSvgEditor(svg);
            decorateSvg();
        }
        const instructions = unifilarContent.querySelector(".ceo-instructions");
        if (instructions && !instructions.dataset.compactV2) {
            instructions.dataset.compactV2 = "true";
            instructions.classList.add("ceo-instructions-compact-v2");
        }
    }

    const observer = new MutationObserver((mutations) => {
        if (decoratingSvg) return;
        const meaningful = mutations.some((mutation) => {
            const nodes = [...mutation.addedNodes, ...mutation.removedNodes];
            return nodes.some((node) => !(
                node.nodeType === Node.ELEMENT_NODE
                && node.classList?.contains("manual-route-handle-v2")
            ));
        });
        if (!meaningful) return;
        window.clearTimeout(enhanceTimer);
        enhanceTimer = window.setTimeout(() => enhanceFusion().catch((error) => notify(error.message, true)), 30);
    });
    observer.observe(unifilarContent, { childList: true, subtree: true });
    unifilarDialog.addEventListener("close", () => {
        lineEditEnabled = false;
        selectedLinkKey = null;
        routeLayout = null;
        routeElementId = null;
        unifilarDialog.classList.remove("fusion-window-moved-v2");
        unifilarDialog.style.left = "";
        unifilarDialog.style.top = "";
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && insertion) removeInsertion();
        if (event.key === "Escape" && lineEditEnabled) {
            lineEditEnabled = false;
            selectedLinkKey = null;
            decorateSvg();
        }
    });
}());
