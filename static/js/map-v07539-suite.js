(function (global) {
    "use strict";

    const VERSION = "0.75.39";
    const state = {
        cableCache: new Map(),
        equipmentCache: new Map(),
        dioCache: new Map(),
        layoutCache: new Map(),
        cableMenu: null,
        modal: null,
        drag: null,
        scanFrame: 0,
        enhanceFrame: 0,
        generation: 0,
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

    function csrfToken() {
        const row = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
        return row ? decodeURIComponent(row.split("=")[1]) : qs("[name='csrfmiddlewaretoken']")?.value || "";
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
        global.networkMap?.notify?.(message, error);
    }

    function canEdit() {
        return document.body.dataset.canEdit === "true";
    }

    function currentContainerId() {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }

    function ensureModal() {
        if (state.modal?.isConnected) return state.modal;
        const dialog = document.createElement("dialog");
        dialog.id = "map-v07539-modal";
        dialog.className = "map-v07539-modal";
        dialog.innerHTML = '<section><header><div><span data-modal-kicker>MAP v0.75.39</span><h2 data-modal-title></h2><p data-modal-subtitle></p></div><button type="button" data-modal-close aria-label="Fechar">×</button></header><div data-modal-body></div></section>';
        document.body.appendChild(dialog);
        qs("[data-modal-close]", dialog).onclick = () => dialog.close();
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        state.modal = dialog;
        return dialog;
    }

    function showModal({ title, subtitle = "", kicker = "MAP v0.75.39", body = "", className = "" }) {
        const dialog = ensureModal();
        dialog.className = `map-v07539-modal ${className}`.trim();
        qs("[data-modal-kicker]", dialog).textContent = kicker;
        qs("[data-modal-title]", dialog).textContent = title;
        qs("[data-modal-subtitle]", dialog).textContent = subtitle;
        qs("[data-modal-body]", dialog).innerHTML = body;
        if (!dialog.open) dialog.showModal();
        return dialog;
    }

    function confirmAction({ title, message, confirmLabel = "Confirmar", danger = false }) {
        return new Promise((resolve) => {
            const dialog = showModal({
                title,
                subtitle: message,
                className: "map-v07539-confirm",
                body: `<footer class="v07539-modal-footer"><button type="button" data-confirm-cancel>Cancelar</button><button type="button" data-confirm-ok class="${danger ? "danger" : "primary"}">${escapeHtml(confirmLabel)}</button></footer>`,
            });
            const finish = (value) => {
                dialog.close();
                resolve(value);
            };
            qs("[data-confirm-cancel]", dialog).onclick = () => finish(false);
            qs("[data-confirm-ok]", dialog).onclick = () => finish(true);
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(false);
            };
        });
    }

    function formDataObject(form) {
        const data = Object.fromEntries(new FormData(form));
        qsa('input[type="checkbox"]', form).forEach((input) => { data[input.name] = input.checked; });
        return data;
    }

    function setFormStatus(form, message, error = false) {
        const node = qs("[data-form-status]", form);
        if (!node) return;
        node.textContent = message || "";
        node.classList.toggle("error", error);
    }

    function refreshContainer(elementId = currentContainerId()) {
        state.dioCache.clear();
        state.equipmentCache.clear();
        if (elementId && global.mapMasterSuite?.openContainerWorkspace) {
            return global.mapMasterSuite.openContainerWorkspace(elementId);
        }
        return Promise.resolve();
    }

    function ensureCableMenu() {
        if (state.cableMenu?.isConnected) return state.cableMenu;
        const menu = document.createElement("div");
        menu.id = "map-v07539-cable-menu";
        menu.className = "map-v07539-cable-menu";
        menu.hidden = true;
        document.body.appendChild(menu);
        document.addEventListener("pointerdown", (event) => {
            if (!event.target.closest("#map-v07539-cable-menu")) menu.hidden = true;
        }, true);
        global.addEventListener("blur", () => { menu.hidden = true; });
        state.cableMenu = menu;
        return menu;
    }

    function positionMenu(menu, clientX, clientY) {
        menu.hidden = false;
        const rect = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(8, Math.min(clientX, global.innerWidth - rect.width - 8))}px`;
        menu.style.top = `${Math.max(8, Math.min(clientY, global.innerHeight - rect.height - 8))}px`;
    }

    function cableUrl(cableId, fibers = true) {
        return `/api/map/v07539/cables/${Number(cableId)}/workspace/${fibers ? "" : "?fibers=0"}`;
    }

    async function loadCable(cableId, fibers = true, force = false) {
        const key = `${Number(cableId)}:${fibers ? 1 : 0}`;
        if (!force && state.cableCache.has(key)) return state.cableCache.get(key);
        const data = await request(cableUrl(cableId, fibers));
        state.cableCache.set(key, data);
        return data;
    }

    function clearCableCache(cableId) {
        state.cableCache.delete(`${Number(cableId)}:0`);
        state.cableCache.delete(`${Number(cableId)}:1`);
    }

    function connectionBadge(type) {
        return ({
            fusion: "FUSÃO",
            dio_fusion: "DIO TRASEIRA",
            splitter_input: "ENTRADA SPLITTER",
            splitter_output: "SAÍDA SPLITTER",
            splitter_cascade: "CASCATA",
            termination: "TERMINAÇÃO",
            cord: "CORDÃO",
        })[type] || String(type || "CONEXÃO").toUpperCase();
    }

    async function openCableInfo(cableId) {
        const data = await loadCable(cableId, true, true);
        const cable = data.cable;
        const summary = cable.fiber_summary;
        const body = `
            <nav class="v07539-tabs"><button type="button" data-tab="overview" class="active">Resumo</button><button type="button" data-tab="fibers">Fibras</button><button type="button" data-tab="connections">Conexões</button><button type="button" data-tab="reserves">Reservas</button></nav>
            <div class="v07539-tab active" data-tab-panel="overview">
                <div class="v07539-stat-grid">
                    <article><small>Tipo</small><strong>${escapeHtml(cable.type_label)}</strong></article>
                    <article><small>Comprimento</small><strong>${Number(cable.length_m || 0).toFixed(1)} m</strong></article>
                    <article><small>Fibras livres</small><strong>${summary.free}</strong></article>
                    <article><small>Em uso</small><strong>${summary.used}</strong></article>
                    <article><small>Reservadas</small><strong>${summary.reserved}</strong></article>
                    <article><small>Danificadas</small><strong>${summary.damaged}</strong></article>
                    <article><small>Perda estimada</small><strong>${Number(data.optical_budget?.total_loss_db || 0).toFixed(2)} dB</strong></article>
                    <article><small>Potência estimada</small><strong>${data.optical_budget?.estimated_rx_dbm == null ? "Não calculada" : `${Number(data.optical_budget.estimated_rx_dbm).toFixed(2)} dBm`}</strong></article>
                </div>
                <dl class="v07539-info-list">
                    <div><dt>Código</dt><dd>${escapeHtml(cable.code || "Sem código")}</dd></div>
                    <div><dt>Origem</dt><dd>${escapeHtml(cable.origin?.name || "Sem origem")}</dd></div>
                    <div><dt>Destino</dt><dd>${escapeHtml(cable.destination?.name || "Sem destino")}</dd></div>
                    <div><dt>Rota</dt><dd>${escapeHtml(cable.route?.name || "Sem rota")}</dd></div>
                    <div><dt>Caixas associadas</dt><dd>${data.passages.length}</dd></div>
                    <div><dt>Conexões registradas</dt><dd>${data.connections.length}</dd></div>
                    <div><dt>Atenuação do trecho</dt><dd>${Number(data.optical_budget?.fiber_loss_db || 0).toFixed(2)} dB</dd></div>
                    <div><dt>Perdas de conexões</dt><dd>${Number(data.optical_budget?.connection_loss_db || 0).toFixed(2)} dB</dd></div>
                </dl>
                <div class="v07539-actions-row" ${canEdit() ? "" : "hidden"}><button type="button" data-cable-edit>Editar cabo</button><button type="button" data-cable-reverse>Inverter sentido</button><button type="button" data-cable-reserve>Adicionar reserva</button><button type="button" data-cable-associate>Associar caixa</button></div>
            </div>
            <div class="v07539-tab" data-tab-panel="fibers">
                <div class="v07539-fiber-table">${cable.fibers.map((fiber) => `<div><i style="--fiber:${escapeHtml(fiber.color_hex)}"></i><strong>F${fiber.number}</strong><span>${escapeHtml(fiber.color_name)}</span><b class="status-${escapeHtml(fiber.status)}">${fiber.used ? "Em uso" : escapeHtml(fiber.status)}</b><small>${escapeHtml(fiber.usage || fiber.notes || "")}</small></div>`).join("") || "<p>Este cabo ainda não possui fibras geradas.</p>"}</div>
            </div>
            <div class="v07539-tab" data-tab-panel="connections">
                <div class="v07539-connection-list">${data.connections.map((item) => `<article><span>${connectionBadge(item.type)}</span><div><strong>${escapeHtml(item.element || "Rede")}</strong><p>${escapeHtml(item.description)}</p></div><small>${item.loss_db == null ? "" : `${item.loss_db} dB`}</small></article>`).join("") || "<p>Nenhuma conexão registrada.</p>"}</div>
            </div>
            <div class="v07539-tab" data-tab-panel="reserves">
                <div class="v07539-reserve-list">${data.reserves.map((item) => `<article><div><strong>${escapeHtml(item.label || "Reserva técnica")}</strong><span>${item.length_m} m · ${escapeHtml(item.reserve_type)} · ${escapeHtml(item.position)}</span><small>${escapeHtml(item.responsible || "Sem responsável")} · ${escapeHtml(item.notes || "")}</small></div>${canEdit() ? `<button type="button" data-delete-reserve="${item.id}">Excluir</button>` : ""}</article>`).join("") || "<p>Nenhuma reserva técnica.</p>"}</div>
                <h3>Passagens e caixas</h3>
                <div class="v07539-reserve-list">${data.passages.map((item) => `<article><div><strong>${escapeHtml(item.element.type_label)} · ${escapeHtml(item.element.name)}</strong><span>${escapeHtml(item.action_label)}</span></div>${canEdit() ? `<button type="button" data-delete-passage="${item.id}">Desassociar</button>` : ""}</article>`).join("") || "<p>Nenhuma caixa associada por passagem.</p>"}</div>
            </div>`;
        const dialog = showModal({
            title: cable.name,
            subtitle: `${cable.fiber_count} fibras · ${cable.origin?.name || "Sem origem"} → ${cable.destination?.name || "Sem destino"}`,
            kicker: "INFORMAÇÕES DO CABO",
            body,
            className: "map-v07539-wide",
        });
        qsa("[data-tab]", dialog).forEach((button) => button.onclick = () => {
            qsa("[data-tab]", dialog).forEach((item) => item.classList.toggle("active", item === button));
            qsa("[data-tab-panel]", dialog).forEach((panel) => panel.classList.toggle("active", panel.dataset.tabPanel === button.dataset.tab));
        });
        qs("[data-cable-edit]", dialog)?.addEventListener("click", () => openCableEdit(cableId, data));
        qs("[data-cable-reverse]", dialog)?.addEventListener("click", () => reverseCable(cableId));
        qs("[data-cable-reserve]", dialog)?.addEventListener("click", () => openReserveForm(cableId, null));
        qs("[data-cable-associate]", dialog)?.addEventListener("click", () => openAssociateBox(cableId, data));
        qsa("[data-delete-reserve]", dialog).forEach((button) => button.onclick = async () => {
            if (!await confirmAction({ title: "Excluir reserva", message: "A reserva técnica será removida do cabo.", confirmLabel: "Excluir", danger: true })) return;
            await request(cableUrl(cableId), { method: "DELETE", body: JSON.stringify({ action: "reserve", reserve_id: Number(button.dataset.deleteReserve) }) });
            clearCableCache(cableId);
            await global.networkMap?.loadStructure?.();
            openCableInfo(cableId);
        });
        qsa("[data-delete-passage]", dialog).forEach((button) => button.onclick = async () => {
            if (!await confirmAction({ title: "Desassociar caixa", message: "A passagem do cabo por esta caixa será removida.", confirmLabel: "Desassociar", danger: true })) return;
            await request(cableUrl(cableId), { method: "DELETE", body: JSON.stringify({ action: "passage", passage_id: Number(button.dataset.deletePassage) }) });
            clearCableCache(cableId);
            await global.networkMap?.loadStructure?.();
            openCableInfo(cableId);
        });
    }

    async function openCableEdit(cableId, existing = null) {
        const data = existing || await loadCable(cableId, false, true);
        const cable = data.cable;
        const dialog = showModal({
            title: `Editar ${cable.name}`,
            subtitle: "Informações diretas do cabo, sem abrir o formulário legado.",
            kicker: "EDITOR DO CABO",
            body: `<form data-cable-edit-form class="v07539-form">
                <div class="v07539-form-grid"><label>Nome<input name="name" value="${escapeHtml(cable.name)}" required></label><label>Código<input name="code" value="${escapeHtml(cable.code || "")}"></label><label>Tipo<select name="cable_type">${[["feeder","Alimentador"],["distribution","Distribuição"],["drop","DROP"],["backbone","Backbone"]].map(([value,label]) => `<option value="${value}" ${cable.type === value ? "selected" : ""}>${label}</option>`).join("")}</select></label><label>Estado<input name="status" value="${escapeHtml(cable.status || "no_data")}"></label></div>
                <p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Salvar cabo</button></footer>
            </form>`,
        });
        const form = qs("[data-cable-edit-form]", dialog);
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request(cableUrl(cableId), { method: "PATCH", body: JSON.stringify({ action: "update", ...formDataObject(form) }) });
                clearCableCache(cableId);
                dialog.close();
                await global.networkMap?.loadStructure?.();
                notify("Cabo atualizado.");
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    async function reverseCable(cableId) {
        const accepted = await confirmAction({
            title: "Inverter sentido do cabo",
            message: "Origem e destino serão trocados e o traçado será invertido quando a geometria permitir.",
            confirmLabel: "Inverter sentido",
        });
        if (!accepted) return;
        await request(cableUrl(cableId), { method: "POST", body: JSON.stringify({ action: "reverse" }) });
        clearCableCache(cableId);
        ensureModal().close();
        await global.networkMap?.loadStructure?.();
        notify("Sentido do cabo invertido.");
    }

    async function openReserveForm(cableId, latlng) {
        const dialog = showModal({
            title: "Adicionar reserva técnica",
            subtitle: "Registre metragem, tipo, posição e responsável.",
            kicker: "RESERVA DO CABO",
            body: `<form data-reserve-form class="v07539-form">
                <div class="v07539-form-grid"><label>Metragem<input name="length_m" type="number" min="0.01" step="0.01" value="20" required></label><label>Rótulo<input name="label" value="Reserva técnica"></label><label>Tipo<select name="reserve_type"><option value="technical">Técnica</option><option value="maintenance">Manutenção</option><option value="expansion">Expansão</option><option value="emergency">Emergência</option></select></label><label>Posição<select name="position"><option value="poste">Poste</option><option value="caixa">Caixa</option><option value="rack">Rack</option><option value="rota" selected>Rota</option><option value="subterranea">Subterrânea</option></select></label><label>Responsável<input name="responsible"></label><label>Latitude<input name="latitude" type="number" step="any" value="${latlng?.lat ?? ""}" required></label><label>Longitude<input name="longitude" type="number" step="any" value="${latlng?.lng ?? ""}" required></label></div><label>Observações<textarea name="notes" rows="4"></textarea></label>
                <p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Adicionar reserva</button></footer>
            </form>`,
        });
        const form = qs("[data-reserve-form]", dialog);
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request(cableUrl(cableId), { method: "POST", body: JSON.stringify({ action: "reserve", ...formDataObject(form) }) });
                clearCableCache(cableId);
                dialog.close();
                await global.networkMap?.loadStructure?.();
                notify("Reserva técnica adicionada.");
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    async function openCreateBox(cableId, subtype, latlng) {
        const label = subtype.toUpperCase();
        const dialog = showModal({
            title: `Adicionar ${label} no cabo`,
            subtitle: "A caixa será criada no ponto clicado e associada à topologia do cabo.",
            kicker: "NOVO ELEMENTO",
            body: `<form data-box-form class="v07539-form"><div class="v07539-form-grid"><label>Nome<input name="name" value="${label}" required></label><label>Código<input name="code"></label><label>Relação com o cabo<select name="passage_action"><option value="pass">Passagem sem corte</option><option value="connect">Conectado na ponta</option><option value="cut">Corte</option><option value="branch">Derivação</option></select></label><label>Latitude<input name="latitude" type="number" step="any" value="${latlng?.lat ?? ""}" required></label><label>Longitude<input name="longitude" type="number" step="any" value="${latlng?.lng ?? ""}" required></label></div><p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Criar ${label}</button></footer></form>`,
        });
        const form = qs("[data-box-form]", dialog);
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request(cableUrl(cableId), { method: "POST", body: JSON.stringify({ action: "create_box", subtype, ...formDataObject(form) }) });
                clearCableCache(cableId);
                dialog.close();
                await global.networkMap?.loadStructure?.();
                notify(`${label} adicionada ao cabo.`);
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    async function openAssociateBox(cableId, existing = null) {
        const data = existing || await loadCable(cableId, false, true);
        const dialog = showModal({
            title: "Associar cabo a uma caixa",
            subtitle: "A associação registra passagem, conexão, corte ou derivação.",
            kicker: "TOPOLOGIA DO CABO",
            body: `<form data-associate-form class="v07539-form"><label>Caixa<select name="element_id" required><option value="">Selecione</option>${data.available_boxes.map((item) => `<option value="${item.id}">${escapeHtml(item.type_label)} · ${escapeHtml(item.name)}</option>`).join("")}</select></label><label>Ação<select name="passage_action"><option value="pass">Passagem sem corte</option><option value="connect">Conectado na ponta</option><option value="cut">Corte</option><option value="branch">Derivação</option></select></label><p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Associar caixa</button></footer></form>`,
        });
        const form = qs("[data-associate-form]", dialog);
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            try {
                await request(cableUrl(cableId), { method: "POST", body: JSON.stringify({ action: "associate_element", ...formDataObject(form) }) });
                clearCableCache(cableId);
                dialog.close();
                await global.networkMap?.loadStructure?.();
                notify("Caixa associada ao cabo.");
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    function openCableContext({ cableId, latlng, originalEvent }) {
        const menu = ensureCableMenu();
        menu.innerHTML = `
            <header><strong>Cabo #${Number(cableId)}</strong><small>Ações da topologia</small></header>
            <button type="button" data-cable-action="info">Informações</button>
            <button type="button" data-cable-action="edit" ${canEdit() ? "" : "disabled"}>Editar cabo</button>
            <button type="button" data-cable-action="reverse" ${canEdit() ? "" : "disabled"}>Alterar sentido</button>
            <hr><button type="button" data-cable-action="cto" ${canEdit() ? "" : "disabled"}>Adicionar CTO</button><button type="button" data-cable-action="ceo" ${canEdit() ? "" : "disabled"}>Adicionar CEO</button><button type="button" data-cable-action="cdo" ${canEdit() ? "" : "disabled"}>Adicionar CDO</button>
            <button type="button" data-cable-action="reserve" ${canEdit() ? "" : "disabled"}>Adicionar reserva</button><button type="button" data-cable-action="associate" ${canEdit() ? "" : "disabled"}>Associar à caixa</button>
            <hr><button type="button" data-cable-action="delete" class="danger" ${canEdit() ? "" : "disabled"}>Excluir cabo</button>`;
        positionMenu(menu, originalEvent?.clientX || 20, originalEvent?.clientY || 20);
        qsa("[data-cable-action]", menu).forEach((button) => button.onclick = async () => {
            menu.hidden = true;
            const action = button.dataset.cableAction;
            try {
                if (action === "info") return openCableInfo(cableId);
                if (action === "edit") return openCableEdit(cableId);
                if (action === "reverse") return reverseCable(cableId);
                if (["cto", "ceo", "cdo"].includes(action)) return openCreateBox(cableId, action, latlng);
                if (action === "reserve") return openReserveForm(cableId, latlng);
                if (action === "associate") return openAssociateBox(cableId);
                if (action === "delete") {
                    const accepted = await confirmAction({ title: "Excluir cabo", message: "O cabo e seus registros dependentes poderão ser removidos. Esta ação é destrutiva.", confirmLabel: "Excluir cabo", danger: true });
                    if (!accepted) return;
                    await request(`/api/map/cables/${Number(cableId)}/?force=1`, { method: "DELETE" });
                    clearCableCache(cableId);
                    await global.networkMap?.loadStructure?.();
                    notify("Cabo excluído.");
                }
            } catch (error) { notify(error.message, true); }
        });
    }

    function scanLeafletLayers() {
        const map = global.networkMap?.map;
        if (!map) return;
        const visit = (layer) => {
            if (layer?.eachLayer) layer.eachLayer(visit);
            const feature = layer?.feature;
            const properties = feature?.properties || {};
            const geometryType = String(feature?.geometry?.type || "");
            if (!geometryType.includes("Line") || !properties.id || properties.fibras == null || layer._v07539CableMenu) return;
            layer._v07539CableMenu = true;
            layer.on?.("contextmenu", (event) => {
                event.originalEvent?.preventDefault?.();
                event.originalEvent?.stopPropagation?.();
                event.originalEvent?.stopImmediatePropagation?.();
                openCableContext({ cableId: properties.id, latlng: event.latlng, originalEvent: event.originalEvent });
            });
        };
        map.eachLayer(visit);
    }

    function scheduleLeafletScan() {
        if (state.scanFrame) return;
        state.scanFrame = global.requestAnimationFrame(() => {
            state.scanFrame = 0;
            scanLeafletLayers();
        });
    }

    async function loadEquipment(elementId, equipmentId, force = false) {
        const key = `${elementId}:${equipmentId}`;
        if (!force && state.equipmentCache.has(key)) return state.equipmentCache.get(key);
        const data = await request(`/api/map/v07539/elements/${elementId}/equipment/${equipmentId}/editor/`);
        state.equipmentCache.set(key, data);
        return data;
    }

    function equipmentTypeFields(type, item = {}) {
        const isOlt = type === "olt";
        const isDio = type === "dio";
        const isOnu = type === "onu";
        const isPto = type === "pto";
        return `<div class="v07539-form-grid">
            <label>Nome<input name="name" value="${escapeHtml(item.name || "")}" required></label><label>Fabricante<input name="vendor" value="${escapeHtml(item.vendor || "")}"></label><label>Modelo<input name="model" value="${escapeHtml(item.model || "")}"></label><label>Serial<input name="serial_number" value="${escapeHtml(item.serial_number || "")}"></label>
            <label>IP de gerenciamento<input name="management_ip" value="${escapeHtml(item.management_ip || "")}" ${isDio || isPto ? "disabled" : ""}></label><label>Provisionamento<select name="provisioning_mode"><option value="manual" ${item.provisioning_mode !== "snmp" ? "selected" : ""}>Manual</option><option value="snmp" ${item.provisioning_mode === "snmp" ? "selected" : ""}>SNMP</option></select></label>
            ${isOlt ? `<label>Potência TX (dBm)<input name="tx_power_dbm" type="number" step="0.01" value="${item.tx_power_dbm ?? ""}"></label><label>Slots/placas<input name="card_count" type="number" min="0" max="64" value="${item.card_count || 0}" ${item.id ? "disabled" : ""}></label><label>PONs por slot<input name="pons_per_card" type="number" min="0" max="64" value="${item.pons_per_card || 0}" ${item.id ? "disabled" : ""}></label>` : ""}
            ${isDio ? `<label>Capacidade do DIO<select name="dio_port_capacity" ${item.id ? "disabled" : ""}>${[12,24,36,48,72,96,144,192,244].map((value) => `<option value="${value}" ${Number(item.dio_port_capacity) === value ? "selected" : ""}>${value} portas</option>`).join("")}</select></label>` : ""}
            ${isDio || isPto ? `<label>Conector<select name="connector_type"><option value="sc_apc" ${item.connector_type === "sc_apc" ? "selected" : ""}>SC/APC</option><option value="sc_upc" ${item.connector_type === "sc_upc" ? "selected" : ""}>SC/UPC</option><option value="lc_upc" ${item.connector_type === "lc_upc" ? "selected" : ""}>LC/UPC</option><option value="lc_apc" ${item.connector_type === "lc_apc" ? "selected" : ""}>LC/APC</option></select></label>` : ""}
            ${isOnu ? `<label>Portas LAN<input name="onu_lan_count" type="number" min="1" max="16" value="${item.onu_lan_count || 4}"></label><label>Conector PON<select name="pon_connector"><option>SC/APC</option><option ${item.pon_connector === "SC/UPC" ? "selected" : ""}>SC/UPC</option></select></label><label>Potência RX (dBm)<input name="rx_power_dbm" type="number" step="0.01" value="${item.rx_power_dbm ?? ""}"></label>` : ""}
            <label>Ativo<input name="enabled" type="checkbox" ${item.enabled !== false ? "checked" : ""}></label>
        </div><label>Observações<textarea name="description" rows="3">${escapeHtml(item.description || "")}</textarea></label>`;
    }

    async function openEquipmentEditor(elementId, equipmentId) {
        const data = await loadEquipment(elementId, equipmentId, true);
        const item = data.equipment;
        const dialog = showModal({
            title: item.name,
            subtitle: `${item.type_label} · ${(item.ports || []).length} porta(s)`,
            kicker: "EDITOR MODERNO DE EQUIPAMENTOS",
            body: `<form data-equipment-form class="v07539-form" data-equipment-id="${item.id}">${equipmentTypeFields(item.type, item)}<details class="v07539-port-summary"><summary>Portas e interfaces (${item.ports.length})</summary><div>${item.ports.map((port) => `<span><b>${escapeHtml(port.label)}</b><small>${escapeHtml(port.type_label)}</small></span>`).join("")}</div></details><p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Salvar equipamento</button></footer></form>`,
            className: "map-v07539-wide",
        });
        const form = qs("[data-equipment-form]", dialog);
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            const payload = formDataObject(form);
            try {
                await request(`/api/map/v07539/elements/${elementId}/equipment/${equipmentId}/editor/`, { method: "PATCH", body: JSON.stringify(payload) });
                state.equipmentCache.delete(`${elementId}:${equipmentId}`);
                dialog.close();
                await refreshContainer(elementId);
                notify("Equipamento atualizado.");
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    function openCreateEquipment(elementId) {
        const dialog = showModal({
            title: "Adicionar equipamento",
            subtitle: "Cadastro direto no Canvas do Rack/Torre.",
            kicker: "NOVO EQUIPAMENTO",
            body: `<form data-create-equipment class="v07539-form"><label>Tipo<select name="equipment_type" data-create-type><option value="olt">OLT</option><option value="dio">DIO</option><option value="switch">Switch</option><option value="router">Roteador</option><option value="firewall">Firewall</option><option value="access_point">Access point</option><option value="ptp">Rádio PTP</option><option value="onu">ONU / ONT</option><option value="pto">PTO</option><option value="other">Outro</option></select></label><div data-create-fields></div><p data-form-status></p><footer class="v07539-modal-footer"><button type="button" data-modal-cancel>Cancelar</button><button type="submit" class="primary">Adicionar equipamento</button></footer></form>`,
        });
        const form = qs("[data-create-equipment]", dialog);
        const typeSelect = qs("[data-create-type]", form);
        const fields = qs("[data-create-fields]", form);
        const render = () => { fields.innerHTML = equipmentTypeFields(typeSelect.value, { enabled: true, provisioning_mode: "manual", connector_type: "sc_apc", dio_port_capacity: 24, onu_lan_count: 4 }); };
        typeSelect.onchange = render;
        render();
        qs("[data-modal-cancel]", form).onclick = () => dialog.close();
        form.onsubmit = async (event) => {
            event.preventDefault();
            const payload = formDataObject(form);
            payload.equipment_type = typeSelect.value;
            try {
                await request(`/api/map/v07539/elements/${elementId}/equipment/`, { method: "POST", body: JSON.stringify(payload) });
                dialog.close();
                await refreshContainer(elementId);
                notify("Equipamento adicionado.");
            } catch (error) { setFormStatus(form, error.message, true); }
        };
    }

    async function loadDio(elementId, equipmentId, force = false) {
        const key = `${elementId}:${equipmentId}`;
        if (!force && state.dioCache.has(key)) return state.dioCache.get(key);
        const data = await request(`/api/map/v07539/elements/${elementId}/dio/${equipmentId}/dual-face/`);
        state.dioCache.set(key, data);
        return data;
    }

    function groupDioCavities(node) {
        if (qs(".v07539-dio-cavities", node)) return;
        const buttons = qsa(".master-node-port[data-port-id]", node);
        if (!buttons.length) return;
        const portIds = [...new Set(buttons.map((button) => Number(button.dataset.portId)))];
        const old = qs(".master-node-ports, .master-dio-trays-v07510", node);
        const cavities = document.createElement("div");
        cavities.className = "v07539-dio-cavities";
        for (let index = 0; index < portIds.length; index += 12) {
            const group = portIds.slice(index, index + 12);
            const section = document.createElement("section");
            section.className = "v07539-dio-cavity";
            section.dataset.cavity = String(index / 12 + 1);
            section.innerHTML = `<header><strong>CAVIDADE ${index / 12 + 1}</strong><small>frente / traseira</small><button type="button" data-cavity-toggle>−</button></header><div></div>`;
            const body = qs(":scope > div", section);
            group.forEach((portId) => {
                const pair = document.createElement("div");
                pair.className = "v07539-dio-pair";
                pair.dataset.portPair = String(portId);
                qsa(`[data-port-id="${portId}"]`, node).forEach((button) => pair.appendChild(button));
                body.appendChild(pair);
            });
            qs("[data-cavity-toggle]", section).onclick = () => {
                section.classList.toggle("collapsed");
                qs("[data-cavity-toggle]", section).textContent = section.classList.contains("collapsed") ? "+" : "−";
                saveLayoutPreference(currentContainerId(), { [`dio_cavity_${node.dataset.equipmentNode}_${section.dataset.cavity}`]: section.classList.contains("collapsed") });
            };
            cavities.appendChild(section);
        }
        old?.replaceWith(cavities);
    }

    async function enhanceDio(node, elementId) {
        const equipmentId = Number(node.dataset.equipmentNode || 0);
        if (!equipmentId) return;
        node.classList.add("v07539-dio-node");
        groupDioCavities(node);
        try {
            const data = await loadDio(elementId, equipmentId, true);
            data.ports.forEach((port) => {
                const front = qs(`[data-port-id="${port.id}"][data-port-role="front"]`, node);
                const rear = qs(`[data-port-id="${port.id}"][data-port-role="rear"]`, node);
                if (front) {
                    front.dataset.linkId = port.front?.id || "";
                    front.classList.toggle("used", Boolean(port.front));
                    front.classList.toggle("v07539-front-linked", Boolean(port.front));
                    front.classList.toggle("v07539-has-rear", Boolean(port.rear));
                    front.dataset.rearStateV07539 = port.rear ? "linked" : "free";
                    front.title = port.front
                        ? `Frente ligada: ${port.front.source_equipment} · ${port.front.source_port}${port.rear ? " · traseira também ligada" : ""}`
                        : port.rear
                            ? `Frente livre para OLT · traseira fundida/terminada · ${port.label}`
                            : `Frente livre · ${port.label}`;
                }
                if (rear) {
                    rear.dataset.linkId = port.rear?.id || "";
                    rear.classList.toggle("used", Boolean(port.rear));
                    rear.classList.toggle("v07539-rear-linked", Boolean(port.rear));
                    rear.classList.toggle("v07539-drop-linked", port.rear?.kind === "drop_termination");
                    rear.title = port.rear ? `Traseira ligada: ${port.rear.cable}${port.rear.fiber_number ? ` F${port.rear.fiber_number}` : ""}` : `Traseira livre · ${port.label}`;
                }
            });
            let legend = qs("[data-dio-face-legend-v07539]", node);
            if (!legend) {
                legend = document.createElement("div");
                legend.dataset.dioFaceLegendV07539 = "1";
                legend.className = "v07539-dio-legend";
                node.appendChild(legend);
            }
            legend.innerHTML = `<span class="front">Frente / OLT ${data.summary.front}</span><span class="rear">Traseira / fusão ${data.summary.rear}</span><span class="both">Completas ${data.summary.both}</span>`;
        } catch (error) {
            node.dataset.v07539DioError = error.message;
        }
    }

    async function disconnectDioFace(button) {
        const node = button.closest('[data-equipment-type="dio"]');
        const elementId = currentContainerId();
        const equipmentId = Number(node?.dataset.equipmentNode || 0);
        const role = button.dataset.portRole;
        const linkId = Number(button.dataset.linkId || 0);
        if (!elementId || !equipmentId || !linkId) return false;
        const accepted = await confirmAction({
            title: role === "rear" ? "Desligar traseira do DIO" : "Desligar frente do DIO",
            message: role === "rear" ? "A fusão/terminação traseira será removida; o cordão frontal continuará intacto." : "O cordão frontal será removido; a fusão traseira continuará intacta.",
            confirmLabel: "Desligar somente este lado",
            danger: true,
        });
        if (!accepted) return true;
        await request(`/api/map/v07539/elements/${elementId}/dio/${equipmentId}/dual-face/`, {
            method: "DELETE",
            body: JSON.stringify({ action: role === "rear" ? "disconnect_rear" : "disconnect_front", link_id: linkId }),
        });
        state.dioCache.delete(`${elementId}:${equipmentId}`);
        await refreshContainer(elementId);
        notify(role === "rear" ? "Traseira do DIO desligada." : "Frente do DIO desligada.");
        return true;
    }

    async function loadLayout(elementId, force = false) {
        if (!force && state.layoutCache.has(elementId)) return state.layoutCache.get(elementId);
        const data = await request(`/api/map/v07539/elements/${elementId}/layout/`);
        state.layoutCache.set(elementId, data.layout || {});
        return data.layout || {};
    }

    async function saveLayoutPreference(elementId, patch) {
        if (!elementId || !canEdit()) return;
        const current = { ...(state.layoutCache.get(elementId) || {}), ...patch };
        state.layoutCache.set(elementId, current);
        await request(`/api/map/v07539/elements/${elementId}/layout/`, { method: "PATCH", body: JSON.stringify({ layout: patch }) }).catch((error) => notify(error.message, true));
    }

    async function enhanceOlt(node, elementId) {
        const equipmentId = Number(node.dataset.equipmentNode || 0);
        node.classList.add("v07539-olt-node");
        qsa(".olt-port-v07510", node).forEach((port, index) => {
            const full = port.dataset.fullPortLabelV07537 || port.title || qs("span", port)?.textContent || `Porta ${index + 1}`;
            port.title = full;
        });
        let controls = qs("[data-olt-size-controls-v07539]", node);
        if (!controls) {
            controls = document.createElement("div");
            controls.dataset.oltSizeControlsV07539 = "1";
            controls.className = "v07539-olt-size-controls";
            controls.innerHTML = '<button type="button" data-size="compact">P</button><button type="button" data-size="medium">M</button><button type="button" data-size="wide">G</button><button type="button" data-size="auto">Auto</button>';
            qs(":scope > header", node)?.appendChild(controls);
            qsa("[data-size]", controls).forEach((button) => button.onclick = (event) => {
                event.preventDefault(); event.stopPropagation();
                const widths = { compact: 505, medium: 620, wide: 820 };
                if (button.dataset.size === "auto") node.style.removeProperty("--olt-width-v07539");
                else node.style.setProperty("--olt-width-v07539", `${widths[button.dataset.size]}px`);
                saveLayoutPreference(elementId, { [`equipment_width_${equipmentId}`]: button.dataset.size === "auto" ? null : widths[button.dataset.size] });
                global.dispatchEvent(new Event("resize"));
            });
        }
        const layout = await loadLayout(elementId).catch(() => ({}));
        const saved = Number(layout[`equipment_width_${equipmentId}`] || 0);
        if (saved) node.style.setProperty("--olt-width-v07539", `${saved}px`);
    }

    async function enhancePassiveEquipment(node, elementId) {
        const type = node.dataset.equipmentType;
        const equipmentId = Number(node.dataset.equipmentNode || 0);
        if (!equipmentId || !["pto", "onu"].includes(type)) return;
        node.classList.add(`v07539-${type}-node`);
        try {
            const data = await loadEquipment(elementId, equipmentId);
            const item = data.equipment;
            let badge = qs("[data-passive-badge-v07539]", node);
            if (!badge) {
                badge = document.createElement("div");
                badge.dataset.passiveBadgeV07539 = "1";
                badge.className = "v07539-passive-badge";
                node.appendChild(badge);
            }
            badge.innerHTML = type === "pto"
                ? `<span>ENTRADA FIBRA</span><i>→</i><strong>${escapeHtml(item.connector_type_label || "SC/APC")}</strong>`
                : `<span>PON ${escapeHtml(item.pon_connector || "SC/APC")}</span><i>→</i><strong>${item.onu_lan_count || 4} LAN</strong>${item.rx_power_dbm == null ? "" : `<small>${item.rx_power_dbm} dBm</small>`}`;
            qsa(".master-node-port", node).forEach((port) => {
                const valid = (type === "pto" && port.dataset.portType === "dio") || (type === "onu" && port.dataset.portType === "pon");
                port.classList.toggle("v07539-drop-target-port", valid);
                if (valid) port.dataset.dropTargetV07539 = "1";
            });
        } catch (error) {
            node.dataset.v07539PassiveError = error.message;
        }
    }

    async function preloadCableTypes(root) {
        await Promise.all(qsa(".master-cable-node[data-cable-node]", root).map(async (node) => {
            const cableId = Number(node.dataset.cableNode || 0);
            if (!cableId) return;
            try {
                const data = await loadCable(cableId, false);
                node.dataset.cableTypeV07539 = data.cable.type;
                if (data.cable.type === "drop") {
                    node.classList.add("v07539-drop-cable");
                    const anchor = qs("[data-rack-cable-anchor-v07538]", node);
                    if (anchor) {
                        anchor.dataset.dropDragV07539 = String(cableId);
                        anchor.title = "Arraste o DROP para DIO, PTO ou PON da ONU/ONT";
                    }
                }
            } catch (_error) {}
        }));
    }

    function dropDragOverlay() {
        let svg = qs("#map-v07539-drop-drag");
        if (!svg) {
            svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.id = "map-v07539-drop-drag";
            svg.innerHTML = "<path></path>";
            document.body.appendChild(svg);
        }
        return svg;
    }

    function startDropDrag(event, anchor) {
        const cableId = Number(anchor.dataset.dropDragV07539 || 0);
        if (!cableId || !canEdit()) return;
        event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
        const rect = anchor.getBoundingClientRect();
        state.drag = { pointerId: event.pointerId, cableId, startX: rect.left + rect.width / 2, startY: rect.top + rect.height / 2, frame: 0, x: event.clientX, y: event.clientY };
        document.body.classList.add("v07539-drop-dragging");
        global.addEventListener("pointermove", moveDropDrag, true);
        global.addEventListener("pointerup", finishDropDrag, true);
        global.addEventListener("pointercancel", cancelDropDrag, true);
        scheduleDropLine(event.clientX, event.clientY);
    }

    function scheduleDropLine(x, y) {
        if (!state.drag) return;
        state.drag.x = x; state.drag.y = y;
        if (state.drag.frame) return;
        state.drag.frame = global.requestAnimationFrame(() => {
            if (!state.drag) return;
            state.drag.frame = 0;
            const svg = dropDragOverlay();
            const mid = (state.drag.startX + state.drag.x) / 2;
            qs("path", svg).setAttribute("d", `M${state.drag.startX},${state.drag.startY} C${mid},${state.drag.startY} ${mid},${state.drag.y} ${state.drag.x},${state.drag.y}`);
        });
    }

    function dropTargetAt(x, y) {
        return document.elementsFromPoint(x, y).map((item) => item.closest?.("[data-drop-target-v07539], [data-port-role='rear'][data-port-id]"))
            .find((item) => item && (item.dataset.dropTargetV07539 || item.closest('[data-equipment-type="dio"]')));
    }

    function moveDropDrag(event) {
        if (!state.drag || event.pointerId !== state.drag.pointerId) return;
        scheduleDropLine(event.clientX, event.clientY);
        qsa(".v07539-drop-hover").forEach((item) => item.classList.remove("v07539-drop-hover"));
        dropTargetAt(event.clientX, event.clientY)?.classList.add("v07539-drop-hover");
    }

    async function finishDropDrag(event) {
        if (!state.drag || event.pointerId !== state.drag.pointerId) return;
        const cableId = state.drag.cableId;
        const target = dropTargetAt(event.clientX, event.clientY);
        cancelDropDrag();
        if (!target) return notify("Solte o DROP sobre a traseira do DIO, uma PTO ou a PON da ONU/ONT.", true);
        const portId = Number(target.dataset.portId || 0);
        const elementId = currentContainerId();
        if (!portId || !elementId) return;
        try {
            await request(`/api/map/v07539/elements/${elementId}/drop-terminations/`, { method: "POST", body: JSON.stringify({ action: "terminate", cable_id: cableId, port_id: portId, loss_db: "0.10" }) });
            clearCableCache(cableId);
            await refreshContainer(elementId);
            notify("DROP terminado no destino óptico.");
        } catch (error) { notify(error.message, true); }
    }

    function cancelDropDrag() {
        if (state.drag?.frame) global.cancelAnimationFrame(state.drag.frame);
        state.drag = null;
        qs("#map-v07539-drop-drag")?.remove();
        document.body.classList.remove("v07539-drop-dragging");
        qsa(".v07539-drop-hover").forEach((item) => item.classList.remove("v07539-drop-hover"));
        global.removeEventListener("pointermove", moveDropDrag, true);
        global.removeEventListener("pointerup", finishDropDrag, true);
        global.removeEventListener("pointercancel", cancelDropDrag, true);
    }

    async function enhanceContainer() {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        if (!root || !dialog?.open) return;
        const elementId = currentContainerId();
        if (!elementId) return;
        root.classList.add("map-v07539-container");
        let add = qs("[data-v07539-add-equipment]", root);
        if (!add && canEdit()) {
            add = document.createElement("button");
            add.type = "button";
            add.dataset.v07539AddEquipment = "1";
            add.className = "v07539-add-equipment";
            add.textContent = "+ Equipamento";
            add.onclick = () => openCreateEquipment(elementId);
            root.appendChild(add);
        }
        await preloadCableTypes(root);
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="dio"]', root).map((node) => enhanceDio(node, elementId)));
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="olt"]', root).map((node) => enhanceOlt(node, elementId)));
        await Promise.all(qsa('.master-canvas-node[data-equipment-type="pto"], .master-canvas-node[data-equipment-type="onu"]', root).map((node) => enhancePassiveEquipment(node, elementId)));
    }

    function scheduleEnhance() {
        if (state.enhanceFrame) return;
        state.enhanceFrame = global.requestAnimationFrame(() => {
            state.enhanceFrame = 0;
            enhanceContainer().catch((error) => console.error("MAP v0.75.39 enhance:", error));
        });
    }

    function installCaptureHandlers() {
        document.addEventListener("click", (event) => {
            const edit = event.target.closest("[data-node-edit], [data-edit-equipment]");
            if (edit && qs("#container-dialog")?.open) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                const equipmentId = Number(edit.dataset.nodeEdit || edit.dataset.editEquipment || 0);
                if (equipmentId) openEquipmentEditor(currentContainerId(), equipmentId).catch((error) => notify(error.message, true));
                return;
            }
            const dioButton = event.target.closest('.master-canvas-node[data-equipment-type="dio"] [data-port-id][data-link-id]:not([data-link-id=""])');
            if (dioButton && qs("#container-dialog")?.open) {
                event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
                disconnectDioFace(dioButton).catch((error) => notify(error.message, true));
            }
        }, true);
        document.addEventListener("pointerdown", (event) => {
            const anchor = event.target.closest("[data-drop-drag-v07539]");
            if (anchor) startDropDrag(event, anchor);
        }, true);
    }

    async function init() {
        installCaptureHandlers();
        for (let attempt = 0; attempt < 100 && !global.networkMap; attempt += 1) {
            await new Promise((resolve) => global.setTimeout(resolve, 50));
        }
        global.networkMap?.map?.on?.("layeradd", scheduleLeafletScan);
        global.networkMap?.map?.on?.("zoomend moveend", scheduleLeafletScan);
        document.addEventListener("map:container-rendered", scheduleEnhance);
        document.addEventListener("map:container-opening", () => global.setTimeout(scheduleEnhance, 100));
        global.addEventListener("resize", scheduleEnhance);
        global.setTimeout(() => { scheduleLeafletScan(); scheduleEnhance(); }, 600);
        global.mapV07539 = Object.freeze({
            version: VERSION,
            openCableInfo,
            openEquipmentEditor,
            enhanceContainer: scheduleEnhance,
            refreshCableMenus: scheduleLeafletScan,
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}(window));
