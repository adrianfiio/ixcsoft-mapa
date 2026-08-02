(function () {
    "use strict";

    const unifilarDialog = document.getElementById("unifilar-dialog");
    const unifilarContent = document.getElementById("unifilar-content");
    const containerDialog = document.getElementById("container-dialog");
    let fusionState = null;
    let fusionStateElementId = null;
    let containerLayout = { positions: {}, routes: {} };
    let containerLayoutId = null;
    let containerLayoutLoading = false;
    let containerLayoutLoadedAt = 0;
    let movingNodes = false;
    let editingContainerLines = false;
    let selectedContainerLink = null;
    let saveTimer = null;
    let decorating = false;

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (cookie) return decodeURIComponent(cookie.split("=")[1]);
        return document.querySelector("[name='csrfmiddlewaretoken']")?.value || "";
    }

    async function request(path, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
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

    function normalizeRoute(value) {
        return String(value || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toUpperCase()
            .replace(/[^A-Z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
    }

    function featureRouteNames(feature) {
        const properties = feature?.properties || feature || {};
        const values = [];
        if (Array.isArray(properties.route_names)) values.push(...properties.route_names);
        if (properties.route_name) values.push(properties.route_name);
        return values.map((value) => normalizeRoute(value)).filter(Boolean);
    }

    function installRouteDataGuard() {
        const api = window.mapV092;
        if (!api?.setData || api.setData.datasetV3 === true) return;
        const original = api.setData.bind(api);
        const guarded = (payload = {}) => {
            const assigned = new Set([...(payload.elements || []), ...(payload.cables || [])].flatMap(featureRouteNames));
            const routes = assigned.size
                ? (payload.routes || []).filter((feature) => {
                    const properties = feature?.properties || {};
                    return [properties.nome, properties.name, properties.codigo, properties.code]
                        .map(normalizeRoute).some((key) => assigned.has(key));
                })
                : [];
            original({ ...payload, routes });
        };
        guarded.datasetV3 = true;
        api.setData = guarded;
    }

    function notify(text, error = false) {
        window.networkMap?.notify?.(text, error);
        const feedback = document.getElementById("unifilar-feedback");
        if (feedback && unifilarDialog?.open) {
            feedback.textContent = text;
            feedback.classList.toggle("error", error);
        }
    }

    function elementId() {
        return unifilarDialog?.dataset.elementId || "";
    }

    async function loadFusionState(force = false) {
        const id = elementId();
        if (!id) return null;
        if (!force && fusionState && String(fusionStateElementId) === String(id)) return fusionState;
        fusionState = await request(`/api/map/elements/${id}/fusion-cables/?radius_m=45`);
        fusionStateElementId = id;
        return fusionState;
    }

    function applyFusionExclusions() {
        if (!fusionState || !unifilarContent) return;
        const excluded = new Set((fusionState.excluded_cable_ids || []).map(String));
        const allowed = new Set((fusionState.cables || []).filter((cable) => !cable.excluded).map((cable) => String(cable.id)));
        unifilarContent.querySelectorAll("[data-cable-node-id]").forEach((node) => {
            const id = String(node.dataset.cableNodeId);
            node.hidden = excluded.has(id) || !allowed.has(id);
        });
    }

    async function hideCable(cableId) {
        if (!confirm("Remover este cabo somente desta caixa/fusão? O cabo continuará existindo no mapa.")) return;
        try {
            await request(`/api/map/elements/${elementId()}/fusion-cables/${cableId}/`, { method: "DELETE" });
            await loadFusionState(true);
            applyFusionExclusions();
            notify("Cabo removido da visualização desta caixa.");
        } catch (error) { notify(error.message, true); }
    }

    async function restoreCable(cableId) {
        try {
            await request(`/api/map/elements/${elementId()}/fusion-cables/${cableId}/`, {
                method: "POST",
                body: JSON.stringify({ action: "pass", max_distance_m: 60 }),
            });
            await loadFusionState(true);
            unifilarDialog.close();
            await window.networkMap?.showUnifilar?.(elementId());
            notify("Cabo adicionado à caixa como passagem sem corte.");
        } catch (error) { notify(error.message, true); }
    }

    function closeCablePanel() {
        document.getElementById("fusion-cable-panel-v3")?.remove();
    }

    async function openCablePanel() {
        closeCablePanel();
        const state = await loadFusionState(true);
        const panel = document.createElement("aside");
        panel.id = "fusion-cable-panel-v3";
        panel.innerHTML = `
            <header><div><strong>Cabos desta caixa</strong><small>Até ${state.radius_m} m</small></div><button type="button" data-close>×</button></header>
            <div class="fusion-cable-list-v3">
                ${(state.cables || []).map((cable) => `
                    <article class="${cable.excluded ? "excluded" : ""}">
                        <div><strong>${escapeHtml(cable.name)}</strong><small>${cable.distance_m == null ? "distância indisponível" : `${cable.distance_m} m`}${cable.route ? ` · ${escapeHtml(cable.route)}` : ""}</small></div>
                        ${cable.excluded
                            ? `<button type="button" data-restore-cable="${cable.id}">Adicionar</button>`
                            : cable.endpoint
                                ? `<span class="fixed">Ponta física</span>`
                                : `<button type="button" class="danger" data-hide-cable="${cable.id}">Remover</button>`}
                    </article>`).join("") || "<p>Nenhum cabo próximo.</p>"}
            </div>`;
        unifilarDialog.appendChild(panel);
        panel.querySelector("[data-close]").onclick = closeCablePanel;
        panel.querySelectorAll("[data-hide-cable]").forEach((button) => {
            button.onclick = async () => { await hideCable(button.dataset.hideCable); closeCablePanel(); };
        });
        panel.querySelectorAll("[data-restore-cable]").forEach((button) => {
            button.onclick = () => restoreCable(button.dataset.restoreCable);
        });
    }

    function useCssFullscreen() {
        const button = unifilarContent?.querySelector("[data-fusion-fullscreen]");
        if (!button || button.dataset.v3 === "true") return;
        const replacement = button.cloneNode(true);
        replacement.dataset.v3 = "true";
        replacement.onclick = async (event) => {
            event.preventDefault();
            event.stopImmediatePropagation();
            if (document.fullscreenElement) {
                try { await document.exitFullscreen(); } catch (_error) {}
            }
            const active = unifilarDialog.classList.toggle("is-fullscreen");
            replacement.textContent = active ? "Desmaximizar" : "Tela cheia";
            replacement.classList.toggle("active", active);
            replacement.setAttribute("aria-pressed", String(active));
            window.setTimeout(() => window.dispatchEvent(new Event("resize")), 80);
        };
        button.replaceWith(replacement);
    }

    function compactFusionToolbar() {
        if (!unifilarContent) return;
        const instructions = unifilarContent.querySelector(".ceo-instructions");
        if (instructions) instructions.classList.add("fusion-compact-v3");
        const toolbar = unifilarContent.querySelector(".fusion-toolbar") || unifilarContent.querySelector(".unifilar-zoom");
        if (toolbar && !toolbar.querySelector("[data-fusion-cables-v3]")) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.fusionCablesV3 = "true";
            button.textContent = "Cabos";
            button.title = "Adicionar ou remover cabos desta caixa";
            button.onclick = () => openCablePanel().catch((error) => notify(error.message, true));
            toolbar.appendChild(button);
        }
        useCssFullscreen();
    }

    function decorateFusionNodes() {
        if (!unifilarContent) return;
        unifilarContent.querySelectorAll("[data-cable-node-id]").forEach((node) => {
            const header = node.querySelector(":scope > header");
            if (!header || header.querySelector("[data-remove-fusion-cable-v3]")) return;
            const button = document.createElement("button");
            button.type = "button";
            button.className = "fusion-remove-cable-v3";
            button.dataset.removeFusionCableV3 = node.dataset.cableNodeId;
            button.title = "Remover este cabo da caixa";
            button.textContent = "×";
            button.onclick = (event) => {
                event.stopPropagation();
                hideCable(node.dataset.cableNodeId).catch((error) => notify(error.message, true));
            };
            header.appendChild(button);
        });
        applyFusionExclusions();
    }

    async function enhanceFusion() {
        if (!unifilarDialog?.open || !unifilarContent?.querySelector(".optical-graph")) return;
        unifilarDialog.classList.add("fusion-v3");
        compactFusionToolbar();
        try { await loadFusionState(); } catch (_error) {}
        decorateFusionNodes();
    }

    function improveMapIcons() {
        const scope = document.getElementById("map") || document;
        scope.querySelectorAll(".network-marker:not(.network-marker-v3)").forEach((marker) => {
            marker.classList.add("network-marker-v3");
            marker.querySelectorAll("small").forEach((small) => { small.hidden = true; });
        });
    }

    function relocateRouteFilter() {
        const panel = document.getElementById("route-filter-v092");
        const map = document.getElementById("map");
        if (!panel || !map) return;
        const list = panel.querySelector("[data-route-list]");
        const hasRoutes = Boolean(list?.querySelector(".route-filter-item-v092"));
        panel.hidden = !hasRoutes;
        if (!hasRoutes) return;
        panel.classList.add("route-filter-floating-v3");
        if (panel.parentElement !== map) map.appendChild(panel);
        if (window.L?.DomEvent && panel.dataset.leafletEventsV3 !== "true") {
            panel.dataset.leafletEventsV3 = "true";
            L.DomEvent.disableClickPropagation(panel);
            L.DomEvent.disableScrollPropagation(panel);
        }
        const heading = panel.querySelector(".section-heading span");
        if (heading) heading.textContent = "Rotas";
    }

    function routeDialog() {
        let dialog = document.getElementById("asset-route-dialog-v3");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "asset-route-dialog-v3";
        dialog.className = "editor-dialog asset-route-dialog-v3";
        dialog.innerHTML = `<form method="dialog"><header><h2>Definir rota</h2><button type="button" data-close>×</button></header><label>Rota<select name="route_id" required></select></label><p data-status></p><footer><button type="button" class="primary-button" data-save>Salvar rota</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        return dialog;
    }

    async function chooseAssetRoute(asset, id) {
        const projectId = document.getElementById("project-select")?.value;
        if (!projectId) return notify("Selecione um projeto.", true);
        const data = await request(`/api/map/routes/?project_id=${encodeURIComponent(projectId)}`);
        const routes = data.features || [];
        if (!routes.length) return notify("Cadastre ou importe uma rota primeiro.", true);
        const dialog = routeDialog();
        const select = dialog.querySelector("select");
        select.innerHTML = '<option value="">Sem rota definida</option>' + routes.map((feature) => `<option value="${feature.id || feature.properties?.id}">${escapeHtml(feature.properties?.nome || feature.properties?.name || feature.properties?.codigo || `Rota ${feature.id}`)}</option>`).join("");
        dialog.querySelector("[data-save]").onclick = async () => {
            try {
                await request("/api/map/assets/route/", {
                    method: "POST",
                    body: JSON.stringify({ route_id: select.value, [`${asset}_id`]: id }),
                });
                dialog.close();
                await window.networkMap?.loadStructure?.();
                notify("Rota vinculada.");
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        dialog.showModal();
    }

    function enhanceLeafletPopup() {
        const scope = document.getElementById("map") || document;
        scope.querySelectorAll(".leaflet-popup-content").forEach((content) => {
            if (content.querySelector("[data-asset-route-v3]")) return;
            const elementButton = content.querySelector("[data-edit-element]");
            const cableButton = content.querySelector("[data-edit-cable]");
            const source = elementButton || cableButton;
            if (!source) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.assetRouteV3 = "true";
            button.textContent = "Definir rota";
            button.onclick = () => chooseAssetRoute(elementButton ? "element" : "cable", elementButton?.dataset.editElement || cableButton?.dataset.editCable)
                .catch((error) => notify(error.message, true));
            source.insertAdjacentElement("afterend", button);
        });
    }

    function equipmentDetailsDialog() {
        let dialog = document.getElementById("equipment-details-dialog-v3");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "equipment-details-dialog-v3";
        dialog.className = "editor-dialog equipment-details-dialog-v3";
        dialog.innerHTML = `<form><header><div><h2>Detalhes do equipamento</h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div class="equipment-detail-grid-v3"><label>Nome<input name="name"></label><label>IP de gerência<input name="management_ip"></label><label>Fabricante<input name="vendor"></label><label>Modelo<input name="model"></label><label>Número de série<input name="serial_number"></label><label>URL da foto<input name="photo_url" placeholder="https://..."></label></div><div class="equipment-photo-v3" data-photo-wrap hidden><img data-photo-preview alt="Foto do equipamento"></div><label>Descrição<textarea name="description" rows="2"></textarea></label><label>Observações<textarea name="notes" rows="3"></textarea></label><section class="equipment-port-create-v3"><h3>Adicionar portas / placas</h3><div data-add-port-row><select data-new-port-type><option value="rj45_100m">RJ45 100 Mb</option><option value="rj45_1g">RJ45 1 Gb</option><option value="sfp_1g">SFP 1 Gb</option><option value="sfp_plus_10g">SFP+ 10 Gb</option><option value="wireless">Interface wireless</option></select><input data-new-port-count type="number" min="1" max="256" value="1"><button type="button" data-add-ports>Adicionar portas</button></div><div data-add-card-row hidden><input data-card-slot type="number" min="1" max="64" placeholder="Slot"><input data-card-pons type="number" min="1" max="64" value="8" placeholder="PONs"><input data-card-name placeholder="Nome da placa"><button type="button" data-add-card>Adicionar placa</button></div></section><section><h3>Portas e módulos instalados</h3><div data-port-modules class="port-modules-v3"></div></section><p data-status></p><footer><button type="submit" class="primary-button">Salvar detalhes</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        return dialog;
    }

    async function openEquipmentDetails(equipmentId) {
        const containerId = containerDialog?.dataset.elementId;
        if (!containerId) return;
        const data = await request(`/api/map/elements/${containerId}/equipment/${equipmentId}/details-v3/`);
        const item = data.equipment;
        const dialog = equipmentDetailsDialog();
        const form = dialog.querySelector("form");
        ["name", "management_ip", "vendor", "model", "serial_number", "photo_url", "description", "notes"].forEach((field) => {
            if (form.elements[field]) form.elements[field].value = item[field] || "";
        });
        dialog.querySelector("[data-subtitle]").textContent = item.type_label;
        const photoWrap = dialog.querySelector("[data-photo-wrap]");
        const photo = dialog.querySelector("[data-photo-preview]");
        const syncPhoto = () => {
            const url = form.elements.photo_url.value.trim();
            photoWrap.hidden = !url;
            if (url) photo.src = url;
        };
        form.elements.photo_url.oninput = syncPhoto;
        photo.onerror = () => { photoWrap.hidden = true; };
        syncPhoto();
        const addPortRow = dialog.querySelector("[data-add-port-row]");
        const addCardRow = dialog.querySelector("[data-add-card-row]");
        addPortRow.hidden = item.type === "olt" || item.type === "dio";
        addCardRow.hidden = item.type !== "olt";
        dialog.querySelector("[data-add-ports]").onclick = async () => {
            try {
                await request(`/api/map/elements/${containerId}/equipment/${equipmentId}/ports/`, {
                    method: "POST",
                    body: JSON.stringify({
                        port_type: dialog.querySelector("[data-new-port-type]").value,
                        count: dialog.querySelector("[data-new-port-count]").value,
                    }),
                });
                dialog.close();
                await window.containerStructureV09?.refresh?.();
                await openEquipmentDetails(equipmentId);
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        dialog.querySelector("[data-add-card]").onclick = async () => {
            try {
                await request(`/api/map/elements/${containerId}/equipment/${equipmentId}/cards/`, {
                    method: "POST",
                    body: JSON.stringify({
                        slot: dialog.querySelector("[data-card-slot]").value,
                        pon_count: dialog.querySelector("[data-card-pons]").value,
                        name: dialog.querySelector("[data-card-name]").value,
                    }),
                });
                dialog.close();
                await window.containerStructureV09?.refresh?.();
                await openEquipmentDetails(equipmentId);
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        const modules = item.port_modules || {};
        dialog.querySelector("[data-port-modules]").innerHTML = item.ports.length ? item.ports.map((port) => `
            <label><span>${escapeHtml(port.label)}<small>${escapeHtml(port.type_label)}</small></span><select data-module-port="${port.id}">
                ${[
                    ["", "Sem módulo/adaptador"], ["sfp_optical_1g", "SFP óptico 1G"], ["sfp_rj45_1g", "SFP/RJ45 1G"],
                    ["sfp_plus_10g", "SFP+ óptico 10G"], ["sfp28_25g", "SFP28 25G"], ["dac", "Cabo DAC"],
                    ["gbic", "GBIC"], ["other", "Outro"],
                ].map(([value, label]) => `<option value="${value}" ${String(modules[port.id] || "") === value ? "selected" : ""}>${label}</option>`).join("")}
            </select></label>`).join("") : "<p>Nenhuma porta cadastrada.</p>";
        form.onsubmit = async (event) => {
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(form));
            payload.port_modules = {};
            dialog.querySelectorAll("[data-module-port]").forEach((select) => {
                if (select.value) payload.port_modules[select.dataset.modulePort] = select.value;
            });
            try {
                await request(`/api/map/elements/${containerId}/equipment/${equipmentId}/details-v3/`, { method: "PATCH", body: JSON.stringify(payload) });
                dialog.close();
                await window.containerStructureV09?.refresh?.();
                notify("Detalhes do equipamento atualizados.");
            } catch (error) { dialog.querySelector("[data-status]").textContent = error.message; }
        };
        dialog.showModal();
    }

    function compactEquipmentList() {
        if (!containerDialog?.open) return;
        containerDialog.querySelectorAll(".container-equipment-group-list-v092 > article").forEach((article) => {
            article.classList.add("equipment-row-v3");
            article.querySelectorAll(".equipment-port-grid, .equipment-card-list").forEach((node) => { node.hidden = true; });
            article.querySelectorAll("[data-add-equipment-ports], [data-add-container-card]").forEach((node) => { node.hidden = true; });
            const edit = article.querySelector("[data-edit-container-equipment]");
            if (edit && !article.querySelector("[data-equipment-details-v3]")) {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.equipmentDetailsV3 = edit.dataset.editContainerEquipment;
                button.textContent = "Detalhes";
                button.onclick = () => openEquipmentDetails(edit.dataset.editContainerEquipment).catch((error) => notify(error.message, true));
                edit.insertAdjacentElement("beforebegin", button);
            }
        });
    }

    async function loadContainerLayout(force = false) {
        const id = containerDialog?.dataset.elementId;
        if (!id) return;
        if (!force && String(containerLayoutId) === String(id)) return;
        // `containerLayoutId` só é gravado depois que o fetch termina — sem
        // essas duas travas, chamadas concorrentes disparadas mais rápido
        // que o round-trip da rede (ex.: outro script mutando o DOM em
        // loop) passavam todas pela checagem acima antes da primeira
        // resposta voltar, e cada uma abria seu próprio fetch. Isso já
        // chegou a gerar milhares de requisições por minuto em produção.
        if (containerLayoutLoading) return;
        if (!force && Date.now() - containerLayoutLoadedAt < 1000) return;
        containerLayoutLoading = true;
        containerLayoutLoadedAt = Date.now();
        try {
            const data = await request(`/api/map/elements/${id}/container-layout-v3/`);
            containerLayout = { positions: {}, routes: {}, ...(data.layout || {}) };
            containerLayout.positions ||= {};
            containerLayout.routes ||= {};
            containerLayoutId = id;
        } finally {
            containerLayoutLoading = false;
        }
    }

    function scheduleContainerSave() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            if (!containerLayoutId) return;
            request(`/api/map/elements/${containerLayoutId}/container-layout-v3/`, {
                method: "PATCH",
                body: JSON.stringify({ layout: containerLayout }),
            }).catch(() => {});
        }, 180);
    }

    function svgPoint(svg, event) {
        const point = svg.createSVGPoint();
        point.x = event.clientX;
        point.y = event.clientY;
        return point.matrixTransform(svg.getScreenCTM().inverse());
    }

    function renderContainerRouteHandles() {
        const svg = document.getElementById("container-diagram-links-v09");
        if (!svg || decorating) return;
        decorating = true;
        svg.querySelectorAll(".container-route-handles-v3").forEach((node) => node.remove());
        svg.querySelectorAll("path[data-link-id]").forEach((path) => {
            const linkId = String(path.dataset.linkId || "");
            if (!linkId) return;
            path.classList.toggle("route-editable-v3", editingContainerLines);
            path.classList.toggle("route-selected-v3", selectedContainerLink === linkId);
            let route = containerLayout.routes[linkId];
            const total = path.getTotalLength?.() || 0;
            const start = total ? path.getPointAtLength(0) : { x: 0, y: 0 };
            const end = total ? path.getPointAtLength(total) : { x: 0, y: 0 };
            if (Array.isArray(route) && route.length) {
                path.setAttribute("d", `M${start.x},${start.y} ${route.map((point) => `L${point.x},${point.y}`).join(" ")} L${end.x},${end.y}`);
            }
            path.onclick = (event) => {
                if (!editingContainerLines) return;
                event.stopPropagation();
                selectedContainerLink = linkId;
                renderContainerRouteHandles();
            };
            path.ondblclick = (event) => {
                if (!editingContainerLines) return;
                event.preventDefault();
                const point = svgPoint(svg, event);
                containerLayout.routes[linkId] ||= [];
                containerLayout.routes[linkId].push({ x: Math.round(point.x), y: Math.round(point.y) });
                selectedContainerLink = linkId;
                scheduleContainerSave();
                renderContainerRouteHandles();
            };
            if (editingContainerLines && selectedContainerLink === linkId) {
                const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
                group.setAttribute("class", "container-route-handles-v3");
                (containerLayout.routes[linkId] || []).forEach((point, index) => {
                    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    circle.setAttribute("cx", point.x);
                    circle.setAttribute("cy", point.y);
                    circle.setAttribute("r", 7);
                    circle.oncontextmenu = (event) => {
                        event.preventDefault();
                        containerLayout.routes[linkId].splice(index, 1);
                        scheduleContainerSave();
                        renderContainerRouteHandles();
                    };
                    circle.onpointerdown = (event) => {
                        event.preventDefault();
                        circle.setPointerCapture?.(event.pointerId);
                        const move = (moveEvent) => {
                            const next = svgPoint(svg, moveEvent);
                            point.x = Math.round(next.x); point.y = Math.round(next.y);
                            circle.setAttribute("cx", point.x); circle.setAttribute("cy", point.y);
                            path.setAttribute("d", `M${start.x},${start.y} ${containerLayout.routes[linkId].map((item) => `L${item.x},${item.y}`).join(" ")} L${end.x},${end.y}`);
                        };
                        const up = () => { window.removeEventListener("pointermove", move); scheduleContainerSave(); };
                        window.addEventListener("pointermove", move);
                        window.addEventListener("pointerup", up, { once: true });
                    };
                    group.appendChild(circle);
                });
                svg.appendChild(group);
            }
        });
        decorating = false;
    }

    function applyContainerPositions() {
        const nodes = document.getElementById("container-diagram-nodes-v09");
        if (!nodes) return;
        const entries = [...nodes.querySelectorAll(".container-diagram-node-v09")];
        if (!entries.length) return;
        const hasSaved = Object.keys(containerLayout.positions || {}).length > 0;
        nodes.classList.toggle("free-layout-v3", movingNodes || hasSaved);
        entries.forEach((node, index) => {
            const id = String(node.dataset.equipmentId);
            const saved = containerLayout.positions[id];
            if (saved) {
                node.style.left = `${saved.x}px`;
                node.style.top = `${saved.y}px`;
            } else if (movingNodes) {
                const rect = node.getBoundingClientRect();
                const parent = nodes.getBoundingClientRect();
                const position = { x: Math.max(20, rect.left - parent.left), y: Math.max(20, rect.top - parent.top) };
                containerLayout.positions[id] = position;
                node.style.left = `${position.x}px`; node.style.top = `${position.y}px`;
            }
            const handle = node.querySelector(":scope > header");
            if (handle && handle.dataset.dragV3 !== "true") {
                handle.dataset.dragV3 = "true";
                handle.onpointerdown = (event) => {
                    if (!movingNodes || event.target.closest("button")) return;
                    event.preventDefault();
                    const start = { x: event.clientX, y: event.clientY };
                    const current = containerLayout.positions[id] || { x: Number.parseFloat(node.style.left) || index * 30, y: Number.parseFloat(node.style.top) || index * 100 };
                    const move = (moveEvent) => {
                        const next = { x: Math.max(0, current.x + moveEvent.clientX - start.x), y: Math.max(0, current.y + moveEvent.clientY - start.y) };
                        containerLayout.positions[id] = next;
                        node.style.left = `${next.x}px`; node.style.top = `${next.y}px`;
                        window.dispatchEvent(new Event("resize"));
                    };
                    const up = () => { window.removeEventListener("pointermove", move); scheduleContainerSave(); };
                    window.addEventListener("pointermove", move);
                    window.addEventListener("pointerup", up, { once: true });
                };
            }
        });
        window.setTimeout(() => { window.dispatchEvent(new Event("resize")); renderContainerRouteHandles(); }, 60);
    }

    async function enhanceContainerDiagram() {
        if (!containerDialog?.open) return;
        const tools = containerDialog.querySelector(".container-diagram-tools-v09");
        const nodes = document.getElementById("container-diagram-nodes-v09");
        const svg = document.getElementById("container-diagram-links-v09");
        if (!tools || !nodes || !svg) return;
        await loadContainerLayout();
        if (!tools.querySelector("[data-container-move-v3]")) {
            const move = document.createElement("button");
            move.type = "button"; move.dataset.containerMoveV3 = "true"; move.textContent = "Mover";
            move.onclick = () => { movingNodes = !movingNodes; move.classList.toggle("active", movingNodes); applyContainerPositions(); };
            const lines = document.createElement("button");
            lines.type = "button"; lines.dataset.containerLinesV3 = "true"; lines.textContent = "Editar linhas";
            lines.onclick = () => { editingContainerLines = !editingContainerLines; lines.classList.toggle("active", editingContainerLines); selectedContainerLink = null; renderContainerRouteHandles(); };
            const reset = document.createElement("button");
            reset.type = "button"; reset.dataset.containerResetV3 = "true"; reset.textContent = "Auto";
            reset.onclick = () => { containerLayout.positions = {}; containerLayout.routes = {}; movingNodes = false; editingContainerLines = false; scheduleContainerSave(); window.containerStructureV09?.setTab?.("equipment"); setTimeout(() => window.containerStructureV09?.setTab?.("diagram"), 30); };
            tools.append(move, lines, reset);
        }
        applyContainerPositions();
        renderContainerRouteHandles();
    }

    function enhanceDropTermination() {
        const form = document.getElementById("container-fiber-termination-form");
        if (!form || form.querySelector("[data-drop-endpoint-v3]")) return;
        const destination = form.elements.destination_port_id;
        const cableSelect = form.elements.cable_id;
        if (!destination || !cableSelect) return;
        const block = document.createElement("fieldset");
        block.className = "drop-endpoint-v3";
        block.dataset.dropEndpointV3 = "true";
        block.innerHTML = `<legend>Destino do DROP</legend><div><label>Tipo<select data-endpoint-type><option value="existing">DIO / porta óptica existente</option><option value="pto">Criar PTO</option><option value="direct_connector">Conector direto</option></select></label><label>Conector<select data-endpoint-connector><option value="sc_apc">SC/APC</option><option value="sc_upc">SC/UPC</option><option value="lc_upc">LC/UPC</option><option value="lc_apc">LC/APC</option></select></label></div><label data-endpoint-name-wrap hidden>Nome<input data-endpoint-name placeholder="PTO Torre 01"></label><button type="button" data-create-endpoint hidden>Criar e selecionar destino</button><p data-endpoint-status></p>`;
        destination.closest("label")?.insertAdjacentElement("beforebegin", block);
        const type = block.querySelector("[data-endpoint-type]");
        const nameWrap = block.querySelector("[data-endpoint-name-wrap]");
        const create = block.querySelector("[data-create-endpoint]");
        const sync = () => {
            const custom = type.value !== "existing";
            nameWrap.hidden = !custom;
            create.hidden = !custom;
            block.querySelector("[data-endpoint-name]").placeholder = type.value === "pto" ? "Ex.: PTO da torre" : "Ex.: Conector direto DROP";
        };
        type.onchange = sync; sync();
        const syncDropVisibility = () => {
            const selected = cableSelect.options[cableSelect.selectedIndex];
            block.hidden = !selected || !/\bdrop\b/i.test(selected.textContent || "");
        };
        cableSelect.addEventListener("change", syncDropVisibility);
        new MutationObserver(syncDropVisibility).observe(cableSelect, { childList: true, subtree: true });
        syncDropVisibility();
        create.onclick = async () => {
            try {
                const result = await request(`/api/map/elements/${containerDialog.dataset.elementId}/passive-endpoints-v3/`, {
                    method: "POST",
                    body: JSON.stringify({ subtype: type.value, connector_type: block.querySelector("[data-endpoint-connector]").value, name: block.querySelector("[data-endpoint-name]").value }),
                });
                destination.add(new Option(`${result.equipment.name} · ${result.port.label}`, result.port.id, true, true));
                block.querySelector("[data-endpoint-status]").textContent = "Destino criado e selecionado. Agora conclua a terminação óptica.";
                window.containerStructureV09?.refresh?.();
            } catch (error) { block.querySelector("[data-endpoint-status]").textContent = error.message; }
        };
    }

    let enhancementTimer = null;
    let enhancementRunning = false;

    function runEnhancements() {
        if (enhancementRunning) return;
        enhancementRunning = true;
        try {
            installRouteDataGuard();
            improveMapIcons();
            relocateRouteFilter();
            enhanceLeafletPopup();
            if (containerDialog?.open) {
                compactEquipmentList();
                enhanceDropTermination();
                enhanceContainerDiagram().catch(() => {});
            }
            if (unifilarDialog?.open) enhanceFusion().catch(() => {});
        } finally {
            enhancementRunning = false;
        }
    }

    function scheduleEnhancements(delay = 40) {
        window.clearTimeout(enhancementTimer);
        enhancementTimer = window.setTimeout(runEnhancements, delay);
    }

    function nodeContainsSelector(node, selector) {
        return node?.nodeType === Node.ELEMENT_NODE && (
            node.matches?.(selector) || node.querySelector?.(selector)
        );
    }

    const mapRootV3 = document.getElementById("map");
    if (mapRootV3) {
        const mapObserver = new MutationObserver((mutations) => {
            const relevant = mutations.some((mutation) => [...mutation.addedNodes].some((node) =>
                nodeContainsSelector(node, ".network-marker, .leaflet-popup-content, #route-filter-v092, .route-filter-item-v092")
            ));
            if (relevant) scheduleEnhancements(50);
        });
        mapObserver.observe(mapRootV3, { childList: true, subtree: true });
    }

    if (unifilarContent) {
        const fusionObserver = new MutationObserver((mutations) => {
            const meaningful = mutations.some((mutation) => {
                const changed = [...mutation.addedNodes, ...mutation.removedNodes];
                return changed.some((node) => !nodeContainsSelector(node, ".manual-route-handle-v2, .container-route-handles-v3"));
            });
            if (meaningful && unifilarDialog?.open) scheduleEnhancements(35);
        });
        fusionObserver.observe(unifilarContent, { childList: true, subtree: true });
    }

    if (containerDialog) {
        const containerObserver = new MutationObserver((mutations) => {
            const openChanged = mutations.some((mutation) => mutation.type === "attributes");
            if (!containerDialog.open && !openChanged) return;
            const meaningful = openChanged || mutations.some((mutation) => {
                const changed = [...mutation.addedNodes, ...mutation.removedNodes];
                return changed.some((node) => !nodeContainsSelector(node, ".container-route-handles-v3"));
            });
            if (meaningful && containerDialog.open) scheduleEnhancements(45);
        });
        containerObserver.observe(containerDialog, { childList: true, subtree: true, attributes: true, attributeFilter: ["open"] });
    }

    document.addEventListener("fullscreenchange", () => {
        if (document.fullscreenElement !== unifilarDialog && unifilarDialog?.classList.contains("is-fullscreen")) {
            compactFusionToolbar();
        }
    });
    unifilarDialog?.addEventListener("close", () => { closeCablePanel(); fusionState = null; fusionStateElementId = null; });
    containerDialog?.addEventListener("close", () => {
        containerLayoutId = null; containerLayout = { positions: {}, routes: {} };
        movingNodes = false; editingContainerLines = false; selectedContainerLink = null;
    });

    installRouteDataGuard();
    improveMapIcons();
    relocateRouteFilter();
    enhanceDropTermination();
    scheduleEnhancements(0);
}());
