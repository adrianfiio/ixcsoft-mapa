(function () {
    "use strict";

    const VERSION = "1.1.0";
    const state = {
        projectId: "",
        bootstrap: null,
        selectedRoutes: new Set(),
        allRoutes: true,
        routeFilters: {
            cables: true,
            cto: true,
            spliceBoxes: true,
            reserves: true,
            containers: true,
            labels: true,
        },
        reserveSession: null,
        actionLock: false,
        fusionKeepOpenUntil: 0,
        container: {
            elementId: "",
            data: null,
            layout: { positions: {}, routes: {}, zoom: 1 },
            selectedPort: null,
            lineMode: false,
            selectedLink: null,
            loadingPromise: null,
            loadingElementId: "",
            rendering: false,
        },
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (cookie) return decodeURIComponent(cookie.split("=")[1]);
        return qs("[name='csrfmiddlewaretoken']")?.value || "";
    }

    async function request(path, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) {
            headers["Content-Type"] = headers["Content-Type"] || "application/json";
        }
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(path, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function notify(message, error = false) {
        window.networkMap?.notify?.(message, error);
        const toast = ensureToast();
        toast.textContent = message || "";
        toast.classList.toggle("error", error);
        toast.classList.add("show");
        window.clearTimeout(toast._timer);
        toast._timer = window.setTimeout(() => toast.classList.remove("show"), 3600);
    }

    function ensureToast() {
        let toast = qs("#map-master-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "map-master-toast";
            toast.className = "map-master-toast";
            document.body.appendChild(toast);
        }
        return toast;
    }

    function projectId() {
        return String(qs("#project-select")?.value || "");
    }

    function storageKey(name) {
        return `ixcsoft-map-master:${projectId() || "none"}:${name}`;
    }

    function saveRoutePreferences() {
        try {
            localStorage.setItem(storageKey("routes"), JSON.stringify({
                allRoutes: state.allRoutes,
                selected: [...state.selectedRoutes],
                filters: state.routeFilters,
            }));
        } catch (_error) {}
    }

    function restoreRoutePreferences() {
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey("routes")) || "null");
            if (!saved) return;
            state.allRoutes = saved.allRoutes !== false;
            state.selectedRoutes = new Set((saved.selected || []).map(String));
            state.routeFilters = { ...state.routeFilters, ...(saved.filters || {}) };
        } catch (_error) {}
    }

    async function refreshBootstrap() {
        const id = projectId();
        state.projectId = id;
        if (!id) {
            state.bootstrap = null;
            renderRouteDrawer();
            return;
        }
        const changed = id !== String(state.bootstrap?.project?.id || "");
        if (changed) {
            state.allRoutes = true;
            state.selectedRoutes.clear();
            restoreRoutePreferences();
        }
        state.bootstrap = await request(`/api/map/master/bootstrap/?project_id=${encodeURIComponent(id)}`);
        const validIds = new Set((state.bootstrap.topology?.routes || []).filter((item) => item.valid).map((item) => String(item.id)));
        state.selectedRoutes = new Set([...state.selectedRoutes].filter((item) => validIds.has(item)));
        renderRouteDrawer();
        installRouteFiltering();
        applyConfiguredIcons();
    }

    // ------------------------------------------------------------------
    // Compact shell and route drawer based on real connected topology
    // ------------------------------------------------------------------

    function installCompactShell() {
        document.body.classList.add("map-master-suite", "map-master-compact");
        const sidebar = qs("#map-sidebar");
        if (sidebar) sidebar.classList.add("map-sidebar-master");
        const map = qs("#map");
        if (!map || qs("#map-master-controls")) return;
        const controls = document.createElement("nav");
        controls.id = "map-master-controls";
        controls.className = "map-master-controls";
        controls.innerHTML = `
            <button type="button" data-master-routes title="Rotas conectadas" hidden>Rotas</button>
            <button type="button" data-master-trace title="Rastrear caminho óptico">Rastrear</button>
            <button type="button" data-master-sidebar title="Alternar menu compacto">Menu</button>`;
        map.appendChild(controls);
        controls.querySelector("[data-master-routes]").onclick = () => toggleRouteDrawer();
        controls.querySelector("[data-master-trace]").onclick = () => openTraceDialog().catch((error) => notify(error.message, true));
        controls.querySelector("[data-master-sidebar]").onclick = () => sidebar?.classList.toggle("master-minimized");
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(controls);
            L.DomEvent.disableScrollPropagation(controls);
        }
    }

    function ensureRouteDrawer() {
        let drawer = qs("#map-master-route-drawer");
        if (drawer) return drawer;
        const map = qs("#map");
        drawer = document.createElement("aside");
        drawer.id = "map-master-route-drawer";
        drawer.className = "map-master-route-drawer collapsed";
        drawer.hidden = true;
        drawer.innerHTML = `
            <header>
                <div><strong>Rotas conectadas</strong><small>Somente trajetos com origem e caixas ligadas</small></div>
                <button type="button" data-route-close aria-label="Fechar">×</button>
            </header>
            <div class="route-master-actions">
                <button type="button" data-route-all>Todas</button>
                <button type="button" data-route-none>Nenhuma</button>
            </div>
            <div data-route-master-list class="route-master-list"></div>
            <details class="route-master-layers">
                <summary>Elementos visíveis</summary>
                <label><input type="checkbox" data-master-filter="cables"> Cabos</label>
                <label><input type="checkbox" data-master-filter="cto"> CTO</label>
                <label><input type="checkbox" data-master-filter="spliceBoxes"> CEO/CDO</label>
                <label><input type="checkbox" data-master-filter="reserves"> Reservas</label>
                <label><input type="checkbox" data-master-filter="containers"> POP/Rack/Torre</label>
                <label><input type="checkbox" data-master-filter="labels"> Nomes</label>
            </details>`;
        map?.appendChild(drawer);
        drawer.querySelector("[data-route-close]").onclick = () => toggleRouteDrawer(false);
        drawer.querySelector("[data-route-all]").onclick = () => {
            state.allRoutes = true;
            state.selectedRoutes.clear();
            applyRouteChanges();
        };
        drawer.querySelector("[data-route-none]").onclick = () => {
            state.allRoutes = false;
            state.selectedRoutes.clear();
            applyRouteChanges();
        };
        qsa("[data-master-filter]", drawer).forEach((input) => {
            input.onchange = () => {
                state.routeFilters[input.dataset.masterFilter] = input.checked;
                applyRouteChanges();
            };
        });
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(drawer);
            L.DomEvent.disableScrollPropagation(drawer);
        }
        return drawer;
    }

    function toggleRouteDrawer(force) {
        const drawer = ensureRouteDrawer();
        const open = force === undefined ? drawer.classList.contains("collapsed") : Boolean(force);
        drawer.classList.toggle("collapsed", !open);
    }

    function validRoutes() {
        return (state.bootstrap?.topology?.routes || []).filter((item) => item.valid);
    }

    function renderRouteDrawer() {
        installCompactShell();
        const drawer = ensureRouteDrawer();
        const routes = validRoutes();
        const button = qs("[data-master-routes]");
        const oldPanel = qs("#route-filter-v092");
        if (oldPanel) oldPanel.hidden = true;
        drawer.hidden = routes.length === 0;
        if (button) button.hidden = routes.length === 0;
        if (!routes.length) {
            drawer.classList.add("collapsed");
            return;
        }
        const list = qs("[data-route-master-list]", drawer);
        list.innerHTML = routes.map((route) => `
            <label class="route-master-item">
                <input type="checkbox" value="${route.id}" ${state.allRoutes || state.selectedRoutes.has(String(route.id)) ? "checked" : ""}>
                <span><strong>${escapeHtml(route.name)}</strong><small>${route.counts.cables} cabos · ${route.counts.ctos} CTO · ${route.counts.splice_boxes} CEO/CDO</small></span>
                <button type="button" data-only-route="${route.id}">Só</button>
            </label>`).join("");
        qsa('input[type="checkbox"]', list).forEach((input) => {
            input.onchange = () => {
                if (state.allRoutes) state.selectedRoutes = new Set(routes.map((item) => String(item.id)));
                state.allRoutes = false;
                if (input.checked) state.selectedRoutes.add(input.value);
                else state.selectedRoutes.delete(input.value);
                applyRouteChanges();
            };
        });
        qsa("[data-only-route]", list).forEach((button) => {
            button.onclick = () => {
                state.allRoutes = false;
                state.selectedRoutes = new Set([String(button.dataset.onlyRoute)]);
                applyRouteChanges();
            };
        });
        qsa("[data-master-filter]", drawer).forEach((input) => {
            input.checked = state.routeFilters[input.dataset.masterFilter] !== false;
        });
    }

    function selectedRouteRows() {
        const rows = validRoutes();
        return state.allRoutes ? rows : rows.filter((item) => state.selectedRoutes.has(String(item.id)));
    }

    function installRouteFiltering() {
        const api = window.mapV092;
        if (!api || api.masterSuiteInstalled) return;
        const original = {
            element: api.isElementVisible?.bind(api),
            cable: api.isCableVisible?.bind(api),
            route: api.isRouteVisible?.bind(api),
            reserves: api.areReservesVisible?.bind(api),
        };
        api.isElementVisible = (feature) => {
            const id = Number(feature?.properties?.id || feature?.id || 0);
            const type = String(feature?.properties?.tipo || feature?.properties?.element_type || "");
            if (type === "cto" && !state.routeFilters.cto) return false;
            if (type === "splice_box" && !state.routeFilters.spliceBoxes) return false;
            if (["rack", "tower"].includes(type) && !state.routeFilters.containers) return false;
            if (!state.bootstrap || state.allRoutes) return original.element ? original.element(feature) : true;
            return selectedRouteRows().some((route) => route.element_ids.includes(id));
        };
        api.isCableVisible = (feature) => {
            if (!state.routeFilters.cables) return false;
            if (!state.bootstrap || state.allRoutes) return original.cable ? original.cable(feature) : true;
            const id = Number(feature?.properties?.id || feature?.id || 0);
            return selectedRouteRows().some((route) => route.cable_ids.includes(id));
        };
        api.isRouteVisible = (feature) => {
            if (!state.bootstrap) return original.route ? original.route(feature) : true;
            const id = Number(feature?.properties?.id || feature?.id || 0);
            return state.allRoutes
                ? validRoutes().some((route) => route.id === id)
                : state.selectedRoutes.has(String(id));
        };
        api.areReservesVisible = () => state.routeFilters.reserves && (original.reserves ? original.reserves() : true);
        api.masterSuiteInstalled = true;
    }

    function applyRouteChanges() {
        saveRoutePreferences();
        renderRouteDrawer();
        const labels = qs("#layer-labels");
        if (labels) labels.checked = state.routeFilters.labels;
        window.networkMap?.loadStructure?.().catch((error) => notify(error.message, true));
    }

    // ------------------------------------------------------------------
    // Cable-only route assignment, robust one-click actions and reserves
    // ------------------------------------------------------------------

    function routeDialog() {
        let dialog = qs("#map-master-route-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-route-dialog";
        dialog.className = "editor-dialog map-master-small-dialog";
        dialog.innerHTML = `
            <form>
                <header><div><h2>Rota do cabo</h2><p>A rota é definida no cabo e herdada pelos elementos conectados.</p></div><button type="button" data-close>×</button></header>
                <label>Rota<select name="route_id"></select></label>
                <p data-status></p>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Salvar rota</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        return dialog;
    }

    async function openCableRoute(cableId) {
        if (!state.bootstrap) await refreshBootstrap();
        const dialog = routeDialog();
        const select = qs("select", dialog);
        const routes = state.bootstrap?.topology?.routes || [];
        select.innerHTML = '<option value="">Sem rota definida</option>' + routes.map((route) =>
            `<option value="${route.id}">${escapeHtml(route.name)}${route.valid ? "" : ` · ${escapeHtml(route.reason)}`}</option>`
        ).join("");
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request(`/api/map/master/cables/${cableId}/route/`, {
                    method: "PATCH",
                    body: JSON.stringify({ route_id: select.value }),
                });
                dialog.close();
                await refreshBootstrap();
                await window.networkMap?.loadStructure?.();
                notify("Rota do cabo atualizada.");
            } catch (error) {
                qs("[data-status]", dialog).textContent = error.message;
            }
        };
        dialog.showModal();
    }

    function flattenCableCoordinates(cable) {
        const geometry = cable?.geometry || {};
        if (geometry.type === "MultiLineString") return geometry.coordinates || [];
        if (geometry.type === "LineString") return [geometry.coordinates || []];
        return [];
    }

    function nearestCablePoint(latlng, cable) {
        const map = window.networkMap?.map;
        if (!map || !latlng) return latlng;
        const point = map.latLngToLayerPoint(latlng);
        let best = null;
        flattenCableCoordinates(cable).forEach((line) => {
            for (let index = 0; index < line.length - 1; index += 1) {
                const a = map.latLngToLayerPoint([line[index][1], line[index][0]]);
                const b = map.latLngToLayerPoint([line[index + 1][1], line[index + 1][0]]);
                const vx = b.x - a.x;
                const vy = b.y - a.y;
                const denominator = vx * vx + vy * vy;
                const ratio = denominator ? Math.max(0, Math.min(1, ((point.x - a.x) * vx + (point.y - a.y) * vy) / denominator)) : 0;
                const projected = L.point(a.x + ratio * vx, a.y + ratio * vy);
                const distance = projected.distanceTo(point);
                if (!best || distance < best.distance) best = { distance, latlng: map.layerPointToLatLng(projected) };
            }
        });
        return best?.latlng || latlng;
    }

    function middleCablePoint(cable) {
        const line = flattenCableCoordinates(cable)[0] || [];
        if (!line.length) return window.networkMap?.map?.getCenter();
        const value = line[Math.floor((line.length - 1) / 2)];
        return L.latLng(value[1], value[0]);
    }

    function cancelReserve() {
        const session = state.reserveSession;
        if (!session) return;
        try { window.networkMap?.map?.removeLayer(session.marker); } catch (_error) {}
        session.panel.remove();
        state.reserveSession = null;
        document.body.classList.remove("map-master-placement-active");
    }

    async function openReserve(cableId) {
        cancelReserve();
        const result = await request(`/api/map/cables/${cableId}/`);
        const cable = result.cable;
        const map = window.networkMap?.map;
        if (!map || !cable) throw new Error("Cabo ou mapa indisponível.");
        const initial = nearestCablePoint(map._popup?.getLatLng?.() || middleCablePoint(cable), cable);
        map.closePopup();
        const marker = L.marker(initial, {
            draggable: true,
            zIndexOffset: 2600,
            icon: L.divIcon({ className: "", html: '<div class="map-master-reserve-marker">RT</div>', iconSize: [34, 34], iconAnchor: [17, 17] }),
        }).addTo(map);
        const panel = document.createElement("section");
        panel.className = "map-master-placement-panel";
        panel.innerHTML = `
            <header><div><strong>Reserva técnica</strong><small>${escapeHtml(cable.name)}</small></div><button type="button" data-close>×</button></header>
            <label>Metragem<input name="length_m" type="number" min="0.1" step="0.1" value="20"></label>
            <label>Identificação<input name="label" maxlength="100" placeholder="Ex.: Reserva poste 01"></label>
            <label>Observação<textarea name="notes" rows="2"></textarea></label>
            <p data-status>Arraste a reserva sobre o cabo e confirme.</p>
            <footer><button type="button" data-cancel>Cancelar</button><button type="button" class="primary" data-save>Salvar reserva</button></footer>`;
        document.body.appendChild(panel);
        state.reserveSession = { cable, marker, panel };
        document.body.classList.add("map-master-placement-active");
        marker.on("drag", () => marker.setLatLng(nearestCablePoint(marker.getLatLng(), cable)));
        panel.querySelector("[data-close]").onclick = cancelReserve;
        panel.querySelector("[data-cancel]").onclick = cancelReserve;
        panel.querySelector("[data-save]").onclick = async () => {
            const position = marker.getLatLng();
            const save = panel.querySelector("[data-save]");
            save.disabled = true;
            try {
                await request(`/api/map/master/cables/${cableId}/reserves/`, {
                    method: "POST",
                    body: JSON.stringify({
                        latitude: position.lat,
                        longitude: position.lng,
                        length_m: panel.querySelector("[name='length_m']").value,
                        label: panel.querySelector("[name='label']").value,
                        notes: panel.querySelector("[name='notes']").value,
                    }),
                });
                cancelReserve();
                await window.networkMap?.loadStructure?.();
                notify("Reserva criada no ponto selecionado.");
            } catch (error) {
                panel.querySelector("[data-status]").textContent = error.message;
                save.disabled = false;
            }
        };
    }

    function decoratePopups(root = document) {
        qsa(".leaflet-popup-content", root).forEach((content) => {
            // Route assignment belongs to cables only.
            qsa("[data-asset-route-v3]", content).forEach((button) => button.remove());
            const cableEdit = qs("[data-edit-cable]", content);
            const elementEdit = qs("[data-edit-element]", content);
            const assetType = cableEdit ? "cable" : elementEdit ? "element" : "";
            const assetId = cableEdit?.dataset.editCable || elementEdit?.dataset.editElement || "";
            if (assetType && assetId && !qs("[data-master-asset-sheet]", content)) {
                const sheet = document.createElement("button");
                sheet.type = "button"; sheet.dataset.masterAssetSheet = assetType; sheet.dataset.assetId = assetId;
                sheet.textContent = "Ficha / QR";
                (cableEdit || elementEdit).insertAdjacentElement("afterend", sheet);
            }
            if (cableEdit && !qs("[data-master-cable-route]", content)) {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.masterCableRoute = cableEdit.dataset.editCable;
                button.textContent = "Rota do cabo";
                cableEdit.insertAdjacentElement("afterend", button);
            }
            const insert = qs("[data-insert-cable]", content);
            if (insert) insert.textContent = "Inserir caixa";
            const reserve = qsa("button, a", content).find((item) => /reserva/i.test(item.textContent || ""));
            if (reserve && !reserve.dataset.masterReserve) {
                const cableId = cableEdit?.dataset.editCable || insert?.dataset.insertCable;
                if (cableId) reserve.dataset.masterReserve = cableId;
            }
        });
    }

    function installActionController() {
        document.addEventListener("click", async (event) => {
            const sheet = event.target.closest("[data-master-asset-sheet]");
            if (sheet) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                return openAssetSheet(sheet.dataset.masterAssetSheet, sheet.dataset.assetId).catch((error) => notify(error.message, true));
            }
            const route = event.target.closest("[data-master-cable-route]");
            if (route) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                return openCableRoute(route.dataset.masterCableRoute).catch((error) => notify(error.message, true));
            }
            const reserve = event.target.closest("[data-master-reserve]");
            if (reserve) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                if (state.actionLock) return;
                state.actionLock = true;
                openReserve(reserve.dataset.masterReserve)
                    .catch((error) => notify(error.message, true))
                    .finally(() => window.setTimeout(() => { state.actionLock = false; }, 100));
                return;
            }
            const insert = event.target.closest("[data-insert-cable]");
            if (insert && window.mapOpticalEditorV2?.openInsertion) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                if (state.actionLock) return;
                state.actionLock = true;
                window.networkMap?.map?.closePopup?.();
                window.mapOpticalEditorV2.openInsertion(insert.dataset.insertCable)
                    .catch((error) => notify(error.message, true))
                    .finally(() => window.setTimeout(() => { state.actionLock = false; }, 100));
            }
        }, true);
        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            cancelReserve();
            window.mapOpticalEditorV2?.cancelInsertion?.();
        });
    }

    // ------------------------------------------------------------------
    // Configurable map icons
    // ------------------------------------------------------------------

    function iconKey(type, subtype = "") {
        return `${type}:${subtype || ""}`;
    }

    function iconStyles() {
        const map = new Map();
        (state.bootstrap?.icons || []).forEach((item) => map.set(iconKey(item.element_type, item.subtype), item));
        return map;
    }

    function markerType(marker) {
        if (marker.classList.contains("cdo")) return ["splice_box", "cdo"];
        if (marker.classList.contains("splice_box")) return ["splice_box", "ceo"];
        for (const type of ["cto", "rack", "tower", "pole", "olt", "dio", "cpd"]) {
            if (marker.classList.contains(type)) return [type === "cpd" ? "other" : type, type === "cpd" ? "cpd" : ""];
        }
        return ["", ""];
    }

    function sanitizeSvg(markup) {
        if (!markup) return "";
        const template = document.createElement("template");
        template.innerHTML = `<svg viewBox="0 0 32 32">${markup}</svg>`;
        const svg = template.content.querySelector("svg");
        const allowed = new Set(["svg", "path", "rect", "circle", "line", "polyline", "polygon", "ellipse", "g"]);
        qsa("*", svg).forEach((node) => {
            if (!allowed.has(node.tagName.toLowerCase())) return node.remove();
            [...node.attributes].forEach((attribute) => {
                if (/^on/i.test(attribute.name) || ["href", "xlink:href", "style"].includes(attribute.name)) node.removeAttribute(attribute.name);
            });
        });
        return svg.outerHTML;
    }

    function applyConfiguredIcons(root = document) {
        const styles = iconStyles();
        qsa(".network-marker:not([data-master-icon])", root).forEach((marker) => {
            const [type, subtype] = markerType(marker);
            const style = styles.get(iconKey(type, subtype)) || styles.get(iconKey(type, ""));
            marker.dataset.masterIcon = "true";
            if (!style) return;
            marker.style.setProperty("--master-icon-fg", style.foreground_color);
            marker.style.setProperty("--master-icon-bg", style.background_color);
            marker.style.setProperty("--master-icon-border", style.border_color);
            marker.style.setProperty("--master-icon-size", `${style.size_px}px`);
            const svg = sanitizeSvg(style.svg_markup);
            if (svg) marker.innerHTML = `${svg}${style.show_name_inside_icon ? `<small>${escapeHtml(style.display_name)}</small>` : ""}`;
            else if (style.image_url) marker.innerHTML = `<img src="${escapeHtml(style.image_url)}" alt="${escapeHtml(style.display_name)}">`;
        });
    }

    // ------------------------------------------------------------------
    // Fusion window: compact, movable, stable fullscreen and snapshots
    // ------------------------------------------------------------------

    function fusionDialog() { return qs("#unifilar-dialog"); }

    function clampDialog(dialog) {
        if (!dialog || dialog.classList.contains("is-fullscreen") || !dialog.open) return;
        const rect = dialog.getBoundingClientRect();
        const left = Math.max(8, Math.min(window.innerWidth - rect.width - 8, rect.left));
        const top = Math.max(8, Math.min(window.innerHeight - rect.height - 8, rect.top));
        dialog.style.left = `${left}px`;
        dialog.style.top = `${top}px`;
        dialog.style.margin = "0";
    }

    function makeFusionDraggable(dialog) {
        if (dialog.dataset.masterDraggable === "true") return;
        dialog.dataset.masterDraggable = "true";
        const header = qs(":scope > section > header", dialog);
        header?.addEventListener("pointerdown", (event) => {
            if (dialog.classList.contains("is-fullscreen") || event.target.closest("button, input, select")) return;
            dialog.dataset.userPositioned = "true";
            dialog.style.transform = "none";
            const rect = dialog.getBoundingClientRect();
            const offsetX = event.clientX - rect.left;
            const offsetY = event.clientY - rect.top;
            const move = (moveEvent) => {
                dialog.style.left = `${moveEvent.clientX - offsetX}px`;
                dialog.style.top = `${moveEvent.clientY - offsetY}px`;
                dialog.style.margin = "0";
                clampDialog(dialog);
            };
            const up = () => window.removeEventListener("pointermove", move);
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        });
    }

    async function saveDiagramRevision(type, elementId, payload, note = "") {
        const id = projectId();
        if (!id) return;
        await request(`/api/map/master/projects/${id}/diagram-revisions/`, {
            method: "POST",
            body: JSON.stringify({ diagram_type: type, element_id: elementId, payload, note }),
        });
    }

    function enhanceFusion() {
        const dialog = fusionDialog();
        const content = qs("#unifilar-content");
        if (!dialog?.open || !content) return;
        dialog.classList.add("map-master-fusion");
        makeFusionDraggable(dialog);
        clampDialog(dialog);
        const toolbar = qs(".fusion-toolbar", content) || qs(".unifilar-zoom", content);
        if (toolbar && !qs("[data-master-fusion-snapshot]", toolbar)) {
            const snapshot = document.createElement("button");
            snapshot.type = "button";
            snapshot.dataset.masterFusionSnapshot = "true";
            snapshot.textContent = "Salvar versão";
            snapshot.onclick = async () => {
                const layout = await request(`/api/map/elements/${dialog.dataset.elementId}/layout/`);
                await saveDiagramRevision("fusion", Number(dialog.dataset.elementId), layout.layout || {}, "Versão manual da fusão");
                notify("Versão do diagrama de fusões salva.");
            };
            toolbar.appendChild(snapshot);
        }
        const full = qs("[data-fusion-fullscreen]", content);
        if (full && full.dataset.masterFullscreen !== "true") {
            // Clone removes handlers antigos que alternavam Fullscreen API e CSS ao mesmo tempo.
            const replacement = full.cloneNode(true);
            replacement.dataset.masterFullscreen = "true";
            replacement.addEventListener("click", (event) => {
                event.preventDefault(); event.stopImmediatePropagation();
                const active = dialog.classList.toggle("is-fullscreen");
                replacement.textContent = active ? "Desmaximizar" : "Tela cheia";
                replacement.setAttribute("aria-pressed", String(active));
                if (!active) clampDialog(dialog);
                window.setTimeout(() => window.dispatchEvent(new Event("resize")), 40);
            }, true);
            full.replaceWith(replacement);
        }
        if (content.dataset.masterKeepOpen !== "true") {
            content.dataset.masterKeepOpen = "true";
            content.addEventListener("click", (event) => {
                if (event.target.closest("[data-add-splitter], [data-delete-splice], [data-delete-splitter], .danger")) {
                    state.fusionKeepOpenUntil = Date.now() + 1600;
                }
            }, true);
        }
    }

    // ------------------------------------------------------------------
    // Full 2D POP/Rack/Tower workspace
    // ------------------------------------------------------------------

    function containerDialog() { return qs("#container-dialog"); }

    async function loadContainerMaster(force = false) {
        const dialog = containerDialog();
        const id = String(dialog?.dataset.elementId || "");
        if (!id) return null;
        if (!force && state.container.elementId === id && state.container.data) return state.container.data;
        if (state.container.loadingPromise && state.container.loadingElementId === id) {
            return state.container.loadingPromise;
        }
        state.container.loadingElementId = id;
        const loading = Promise.all([
            request(`/api/map/elements/${id}/equipment/`),
            request(`/api/map/elements/${id}/container-layout-v3/`).catch(() => ({ layout: {} })),
        ]).then(([data, layout]) => {
            if (String(containerDialog()?.dataset.elementId || "") !== id) return null;
            state.container.elementId = id;
            state.container.data = data;
            state.container.layout = { positions: {}, routes: {}, zoom: 1, ...(layout.layout || {}) };
            state.container.layout.positions ||= {};
            state.container.layout.routes ||= {};
            return data;
        });
        state.container.loadingPromise = loading;
        try {
            return await loading;
        } finally {
            if (state.container.loadingPromise === loading) {
                state.container.loadingPromise = null;
                state.container.loadingElementId = "";
            }
        }
    }

    function equipmentGroup(type, item) {
        const subtype = String(item.metadata?.equipment_subtype || "").toLowerCase();
        if (type === "olt") return "OLTs";
        if (type === "dio") return "DIOs";
        if (type === "switch") return "Switches";
        if (type === "router") return "Roteadores";
        if (type === "firewall") return "Firewalls";
        if (type === "ptp") return "Rádios PTP";
        if (type === "access_point") return "Access points";
        if (type === "onu" || subtype === "onu") return "ONUs / ONTs";
        if (type === "pto" || subtype === "pto") return "PTOs";
        return "Outros";
    }

    function ensureContainerWorkspace() {
        const dialog = containerDialog();
        if (!dialog || qs("#map-master-container", dialog)) return qs("#map-master-container", dialog);
        const section = qs(":scope > section", dialog);
        const root = document.createElement("div");
        root.id = "map-master-container";
        root.className = "map-master-container";
        root.innerHTML = `
            <nav class="master-container-tabs">
                <button type="button" data-tab="equipment" class="active">Equipamentos</button>
                <button type="button" data-tab="canvas">Canvas 2D</button>
                <button type="button" data-tab="matrix">Matriz de manobra</button>
                <button type="button" data-tab="fibers">Fibras e terminações</button>
                <button type="button" data-tab="models">YAML / modelos</button>
            </nav>
            <div class="master-container-toolbar">
                <button type="button" data-container-add>+ Equipamento</button>
                <button type="button" data-container-organize>Organizar</button>
                <button type="button" data-container-lines>Editar linhas</button>
                <button type="button" data-container-export>Exportar PNG</button>
                <button type="button" data-container-revision>Salvar versão</button>
                <button type="button" data-container-fullscreen>Tela cheia</button>
            </div>
            <section data-panel="equipment" class="master-container-panel active"></section>
            <section data-panel="canvas" class="master-container-panel"><div class="master-canvas-scroll"><div class="master-canvas"><svg class="master-canvas-links"></svg><div class="master-canvas-nodes"></div></div></div></section>
            <section data-panel="matrix" class="master-container-panel"></section>
            <section data-panel="fibers" class="master-container-panel"></section>
            <section data-panel="models" class="master-container-panel"></section>`;
        section.insertBefore(root, section.children[1] || null);
        qsa(":scope > section > .container-workspace, :scope > section > #container-optical-links, :scope > section > .container-extension-grid, :scope > section > #container-equipment-form", dialog)
            .forEach((node) => node.classList.add("master-legacy-hidden"));
        qsa("[data-tab]", root).forEach((button) => {
            button.onclick = () => {
                qsa("[data-tab]", root).forEach((item) => item.classList.toggle("active", item === button));
                qsa("[data-panel]", root).forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab));
                if (button.dataset.tab === "canvas") renderContainerCanvas();
            };
        });
        qs("[data-container-add]", root).onclick = () => openEquipmentCreateDialog();
        qs("[data-container-organize]", root).onclick = () => organizeContainerNodes();
        qs("[data-container-lines]", root).onclick = (event) => {
            state.container.lineMode = !state.container.lineMode;
            event.currentTarget.classList.toggle("active", state.container.lineMode);
            event.currentTarget.textContent = state.container.lineMode ? "Concluir linhas" : "Editar linhas";
            renderContainerCanvas();
        };
        qs("[data-container-export]", root).onclick = () => exportContainerPng();
        qs("[data-container-revision]", root).onclick = async () => {
            await saveDiagramRevision("container", Number(state.container.elementId), state.container.layout, "Versão do Canvas 2D");
            notify("Versão do Canvas 2D salva.");
        };
        qs("[data-container-fullscreen]", root).onclick = (event) => {
            const active = dialog.classList.toggle("master-container-fullscreen");
            event.currentTarget.textContent = active ? "Desmaximizar" : "Tela cheia";
            renderContainerCanvas();
        };
        return root;
    }

    async function enhanceContainer() {
        const dialog = containerDialog();
        if (!dialog?.open || !dialog.dataset.elementId || state.container.rendering) return;
        state.container.rendering = true;
        try {
            ensureContainerWorkspace();
            const data = await loadContainerMaster(false);
            if (!data || !dialog.open) return;
            renderEquipmentList();
            renderContainerCanvas();
            renderConnectionMatrix();
            attachLegacyPanels();
            document.dispatchEvent(new CustomEvent("map:container-rendered", { detail: { root: dialog, data } }));
        } finally {
            state.container.rendering = false;
        }
    }

    function attachLegacyPanels() {
        const root = qs("#map-master-container");
        const fibers = qs('[data-panel="fibers"]', root);
        const models = qs('[data-panel="models"]', root);
        const extension = qs("#container-dialog .container-extension-grid");
        if (!extension) return;
        const cards = qsa(":scope > article", extension);
        if (cards[1] && cards[1].parentElement !== fibers) fibers.appendChild(cards[1]);
        if (cards[0] && cards[0].parentElement !== models) models.appendChild(cards[0]);
    }

    function renderEquipmentList() {
        const panel = qs('#map-master-container [data-panel="equipment"]');
        const equipment = state.container.data?.equipment || [];
        const groups = new Map();
        equipment.forEach((item) => {
            const group = equipmentGroup(item.type, item);
            if (!groups.has(group)) groups.set(group, []);
            groups.get(group).push(item);
        });
        panel.innerHTML = `<div class="master-equipment-summary"><strong>${equipment.length} equipamento(s)</strong><span>Clique em editar para portas, módulos, foto e detalhes.</span></div>` +
            ([...groups.entries()].map(([group, items]) => `
                <details class="master-equipment-group" open>
                    <summary>${escapeHtml(group)} <span>${items.length}</span></summary>
                    <div>${items.map((item) => `
                        <article class="master-equipment-row" data-equipment-id="${item.id}" data-equipment-type="${escapeHtml(item.type)}" data-provisioning-mode="${escapeHtml(item.provisioning_mode || 'manual')}" data-monitoring-eligible="${item.monitoring_eligible === true ? 'true' : 'false'}" data-monitoring-configured="${item.monitoring_configured === true ? 'true' : 'false'}">
                            <div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.type_label)}${item.vendor ? ` · ${escapeHtml(item.vendor)}` : ""}${item.model ? ` ${escapeHtml(item.model)}` : ""} · ${(item.ports || []).length} porta(s)</small></div>
                            <div><button type="button" data-equipment-sheet="${item.id}">Ficha</button><button type="button" data-edit-equipment="${item.id}">Editar</button><button type="button" class="danger" data-delete-equipment="${item.id}">Excluir</button></div>
                        </article>`).join("")}</div>
                </details>`).join("") || "<p>Nenhum equipamento cadastrado.</p>");
        document.dispatchEvent(new CustomEvent("map:container-rendered", { detail: { root: panel, data: state.container.data } }));
        qsa("[data-equipment-sheet]", panel).forEach((button) => button.onclick = () => openAssetSheet("equipment", button.dataset.equipmentSheet).catch((error) => notify(error.message, true)));
        qsa("[data-edit-equipment]", panel).forEach((button) => button.onclick = () => openEquipmentEditor(button.dataset.editEquipment));
        qsa("[data-delete-equipment]", panel).forEach((button) => button.onclick = async () => {
            if (!confirm("Excluir este equipamento e suas portas/ligações?")) return;
            await request(`/api/map/elements/${state.container.elementId}/equipment/${button.dataset.deleteEquipment}/`, { method: "DELETE" });
            await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); renderConnectionMatrix();
        });
    }

    function defaultNodePosition(item, index) {
        const columns = { olt: 0, dio: 0, switch: 1, router: 1, firewall: 1, onu: 2, access_point: 2, ptp: 2, pto: 2, other: 2 };
        const column = columns[item.type] ?? 2;
        const siblings = (state.container.data?.equipment || []).slice(0, index).filter((row) => (columns[row.type] ?? 2) === column).length;
        return { x: 40 + column * 340, y: 35 + siblings * 220 };
    }

    function nodePosition(item, index) {
        return state.container.layout.positions[String(item.id)] || defaultNodePosition(item, index);
    }

    function portSide(port, index) {
        const optical = ["pon", "dio", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "sc_apc", "sc_upc", "lc"].includes(port.type);
        return optical || index % 2 === 0 ? "right" : "left";
    }

    function renderContainerCanvas() {
        const root = qs("#map-master-container");
        if (!root || !state.container.data) return;
        const canvas = qs(".master-canvas", root);
        const nodes = qs(".master-canvas-nodes", canvas);
        const equipment = state.container.data.equipment || [];
        nodes.innerHTML = equipment.map((item, index) => {
            const position = nodePosition(item, index);
            return `<article class="master-canvas-node" data-equipment-node="${item.id}" data-equipment-type="${escapeHtml(item.type)}" data-provisioning-mode="${escapeHtml(item.provisioning_mode || 'manual')}" data-monitoring-eligible="${item.monitoring_eligible === true ? 'true' : 'false'}" data-pos-x="${position.x}" data-pos-y="${position.y}" style="transform:translate(${position.x}px,${position.y}px)">
                <header><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.type_label)}</small></header>
                <div class="master-node-ports">${(item.ports || []).map((port, portIndex) => {
                    const side = portSide(port, portIndex);
                    return `<button type="button" class="master-node-port ${side} ${port.used ? "used" : ""}" data-port-id="${port.id}" data-port-type="${port.type}" title="${escapeHtml(port.type_label || port.type)}"><span>${escapeHtml(port.label)}</span><i></i></button>`;
                }).join("") || '<small class="empty">Sem portas</small>'}</div>
            </article>`;
        }).join("");
        qsa("[data-equipment-node]", nodes).forEach((node) => installNodeDrag(node));
        qsa("[data-port-id]", nodes).forEach((button) => button.onclick = () => selectContainerPort(button));
        document.dispatchEvent(new CustomEvent("map:container-rendered", { detail: { root, data: state.container.data } }));
        drawContainerLinks();
    }

    function installNodeDrag(node) {
        const header = qs("header", node);
        header.onpointerdown = (event) => {
            if (event.button !== 0) return;
            const id = String(node.dataset.equipmentNode);
            const position = state.container.layout.positions[id] || {
                x: Number(node.dataset.posX || 0),
                y: Number(node.dataset.posY || 0),
            };
            const origin = { x: event.clientX, y: event.clientY, left: position.x, top: position.y };
            const move = (moveEvent) => {
                const next = { x: Math.max(0, origin.left + moveEvent.clientX - origin.x), y: Math.max(0, origin.top + moveEvent.clientY - origin.y) };
                state.container.layout.positions[id] = next;
                node.dataset.posX = String(next.x); node.dataset.posY = String(next.y);
                node.style.transform = `translate(${next.x}px,${next.y}px)`;
                drawContainerLinks();
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                saveContainerLayout();
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        };
    }

    function portAnchor(portId) {
        const canvas = qs("#map-master-container .master-canvas");
        const port = qs(`[data-port-id="${portId}"]`, canvas);
        if (!port) return null;
        const canvasRect = canvas.getBoundingClientRect();
        const rect = port.getBoundingClientRect();
        const right = port.classList.contains("right");
        return { x: (right ? rect.right : rect.left) - canvasRect.left, y: rect.top + rect.height / 2 - canvasRect.top };
    }

    function orthogonalPath(start, end, manual = []) {
        if (manual.length) return `M${start.x},${start.y} ${manual.map((point) => `L${point.x},${point.y}`).join(" ")} L${end.x},${end.y}`;
        const middle = start.x + (end.x - start.x) / 2;
        return `M${start.x},${start.y} L${middle},${start.y} L${middle},${end.y} L${end.x},${end.y}`;
    }

    function drawContainerLinks() {
        const svg = qs("#map-master-container .master-canvas-links");
        if (!svg) return;
        const links = state.container.data?.links || [];
        svg.innerHTML = links.map((link) => {
            const start = portAnchor(link.source_port_id);
            const end = portAnchor(link.destination_port_id);
            if (!start || !end) return "";
            const manual = state.container.layout.routes[String(link.id)] || [];
            return `<path data-master-link="${link.id}" class="link-${link.link_type} ${state.container.selectedLink === String(link.id) ? "selected" : ""}" d="${orthogonalPath(start, end, manual)}"></path>`;
        }).join("");
        qsa("[data-master-link]", svg).forEach((path) => {
            path.onclick = (event) => {
                if (!state.container.lineMode) return;
                event.stopPropagation();
                state.container.selectedLink = path.dataset.masterLink;
                drawContainerLinks();
            };
            path.ondblclick = (event) => {
                if (!state.container.lineMode) return;
                event.preventDefault();
                const rect = svg.getBoundingClientRect();
                const points = state.container.layout.routes[String(path.dataset.masterLink)] || [];
                points.push({ x: event.clientX - rect.left, y: event.clientY - rect.top });
                state.container.layout.routes[String(path.dataset.masterLink)] = points;
                saveContainerLayout(); drawContainerLinks();
            };
        });
        renderLinkHandles();
    }

    function renderLinkHandles() {
        const svg = qs("#map-master-container .master-canvas-links");
        if (!svg || !state.container.lineMode || !state.container.selectedLink) return;
        const points = state.container.layout.routes[state.container.selectedLink] || [];
        points.forEach((point, index) => {
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", point.x); circle.setAttribute("cy", point.y); circle.setAttribute("r", "7");
            circle.classList.add("master-link-handle");
            circle.onpointerdown = (event) => {
                event.preventDefault(); event.stopPropagation();
                const rect = svg.getBoundingClientRect();
                const move = (moveEvent) => {
                    points[index] = { x: moveEvent.clientX - rect.left, y: moveEvent.clientY - rect.top };
                    state.container.layout.routes[state.container.selectedLink] = points;
                    drawContainerLinks();
                };
                const up = () => { window.removeEventListener("pointermove", move); saveContainerLayout(); };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", up, { once: true });
            };
            circle.oncontextmenu = (event) => {
                event.preventDefault();
                points.splice(index, 1);
                state.container.layout.routes[state.container.selectedLink] = points;
                saveContainerLayout(); drawContainerLinks();
            };
            svg.appendChild(circle);
        });
    }

    async function selectCreatedLinkForEditing(linkId) {
        const link = (state.container.data?.links || []).find((item) => String(item.id) === String(linkId));
        if (!link) return;
        const start = portAnchor(link.source_port_id);
        const end = portAnchor(link.destination_port_id);
        if (!start || !end) return;
        const middle = start.x + (end.x - start.x) / 2;
        state.container.selectedLink = String(linkId);
        state.container.layout.routes[String(linkId)] = [
            { x: middle, y: start.y },
            { x: middle, y: end.y },
        ];
        drawContainerLinks();
        await saveContainerLayout();
    }

    async function selectContainerPort(button) {
        if (button.dataset.busy === "true") return;
        const current = { id: Number(button.dataset.portId), type: button.dataset.portType, button };
        if (!state.container.selectedPort) {
            state.container.selectedPort = current;
            button.classList.add("selected");
            notify("Agora clique na porta de destino.");
            return;
        }
        const source = state.container.selectedPort;
        source.button.classList.remove("selected");
        state.container.selectedPort = null;
        if (source.id === current.id) return;
        const optical = new Set(["pon", "dio", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "qsfp_plus_40g", "qsfp28_100g", "sc_apc", "sc_upc", "lc"]);
        const copper = new Set(["rj45_100m", "rj45_1g", "rj45_2g5"]);
        let linkType = "";
        if (optical.has(source.type) && optical.has(current.type)) linkType = "fiber";
        else if (copper.has(source.type) && copper.has(current.type)) linkType = "copper";
        else if (source.type === "wireless" && current.type === "wireless") linkType = "wireless";
        if (!linkType) return notify("Portas incompatíveis.", true);
        try {
            const created = await request(`/api/map/elements/${state.container.elementId}/equipment-links/`, {
                method: "POST",
                body: JSON.stringify({ source_port_id: source.id, destination_port_id: current.id, link_type: linkType }),
            });
            await loadContainerMaster(true); renderContainerCanvas(); renderConnectionMatrix();
            await selectCreatedLinkForEditing(created.link?.id);
            notify("Ligação criada e selecionada. Arraste os pontos brancos para ajustar o caminho.");
        } catch (error) { notify(error.message, true); }
    }

    async function saveContainerLayout() {
        await request(`/api/map/elements/${state.container.elementId}/container-layout-v3/`, {
            method: "PATCH",
            body: JSON.stringify({ layout: state.container.layout }),
        }).catch((error) => notify(error.message, true));
    }

    function organizeContainerNodes() {
        state.container.layout.positions = {};
        (state.container.data?.equipment || []).forEach((item, index) => {
            state.container.layout.positions[String(item.id)] = defaultNodePosition(item, index);
        });
        saveContainerLayout(); renderContainerCanvas();
    }

    function renderConnectionMatrix() {
        const panel = qs('#map-master-container [data-panel="matrix"]');
        const equipment = state.container.data?.equipment || [];
        const ports = equipment.flatMap((item) => (item.ports || []).map((port) => ({ ...port, equipment: item.name })));
        panel.innerHTML = `
            <div class="master-matrix-head"><div><strong>Matriz de manobra</strong><span>Conecte portas sem precisar abrir todos os cards.</span></div></div>
            <form class="master-matrix-form">
                <label>Origem<select name="source">${ports.map((port) => `<option value="${port.id}" data-type="${port.type}">${escapeHtml(port.equipment)} · ${escapeHtml(port.label)}</option>`).join("")}</select></label>
                <span>→</span>
                <label>Destino<select name="destination">${ports.map((port) => `<option value="${port.id}" data-type="${port.type}">${escapeHtml(port.equipment)} · ${escapeHtml(port.label)}</option>`).join("")}</select></label>
                <button type="submit">Conectar</button>
            </form>
            <div class="master-matrix-links">${(state.container.data?.links || []).map((link) => `<article><div><strong>${escapeHtml(link.source)}</strong><span>→ ${escapeHtml(link.destination)}</span><small>${escapeHtml(link.link_type_label)}</small></div><button type="button" class="danger" data-delete-link="${link.id}">Desligar</button></article>`).join("") || "<p>Nenhuma ligação interna.</p>"}</div>`;
        qs("form", panel).onsubmit = async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            await request(`/api/map/elements/${state.container.elementId}/equipment-links/`, {
                method: "POST",
                body: JSON.stringify({ source_port_id: form.elements.source.value, destination_port_id: form.elements.destination.value }),
            });
            await loadContainerMaster(true); renderConnectionMatrix(); renderContainerCanvas();
        };
        qsa("[data-delete-link]", panel).forEach((button) => button.onclick = async () => {
            await request(`/api/map/elements/${state.container.elementId}/equipment-links/${button.dataset.deleteLink}/`, { method: "DELETE" });
            await loadContainerMaster(true); renderConnectionMatrix(); renderContainerCanvas();
        });
    }

    function equipmentCreateDialog() {
        let dialog = qs("#map-master-equipment-create");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-equipment-create";
        dialog.className = "editor-dialog map-master-equipment-dialog";
        dialog.innerHTML = `<form><header><h2>Novo equipamento</h2><button type="button" data-close>×</button></header><div class="master-form-grid"><label>Tipo<select name="equipment_type"></select></label><label>Nome<input name="name" required></label><label>Fabricante<input name="vendor"></label><label>Modelo<input name="model"></label><label>IP de gerência<input name="management_ip"></label><label>Portas LAN da ONU<input name="onu_lan_count" type="number" min="1" max="16" value="4"></label><label>Portas do DIO<select name="dio_port_capacity"><option>12</option><option selected>24</option><option>36</option><option>48</option><option>72</option><option>96</option><option>144</option><option>192</option><option>244</option></select></label><label>Conector<select name="connector_type"><option value="sc_apc">SC/APC</option><option value="sc_upc">SC/UPC</option><option value="lc_upc">LC/UPC</option><option value="lc_apc">LC/APC</option></select></label></div><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Adicionar</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        return dialog;
    }

    function openEquipmentCreateDialog() {
        const dialog = equipmentCreateDialog();
        const types = (state.bootstrap?.equipment_types || []).filter(([value]) => value !== "server");
        dialog.querySelector("select[name='equipment_type']").innerHTML = types.map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("");
        dialog.querySelector("form").reset();
        dialog.querySelector("form").onsubmit = async (event) => {
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(event.currentTarget));
            try {
                await request(`/api/map/elements/${state.container.elementId}/equipment/`, { method: "POST", body: JSON.stringify(payload) });
                dialog.close();
                await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); renderConnectionMatrix();
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        dialog.showModal();
    }

    function equipmentEditorDialog() {
        let dialog = qs("#map-master-equipment-editor");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-equipment-editor";
        dialog.className = "editor-dialog map-master-equipment-dialog";
        dialog.innerHTML = `<form><header><div><h2>Editar equipamento</h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div class="master-form-grid"><label>Nome<input name="name"></label><label>IP de gerência<input name="management_ip"></label><label>Fabricante<input name="vendor"></label><label>Modelo<input name="model"></label><label>Número de série<input name="serial_number"></label><label>Patrimônio<input name="asset_tag"></label><label>Posição no rack (U)<input name="rack_unit"></label><label>Altura (U)<input name="height_units" type="number" min="1"></label><label>Face<select name="rack_face"><option value="">Não informado</option><option value="front">Frente</option><option value="rear">Traseira</option></select></label><label>Foto/URL<input name="photo_url"></label><label>Documentação/URL<input name="documentation_url"></label><label>Firmware<input name="firmware"></label><label>Função<input name="role"></label><label>Slots do chassi<input name="chassis_slots" type="number" min="0"></label><label>Uplinks<input name="uplink_count" type="number" min="0"></label><label>Potência TX (dBm)<input name="tx_power_dbm" type="number" step="0.01"></label><label>Conector<select name="connector_type"><option value="">Não informado</option><option value="sc_apc">SC/APC</option><option value="sc_upc">SC/UPC</option><option value="lc_upc">LC/UPC</option><option value="lc_apc">LC/APC</option></select></label><label>Bandejas do DIO<input name="tray_count" type="number" min="0"></label><label>Portas por bandeja<input name="ports_per_tray" type="number" min="0"></label></div><label>Descrição<textarea name="description" rows="2"></textarea></label><label>Observações<textarea name="notes" rows="3"></textarea></label><section class="master-equipment-expand"><h3>Adicionar portas</h3><div><select data-new-port-type></select><input data-new-port-count type="number" min="1" max="256" value="1"><button type="button" data-add-ports>Adicionar</button></div></section><section class="master-equipment-expand" data-card-editor><h3>Adicionar placa à OLT</h3><div><input data-card-slot type="number" min="1" max="64" placeholder="Slot"><input data-card-pons type="number" min="1" max="64" value="8" placeholder="PONs"><input data-card-name placeholder="Nome da placa"><button type="button" data-add-card>Adicionar placa</button></div></section><section><h3>Portas e módulos</h3><div data-ports class="master-equipment-ports"></div></section><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Salvar</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        return dialog;
    }

    async function openEquipmentEditor(equipmentId) {
        const data = await request(`/api/map/master/elements/${state.container.elementId}/equipment/${equipmentId}/`);
        const item = data.equipment;
        const dialog = equipmentEditorDialog();
        const form = qs("form", dialog);
        const metadata = item.metadata || {};
        ["name", "management_ip", "vendor", "model", "serial_number", "description"].forEach((name) => { if (form.elements[name]) form.elements[name].value = item[name] || ""; });
        ["asset_tag", "rack_unit", "rack_face", "photo_url", "documentation_url", "firmware", "role", "notes", "chassis_slots", "uplink_count", "tray_count", "ports_per_tray", "height_units"].forEach((name) => { form.elements[name].value = metadata[name] || ""; });
        form.elements.tx_power_dbm.value = item.tx_power_dbm ?? "";
        form.elements.connector_type.value = item.connector_type || "";
        qs("[data-new-port-type]", dialog).innerHTML = (state.bootstrap?.port_types || []).map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("");
        qs("[data-card-editor]", dialog).hidden = item.type !== "olt";
        qs("[data-subtitle]", dialog).textContent = item.type_label;
        qs("[data-ports]", dialog).innerHTML = (item.ports || []).map((port) => `<label><span><strong>${escapeHtml(port.label)}</strong><small>${escapeHtml(port.type_label)}</small></span><select data-port-module="${port.id}">${[["", "Sem módulo"], ["sfp_optical_1g", "SFP óptico 1G"], ["sfp_rj45_1g", "SFP/RJ45 1G"], ["sfp_plus_10g", "SFP+ 10G"], ["sfp28_25g", "SFP28 25G"], ["qsfp_40g", "QSFP+ 40G"], ["qsfp28_100g", "QSFP28 100G"], ["dac", "DAC"], ["gbic", "GBIC"], ["other", "Outro"]].map(([value, label]) => `<option value="${value}" ${port.module === value ? "selected" : ""}>${label}</option>`).join("")}</select></label>`).join("") || "<p>Sem portas cadastradas.</p>";
        qs("[data-add-ports]", dialog).onclick = async () => {
            try {
                await request(`/api/map/elements/${state.container.elementId}/equipment/${equipmentId}/ports/`, { method: "POST", body: JSON.stringify({ port_type: qs("[data-new-port-type]", dialog).value, count: qs("[data-new-port-count]", dialog).value }) });
                dialog.close(); await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); await openEquipmentEditor(equipmentId);
            } catch (error) { qs("[data-status]", dialog).textContent = error.message; }
        };
        qs("[data-add-card]", dialog).onclick = async () => {
            try {
                await request(`/api/map/elements/${state.container.elementId}/equipment/${equipmentId}/cards/`, { method: "POST", body: JSON.stringify({ slot: qs("[data-card-slot]", dialog).value, pon_count: qs("[data-card-pons]", dialog).value, name: qs("[data-card-name]", dialog).value }) });
                dialog.close(); await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); await openEquipmentEditor(equipmentId);
            } catch (error) { qs("[data-status]", dialog).textContent = error.message; }
        };
        form.onsubmit = async (event) => {
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(form));
            payload.port_modules = {};
            qsa("[data-port-module]", dialog).forEach((select) => { if (select.value) payload.port_modules[String(select.dataset.portModule)] = select.value; });
            try {
                await request(`/api/map/master/elements/${state.container.elementId}/equipment/${equipmentId}/`, { method: "PATCH", body: JSON.stringify(payload) });
                dialog.close();
                await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas();
                notify("Equipamento atualizado.");
            } catch (error) { qs("[data-status]", dialog).textContent = error.message; }
        };
        dialog.showModal();
    }

    async function exportContainerPng() {
        const canvasRoot = qs("#map-master-container .master-canvas");
        if (!canvasRoot) return;
        const clone = canvasRoot.cloneNode(true);
        clone.style.transform = "none";
        const svgText = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvasRoot.scrollWidth}" height="${canvasRoot.scrollHeight}"><foreignObject width="100%" height="100%">${new XMLSerializer().serializeToString(clone)}</foreignObject></svg>`;
        const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const image = new Image();
        image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = image.width; canvas.height = image.height;
            const context = canvas.getContext("2d");
            context.fillStyle = "#07111f"; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(image, 0, 0);
            URL.revokeObjectURL(url);
            const link = document.createElement("a");
            link.download = `estrutura-${state.container.elementId}-${Date.now()}.png`;
            link.href = canvas.toDataURL("image/png"); link.click();
        };
        image.src = url;
    }


    // ------------------------------------------------------------------
    // Technical sheets, lifecycle history, printing and QR code
    // ------------------------------------------------------------------

    function assetSheetDialog() {
        let dialog = qs("#map-master-asset-sheet");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-asset-sheet";
        dialog.className = "editor-dialog map-master-asset-sheet";
        dialog.innerHTML = `<section>
            <header>
                <div><h2>Ficha técnica</h2><p data-subtitle></p></div>
                <div class="master-sheet-header-actions">
                    <button type="button" class="primary" data-print>Imprimir / PDF</button>
                    <a data-qr target="_blank" rel="noopener">QR Code</a>
                    <button type="button" data-close>Fechar</button>
                </div>
            </header>
            <div class="master-sheet-scroll">
                <div data-sheet-body></div>
                <section class="master-lifecycle-editor">
                    <h3>Estado de implantação</h3>
                    <div><select data-stage><option value="planning">Em projeto</option><option value="not_deployed">Não implantado</option><option value="deployed">Implantado</option><option value="certified">Certificado</option><option value="disabled">Desativado</option></select><input data-stage-note placeholder="Observação"><button type="button" data-stage-save>Registrar</button></div>
                </section>
            </div>
        </section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        return dialog;
    }

    function humanizeSheetKey(key) {
        const labels = {
            id: "ID", project_id: "ID do projeto", transmitter_id: "ID do transmissor",
            latitude: "Latitude", longitude: "Longitude", updated_at: "Última atualização",
            created_at: "Criado em", element_type: "Tipo", asset_type: "Tipo de ativo",
            serial_number: "Número de série", management_ip: "IP de gerência",
        };
        if (labels[key]) return labels[key];
        return String(key || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
    }

    function sheetPrimitive(value, key = "") {
        if (value == null || value === "") return '<span class="empty">Não informado</span>';
        if (typeof value === "boolean") return value ? "Sim" : "Não";
        const string = String(value);
        if (/^https?:\/\//i.test(string)) return `<a class="master-sheet-link" href="${escapeHtml(string)}" target="_blank" rel="noopener">${escapeHtml(string)}</a>`;
        if (/(_at|data|date)$/i.test(key) || /^\d{4}-\d{2}-\d{2}T/.test(string)) {
            const parsed = new Date(string);
            if (!Number.isNaN(parsed.getTime())) return escapeHtml(parsed.toLocaleString("pt-BR"));
        }
        const className = /latitude|longitude/i.test(key) ? "master-sheet-value-coordinate" : /^-?\d+(?:[.,]\d+)?$/.test(string) ? "master-sheet-value-number" : "";
        return `<span class="${className}">${escapeHtml(string)}</span>`;
    }

    function sheetRows(value, depth = 0) {
        if (value == null || value === "") return '<span class="empty">Não informado</span>';
        if (Array.isArray(value)) {
            if (!value.length) return '<span class="empty">Nenhum registro</span>';
            return `<div class="master-sheet-list">${value.map((item) => `<article>${typeof item === "object" ? sheetRows(item, depth + 1) : sheetPrimitive(item)}</article>`).join("")}</div>`;
        }
        if (typeof value === "object") {
            const entries = Object.entries(value).filter(([, item]) => item != null && item !== "" && (!Array.isArray(item) || item.length));
            if (!entries.length) return '<span class="empty">Nenhum dado</span>';
            return `<dl class="master-sheet-definition">${entries.map(([key, item]) => `<div><dt>${escapeHtml(humanizeSheetKey(key))}</dt><dd>${typeof item === "object" ? sheetRows(item, depth + 1) : sheetPrimitive(item, key)}</dd></div>`).join("")}</dl>`;
        }
        return sheetPrimitive(value);
    }

    function printableSheetHtml(report, qrUrl) {
        const asset = report.asset || {};
        return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ficha técnica · ${escapeHtml(asset.name || asset.id)}</title><style>
            *{box-sizing:border-box}body{font:13px Inter,Arial,sans-serif;color:#172033;margin:24px;background:#fff}header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;border-bottom:2px solid #172033;padding-bottom:12px;margin-bottom:18px}h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;margin:20px 0 8px}.qr{width:112px;height:112px;object-fit:contain}.master-sheet-definition{margin:0}.master-sheet-definition>div{display:grid;grid-template-columns:170px minmax(0,1fr);gap:12px;padding:7px 2px;border-bottom:1px solid #e2e8f0}.master-sheet-definition dt{font-weight:700;color:#526174}.master-sheet-definition dd{min-width:0;margin:0;overflow-wrap:anywhere}.master-sheet-list{display:grid;gap:6px}.master-sheet-list article{border:1px solid #d8dee8;padding:8px;border-radius:7px}.empty{color:#8a96a7}@media(max-width:680px){header{display:block}.qr{margin-top:12px}.master-sheet-definition>div{grid-template-columns:1fr}}@media print{body{margin:12mm}header{break-inside:avoid}article,.master-sheet-definition>div{break-inside:avoid}}
        </style></head><body><header><div><h1>${escapeHtml(asset.name || "Ativo")}</h1><p>${escapeHtml(report.project?.name || "")} · ${escapeHtml(report.project?.code || "")} · ${escapeHtml(report.asset_type || "")}</p></div><img class="qr" src="${escapeHtml(qrUrl)}" alt="QR Code"></header><h2>Dados do ativo</h2>${sheetRows(asset)}<h2>Histórico de implantação</h2>${sheetRows(report.lifecycle || [])}<script>window.onload=()=>setTimeout(()=>window.print(),250)<\/script></body></html>`;
    }

    async function openAssetSheet(assetType, assetId) {
        const id = projectId();
        if (!id) throw new Error("Selecione um projeto.");
        const report = await request(`/api/map/master/projects/${id}/asset-report/?asset_type=${encodeURIComponent(assetType)}&asset_id=${encodeURIComponent(assetId)}`);
        const dialog = assetSheetDialog();
        const qrUrl = `/api/map/master/projects/${id}/asset-qr/?asset_type=${encodeURIComponent(assetType)}&asset_id=${encodeURIComponent(assetId)}`;
        const asset = report.asset || {};
        const identityKeys = new Set(["id", "name", "code", "description", "element_type", "type", "status", "enabled"]);
        const locationKeys = new Set(["latitude", "longitude", "address", "city", "state", "cep"]);
        const identity = {};
        const location = {};
        const technical = {};
        Object.entries(asset).forEach(([key, value]) => {
            if (identityKeys.has(key)) identity[key] = value;
            else if (locationKeys.has(key)) location[key] = value;
            else technical[key] = value;
        });
        qs("[data-subtitle]", dialog).textContent = `${report.project?.name || "Projeto"} · ${report.asset_type} #${asset.id}`;
        qs("[data-sheet-body]", dialog).innerHTML = `<div class="master-sheet-grid">
            <section class="master-sheet-card"><h3>Identificação</h3>${sheetRows(identity)}</section>
            <section class="master-sheet-card"><h3>Localização</h3>${sheetRows(location)}</section>
            <section class="master-sheet-card full"><h3>Dados técnicos</h3>${sheetRows(technical)}</section>
            <section class="master-sheet-card full"><h3>Histórico de implantação</h3>${sheetRows(report.lifecycle || [])}</section>
        </div>`;
        qs("[data-qr]", dialog).href = qrUrl;
        qs("[data-print]", dialog).onclick = () => {
            const popup = window.open("", "_blank", "width=1000,height=820,scrollbars=yes");
            if (!popup) return notify("O navegador bloqueou a janela de impressão/PDF.", true);
            try { popup.opener = null; } catch (_error) {}
            popup.document.open();
            popup.document.write(printableSheetHtml(report, new URL(qrUrl, window.location.origin).href));
            popup.document.close();
        };
        qs("[data-stage-save]", dialog).onclick = async () => {
            await request(`/api/map/master/projects/${id}/lifecycle/`, {
                method: "POST",
                body: JSON.stringify({ asset_type: assetType, asset_id: assetId, stage: qs("[data-stage]", dialog).value, note: qs("[data-stage-note]", dialog).value }),
            });
            notify("Estado registrado no histórico.");
            dialog.close();
            await openAssetSheet(assetType, assetId);
        };
        dialog.showModal();
    }

    // ------------------------------------------------------------------
    // Optical trace dialog
    // ------------------------------------------------------------------

    function traceDialog() {
        let dialog = qs("#map-master-trace-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-trace-dialog";
        dialog.className = "editor-dialog map-master-trace-dialog";
        dialog.innerHTML = `<form><header><div><h2>Rastreamento óptico</h2><p>OLT/DIO → cabo → CEO/CDO → CTO → destino</p></div><button type="button" data-close>×</button></header><div class="master-form-grid"><label>Origem<select name="start"></select></label><label>Destino<select name="end"></select></label><label>Rota<select name="route_id"><option value="">Todas as rotas</option></select></label></div><button type="submit" class="primary-button">Rastrear</button><div data-result class="master-trace-result"></div></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        return dialog;
    }

    function traceNodeLabel(node, catalog = {}) {
        const [kind, rawId] = String(node || "").split(":", 2);
        const id = Number(rawId);
        const groups = { element: "elements", cable: "cables", fiber: "fibers", port: "ports", equipment: "equipment", splitter_port: "splitter_ports" };
        const item = catalog[groups[kind]]?.[id] || catalog[groups[kind]]?.[String(id)];
        if (!item) return node;
        if (kind === "element") return `${item.name} · ${item.subtype || item.type}`;
        if (kind === "cable") return `${item.name} · ${item.fiber_count}F`;
        if (kind === "fiber") return `${item.cable} · Fibra ${item.number} · ${item.color}`;
        if (kind === "port") return `${item.equipment} · ${item.label}`;
        if (kind === "equipment") return `${item.name} · ${item.type}`;
        if (kind === "splitter_port") return `${item.box} · ${item.ratio} saída ${item.number}`;
        return node;
    }

    async function openTraceDialog() {
        const id = projectId();
        if (!id) throw new Error("Selecione um projeto.");
        if (!state.bootstrap) await refreshBootstrap();
        const elements = await request(`/api/map/elements/?project_id=${encodeURIComponent(id)}`);
        const dialog = traceDialog();
        const options = (elements.features || []).map((feature) => `<option value="element:${feature.properties.id}">${escapeHtml(feature.properties.nome)} · ${escapeHtml(feature.properties.tipo)}</option>`).join("");
        dialog.querySelector("select[name='start']").innerHTML = options;
        dialog.querySelector("select[name='end']").innerHTML = options;
        dialog.querySelector("select[name='route_id']").innerHTML = '<option value="">Todas as rotas</option>' + validRoutes().map((route) => `<option value="${route.id}">${escapeHtml(route.name)}</option>`).join("");
        dialog.querySelector("form").onsubmit = async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const query = new URLSearchParams({ start: form.elements.start.value, end: form.elements.end.value });
            if (form.elements.route_id.value) query.set("route_id", form.elements.route_id.value);
            const result = await request(`/api/map/master/projects/${id}/trace/?${query}`);
            const target = qs("[data-result]", dialog);
            target.innerHTML = result.found ? result.nodes.map((node, index) => `<div><span>${index + 1}</span><strong>${escapeHtml(traceNodeLabel(node, result.catalog))}</strong></div>`).join("") : "<p>Nenhum caminho conectado foi encontrado.</p>";
        };
        dialog.showModal();
    }



    async function applyInitialFocus() {
        const focus = new URLSearchParams(window.location.search).get("focus");
        if (!focus || sessionStorage.getItem(`map-master-focused:${focus}`)) return;
        const [type, rawId] = focus.split(":", 2);
        const id = Number(rawId);
        const map = window.networkMap?.map;
        if (!map || !id) return;
        if (type === "element") {
            const result = await request(`/api/map/elements/${id}/`);
            const item = result.element;
            if (item?.latitude != null && item?.longitude != null) map.setView([item.latitude, item.longitude], 21);
        } else if (type === "cable") {
            const result = await request(`/api/map/cables/${id}/`);
            const points = flattenCableCoordinates(result.cable).flat().map(([longitude, latitude]) => [latitude, longitude]);
            if (points.length) map.fitBounds(points, { padding: [50, 50], maxZoom: 21 });
        } else if (type === "equipment" && projectId()) {
            const result = await request(`/api/map/master/projects/${projectId()}/asset-report/?asset_type=equipment&asset_id=${id}`);
            if (result.asset?.latitude != null && result.asset?.longitude != null) map.setView([result.asset.latitude, result.asset.longitude], 21);
        }
        sessionStorage.setItem(`map-master-focused:${focus}`, "1");
    }

    // ------------------------------------------------------------------
    // Observers limited to relevant UI roots
    // ------------------------------------------------------------------

    function installObservers() {
        const map = qs("#map");
        if (map) {
            let scheduled = false;
            new MutationObserver((mutations) => {
                const relevant = mutations.some((mutation) => [...mutation.addedNodes].some((node) => node.nodeType === 1 && (node.matches?.(".leaflet-popup, .leaflet-marker-icon") || node.querySelector?.(".leaflet-popup, .leaflet-marker-icon"))));
                if (!relevant || scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => { scheduled = false; decoratePopups(map); applyConfiguredIcons(map); });
            }).observe(map, { childList: true, subtree: true });
        }
        const fusion = fusionDialog();
        if (fusion) {
            new MutationObserver(() => requestAnimationFrame(enhanceFusion)).observe(fusion, { childList: true, subtree: true, attributes: true, attributeFilter: ["open"] });
            fusion.addEventListener("close", () => {
                fusion.removeAttribute("data-user-positioned");
                fusion.style.removeProperty("left");
                fusion.style.removeProperty("top");
                fusion.style.removeProperty("margin");
                fusion.style.removeProperty("transform");
                if (Date.now() < state.fusionKeepOpenUntil && fusion.dataset.elementId) {
                    window.setTimeout(() => window.networkMap?.showUnifilar?.(fusion.dataset.elementId), 40);
                }
            });
        }
        const container = containerDialog();
        if (container) {
            let scheduledContainer = false;
            new MutationObserver(() => {
                if (!container.open || !container.dataset.elementId || scheduledContainer) return;
                scheduledContainer = true;
                requestAnimationFrame(() => {
                    scheduledContainer = false;
                    enhanceContainer().catch((error) => notify(error.message, true));
                });
            }).observe(container, { attributes: true, attributeFilter: ["open", "data-element-id"] });
        }
    }

    async function init() {
        installCompactShell();
        installActionController();
        installObservers();
        decoratePopups();
        const select = qs("#project-select");
        select?.addEventListener("change", () => window.setTimeout(() => refreshBootstrap().catch((error) => notify(error.message, true)), 40));
        for (let attempt = 0; attempt < 80 && !window.networkMap; attempt += 1) {
            await new Promise((resolve) => window.setTimeout(resolve, 50));
        }
        await refreshBootstrap().catch((error) => notify(`Mapa mestre: ${error.message}`, true));
        await applyInitialFocus().catch((error) => notify(`Foco do mapa: ${error.message}`, true));
        window.addEventListener("resize", () => { clampDialog(fusionDialog()); drawContainerLinks(); });
        window.mapMasterSuite = {
            version: VERSION,
            refresh: refreshBootstrap,
            openReserve,
            openCableRoute,
            enhanceContainer,
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init());
    else init();
}());
