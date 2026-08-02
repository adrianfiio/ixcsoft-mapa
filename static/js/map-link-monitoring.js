(function () {
    "use strict";

    const projectSelect = document.getElementById("project-select");
    const canEdit = document.body.dataset.canEdit === "true";
    if (!projectSelect) return;

    const state = {
        projectId: "",
        snapshot: null,
        layer: null,
        timer: null,
        busy: false,
        preselectedCableId: "",
        profileEquipmentId: null,
        profileData: null,
    };

    function apiRoot() { return "/api/monitoring"; }
    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
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
        const element = document.createElement("span");
        element.textContent = value == null ? "" : String(value);
        return element.innerHTML;
    }
    function notify(message, error = false) {
        if (window.networkMap?.notify) window.networkMap.notify(message, error);
    }
    function statusClass(value) {
        return `monitor-status-${String(value || "no_data").replace(/_/g, "-")}`;
    }
    function statusColor(properties) {
        if (properties.status === "offline") return properties.down_color || "#ef4444";
        if (properties.status === "degraded" || properties.status === "warning") return "#f59e0b";
        if (properties.status === "recovering") return "#22c55e";
        if (properties.status === "no_data") return "#64748b";
        return properties.normal_color || "#38bdf8";
    }
    function mapApi() { return window.networkMap || null; }

    function ensureLayer() {
        const api = mapApi();
        if (!api?.map || !window.L) return null;
        if (!state.layer) state.layer = L.layerGroup().addTo(api.map);
        return state.layer;
    }

    function linkPopup(properties) {
        const src = properties.source_binding;
        const dst = properties.destination_binding;
        return `<section class="monitor-link-popup">
            <strong>${escapeHtml(properties.name)}</strong>
            <span class="monitor-badge ${statusClass(properties.status)}">${escapeHtml(properties.status_label)}</span>
            <small>${escapeHtml(properties.link_type_label)}</small>
            <div>${escapeHtml(properties.source_element)}${src ? ` · ${escapeHtml(src.equipment_port || src.if_name)} (${escapeHtml(src.last_status.toUpperCase())})` : ""}</div>
            <div>↔ ${escapeHtml(properties.destination_element)}${dst ? ` · ${escapeHtml(dst.equipment_port || dst.if_name)} (${escapeHtml(dst.last_status.toUpperCase())})` : ""}</div>
            ${properties.cable ? `<div>Cabo: ${escapeHtml(properties.cable)}</div>` : ""}
            ${properties.last_message ? `<p>${escapeHtml(properties.last_message)}</p>` : ""}
            ${canEdit ? `<button type="button" data-open-monitor-links="${properties.id}">Editar enlace</button>` : ""}
        </section>`;
    }

    function renderLinks() {
        const layer = ensureLayer();
        if (!layer) return;
        layer.clearLayers();
        const features = state.snapshot?.links?.features || [];
        features.forEach((feature) => {
            if (!feature.geometry) return;
            const p = feature.properties || {};
            const color = statusColor(p);
            const style = {
                color,
                weight: Number(p.weight || 5),
                opacity: p.enabled === false ? 0.35 : 0.92,
                dashArray: p.link_type === "wireless" ? (p.dash_array || "12 10") : (p.dash_array || null),
                lineCap: "round",
                lineJoin: "round",
                interactive: true,
            };
            const polyline = L.geoJSON(feature, { style }).bindPopup(linkPopup(p));
            polyline.eachLayer((part) => {
                part.options.monitorLinkId = p.id;
                part.on("popupopen", () => installPopupActions());
                const element = part.getElement?.();
                if (element) element.classList.add("monitored-network-link", statusClass(p.status));
            });
            polyline.addTo(layer);
        });
    }

    function markerElementId(marker) {
        const html = marker?.getPopup?.()?.getContent?.();
        if (typeof html !== "string") return null;
        const match = html.match(/data-edit-element=["'](\d+)["']/) || html.match(/data-show-element-cables=["'](\d+)["']/);
        return match ? Number(match[1]) : null;
    }

    function decorateMapElements() {
        const map = mapApi()?.map;
        if (!map) return;
        const statuses = new Map((state.snapshot?.element_statuses || []).map((row) => [Number(row.element_id), row]));
        const visited = new Set();
        const visit = (layer) => {
            if (!layer || visited.has(layer)) return;
            visited.add(layer);
            if (layer instanceof L.Marker) {
                const id = markerElementId(layer);
                if (!id) return;
                const row = statuses.get(id);
                const root = layer.getElement?.()?.querySelector?.(".network-marker");
                if (!root) return;
                [...root.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => root.classList.remove(name));
                root.classList.toggle("monitoring-enabled", Boolean(row));
                if (row) {
                    root.classList.add(statusClass(row.status));
                    root.title = row.message || `Monitoramento: ${row.status}`;
                }
                return;
            }
            if (typeof layer.eachLayer === "function") layer.eachLayer(visit);
        };
        map.eachLayer(visit);
    }

    function decorateEquipmentAndPorts() {
        const equipmentRows = new Map((state.snapshot?.equipment_statuses || []).filter((row) => row.equipment_id).map((row) => [String(row.equipment_id), row]));
        const portRows = new Map((state.snapshot?.port_statuses || []).map((row) => [String(row.port_id), row]));
        equipmentRows.forEach((row, id) => {
            document.querySelectorAll(`[data-equipment-node="${CSS.escape(id)}"]`).forEach((node) => {
                [...node.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => node.classList.remove(name));
                node.classList.add("monitoring-enabled", statusClass(row.status));
                node.title = row.message || "";
            });
            document.querySelectorAll(`[data-edit-equipment="${CSS.escape(id)}"], [data-edit-container-equipment="${CSS.escape(id)}"]`).forEach((button) => {
                const article = button.closest("article");
                if (!article) return;
                [...article.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => article.classList.remove(name));
                article.classList.add("monitoring-equipment-row", statusClass(row.status));
            });
        });
        portRows.forEach((row, id) => {
            document.querySelectorAll(`[data-port-id="${CSS.escape(id)}"]`).forEach((port) => {
                [...port.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => port.classList.remove(name));
                port.classList.add("monitoring-port", statusClass(row.status));
                port.title = `${port.title || port.textContent.trim()} · SNMP ${String(row.status).toUpperCase()}`;
            });
        });
    }

    function scheduleDecorations() {
        window.requestAnimationFrame(() => {
            renderLinks();
            decorateMapElements();
            decorateEquipmentAndPorts();
            injectEquipmentButtons();
            injectCablePopupActions();
        });
    }

    async function refreshSnapshot({ silent = true } = {}) {
        const projectId = String(projectSelect.value || "");
        if (!projectId || state.busy || document.hidden) return;
        state.busy = true;
        try {
            state.projectId = projectId;
            state.snapshot = await request(`${apiRoot()}/projects/${encodeURIComponent(projectId)}/snapshot/`);
            scheduleDecorations();
        } catch (error) {
            if (!silent) notify(`Falha no monitoramento: ${error.message}`, true);
        } finally {
            state.busy = false;
        }
    }

    function ensureProfileDialog() {
        let dialog = document.getElementById("equipment-monitoring-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "equipment-monitoring-dialog";
        dialog.className = "editor-dialog monitoring-dialog";
        dialog.innerHTML = `<section>
            <header><div><h2>Monitoramento SNMP</h2><p data-monitor-subtitle></p></div><button type="button" data-close>×</button></header>
            <form data-profile-form>
                <div class="monitor-form-grid">
                    <label>IP de gerência<input name="management_ip" required></label>
                    <label>Porta SNMP<input name="port" type="number" min="1" max="65535" value="161"></label>
                    <label>Community<input name="community" type="password" autocomplete="new-password" placeholder="Deixe vazio para manter"></label>
                    <label>Coleta<select name="polling_interval_seconds"><option value="15">15 segundos</option><option value="30" selected>30 segundos</option><option value="60">60 segundos</option><option value="120">2 minutos</option></select></label>
                </div>
                <label class="monitor-check"><input name="enabled" type="checkbox" checked> Monitoramento ativo</label>
                <div class="monitor-actions"><button type="button" data-delete-profile class="danger">Remover monitoramento</button><button type="button" data-poll-now>Consultar agora</button><button type="submit" class="primary-button">Salvar perfil</button></div>
            </form>
            <section class="monitor-interface-section">
                <div class="monitor-section-heading"><div><h3>Portas detectadas e vínculo</h3><p>Associe o ifName/ifIndex do SNMP à porta criada no equipamento.</p></div><button type="button" data-refresh-profile>Atualizar</button></div>
                <div data-interface-list></div>
                <div class="monitor-actions"><button type="button" class="primary-button" data-save-bindings>Salvar vínculos</button></div>
            </section>
            <p data-monitor-status role="status"></p>
        </section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-refresh-profile]").onclick = () => loadEquipmentProfile(state.profileEquipmentId, true);
        dialog.querySelector("[data-poll-now]").onclick = () => pollEquipmentNow();
        dialog.querySelector("[data-delete-profile]").onclick = () => deleteEquipmentProfile();
        dialog.querySelector("[data-save-bindings]").onclick = () => saveBindings();
        dialog.querySelector("[data-profile-form]").onsubmit = (event) => saveEquipmentProfile(event);
        return dialog;
    }

    function setDialogStatus(text, error = false) {
        const target = document.querySelector("#equipment-monitoring-dialog [data-monitor-status]");
        if (target) {
            target.textContent = text || "";
            target.classList.toggle("error", error);
        }
    }

    function interfaceBindingMap(data) {
        const map = new Map();
        (data.bindings || []).forEach((binding) => {
            const key = binding.if_index != null ? `index:${binding.if_index}` : `name:${String(binding.if_name).toLowerCase()}`;
            map.set(key, binding);
        });
        return map;
    }

    function renderInterfaces(data) {
        const dialog = ensureProfileDialog();
        const list = dialog.querySelector("[data-interface-list]");
        const bindings = interfaceBindingMap(data);
        const internalPorts = data.ports || [];
        const interfaces = data.interfaces || [];
        if (!data.profile) {
            list.innerHTML = '<p class="monitor-empty">Salve o perfil e aguarde a primeira coleta para detectar as interfaces.</p>';
            dialog.querySelector("[data-save-bindings]").disabled = true;
            return;
        }
        dialog.querySelector("[data-save-bindings]").disabled = false;
        const rows = interfaces.length ? interfaces : (data.bindings || []).map((binding) => ({
            if_name: binding.if_name,
            if_index: binding.if_index,
            if_alias: "",
            status: binding.last_status,
            status_label: String(binding.last_status).toUpperCase(),
        }));
        list.innerHTML = rows.length ? rows.map((item) => {
            const key = item.if_index != null ? `index:${item.if_index}` : `name:${String(item.if_name).toLowerCase()}`;
            const binding = bindings.get(key) || {};
            return `<article class="monitor-interface-row ${statusClass(item.status)}" data-interface-row data-binding-id="${binding.id || ""}" data-if-name="${escapeHtml(item.if_name)}" data-if-index="${item.if_index ?? ""}">
                <div class="monitor-interface-name"><strong>${escapeHtml(item.if_name)}</strong><small>${item.if_index != null ? `ifIndex ${item.if_index}` : "sem ifIndex"}${item.if_alias ? ` · ${escapeHtml(item.if_alias)}` : ""}</small></div>
                <span class="monitor-badge ${statusClass(item.status)}">${escapeHtml(item.status_label || item.status)}</span>
                <label>Porta interna<select data-binding-port><option value="">Sem porta vinculada</option>${internalPorts.map((port) => `<option value="${port.id}" ${String(binding.equipment_port_id || "") === String(port.id) ? "selected" : ""}>${escapeHtml(port.label)} · ${escapeHtml(port.type_label)}</option>`).join("")}</select></label>
                <label>Função<select data-binding-role>${[["backbone","Backbone"],["uplink","Uplink"],["access","Acesso"],["wireless","Wireless/PTP"],["management","Gerência"],["other","Outro"]].map(([value,label]) => `<option value="${value}" ${(binding.role || "other") === value ? "selected" : ""}>${label}</option>`).join("")}</select></label>
                <label class="monitor-check"><input type="checkbox" data-binding-enabled ${binding.enabled !== false ? "checked" : ""}> Usar</label>
                <label class="monitor-check"><input type="checkbox" data-binding-alert ${binding.alert_enabled !== false ? "checked" : ""}> Alertar</label>
            </article>`;
        }).join("") : '<p class="monitor-empty">Nenhuma interface retornada pelo InfluxDB.</p>';
    }

    async function loadEquipmentProfile(equipmentId, show = false) {
        if (!equipmentId) return;
        state.profileEquipmentId = Number(equipmentId);
        const dialog = ensureProfileDialog();
        try {
            const data = await request(`${apiRoot()}/equipment/${equipmentId}/`);
            state.profileData = data;
            dialog.querySelector("[data-monitor-subtitle]").textContent = `${data.equipment.type_label} · ${data.equipment.name} · ${data.equipment.container}`;
            const form = dialog.querySelector("[data-profile-form]");
            form.elements.management_ip.value = data.profile?.management_ip || data.equipment.management_ip || "";
            form.elements.port.value = data.profile?.port || 161;
            form.elements.polling_interval_seconds.value = String(data.profile?.polling_interval_seconds || 30);
            form.elements.enabled.checked = data.profile?.enabled !== false;
            form.elements.community.value = "";
            dialog.querySelector("[data-delete-profile]").hidden = !data.profile;
            renderInterfaces(data);
            setDialogStatus(data.profile?.last_poll_message || "");
            if (show && !dialog.open) dialog.showModal();
        } catch (error) {
            setDialogStatus(error.message, true);
            if (show && !dialog.open) dialog.showModal();
        }
    }

    async function saveEquipmentProfile(event) {
        event.preventDefault();
        const dialog = ensureProfileDialog();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form));
        payload.enabled = form.elements.enabled.checked;
        payload.polling_interval_seconds = Number(payload.polling_interval_seconds || 30);
        payload.port = Number(payload.port || 161);
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/`, { method: "PUT", body: JSON.stringify(payload) });
            setDialogStatus("Perfil salvo. O Telegraf será recarregado em segundo plano.");
            await loadEquipmentProfile(state.profileEquipmentId, false);
        } catch (error) { setDialogStatus(error.message, true); }
    }

    async function saveBindings() {
        const rows = [...document.querySelectorAll("#equipment-monitoring-dialog [data-interface-row]")].map((row) => ({
            id: row.dataset.bindingId || null,
            if_name: row.dataset.ifName,
            if_index: row.dataset.ifIndex || null,
            equipment_port_id: row.querySelector("[data-binding-port]").value || null,
            role: row.querySelector("[data-binding-role]").value,
            enabled: row.querySelector("[data-binding-enabled]").checked,
            expected_up: true,
            alert_enabled: row.querySelector("[data-binding-alert]").checked,
            outage_persistence_seconds: 30,
            recovery_seconds: 30,
        }));
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/bindings/`, { method: "PUT", body: JSON.stringify({ bindings: rows }) });
            setDialogStatus("Vínculos de portas salvos.");
            await loadEquipmentProfile(state.profileEquipmentId, false);
            await refreshSnapshot({ silent: true });
        } catch (error) { setDialogStatus(error.message, true); }
    }

    async function pollEquipmentNow() {
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/poll/`, { method: "POST", body: "{}" });
            setDialogStatus("Consulta enfileirada. Atualize em alguns segundos.");
            window.setTimeout(() => loadEquipmentProfile(state.profileEquipmentId, false), 5000);
        } catch (error) { setDialogStatus(error.message, true); }
    }

    async function deleteEquipmentProfile() {
        if (!confirm("Remover o monitoramento SNMP deste equipamento?")) return;
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/`, { method: "DELETE", body: "{}" });
            setDialogStatus("Monitoramento removido.");
            await loadEquipmentProfile(state.profileEquipmentId, false);
            await refreshSnapshot({ silent: true });
        } catch (error) { setDialogStatus(error.message, true); }
    }

    function isOltArticle(article) {
        const text = String(article?.querySelector("small")?.textContent || article?.textContent || "").trim().toLowerCase();
        return /^olt\b/.test(text) || text.includes("· olt") || text.includes(" olt ·");
    }

    function injectEquipmentButtons() {
        if (!canEdit) return;
        document.querySelectorAll("[data-edit-equipment], [data-edit-container-equipment]").forEach((edit) => {
            const id = edit.dataset.editEquipment || edit.dataset.editContainerEquipment;
            const article = edit.closest("article");
            if (!id || !article || isOltArticle(article) || article.querySelector(`[data-equipment-monitoring="${CSS.escape(String(id))}"]`)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.equipmentMonitoring = String(id);
            button.className = "monitoring-button";
            button.textContent = "Monitoramento";
            button.title = "Configurar SNMP, portas e enlaces";
            button.onclick = (event) => {
                event.preventDefault(); event.stopPropagation();
                loadEquipmentProfile(id, true);
            };
            edit.insertAdjacentElement("beforebegin", button);
        });
    }

    function ensureLinkDialog() {
        let dialog = document.getElementById("monitor-link-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "monitor-link-dialog";
        dialog.className = "editor-dialog monitor-link-dialog";
        dialog.innerHTML = `<section>
            <header><div><h2>Enlaces monitorados</h2><p>Backbone por cabo e PTP wireless entre estruturas.</p></div><button type="button" data-close>×</button></header>
            <form data-link-form>
                <div class="monitor-form-grid">
                    <label>Tipo<select name="link_type"><option value="backbone">Backbone óptico</option><option value="fiber">Fibra óptica</option><option value="copper">Cobre</option><option value="wireless">PTP wireless</option></select></label>
                    <label>Nome<input name="name" placeholder="Cidade A ↔ Cidade B"></label>
                    <label>Cabo<select name="cable_id"><option value="">Sem cabo (wireless/cobre)</option></select></label>
                    <label>Cor normal<input name="normal_color" type="color" value="#38bdf8"></label>
                    <label>Porta origem<select name="source_binding_id" required></select></label>
                    <label>Porta destino<select name="destination_binding_id" required></select></label>
                    <label>Confirmar queda após<input name="outage_persistence_seconds" type="number" min="0" value="30"><small>segundos</small></label>
                    <label>Confirmar retorno após<input name="recovery_seconds" type="number" min="0" value="30"><small>segundos</small></label>
                </div>
                <label class="monitor-check"><input name="alert_enabled" type="checkbox" checked> Gerar alerta na central</label>
                <footer><button type="submit" class="primary-button">Criar enlace</button></footer>
            </form>
            <div data-link-list class="monitor-link-list"></div>
            <p data-link-status></p>
        </section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-link-form]").onsubmit = (event) => saveMonitoredLink(event);
        dialog.querySelector("select[name='link_type']").onchange = syncLinkTypeForm;
        return dialog;
    }

    function bindingOption(binding) {
        const status = String(binding.last_status || "unknown").toUpperCase();
        return `<option value="${binding.id}">${escapeHtml(binding.element)} · ${escapeHtml(binding.equipment)} · ${escapeHtml(binding.equipment_port || binding.if_name)} [${status}]</option>`;
    }

    function syncLinkTypeForm() {
        const dialog = ensureLinkDialog();
        const form = dialog.querySelector("[data-link-form]");
        const wireless = form.elements.link_type.value === "wireless";
        form.elements.cable_id.closest("label").hidden = wireless;
        if (wireless) {
            form.elements.cable_id.value = "";
            form.elements.normal_color.value = "#a855f7";
        }
    }

    function renderLinkList() {
        const dialog = ensureLinkDialog();
        const list = dialog.querySelector("[data-link-list]");
        const links = state.snapshot?.links?.features || [];
        list.innerHTML = links.length ? links.map((feature) => {
            const p = feature.properties;
            return `<article><span class="monitor-link-swatch" style="--monitor-color:${statusColor(p)}"></span><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.link_type_label)} · ${escapeHtml(p.status_label)}${p.cable ? ` · ${escapeHtml(p.cable)}` : ""}</small><p>${escapeHtml(p.last_message || "")}</p></div>${canEdit ? `<button type="button" class="danger" data-delete-monitor-link="${p.id}">Excluir</button>` : ""}</article>`;
        }).join("") : '<p class="monitor-empty">Nenhum enlace monitorado neste projeto.</p>';
        list.querySelectorAll("[data-delete-monitor-link]").forEach((button) => button.onclick = async () => {
            if (!confirm("Excluir este enlace monitorado? O cabo/equipamentos continuarão cadastrados.")) return;
            try {
                await request(`${apiRoot()}/links/${button.dataset.deleteMonitorLink}/`, { method: "DELETE", body: "{}" });
                await refreshSnapshot({ silent: false });
                populateLinkDialog();
            } catch (error) { dialog.querySelector("[data-link-status]").textContent = error.message; }
        });
    }

    function populateLinkDialog(focusLinkId = null) {
        const dialog = ensureLinkDialog();
        const form = dialog.querySelector("[data-link-form]");
        const bindings = state.snapshot?.bindings || [];
        const cables = state.snapshot?.cables || [];
        form.elements.source_binding_id.innerHTML = '<option value="">Escolha a porta de origem</option>' + bindings.map(bindingOption).join("");
        form.elements.destination_binding_id.innerHTML = '<option value="">Escolha a porta de destino</option>' + bindings.map(bindingOption).join("");
        form.elements.cable_id.innerHTML = '<option value="">Sem cabo (wireless/cobre)</option>' + cables.map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${escapeHtml(cable.type)}</option>`).join("");
        if (state.preselectedCableId) form.elements.cable_id.value = String(state.preselectedCableId);
        renderLinkList();
        syncLinkTypeForm();
        if (!dialog.open) dialog.showModal();
        if (focusLinkId) dialog.querySelector(`[data-delete-monitor-link="${CSS.escape(String(focusLinkId))}"]`)?.closest("article")?.scrollIntoView({ block: "center" });
    }

    async function openLinkDialog(focusLinkId = null) {
        if (!projectSelect.value) return notify("Selecione um projeto.", true);
        await refreshSnapshot({ silent: false });
        populateLinkDialog(focusLinkId);
    }

    async function saveMonitoredLink(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form));
        payload.project_id = projectSelect.value;
        payload.alert_enabled = form.elements.alert_enabled.checked;
        payload.outage_persistence_seconds = Number(payload.outage_persistence_seconds || 30);
        payload.recovery_seconds = Number(payload.recovery_seconds || 30);
        if (payload.link_type === "wireless") payload.cable_id = "";
        const status = document.querySelector("#monitor-link-dialog [data-link-status]");
        try {
            await request(`${apiRoot()}/links/`, { method: "POST", body: JSON.stringify(payload) });
            form.reset();
            form.elements.normal_color.value = "#38bdf8";
            form.elements.alert_enabled.checked = true;
            state.preselectedCableId = "";
            status.textContent = "Enlace criado e consulta SNMP enfileirada.";
            await refreshSnapshot({ silent: true });
            populateLinkDialog();
        } catch (error) { status.textContent = error.message; status.classList.add("error"); }
    }

    function installPopupActions() {
        document.querySelectorAll("[data-open-monitor-links]").forEach((button) => {
            if (button.dataset.monitorInstalled === "true") return;
            button.dataset.monitorInstalled = "true";
            button.onclick = () => openLinkDialog(button.dataset.openMonitorLinks);
        });
        injectCablePopupActions();
    }

    function injectCablePopupActions() {
        if (!canEdit) return;
        document.querySelectorAll(".leaflet-popup-content [data-edit-cable]").forEach((edit) => {
            const cableId = edit.dataset.editCable;
            const content = edit.closest(".leaflet-popup-content");
            if (!content || content.querySelector(`[data-monitor-cable="${CSS.escape(String(cableId))}"]`)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.monitorCable = cableId;
            button.textContent = "Monitorar enlace";
            button.onclick = async (event) => {
                event.preventDefault(); event.stopPropagation();
                state.preselectedCableId = cableId;
                await openLinkDialog();
            };
            edit.insertAdjacentElement("afterend", button);
        });
    }

    function ensureToolbarButton() {
        const toolbar = document.querySelector(".map-mode-control");
        if (!toolbar || toolbar.querySelector("[data-monitor-links-toggle]")) return;
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.monitorLinksToggle = "true";
        button.title = "Enlaces e monitoramento";
        button.setAttribute("aria-label", "Enlaces e monitoramento");
        button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M5 12h4m6 0h4M9 8l3 4-3 4m6-8-3 4 3 4"></path><circle cx="4" cy="12" r="2"></circle><circle cx="20" cy="12" r="2"></circle></svg>';
        button.onclick = () => openLinkDialog().catch((error) => notify(error.message, true));
        toolbar.appendChild(button);
        if (window.L?.DomEvent) L.DomEvent.disableClickPropagation(button);
    }

    const observer = new MutationObserver((mutations) => {
        const relevant = mutations.some((mutation) => [...mutation.addedNodes].some((node) => node.nodeType === 1 && (
            node.matches?.("article, .leaflet-popup-content, [data-equipment-node], [data-port-id]")
            || node.querySelector?.("[data-edit-equipment], [data-edit-container-equipment], .leaflet-popup-content, [data-equipment-node], [data-port-id]")
        )));
        if (relevant) window.requestAnimationFrame(() => { injectEquipmentButtons(); injectCablePopupActions(); decorateEquipmentAndPorts(); });
    });
    observer.observe(document.getElementById("map") || document.body, { childList: true, subtree: true });
    const containerDialog = document.getElementById("container-dialog");
    if (containerDialog) observer.observe(containerDialog, { childList: true, subtree: true });

    projectSelect.addEventListener("change", () => {
        state.projectId = String(projectSelect.value || "");
        state.snapshot = null;
        if (state.layer) state.layer.clearLayers();
        refreshSnapshot({ silent: true });
    });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshSnapshot({ silent: true }); });
    document.addEventListener("popupopen", installPopupActions);

    function start() {
        ensureToolbarButton();
        injectEquipmentButtons();
        refreshSnapshot({ silent: true });
        window.clearInterval(state.timer);
        state.timer = window.setInterval(() => refreshSnapshot({ silent: true }), 15000);
    }
    window.mapLinkMonitoring = {
        refresh: refreshSnapshot,
        openEquipment: (id) => loadEquipmentProfile(id, true),
        openLinks: openLinkDialog,
    };
    window.setTimeout(start, 250);
}());
