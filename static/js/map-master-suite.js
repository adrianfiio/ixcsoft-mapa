(function () {
    "use strict";

    const VERSION = "1.3.0";
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
            layout: { positions: {}, cablePositions: {}, dioPages: {}, routes: {}, nodeWidths: {}, zoom: 1 },
            selectedPort: null,
            selectedFiber: null,
            lineMode: false,
            selectedLink: null,
            loadingPromise: null,
            loadingElementId: "",
            rendering: false,
            // Incrementada a cada abertura/fechamento; qualquer await em voo
            // que resolver depois da geração ter mudado é descartado (evita
            // resposta atrasada sobrescrever o editor de um elemento novo).
            openGeneration: 0,
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
            <button type="button" data-master-routes title="Criar, selecionar e filtrar rotas">Rotas</button>
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
                <div><strong>Rotas</strong><small>Crie, selecione e filtre rotas do projeto</small></div>
                <button type="button" data-route-close aria-label="Fechar">×</button>
            </header>
            <div class="route-master-actions">
                <button type="button" data-route-create>+ Nova rota</button>
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
        drawer.querySelector("[data-route-create]").onclick = () => {
            createRoute().catch((error) => notify(error.message, true));
        };
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
        const routes = state.bootstrap?.topology?.routes || [];
        const button = qs("[data-master-routes]");
        const oldPanel = qs("#route-filter-v092");
        if (oldPanel) oldPanel.hidden = true;
        drawer.hidden = false;
        if (button) button.hidden = false;
        const list = qs("[data-route-master-list]", drawer);
        if (!routes.length) {
            list.innerHTML = '<p class="help-text">Nenhuma rota cadastrada. Use “+ Nova rota”.</p>';
        } else {
            list.innerHTML = routes.map((route) => `
                <label class="route-master-item ${route.valid ? "" : "invalid"}">
                    <input type="checkbox" value="${route.id}" ${state.allRoutes || state.selectedRoutes.has(String(route.id)) ? "checked" : ""}>
                    <span><strong>${escapeHtml(route.name)}</strong><small>${route.counts.cables} cabos · ${route.counts.ctos} CTO · ${route.counts.splice_boxes} CEO/CDO${route.valid ? "" : ` · ${escapeHtml(route.reason)}`}</small></span>
                    <button type="button" data-only-route="${route.id}">Só</button>
                </label>`).join("");
        }
        qsa('input[type="checkbox"]', list).forEach((input) => {
            input.onchange = () => {
                if (state.allRoutes) {
                    state.selectedRoutes = new Set(routes.map((item) => String(item.id)));
                }
                state.allRoutes = false;
                if (input.checked) state.selectedRoutes.add(input.value);
                else state.selectedRoutes.delete(input.value);
                applyRouteChanges();
            };
        });
        qsa("[data-only-route]", list).forEach((onlyButton) => {
            onlyButton.onclick = () => {
                state.allRoutes = false;
                state.selectedRoutes = new Set([String(onlyButton.dataset.onlyRoute)]);
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
                <header><div><h2 data-route-dialog-title>Adicionar na rota</h2><p>Selecione uma rota existente ou crie uma nova.</p></div><button type="button" data-close>×</button></header>
                <label>Rota<select name="route_id"></select></label>
                <button type="button" data-create-inline>+ Criar nova rota</button>
                <p data-status></p>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Adicionar na rota</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        dialog.querySelector("[data-create-inline]").onclick = async () => {
            const route = await createRoute();
            if (!route) return;
            const select = qs("select", dialog);
            const option = document.createElement("option");
            option.value = String(route.id);
            option.textContent = route.name;
            select.appendChild(option);
            select.value = String(route.id);
        };
        return dialog;
    }

    function routeCreateDialog() {
        let dialog = qs("#map-master-route-create-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-route-create-dialog";
        dialog.className = "editor-dialog map-master-small-dialog";
        dialog.innerHTML = `
            <form>
                <header><div><h2>Nova rota</h2><p>O código é gerado automaticamente e permanece único por empresa.</p></div><button type="button" data-close>×</button></header>
                <label>Nome da rota<input name="name" maxlength="180" required placeholder="Ex.: Rota Centro 01"></label>
                <label>Código opcional<input name="code" maxlength="80" placeholder="Ex.: CENTRO-01"></label>
                <p data-status></p>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Criar rota</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        return dialog;
    }

    async function createRoute() {
        const id = projectId();
        if (!id) throw new Error("Selecione um projeto antes de criar a rota.");
        const dialog = routeCreateDialog();
        const form = qs("form", dialog);
        const status = qs("[data-status]", dialog);
        form.reset();
        status.textContent = "";
        if (!dialog.open) dialog.showModal();
        return new Promise((resolve) => {
            let settled = false;
            const finish = (value) => {
                if (settled) return;
                settled = true;
                if (dialog.open) dialog.close();
                resolve(value);
            };
            form.onsubmit = async (event) => {
                event.preventDefault();
                const payload = Object.fromEntries(new FormData(form));
                payload.project_id = Number(id);
                try {
                    const data = await request("/api/map/routes/", {
                        method: "POST",
                        body: JSON.stringify(payload),
                    });
                    await refreshBootstrap();
                    notify(`Rota ${data.route.name} criada.`);
                    finish(data.route);
                } catch (error) {
                    status.textContent = error.message;
                }
            };
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(null);
            };
            qs("[data-cancel]", dialog).onclick = () => finish(null);
            qs("[data-close]", dialog).onclick = () => finish(null);
        });
    }

    function fillRouteSelect(select) {
        const routes = state.bootstrap?.topology?.routes || [];
        select.innerHTML = '<option value="">Sem rota definida</option>' + routes.map((route) =>
            `<option value="${route.id}">${escapeHtml(route.name)}${route.valid ? "" : ` · ${escapeHtml(route.reason)}`}</option>`
        ).join("");
    }

    async function openCableRoute(cableId) {
        if (!state.bootstrap) await refreshBootstrap();
        const dialog = routeDialog();
        qs("[data-route-dialog-title]", dialog).textContent = "Adicionar cabo na rota";
        const select = qs("select", dialog);
        fillRouteSelect(select);
        qs("[data-status]", dialog).textContent = "";
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request("/api/map/assets/route/", {
                    method: "POST",
                    body: JSON.stringify({
                        cable_id: Number(cableId),
                        route_id: select.value,
                    }),
                });
                dialog.close();
                await refreshBootstrap();
                await window.networkMap?.loadStructure?.();
                notify("Rota do cabo atualizada.");
            } catch (error) {
                qs("[data-status]", dialog).textContent = error.message;
            }
        };
        if (!dialog.open) dialog.showModal();
    }

    async function openElementRoute(elementId, elementType = "") {
        if (!state.bootstrap) await refreshBootstrap();
        const dialog = routeDialog();
        const isCto = String(elementType) === "cto";
        qs("[data-route-dialog-title]", dialog).textContent = isCto
            ? "Adicionar CTO na rota"
            : "Adicionar CEO/CDO na rota";
        const select = qs("select", dialog);
        fillRouteSelect(select);
        qs("[data-status]", dialog).textContent = "";
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            try {
                const data = await request("/api/map/assets/route/", {
                    method: "POST",
                    body: JSON.stringify({
                        element_id: Number(elementId),
                        route_id: select.value,
                    }),
                });
                dialog.close();
                await refreshBootstrap();
                await window.networkMap?.loadStructure?.();
                notify(
                    data.route
                        ? `Elemento adicionado à rota ${data.route}.`
                        : "Rotas do elemento atualizadas."
                );
            } catch (error) {
                qs("[data-status]", dialog).textContent = error.message;
            }
        };
        if (!dialog.open) dialog.showModal();
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
        qsa(".network-marker", root).forEach((marker) => {
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
            state.container.layout = { positions: {}, cablePositions: {}, dioPages: {}, routes: {}, nodeWidths: {}, zoom: 1, ...(layout.layout || {}) };
            state.container.layout.positions ||= {};
            state.container.layout.cablePositions ||= {};
            state.container.layout.dioPages ||= {};
            state.container.layout.routes ||= {};
            state.container.layout.nodeWidths ||= {};
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
        if (type === "server") return "Servidores";
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
                <button type="button" data-tab="equipment">Equipamentos</button>
                <button type="button" data-tab="canvas" class="active">Canvas 2D</button>
                <button type="button" data-tab="matrix">Matriz de manobra</button>
                <button type="button" data-tab="fibers">Fibras e terminações</button>
                <button type="button" data-tab="models">YAML / modelos</button>
            </nav>
            <div class="master-container-toolbar">
                <button type="button" data-container-add>+ Equipamento</button>
                <button type="button" data-container-organize>Organizar</button>
                <button type="button" data-container-lines>Editar linhas</button>
                <button type="button" data-container-export>Exportar PNG</button>
                <button type="button" data-container-export-pdf>Exportar PDF</button>
                <button type="button" data-container-revision>Salvar versão</button>
                <button type="button" data-container-fullscreen>Tela cheia</button>
            </div>
            <section data-panel="equipment" class="master-container-panel"></section>
            <section data-panel="canvas" class="master-container-panel active"><div class="master-canvas-scroll"><div class="master-canvas"><svg class="master-canvas-links"></svg><div class="master-canvas-nodes"></div></div></div></section>
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
        qs("[data-container-add]", root).onclick = () => openEquipmentCreateDialog().catch((error) => notify(error.message, true));
        qs("[data-container-organize]", root).onclick = () => organizeContainerNodes();
        qs("[data-container-lines]", root).onclick = (event) => {
            state.container.lineMode = !state.container.lineMode;
            root.classList.toggle("line-mode-active", state.container.lineMode);
            event.currentTarget.classList.toggle("active", state.container.lineMode);
            event.currentTarget.textContent = state.container.lineMode ? "Concluir linhas" : "Editar linhas";
            renderContainerCanvas();
        };
        qs("[data-container-export]", root).onclick = () => exportContainerPng();
        qs("[data-container-export-pdf]", root).onclick = () => exportContainerPdf();
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

    // Função pública única pra abrir o editor de Rack/Torre (v0.75.9).
    // Chamada direto pelo clique no marker (map-editor.js) — não existe mais
    // nenhum caminho paralelo (nem manageContainer legado, nem
    // MutationObserver): só ela decide quando o container-dialog abre, e só
    // abre depois que equipment/ + container-layout-v3/ já chegaram e o
    // Canvas já foi desenhado — nunca mostra o dialog vazio esperando dado.
    async function openContainerWorkspace(id) {
        const dialog = containerDialog();
        if (!dialog) return null;
        if (state.container.rendering) return null;
        state.container.openGeneration += 1;
        const generation = state.container.openGeneration;
        dialog.dataset.elementId = String(id);
        dialog.dataset.containerType = "";
        dialog.dataset.containerName = "";
        state.container.rendering = true;
        try {
            let data;
            try {
                data = await loadContainerMaster(true);
            } catch (error) {
                if (generation === state.container.openGeneration) notify(error.message, true);
                throw error;
            }
            // Resposta atrasada de uma abertura anterior (ou o usuário já
            // fechou/trocou de elemento enquanto a requisição estava em
            // voo): descarta em silêncio, sem sobrescrever o editor atual.
            if (generation !== state.container.openGeneration) return null;
            if (!data) return null;
            const root = ensureContainerWorkspace();
            // Sempre abre na aba Canvas 2D, mesmo que o workspace já existisse
            // de uma abertura anterior nesta mesma página (o template já nasce
            // com "canvas" ativo, mas isso garante o mesmo resultado em toda
            // reabertura, não só na primeira vez).
            if (root) {
                qsa("[data-tab]", root).forEach((button) => button.classList.toggle("active", button.dataset.tab === "canvas"));
                qsa("[data-panel]", root).forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === "canvas"));
            }
            renderEquipmentList();
            renderContainerCanvas();
            renderConnectionMatrix();
            attachLegacyPanels();
            if (generation !== state.container.openGeneration) return null;
            if (!dialog.open) dialog.show();
            document.dispatchEvent(new CustomEvent("map:container-opening", { detail: { dialog, elementId: id } }));
            document.dispatchEvent(new CustomEvent("map:container-rendered", { detail: { root: dialog, data } }));
            return data;
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
        // MAP_V07533_OPTICAL_CLEANUP: guarda defensiva -- se o painel de
        // equipamentos sumir por qualquer motivo (workspace ainda não
        // montado, DOM alterado por algum código externo), registra o
        // problema em vez de derrubar o editor inteiro com um TypeError.
        if (!panel) {
            const dialog = containerDialog();
            console.error("[MapMaster] Painel de equipamentos não encontrado.", {
                dialog, containerId: dialog?.dataset.elementId, containerType: dialog?.dataset.containerType,
            });
            return;
        }
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

    function estimatedNodeHeightV07510(item) {
        const ports = item?.ports || [];
        if (item?.type === "dio" && ports.length > 24) return 90 + Math.ceil(ports.length / 12) * 72;
        if (item?.type === "olt" && Object.keys(item?.metadata?.device_type || {}).length) {
            const definitions = item.metadata.device_type.interfaces || [];
            const groups = new Set(definitions.map((row) => row.group_name || row.description || "Interfaces"));
            // MAP_V07515_OLT_PON_ONLY: sem a grade de utilidades (módulos/PWR)
            // renderizada, não há mais altura extra pra reservar pra ela.
            return 120 + Math.ceil(Math.max(1, groups.size) / 2) * 150;
        }
        return 180;
    }

    function defaultNodePosition(item, index) {
        const columns = { olt: 0, dio: 0, switch: 1, router: 1, firewall: 1, onu: 2, access_point: 2, ptp: 2, pto: 2, other: 2 };
        const column = columns[item.type] ?? 2;
        const previous = (state.container.data?.equipment || []).slice(0, index).filter((row) => (columns[row.type] ?? 2) === column);
        const y = 35 + previous.reduce((total, row) => total + estimatedNodeHeightV07510(row) + 55, 0);
        return { x: 40 + column * 380, y };
    }

    function nodePosition(item, index) {
        return state.container.layout.positions[String(item.id)] || defaultNodePosition(item, index);
    }

    function defaultCablePosition(cable, index) {
        return { x: cable.relation === "output" ? 1010 : 25, y: 35 + index * 205 };
    }

    function cablePosition(cable, index) {
        return state.container.layout.cablePositions?.[String(cable.id)] || defaultCablePosition(cable, index);
    }

    function containerCanvasMidpoint() {
        const rows = state.container.data?.equipment || [];
        if (!rows.length) return 600;
        const positions = rows.map((item, index) => nodePosition(item, index).x);
        return (Math.min(...positions) + Math.max(...positions) + 220) / 2;
    }

    function cableVisualSide(position) {
        return Number(position?.x || 0) + 105 >= containerCanvasMidpoint() ? "right" : "left";
    }

    function syncCableVisualSide(node) {
        if (!node) return "left";
        const side = cableVisualSide({ x: Number(node.dataset.posX || 0) });
        node.dataset.cableSide = side;
        node.classList.toggle("side-right-v0758", side === "right");
        node.classList.toggle("side-left-v0758", side === "left");
        return side;
    }

    function portSide(port, index) {
        return index % 2 === 0 ? "left" : "right";
    }

    function chunkV07510(items, size) {
        const chunks = [];
        for (let index = 0; index < items.length; index += size) chunks.push(items.slice(index, index + size));
        return chunks;
    }

    function equipmentDeviceTypeV07510(item) {
        return item?.metadata?.device_type || {};
    }

    function renderDioPortPairV07510(port) {
        const rearLink = port.fusion_link_id || "";
        const frontLink = port.link_id || "";
        // MAP_V07558_DIO_SINGLE_PORT: 1 elemento só por porta física, a
        // pedido do usuário (mockup "Painel D.I.O") — antes eram 2
        // quadrados (frente/trás) lado a lado ou empilhados, sempre lendo
        // como "2 portas". Agora é 1 quadrado (clique = fusão/rua, cor
        // vermelho/laranja) com 1 bolinha central (clique = OLT/PON, cor
        // preto/azul) — mesmo par de dados de sempre (front = PON,
        // rear = fusão), só que num único elemento visual.
        return `<button type="button" class="master-node-port v07558-dio-unit ${port.fusion_used ? "used" : ""}" data-port-id="${port.id}" data-port-role="rear" data-port-type="${port.type}" data-link-id="${rearLink}" title="${escapeHtml(port.label)} · fusão com o cabo da rua"><i class="v07558-dio-dot" data-port-id="${port.id}" data-port-role="front" data-port-type="${port.type}" data-link-id="${frontLink}" title="${escapeHtml(port.label)} · porta da OLT/PON"></i><span>${escapeHtml(port.label)}</span></button>`;
    }

    function renderDioTraysV07510(ports) {
        if (ports.length <= 24) {
            return `<div class="master-node-ports">${ports.map((port) => renderDioPortPairV07510(port)).join("") || '<small class="empty">Sem portas</small>'}</div>`;
        }
        return `<div class="master-dio-trays-v07510">${chunkV07510(ports, 12).map((tray, index) => `
            <section class="master-dio-tray-v07510" data-dio-tray="${index + 1}">
                <strong class="master-dio-tray-label-v07510">T${index + 1}</strong>
                <div class="master-dio-tray-ports-v07510">${tray.map((port) => renderDioPortPairV07510(port)).join("")}</div>
            </section>`).join("")}</div>`;
    }

    function renderGenericPortsV07510(ports) {
        return `<div class="master-node-ports">${ports.map((port, portIndex) => {
            const side = portSide(port, portIndex);
            return `<button type="button" class="master-node-port ${side} ${port.used ? "used" : ""}" data-port-id="${port.id}" data-port-role="front" data-port-type="${port.type}" data-link-id="${port.link_id || ""}" title="${escapeHtml(port.type_label || port.type)}"><span>${escapeHtml(port.label)}</span><i></i></button>`;
        }).join("") || '<small class="empty">Sem portas</small>'}</div>`;
    }

    function oltInterfaceGroupsV07510(item, ports) {
        const metadata = equipmentDeviceTypeV07510(item);
        const definitions = Array.isArray(metadata.interfaces) ? metadata.interfaces : [];
        const portByLabel = new Map(ports.map((port) => [String(port.label || ""), port]));
        const used = new Set();
        const groups = new Map();
        definitions.forEach((definition, index) => {
            const port = portByLabel.get(String(definition.name || ""));
            if (!port) return;
            used.add(port.id);
            const name = definition.group_name || definition.description || "Interfaces";
            if (!groups.has(name)) groups.set(name, { name, order: Number(definition.group_order ?? 9999), kind: definition.group_kind || "interface", ports: [] });
            groups.get(name).ports.push(port);
        });
        const unmatched = ports.filter((port) => !used.has(port.id));
        if (unmatched.length) groups.set("Outras interfaces", { name: "Outras interfaces", order: 9999, kind: "interface", ports: unmatched });
        return [...groups.values()].sort((first, second) => first.order - second.order || first.name.localeCompare(second.name));
    }

    function renderOltChassisV07510(item, ports) {
        const metadata = equipmentDeviceTypeV07510(item);
        const groups = oltInterfaceGroupsV07510(item, ports);
        // MAP_V07515_OLT_PON_ONLY: só as placas de serviço (PON/uplink)
        // interessam no Canvas — os slots utilitários do chassi (módulos
        // vazios, fonte de alimentação) importados do YAML do fabricante
        // não têm porta nenhuma pra ligar e só ocupavam espaço.
        return `<div class="master-olt-chassis-body-v07510">
            <div class="master-olt-chassis-meta-v07510"><span>${escapeHtml(metadata.manufacturer || item.vendor || "OLT")} · ${escapeHtml(metadata.model || item.model || item.name)}</span><span>${metadata.u_height ? `${metadata.u_height}U` : "Chassi modular"}</span></div>
            <div class="master-olt-slots-v07510">${groups.map((group) => `<section class="master-olt-slot-v07510" data-slot-kind="${escapeHtml(group.kind)}"><header><strong>${escapeHtml(group.name)}</strong><span>${group.ports.length} porta(s)</span></header><div class="master-olt-slot-ports-v07510">${group.ports.map((port) => `<button type="button" class="master-node-port right olt-port-v07510 ${port.used ? "used" : ""}" data-port-id="${port.id}" data-port-role="front" data-port-type="${port.type}" data-link-id="${port.link_id || ""}" title="${escapeHtml(port.type_label || port.type)}"><span>${escapeHtml(port.label)}</span><i></i></button>`).join("")}</div></section>`).join("")}</div>
        </div>
        <span class="master-olt-resize-grip-v07515" title="Arraste para aumentar/diminuir a largura" aria-hidden="true">⋮⋮</span>`;
    }

    function renderEquipmentBodyV07510(item, ports) {
        if (item.type === "dio") return renderDioTraysV07510(ports);
        if (item.type === "olt" && Object.keys(equipmentDeviceTypeV07510(item)).length) return renderOltChassisV07510(item, ports);
        return renderGenericPortsV07510(ports);
    }


    function noteStoreV07511() {
        state.container = state.container || {};
        state.container.layout = state.container.layout || {};
        if (!Array.isArray(state.container.layout.notes)) state.container.layout.notes = [];
        return state.container.layout.notes;
    }

    function clampV07511(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function ensureNoteDialogV07511() {
        let dialog = document.querySelector("#master-v07511-note-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "master-v07511-note-dialog";
        dialog.className = "master-v07511-note-dialog";
        dialog.innerHTML = `
            <form method="dialog">
                <header><strong>Nota técnica</strong><small>Escreva livremente. Você pode arrastar, editar e excluir depois.</small></header>
                <textarea name="text" rows="12" maxlength="20000" required></textarea>
                <footer>
                    <button type="button" data-note-cancel>Cancelar</button>
                    <button type="submit" class="primary-button">Salvar nota</button>
                </footer>
            </form>`;
        document.body.appendChild(dialog);
        return dialog;
    }

    function editNoteDialogV07511(value) {
        const dialog = ensureNoteDialogV07511();
        const textarea = dialog.querySelector("textarea");
        textarea.value = value || "";
        if (!dialog.open) dialog.showModal();
        setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }, 20);
        return new Promise((resolve) => {
            let done = false;
            const finish = (result) => {
                if (done) return;
                done = true;
                if (dialog.open) dialog.close();
                resolve(result);
            };
            dialog.querySelector("form").onsubmit = (event) => {
                event.preventDefault();
                const text = textarea.value.trim();
                if (!text) {
                    textarea.focus();
                    return;
                }
                finish(text);
            };
            dialog.querySelector("[data-note-cancel]").onclick = () => finish(null);
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(null);
            };
        });
    }

    function openEditNoteV07511(index) {
        const notes = noteStoreV07511();
        const note = notes[index];
        if (!note) return;
        editNoteDialogV07511(note.text || "").then((text) => {
            if (!text) return;
            note.text = text;
            saveContainerLayout();
            renderContainerCanvas();
        });
    }

    function openDeleteNoteV07511(index) {
        const notes = noteStoreV07511();
        if (!notes[index]) return;
        if (!window.confirm("Excluir esta nota técnica?")) return;
        notes.splice(index, 1);
        saveContainerLayout();
        renderContainerCanvas();
    }

    function installNoteDragV07511(node) {
        if (!node || node.dataset.dragReadyV07511 === "true") return;
        node.dataset.dragReadyV07511 = "true";
        const index = Number(node.dataset.canvasNote);
        const notes = noteStoreV07511();
        const note = notes[index];
        const workspace = node.closest("#map-master-container") || document.querySelector("#map-master-container");
        const canvas = workspace?.querySelector("[data-panel='canvas'] .master-canvas") || workspace?.querySelector(".master-canvas");
        let startX = 0;
        let startY = 0;
        let originX = Number(note?.x || 40);
        let originY = Number(note?.y || 40);

        const apply = (x, y) => {
            node.style.transform = `translate(${x}px,${y}px)`;
            if (note) {
                note.x = x;
                note.y = y;
            }
        };

        const pointerMove = (event) => {
            const rect = canvas?.getBoundingClientRect();
            const x = originX + (event.clientX - startX);
            const y = originY + (event.clientY - startY);
            const maxX = Math.max(40, (rect?.width || 1800) - node.offsetWidth - 16);
            const maxY = Math.max(40, (rect?.height || 1200) - node.offsetHeight - 16);
            apply(clampV07511(x, 12, maxX), clampV07511(y, 12, maxY));
        };

        const pointerUp = () => {
            node.classList.remove("dragging-v07511");
            window.removeEventListener("pointermove", pointerMove);
            window.removeEventListener("pointerup", pointerUp);
            saveContainerLayout();
        };

        node.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            if (event.target.closest("button")) return;
            event.preventDefault();
            startX = event.clientX;
            startY = event.clientY;
            originX = Number(note?.x || 40);
            originY = Number(note?.y || 40);
            node.classList.add("dragging-v07511");
            window.addEventListener("pointermove", pointerMove);
            window.addEventListener("pointerup", pointerUp, { once: true });
        });

        node.addEventListener("dblclick", () => openEditNoteV07511(index));
        node.querySelector("[data-edit-note]")?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            openEditNoteV07511(index);
        });
        node.querySelector("[data-delete-note]")?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            openDeleteNoteV07511(index);
        });
    }

    function cableAccentV07511(cable) {
        return ((cable.fibers || []).find((fiber) => fiber.color_hex)?.color_hex) || "#22d3ee";
    }
    function renderContainerCanvas() {
        const root = qs("#map-master-container");
        if (!root || !state.container.data) return;
        const canvas = qs(".master-canvas", root);
        const nodes = qs(".master-canvas-nodes", canvas);
        const equipment = state.container.data.equipment || [];
        // MAP_V07562_RACK_CABLES_MATRIX_ONLY: a pedido do usuário — o
        // "widget" do cabo (card com as fibras coloridas, arraste até
        // um DIO) não aparece mais sozinho no Canvas do Rack; o cabo
        // já tem seu próprio jeito de virar fusão direto na Matriz de
        // Fusão (+ Vincular, ver map-dio-fusion-v07538.js), então isso
        // não tira nenhuma funcionalidade, só o card duplicado. A Torre
        // não muda — só o Rack tinha esse pedido.
        const isRackContainer = state.container.data.container?.type === "rack";
        const cables = isRackContainer ? [] : (state.container.data.cables || []);
        root.classList.toggle("line-mode-active", state.container.lineMode);
        nodes.innerHTML = equipment.map((item, index) => {
            const position = nodePosition(item, index);
            const ports = item.ports || [];
            const nodeClasses = ["master-canvas-node"];
            if (item.type === "dio" && ports.length > 24) nodeClasses.push("master-dio-large-v07510");
            const isOltChassis = item.type === "olt" && Object.keys(equipmentDeviceTypeV07510(item)).length;
            if (isOltChassis) nodeClasses.push("master-olt-chassis-v07510");
            // MAP_V07515_OLT_RESIZE: largura salva (se o usuário já arrastou
            // a alça de redimensionar) vira variável CSS por nó; sem valor
            // salvo, a regra padrão do CSS (--olt-width com fallback) vale.
            const savedWidth = isOltChassis ? Number(state.container.layout.nodeWidths?.[String(item.id)]) : 0;
            const widthStyle = savedWidth > 0 ? `--olt-width:${savedWidth}px;` : "";
            return `<article class="${nodeClasses.join(" ")}" data-equipment-node="${item.id}" data-equipment-type="${escapeHtml(item.type)}" data-provisioning-mode="${escapeHtml(item.provisioning_mode || 'manual')}" data-monitoring-eligible="${item.monitoring_eligible === true ? 'true' : 'false'}" data-pos-x="${position.x}" data-pos-y="${position.y}" style="${widthStyle}transform:translate(${position.x}px,${position.y}px)">
                <header><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.type_label)}</small><span class="master-node-actions"><button type="button" class="master-node-edit" data-node-edit="${item.id}" title="Editar propriedades" aria-label="Editar ${escapeHtml(item.name)}"><svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"></path><path d="m13.5 6.5 3.5 3.5"></path></svg></button><button type="button" class="master-node-delete" data-node-delete="${item.id}" title="Excluir equipamento" aria-label="Excluir ${escapeHtml(item.name)}"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6"></path></svg></button></span></header>
                ${renderEquipmentBodyV07510(item, ports)}
            </article>`;
        }).join("") + cables.map((cable, index) => {
            const position = cablePosition(cable, index);
            const relation = cable.relation === "output" ? "Saída" : "Entrada";
            const visualSide = cableVisualSide(position);
            const accent = cableAccentV07511(cable);
            return `<article class="master-cable-node vertical-v07510 ${cable.relation === "output" ? "output" : "input"} side-${visualSide}-v0757" data-cable-side="${visualSide}" data-cable-node="${cable.id}" data-fiber-count="${cable.fiber_count || 0}" data-pos-x="${position.x}" data-pos-y="${position.y}" style="--cable-accent:${escapeHtml(accent)};transform:translate(${position.x}px,${position.y}px)">
                <header><span><strong>${escapeHtml(cable.name)}</strong><small>${relation} · ${cable.fiber_count} FO</small></span><b>→</b></header>
                <div class="master-cable-fibers">${(cable.fibers || []).map((fiber) => `<button type="button" class="master-cable-fiber ${fiber.used ? "used" : ""}" data-cable-fiber="${fiber.id}" data-link-id="${fiber.link_id || ""}" style="--fiber-color:${escapeHtml(fiber.color_hex || "#94a3b8")}" title="F${fiber.number} · ${escapeHtml(fiber.color_name)}${fiber.used_by ? ` · ${escapeHtml(fiber.used_by)}` : ""}"><i></i><span>F${fiber.number} · ${escapeHtml(fiber.color_name || "")}</span></button>`).join("") || '<small>Gere as fibras deste cabo.</small>'}</div>
            </article>`;
        }).join("") + (state.container.layout.notes || []).map((note, index) => `
            <article class="master-canvas-note" data-canvas-note="${index}" style="transform:translate(${Number(note.x || 40)}px,${Number(note.y || 40)}px)">
                <div class="master-note-actions"><button type="button" data-edit-note="${index}" title="Editar nota" aria-label="Editar nota"><svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"></path><path d="m13.5 6.5 3.5 3.5"></path></svg></button><button type="button" data-delete-note="${index}" title="Excluir nota" aria-label="Excluir nota"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3m-9 0 1 14h10l1-14M10 11v6m4-6v6"></path></svg></button></div>
                <p>${escapeHtml(note.text)}</p>
            </article>`).join("");
        qsa("[data-equipment-node]", nodes).forEach((node) => installNodeDrag(node));
        qsa("[data-canvas-note]", nodes).forEach((node) => installNoteDragV07511(node));
        qsa(".master-olt-chassis-v07510", nodes).forEach((node) => installOltResizeGripV07515(node));
        qsa("[data-cable-node]", nodes).forEach((node) => { installCableDrag(node); syncCableVisualSide(node); });
        qsa("[data-cable-fiber]", nodes).forEach((button) => button.onclick = () => selectCableFiber(button));
        qsa("[data-dio-page]", nodes).forEach((select) => select.onchange = () => {
            state.container.layout.dioPages ||= {};
            state.container.layout.dioPages[String(select.dataset.dioPage)] = Number(select.value);
            saveContainerLayout();
            renderContainerCanvas();
        });
        qsa("[data-node-edit]", nodes).forEach((button) => button.onclick = (event) => {
            event.stopPropagation();
            openEquipmentEditor(button.dataset.nodeEdit);
        });
        // MAP_V07558_DIO_SINGLE_PORT: a bolinha (front) fica dentro do
        // quadrado (rear) — sem parar a propagação aqui, um clique na
        // bolinha dispararia selectContainerPort duas vezes (bolinha E
        // quadrado, já que o clique borbulha do filho pro pai).
        qsa("[data-port-id]", nodes).forEach((button) => button.onclick = (event) => { event.stopPropagation(); selectContainerPort(button); });
        qsa("[data-delete-note]", nodes).forEach((button) => button.onclick = async (event) => {
            event.stopPropagation();
            const accepted = await window.mapV0758?.confirmAction?.({
                title: "Excluir nota",
                message: "A nota será removida deste Canvas.",
                confirmLabel: "Excluir nota",
                danger: true,
            });
            if (!accepted) return;
            state.container.layout.notes.splice(Number(button.dataset.deleteNote), 1);
            await saveContainerLayout(); renderContainerCanvas();
        });
        qsa("[data-node-delete]", nodes).forEach((button) => button.onclick = async (event) => {
            event.stopPropagation();
            if (!window.confirm("Excluir este equipamento e suas portas/ligações?")) return;
            await request(`/api/map/elements/${state.container.elementId}/equipment/${button.dataset.nodeDelete}/`, { method: "DELETE" });
            await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); renderConnectionMatrix();
            notify("Equipamento excluído.");
        });
        qsa("[data-edit-note]", nodes).forEach((button) => button.onclick = async (event) => {
            event.stopPropagation();
            const note = state.container.layout.notes[Number(button.dataset.editNote)];
            const text = await window.mapV0758?.editLongText?.({ title: "Editar nota técnica", value: note?.text || "" });
            if (text === null || text === undefined) return;
            note.text = text;
            await saveContainerLayout(); renderContainerCanvas();
        });
        if (canvas.dataset.notesReady !== "1") {
            canvas.dataset.notesReady = "1";
            const menu = document.createElement("div");
            menu.className = "master-note-context";
            menu.hidden = true;
            menu.innerHTML = '<button type="button" data-add-canvas-note>＋ Adicionar nota</button>';
            canvas.appendChild(menu);
            let menuPoint = null;
            canvas.addEventListener("contextmenu", (event) => {
                if (event.target.closest(".master-canvas-node, .master-canvas-note")) return;
                event.preventDefault();
                event.stopPropagation();
                const rect = canvas.getBoundingClientRect();
                menuPoint = { x: event.clientX - rect.left, y: event.clientY - rect.top };
                menu.style.left = `${menuPoint.x}px`;
                menu.style.top = `${menuPoint.y}px`;
                menu.hidden = false;
            });
            menu.querySelector("[data-add-canvas-note]").onclick = async () => {
                menu.hidden = true;
                const text = await window.mapV0758?.editLongText?.({ title: "Nova nota técnica" });
                if (text === null || text === undefined) return;
                state.container.layout.notes ||= [];
                state.container.layout.notes.push({ id: `n${Date.now()}`, text, x: menuPoint.x, y: menuPoint.y });
                await saveContainerLayout(); renderContainerCanvas();
            };
            document.addEventListener("click", (event) => { if (!event.target.closest(".master-note-context")) menu.hidden = true; });
        }
        document.dispatchEvent(new CustomEvent("map:container-rendered", { detail: { root, data: state.container.data } }));
        drawContainerLinks();
    }

    function installNoteDrag(note) {
        note.onpointerdown = (event) => {
            if (event.button !== 0 || event.target.closest("button")) return;
            event.preventDefault();
            event.stopPropagation();
            note.setPointerCapture?.(event.pointerId);
            const index = Number(note.dataset.canvasNote);
            const item = state.container.layout.notes[index];
            const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
            const origin = { x: event.clientX, y: event.clientY, left: Number(item.x || 0), top: Number(item.y || 0) };
            const move = (moveEvent) => {
                item.x = origin.left + (moveEvent.clientX - origin.x) / scale;
                item.y = origin.top + (moveEvent.clientY - origin.y) / scale;
                note.style.transform = `translate(${item.x}px,${item.y}px)`;
            };
            const up = () => { window.removeEventListener("pointermove", move); saveContainerLayout(); };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        };
    }

    function installNodeDrag(node) {
        const header = qs("header", node);
        header.onpointerdown = (event) => {
            if (event.button !== 0 || event.target.closest("button, select")) return;
            event.preventDefault();
            event.stopPropagation();
            header.setPointerCapture?.(event.pointerId);
            const id = String(node.dataset.equipmentNode);
            const position = state.container.layout.positions[id] || {
                x: Number(node.dataset.posX || 0),
                y: Number(node.dataset.posY || 0),
            };
            const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
            const origin = { x: event.clientX, y: event.clientY, left: position.x, top: position.y };
            const move = (moveEvent) => {
                const next = { x: origin.left + (moveEvent.clientX - origin.x) / scale, y: origin.top + (moveEvent.clientY - origin.y) / scale };
                state.container.layout.positions[id] = next;
                node.dataset.posX = String(next.x); node.dataset.posY = String(next.y);
                node.style.transform = `translate(${next.x}px,${next.y}px)`;
                drawContainerLinks();
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                saveContainerLayout();
                // MAP_V07516_CLEAR_MANUAL_ROUTES_ON_MOVE: uma rota manual
                // (ponto de dobra arrastado à mão) fica com coordenada
                // absoluta fixa — se o equipamento se move e a rota não,
                // a linha passa a cortar por cima de outra coisa. Ao
                // terminar de mover, os links ligados a este equipamento
                // voltam pro roteamento automático (que já evita obstáculo),
                // em vez de ficar "presos" no ponto antigo.
                document.dispatchEvent(new CustomEvent("map:node-moved", { detail: { equipmentId: id } }));
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        };
    }

    // MAP_V07515_OLT_RESIZE: alça própria da OLT pra aumentar a largura do
    // chassi — a grade de portas é fluida (auto-fill), então alargar joga
    // automaticamente mais portas lado a lado, sem depender de um layout
    // fixo de colunas.
    function installOltResizeGripV07515(node) {
        const grip = qs(".master-olt-resize-grip-v07515", node);
        if (!grip) return;
        grip.onpointerdown = (event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            event.stopPropagation();
            grip.setPointerCapture?.(event.pointerId);
            const id = String(node.dataset.equipmentNode);
            const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
            const startWidth = node.getBoundingClientRect().width / scale;
            const startX = event.clientX;
            const move = (moveEvent) => {
                const next = Math.max(420, Math.min(2200, startWidth + (moveEvent.clientX - startX) / scale));
                node.style.setProperty("--olt-width", `${next}px`);
                state.container.layout.nodeWidths[id] = next;
                drawContainerLinks();
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                saveContainerLayout();
                document.dispatchEvent(new CustomEvent("map:node-moved", { detail: { equipmentId: id } }));
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        };
    }


    function installCableDrag(node) {
        const header = qs("header", node);
        header.onpointerdown = (event) => {
            if (event.button !== 0 || event.target.closest("button, select")) return;
            event.preventDefault();
            event.stopPropagation();
            const id = String(node.dataset.cableNode);
            const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
            const current = state.container.layout.cablePositions?.[id] || {
                x: Number(node.dataset.posX || 0),
                y: Number(node.dataset.posY || 0),
            };
            const origin = { x: event.clientX, y: event.clientY, left: current.x, top: current.y };
            const move = (moveEvent) => {
                const next = {
                    x: origin.left + (moveEvent.clientX - origin.x) / scale,
                    y: origin.top + (moveEvent.clientY - origin.y) / scale,
                };
                state.container.layout.cablePositions ||= {};
                state.container.layout.cablePositions[id] = next;
                node.dataset.posX = String(next.x);
                node.dataset.posY = String(next.y);
                node.style.transform = `translate(${next.x}px,${next.y}px)`;
                syncCableVisualSide(node);
                drawContainerLinks();
            };
            const up = () => {
                window.removeEventListener("pointermove", move);
                saveContainerLayout();
                document.dispatchEvent(new CustomEvent("map:node-moved", { detail: { cableId: id } }));
            };
            window.addEventListener("pointermove", move);
            window.addEventListener("pointerup", up, { once: true });
        };
    }

    function portAnchor(portId, role = "front") {
        const canvas = qs("#map-master-container .master-canvas");
        const port = qs(`[data-port-id="${portId}"][data-port-role="${role}"]`, canvas)
            || qs(`[data-port-id="${portId}"]`, canvas);
        if (!port) return null;
        const canvasRect = canvas.getBoundingClientRect();
        const socket = qs("i", port);
        const rect = (socket || port).getBoundingClientRect();
        const scale = Number(canvas.dataset.v0741Scale || 1) || 1;
        return {
            x: (rect.left + rect.width / 2 - canvasRect.left) / scale,
            y: (rect.top + rect.height / 2 - canvasRect.top) / scale,
        };
    }

    function fiberAnchor(fiberId) {
        const canvas = qs("#map-master-container .master-canvas");
        const fiber = qs(`[data-cable-fiber="${fiberId}"]`, canvas);
        if (!fiber) return null;
        const canvasRect = canvas.getBoundingClientRect();
        const rect = fiber.getBoundingClientRect();
        const scale = Number(canvas.dataset.v0741Scale || 1) || 1;
        const sideRight = fiber.closest(".master-cable-node")?.classList.contains("side-right-v0758");
        return {
            x: ((sideRight ? rect.left : rect.right) - canvasRect.left) / scale,
            y: (rect.top + rect.height / 2 - canvasRect.top) / scale,
        };
    }

    function cableAnchor(cableId, end) {
        const canvas = qs("#map-master-container .master-canvas");
        const node = qs(`.master-cable-node[data-cable-node="${cableId}"]`, canvas);
        if (!canvas || !node) return null;
        const canvasRect = canvas.getBoundingClientRect();
        const rect = node.getBoundingClientRect();
        const scale = Number(canvas.dataset.v0741Scale || 1) || 1;
        const centerX = (rect.left + rect.width / 2 - canvasRect.left) / scale;
        const endX = Number(end?.x ?? centerX);
        const x = ((endX >= centerX ? rect.right : rect.left) - canvasRect.left) / scale;
        const y = (rect.top + Math.min(42, rect.height / 2) - canvasRect.top) / scale;
        return { x, y };
    }

    function orthogonalPath(start, end, manual = []) {
        if (manual.length) return `M${start.x},${start.y} ${manual.map((point) => `L${point.x},${point.y}`).join(" ")} L${end.x},${end.y}`;
        const middle = start.x + (end.x - start.x) / 2;
        return `M${start.x},${start.y} L${middle},${start.y} L${middle},${end.y} L${end.x},${end.y}`;
    }

    function roundedTowerPolyline(points, radius = 18) {
        if (!Array.isArray(points) || points.length < 2) return "";
        if (points.length === 2) return `M${points[0].x},${points[0].y} L${points[1].x},${points[1].y}`;
        const distance = (a, b) => Math.hypot(b.x - a.x, b.y - a.y) || 1;
        let d = `M${points[0].x},${points[0].y}`;
        for (let index = 1; index < points.length - 1; index += 1) {
            const previous = points[index - 1];
            const current = points[index];
            const next = points[index + 1];
            const r = Math.min(radius, distance(previous, current) / 2, distance(current, next) / 2);
            const inScale = r / distance(previous, current);
            const outScale = r / distance(current, next);
            const before = {
                x: current.x - (current.x - previous.x) * inScale,
                y: current.y - (current.y - previous.y) * inScale,
            };
            const after = {
                x: current.x + (next.x - current.x) * outScale,
                y: current.y + (next.y - current.y) * outScale,
            };
            d += ` L${before.x},${before.y} Q${current.x},${current.y} ${after.x},${after.y}`;
        }
        const last = points.at(-1);
        return `${d} L${last.x},${last.y}`;
    }

    function towerOrthogonalPath(start, end, manual = [], laneIndex = 0) {
        if (manual.length) return roundedTowerPolyline([start, ...manual, end], 22);
        // MAP_V078_TOWER_BOTTOM_LANES: toda ligação automática sai pelo rodapé
        // do equipamento, desce para um corredor horizontal exclusivo e só
        // então volta à porta de destino. Isso mantém as linhas fora dos cards
        // e preserva a edição manual por pontos do Canvas.
        const lane = Math.abs(Number(laneIndex || 0)) % 18;
        const laneY = Math.max(start.y, end.y) + 48 + lane * 14;
        return roundedTowerPolyline([
            start,
            { x: start.x, y: laneY },
            { x: end.x, y: laneY },
            end,
        ], 18);
    }

    function drawContainerLinks() {
        const svg = qs("#map-master-container .master-canvas-links");
        if (!svg) return;
        const links = state.container.data?.links || [];
        svg.innerHTML = links.map((link, linkIndex) => {
            const destinationRole = !link.source_port_id && (link.cable_id || link.cable_fiber_id) ? "rear" : "front";
            const end = portAnchor(link.destination_port_id, destinationRole);
            const externalPosition = state.container.layout.externalLinks?.[String(link.id)];
            const fiberStart = link.cable_fiber_id ? fiberAnchor(link.cable_fiber_id) : null;
            const cableStart = link.cable_id ? cableAnchor(link.cable_id, end) : null;
            const isTower = String(state.container.data?.container?.type || "") === "tower";
            const defaultExternal = end
                ? (isTower ? { x: end.x + 190, y: end.y } : { x: 24, y: end.y })
                : null;
            const start = link.source_port_id
                ? portAnchor(link.source_port_id, "front")
                : fiberStart || cableStart || (end ? externalPosition || defaultExternal : null);
            if (!start || !end) return "";
            const manual = state.container.layout.routes[String(link.id)] || [];
            const external = !link.source_port_id && !fiberStart && !cableStart
                ? `<circle data-drop-entry="${link.id}" class="master-drop-entry" cx="${start.x}" cy="${start.y}" r="7"></circle><text class="master-drop-label" x="${start.x + 11}" y="${start.y - 9}">${escapeHtml(link.cable || "DROP")}</text>`
                : "";
            const route = isTower
                ? towerOrthogonalPath(start, end, manual, linkIndex)
                : orthogonalPath(start, end, manual);
            return `${external}<path data-master-link="${link.id}" class="link-${link.link_type} ${state.container.selectedLink === String(link.id) ? "selected" : ""}" d="${route}"></path>`;
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
                const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
                const points = state.container.layout.routes[String(path.dataset.masterLink)] || [];
                points.push({ x: (event.clientX - rect.left) / scale, y: (event.clientY - rect.top) / scale });
                state.container.layout.routes[String(path.dataset.masterLink)] = points;
                saveContainerLayout(); drawContainerLinks();
            };
            path.oncontextmenu = async (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (!window.confirm("Excluir esta ligação?")) return;
                await request(`/api/map/elements/${state.container.elementId}/equipment-links/${path.dataset.masterLink}/`, { method: "DELETE" });
                state.container.selectedLink = null;
                await loadContainerMaster(true); renderContainerCanvas(); renderConnectionMatrix();
                notify("Ligação excluída.");
            };
        });
        qsa("[data-drop-entry]", svg).forEach((handle) => {
            handle.onpointerdown = (event) => {
                event.preventDefault(); event.stopPropagation();
                const id = String(handle.dataset.dropEntry);
                const rect = svg.getBoundingClientRect();
                const scale = Number(qs("#map-master-container .master-canvas")?.dataset.v0741Scale || 1) || 1;
                const move = (moveEvent) => {
                    state.container.layout.externalLinks ||= {};
                    state.container.layout.externalLinks[id] = {
                        x: (moveEvent.clientX - rect.left) / scale,
                        y: (moveEvent.clientY - rect.top) / scale,
                    };
                    drawContainerLinks();
                };
                const up = () => { window.removeEventListener("pointermove", move); saveContainerLayout(); };
                window.addEventListener("pointermove", move);
                window.addEventListener("pointerup", up, { once: true });
            };
        });
        renderLinkHandles();
    }

    function renderLinkHandles() {
        // MAP_V07513_DISABLE_LEGACY_HANDLES: map-v07512-links-ptp.js's
        // renderPluginHandles() já cobre seleção/arraste/exclusão de ponto
        // nesta mesma <svg>, sem depender de lineMode. Manter os dois juntos
        // desenhava dois círculos sobrepostos no mesmo ponto — arrastar um
        // deixava o outro "fantasma" parado ali até o próximo redraw
        // completo, o que tornava difícil reencontrar o ponto certo depois
        // de movê-lo.
    }

    async function selectCreatedLinkForEditing(linkId) {
        const link = (state.container.data?.links || []).find((item) => String(item.id) === String(linkId));
        if (!link) return;
        state.container.selectedLink = String(linkId);
        state.container.layout.routes[String(linkId)] = [];
        drawContainerLinks();
        await saveContainerLayout();
    }

    async function selectCableFiber(button) {
        const fiberId = Number(button.dataset.cableFiber);
        const existingLinkId = String(button.dataset.linkId || "");
        if (existingLinkId) {
            if (!window.confirm("Esta fibra já está ligada. Deseja excluir a terminação?")) return;
            try {
                await request(`/api/map/elements/${state.container.elementId}/equipment-links/${existingLinkId}/`, { method: "DELETE" });
                state.container.selectedFiber = null;
                await loadContainerMaster(true);
                renderContainerCanvas();
                renderConnectionMatrix();
                notify("Terminação removida.");
            } catch (error) {
                notify(error.message, true);
            }
            return;
        }
        if (state.container.selectedFiber?.id === fiberId) {
            button.classList.remove("selected");
            state.container.selectedFiber = null;
            notify("Seleção da fibra cancelada.");
            return;
        }
        qsa(".master-cable-fiber.selected", qs("#map-master-container")).forEach((item) => item.classList.remove("selected"));
        state.container.selectedFiber = { id: fiberId, button };
        button.classList.add("selected");
        notify("Fibra selecionada. Clique no conector TRÁS da porta do DIO.");
    }

    async function selectContainerPort(button) {
        if (button.dataset.busy === "true") return;
        const existingLinkId = String(button.dataset.linkId || "");
        if (existingLinkId) {
            const role = button.dataset.portRole === "rear" ? "traseira" : "frontal";
            if (!window.confirm(`Esta porta ${role} já está ligada. Deseja excluir a ligação?`)) return;
            await request(`/api/map/elements/${state.container.elementId}/equipment-links/${existingLinkId}/`, { method: "DELETE" });
            state.container.selectedPort = null;
            await loadContainerMaster(true); renderContainerCanvas(); renderConnectionMatrix();
            notify("Ligação removida.");
            return;
        }
        if (button.dataset.portRole === "rear") {
            if (!state.container.selectedFiber) {
                notify("Selecione primeiro uma fibra colorida do cabo de entrada.");
                return;
            }
            const fiber = state.container.selectedFiber;
            fiber.button?.classList.remove("selected");
            state.container.selectedFiber = null;
            try {
                const created = await request(`/api/map/elements/${state.container.elementId}/equipment-links/`, {
                    method: "POST",
                    body: JSON.stringify({ cable_fiber_id: fiber.id, destination_port_id: Number(button.dataset.portId) }),
                });
                await loadContainerMaster(true);
                renderContainerCanvas();
                renderConnectionMatrix();
                await selectCreatedLinkForEditing(created.link?.id);
                notify("Fibra terminada no DIO. A linha ficou selecionada para ajuste.");
            } catch (error) {
                notify(error.message, true);
            }
            return;
        }
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
        state.container.layout.cablePositions = {};
        (state.container.data?.equipment || []).forEach((item, index) => {
            state.container.layout.positions[String(item.id)] = defaultNodePosition(item, index);
        });
        (state.container.data?.cables || []).forEach((cable, index) => {
            state.container.layout.cablePositions[String(cable.id)] = defaultCablePosition(cable, index);
        });
        saveContainerLayout(); renderContainerCanvas();
    }

    function renderConnectionMatrix() {
        const panel = qs('#map-master-container [data-panel="matrix"]');
        const equipment = state.container.data?.equipment || [];
        const ports = equipment.flatMap((item) => (item.ports || []).map((port) => ({ ...port, equipment: item.name })));
        panel.innerHTML = `
            <div class="master-matrix-head"><div><strong>Relatório de ligações</strong><span>Conexões registradas no Canvas 2D.</span></div></div>
            <div class="master-matrix-links">${(state.container.data?.links || []).map((link) => `<article><div><strong>${escapeHtml(link.source)}</strong><span>→ ${escapeHtml(link.destination)}</span><small>${escapeHtml(link.link_type_label)}</small></div><button type="button" class="danger" data-delete-link="${link.id}">Desligar</button></article>`).join("") || "<p>Nenhuma ligação interna.</p>"}</div>`;
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
        dialog.innerHTML = `<form><header><h2>Novo equipamento</h2><button type="button" data-close>×</button></header><div class="master-form-grid"><label>Tipo<select name="equipment_type"></select></label><label>Nome<input name="name" required></label><label>Fabricante<input name="vendor"></label><label>Modelo<input name="model"></label><label data-create-field="management">IP de gerência<input name="management_ip"></label><label data-create-field="onu-lan">Portas LAN da ONU<input name="onu_lan_count" type="number" min="1" max="16" value="4"></label><label data-create-field="port-count">Quantidade de portas<select name="port_count">${[4, 8, 12, 16, 24, 48].map((count) => `<option value="${count}">${count} portas</option>`).join("")}</select></label><label data-create-field="drop">Cabo DROP ligado à torre<select name="drop_cable_id"></select><small>Opcional. Se escolhido, o DROP será conectado diretamente à porta óptica da ONU.</small></label><label data-create-field="dio-capacity">Portas do DIO<select name="dio_port_capacity"><option>12</option><option selected>24</option><option>36</option><option>48</option><option>72</option><option>96</option><option>144</option><option>192</option><option>244</option></select></label><label data-create-field="connector">Conector<select name="connector_type"><option value="sc_apc">SC/APC</option><option value="sc_upc">SC/UPC</option><option value="lc_upc">LC/UPC</option><option value="lc_apc">LC/APC</option></select></label></div><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Adicionar</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        return dialog;
    }

    function showEquipmentDialogWithFade(dialog) {
        document.body.classList.add("tower-equipment-modal-open");
        dialog.addEventListener("close", () => {
            document.body.classList.remove("tower-equipment-modal-open");
        }, { once: true });
        dialog.showModal();
    }

    function configureEquipmentCreateForType(dialog) {
        const form = qs("form", dialog);
        const type = form.elements.equipment_type.value;
        const show = (field, visible) => {
            const wrapper = qs(`[data-create-field="${field}"]`, form);
            if (wrapper) wrapper.hidden = !visible;
        };
        show("management", !["dio", "pto"].includes(type));
        show("onu-lan", type === "onu");
        show("drop", type === "onu");
        show("dio-capacity", type === "dio");
        show("connector", ["dio", "pto"].includes(type));
        // MAP_V07557_TOWER_SWITCH_PORTS: sem este campo, Switch/Router/
        // Firewall/Servidor criados por aqui sempre caíam no valor padrão
        // do backend, sem opção de escolher a quantidade de portas.
        const portCountTypes = ["switch", "router", "firewall", "server"];
        show("port-count", portCountTypes.includes(type));
        const portCount = form.elements.port_count;
        if (portCount && portCountTypes.includes(type)) {
            portCount.value = type === "switch" ? "24" : "8";
        }
        const capacity = form.elements.dio_port_capacity;
        if (capacity) {
            const tower = state.container.data?.container?.type === "tower";
            [...capacity.options].forEach((option) => {
                option.hidden = tower && Number(option.value) > 24;
                option.disabled = tower && Number(option.value) > 24;
            });
            if (tower && Number(capacity.value) > 24) capacity.value = "24";
        }
    }

    async function openEquipmentCreateDialog() {
        // MAP_V07555_BOOTSTRAP_RACE: state.bootstrap só é preenchido em
        // init() depois de esperar window.networkMap existir — mas
        // window.networkMap já fica truthy antes de loadProjects() (em
        // map-editor.js) terminar de selecionar o projeto no
        // #project-select. Se o primeiro refreshBootstrap() rodar antes
        // disso, projectId() lê "" e o bootstrap fica null pra sempre (não
        // há retry automático — só reage a um "change" real do select, que
        // nunca dispara quando o valor é setado por código). Sem isso, o
        // <select> de tipo de equipamento ficava sempre vazio e qualquer
        // criação (Rack ou Torre) falhava com "Tipo de equipamento
        // inválido para esta estrutura." sem nenhum aviso claro.
        if (!state.bootstrap) await refreshBootstrap();
        const dialog = equipmentCreateDialog();
        const containerType = String(state.container.data?.container?.type || "tower");
        const allowed = containerType === "rack"
            ? new Set(["olt", "dio", "switch", "router", "firewall", "pto", "other"])
            : new Set(["dio", "switch", "router", "firewall", "pto", "other", "access_point", "ptp", "onu"]);
        const types = (state.bootstrap?.equipment_types || []).filter(([value]) => allowed.has(value));
        dialog.querySelector("select[name='equipment_type']").innerHTML = types.map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join("");
        const drops = (state.container.data?.cables || []).filter((cable) => cable.cable_type === "drop");
        dialog.querySelector("select[name='drop_cable_id']").innerHTML = `<option value="">Adicionar sem conectar DROP</option>${drops.map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${cable.fiber_count} FO</option>`).join("")}`;
        dialog.querySelector("form").reset();
        const typeSelect = dialog.querySelector("select[name='equipment_type']");
        typeSelect.onchange = () => configureEquipmentCreateForType(dialog);
        configureEquipmentCreateForType(dialog);
        dialog.querySelector("form").onsubmit = async (event) => {
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(event.currentTarget));
            try {
                await request(`/api/map/elements/${state.container.elementId}/equipment/`, { method: "POST", body: JSON.stringify(payload) });
                dialog.close();
                await loadContainerMaster(true); renderEquipmentList(); renderContainerCanvas(); renderConnectionMatrix();
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        showEquipmentDialogWithFade(dialog);
    }

    function equipmentEditorDialog() {
        let dialog = qs("#map-master-equipment-editor");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-master-equipment-editor";
        dialog.className = "editor-dialog map-master-equipment-dialog";
        dialog.innerHTML = `<form><header><div><h2>Editar equipamento</h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div class="master-form-grid"><label>Nome<input name="name"></label><label>IP de gerência<input name="management_ip"></label><label>Fabricante<input name="vendor"></label><label>Modelo<input name="model"></label><label>Número de série<input name="serial_number"></label><label>Patrimônio<input name="asset_tag"></label><label>Posição no rack (U)<input name="rack_unit"></label><label>Altura (U)<input name="height_units" type="number" min="1"></label><label>Face<select name="rack_face"><option value="">Não informado</option><option value="front">Frente</option><option value="rear">Traseira</option></select></label><label>Foto/URL<input name="photo_url"></label><label>Documentação/URL<input name="documentation_url"></label><label>Firmware<input name="firmware"></label><label>Função<input name="role"></label><label>Slots do chassi<input name="chassis_slots" type="number" min="0"></label><label>Uplinks<input name="uplink_count" type="number" min="0"></label><label>Potência TX (dBm)<input name="tx_power_dbm" type="number" step="0.01"></label><label>Conector<select name="connector_type"><option value="">Não informado</option><option value="sc_apc">SC/APC</option><option value="sc_upc">SC/UPC</option><option value="lc_upc">LC/UPC</option><option value="lc_apc">LC/APC</option></select></label><label>Bandejas do DIO<input name="tray_count" type="number" min="0"></label><label>Portas por bandeja<input name="ports_per_tray" type="number" min="0"></label></div><label>Descrição<textarea name="description" rows="2"></textarea></label><label>Observações<textarea name="notes" rows="3"></textarea></label><section class="master-equipment-expand" data-port-editor><h3>Adicionar interfaces compatíveis</h3><div><select data-new-port-type></select><input data-new-port-count type="number" min="1" max="256" value="1"><button type="button" data-add-ports>Adicionar</button></div></section><section class="master-equipment-expand" data-card-editor><h3>Adicionar placa à OLT</h3><div><input data-card-slot type="number" min="1" max="64" placeholder="Slot"><input data-card-pons type="number" min="1" max="64" value="8" placeholder="PONs"><input data-card-name placeholder="Nome da placa"><button type="button" data-add-card>Adicionar placa</button></div></section><section><h3>Portas e módulos</h3><div data-ports class="master-equipment-ports"></div></section><p data-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Salvar</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        return dialog;
    }

    function configureEquipmentEditorForType(dialog, item) {
        const form = qs("form", dialog);
        const type = String(item.type || "other");
        const mounted = new Set(["olt", "dio", "switch", "router", "firewall", "server"]);
        const managed = new Set(["olt", "switch", "router", "firewall", "server", "access_point", "ptp", "onu", "other"]);
        const fieldRules = {
            management_ip: managed.has(type),
            rack_unit: mounted.has(type), height_units: mounted.has(type), rack_face: mounted.has(type),
            firmware: managed.has(type), chassis_slots: ["olt", "switch", "router", "firewall", "server"].includes(type),
            uplink_count: managed.has(type), tx_power_dbm: type === "olt",
            connector_type: type === "dio", tray_count: type === "dio", ports_per_tray: type === "dio",
        };
        Object.entries(fieldRules).forEach(([name, visible]) => {
            const wrapper = form.elements[name]?.closest("label");
            if (wrapper) wrapper.hidden = !visible;
        });
        const allowedPorts = {
            // MAP_V07513_OLT_UPLINK_CARD: só uplink (SFP/SFP+) + gerência +
            // alimentação — as portas PON continuam exclusivas do fluxo
            // "Adicionar placa" (numeração por slot), não deste editor
            // genérico, pra não duplicar/confundir os dois caminhos.
            olt: ["rj45_1g", "sfp_1g", "sfp_plus_10g", "power"],
            switch: ["rj45_100m", "rj45_1g", "rj45_2g5", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "qsfp_plus_40g", "qsfp28_100g"],
            router: ["rj45_100m", "rj45_1g", "rj45_2g5", "sfp_1g", "sfp_plus_10g", "sfp28_25g", "qsfp_plus_40g", "qsfp28_100g"],
            firewall: ["rj45_1g", "rj45_2g5", "sfp_1g", "sfp_plus_10g"],
            server: ["rj45_1g", "rj45_2g5", "sfp_1g", "sfp_plus_10g", "sfp28_25g"],
            access_point: ["rj45_100m", "rj45_1g", "rj45_2g5", "wireless", "power"],
            ptp: ["rj45_100m", "rj45_1g", "sfp_1g", "wireless", "power"],
            onu: ["pon", "rj45_100m", "rj45_1g", "rj45_2g5", "power"],
            other: ["rj45_1g", "sfp_1g", "wireless", "power"],
        }[type] || [];
        const portEditor = qs("[data-port-editor]", dialog);
        portEditor.hidden = !allowedPorts.length;
        const choices = new Map(state.bootstrap?.port_types || []);
        qs("[data-new-port-type]", dialog).innerHTML = allowedPorts
            .filter((value) => choices.has(value))
            .map((value) => `<option value="${value}">${escapeHtml(choices.get(value))}</option>`).join("");
        qs("[data-card-editor]", dialog).hidden = type !== "olt";
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
        configureEquipmentEditorForType(dialog, item);
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
        showEquipmentDialogWithFade(dialog);
    }

    function buildContainerExportSvg() {
        const canvasRoot = qs("#map-master-container .master-canvas");
        if (!canvasRoot) return null;
        const width = Math.max(1200, canvasRoot.scrollWidth);
        const height = Math.max(760, canvasRoot.scrollHeight);
        const links = qs(".master-canvas-links", canvasRoot)?.innerHTML || "";
        const cards = (state.container.data?.equipment || []).map((item, index) => {
            const position = nodePosition(item, index);
            const cardWidth = 250;
            const rowHeight = 24;
            const ports = item.ports || [];
            const cardHeight = 58 + Math.max(1, Math.ceil(ports.length / 2)) * rowHeight;
            const portRows = ports.map((port, portIndex) => {
                const column = portIndex % 2;
                const row = Math.floor(portIndex / 2);
                const x = position.x + 10 + column * 118;
                const y = position.y + 44 + row * rowHeight;
                return `<rect x="${x}" y="${y}" width="108" height="18" rx="4" fill="#102a43" stroke="#24506f"/><text x="${x + 8}" y="${y + 12}" fill="#dbeafe" font-size="8" font-family="Arial">${escapeHtml(port.label)}</text>`;
            }).join("");
            return `<g><rect x="${position.x}" y="${position.y}" width="${cardWidth}" height="${cardHeight}" rx="10" fill="#091d30" stroke="#24506f" stroke-width="2"/><text x="${position.x + 14}" y="${position.y + 25}" fill="#f8fafc" font-size="13" font-weight="700" font-family="Arial">${escapeHtml(item.name)}</text><text x="${position.x + cardWidth - 12}" y="${position.y + 25}" text-anchor="end" fill="#94a3b8" font-size="9" font-family="Arial">${escapeHtml(item.type_label)}</text>${portRows}</g>`;
        }).join("");
        const cables = (state.container.data?.cables || []).map((cable, index) => {
            const position = cablePosition(cable, index);
            const fibers = cable.fibers || [];
            const cardWidth = 218;
            const cardHeight = 54 + Math.max(1, fibers.length) * 18;
            const fiberRows = fibers.map((fiber, fiberIndex) => {
                const color = fiber.color_hex || "#38bdf8";
                const y = position.y + 48 + fiberIndex * 18;
                return `<circle cx="${position.x + 16}" cy="${y - 3}" r="5" fill="${escapeHtml(color)}" stroke="#e2e8f0" stroke-width="1.5"/><text x="${position.x + 28}" y="${y}" fill="#dbeafe" font-size="9" font-family="Arial">F${escapeHtml(fiber.number)} · ${escapeHtml(fiber.color_name || "Fibra")}</text>`;
            }).join("");
            return `<g><rect x="${position.x}" y="${position.y}" width="${cardWidth}" height="${cardHeight}" rx="10" fill="#091d30" stroke="#0ea5e9" stroke-width="2"/><text x="${position.x + 14}" y="${position.y + 23}" fill="#f8fafc" font-size="12" font-weight="700" font-family="Arial">${escapeHtml(cable.name)}</text><text x="${position.x + cardWidth - 12}" y="${position.y + 23}" text-anchor="end" fill="#7dd3fc" font-size="8" font-family="Arial">${cable.relation === "output" ? "SAÍDA" : "ENTRADA"}</text>${fiberRows}</g>`;
        }).join("");
        const notes = (state.container.layout.notes || []).map((note) => `<g><rect x="${Number(note.x || 40)}" y="${Number(note.y || 40)}" width="190" height="64" rx="9" fill="#42300a" stroke="#facc15"/><text x="${Number(note.x || 40) + 12}" y="${Number(note.y || 40) + 25}" fill="#fef3c7" font-size="10" font-family="Arial">${escapeHtml(note.text)}</text></g>`).join("");
        return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#07111f"/><style>.master-canvas-links path{fill:none;stroke:#38bdf8;stroke-width:3}.master-canvas-links circle{fill:#fff;stroke:#38bdf8;stroke-width:2}.master-drop-label{fill:#e2e8f0;font:10px Arial}</style><g class="master-canvas-links">${links}</g>${cables}${cards}${notes}</svg>`;
    }

    async function exportContainerPng() {
        const svgText = buildContainerExportSvg();
        if (!svgText) return;
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
            try {
                link.href = canvas.toDataURL("image/png"); link.click();
            } catch (error) {
                notify(`Não foi possível exportar PNG: ${error.message}`, true);
            }
        };
        image.onerror = () => { URL.revokeObjectURL(url); notify("Não foi possível preparar a imagem PNG.", true); };
        image.src = url;
    }

    async function exportContainerPdf() {
        const svgText = buildContainerExportSvg();
        if (!svgText) return;
        const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const popup = window.open("", "_blank", "width=1200,height=850,scrollbars=yes");
        if (!popup) {
            URL.revokeObjectURL(url);
            return notify("O navegador bloqueou a janela de exportação PDF.", true);
        }
        popup.document.write(`<!doctype html><html><head><title>Canvas da estrutura</title><style>@page{size:landscape;margin:8mm}body{margin:0;background:#fff}img{display:block;width:100%;height:auto;object-fit:contain}</style></head><body><img src="${url}"><script>const image=document.querySelector('img');image.onload=()=>setTimeout(()=>window.print(),250);window.onafterprint=()=>window.close();<\/script></body></html>`);
        popup.document.close();
        window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    }


    // ------------------------------------------------------------------
    // Technical sheets, lifecycle history, printing and QR code
    // ------------------------------------------------------------------

    function assetSheetDialog() {
        let dialog = qs("#map-master-asset-sheet");
        if (dialog && !qs("[data-stage-save]", dialog)) {
            dialog.remove();
            dialog = null;
        }
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
        // v0.75.9: nada de MutationObserver aqui. O carregamento do Rack/Torre
        // (equipment/ + container-layout-v3/) só acontece por chamada
        // explícita de openContainerWorkspace() (ver map-editor.js, clique no
        // marker) — nunca reagindo "por tabela" a uma mudança de atributo do
        // dialog, que era o que causava a segunda chamada de equipment/ e,
        // pra CTO/CDO, chamadas stale vindas de uma abertura anterior de
        // Rack/Torre na mesma sessão.
        const container = containerDialog();
        if (container && container.dataset.v0759CloseGuard !== "1") {
            container.dataset.v0759CloseGuard = "1";
            container.addEventListener("close", () => {
                // Ao fechar: nova geração (qualquer resposta em voo de uma
                // abertura anterior deixa de valer), limpa o id do elemento e
                // o estado temporário do container — sem disparar novo
                // carregamento.
                state.container.openGeneration += 1;
                container.dataset.elementId = "";
                container.dataset.containerType = "";
                container.dataset.containerName = "";
                state.container.elementId = "";
                state.container.data = null;
                state.container.selectedPort = null;
                state.container.selectedFiber = null;
                state.container.selectedLink = null;
                state.container.lineMode = false;
            });
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
            openElementRoute,
            createRoute,
            enhanceContainer,
            openContainerWorkspace,
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init());
    else init();
}());
