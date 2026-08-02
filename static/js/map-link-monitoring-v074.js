(function () {
    "use strict";

    const projectSelect = document.getElementById("project-select");
    const canEdit = document.body.dataset.canEdit === "true";
    if (!projectSelect) return;

    const SUPPORTED_TYPES = new Set(["switch", "router", "firewall", "access_point", "ptp", "onu", "other"]);
    const REFRESH_MS = 5 * 60 * 1000;
    const state = {
        projectId: "",
        snapshot: null,
        snapshotSignature: "",
        layer: null,
        timer: null,
        requestController: null,
        busy: false,
        generation: 0,
        profileEquipmentId: null,
        profileData: null,
        preselectedCableId: "",
        lastFetchAt: 0,
    };

    function apiRoot() { return "/api/monitoring"; }
    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }
    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }
    function notify(message, error = false) {
        window.networkMap?.notify?.(message, error);
    }
    function statusClass(value) {
        return `monitor-status-${String(value || "no_data").replace(/_/g, "-")}`;
    }
    function statusColor(properties) {
        if (properties.status === "offline") return properties.down_color || "#ef4444";
        if (["degraded", "warning"].includes(properties.status)) return "#f59e0b";
        if (properties.status === "recovering") return "#22c55e";
        if (properties.status === "no_data") return "#64748b";
        return properties.normal_color || "#38bdf8";
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
    function mapApi() { return window.networkMap || null; }
    function ensureLayer() {
        const api = mapApi();
        if (!api?.map || !window.L) return null;
        if (!state.layer) state.layer = L.layerGroup().addTo(api.map);
        return state.layer;
    }
    function stopTimer() {
        window.clearInterval(state.timer);
        state.timer = null;
    }
    function startTimer() {
        stopTimer();
        if (!state.snapshot?.monitoring_enabled || document.hidden) return;
        const elapsed = Date.now() - Number(state.lastFetchAt || 0);
        const delay = Math.max(1000, REFRESH_MS - elapsed);
        state.timer = window.setTimeout(() => refreshSnapshot({ silent: true }), delay);
    }
    function snapshotSignature(snapshot) {
        return JSON.stringify({
            enabled: Boolean(snapshot?.monitoring_enabled),
            links: (snapshot?.links?.features || []).map((f) => [f.properties?.id, f.properties?.status, f.properties?.last_evaluated_at]),
            equipment: (snapshot?.equipment_statuses || []).map((r) => [r.equipment_id, r.status, r.message]),
            ports: (snapshot?.port_statuses || []).map((r) => [r.port_id, r.status, r.last_seen_at]),
        });
    }
    function clearDecorations() {
        state.layer?.clearLayers();
        document.querySelectorAll(".monitoring-enabled, .monitoring-equipment-row, .monitoring-port").forEach((node) => {
            node.classList.remove("monitoring-enabled", "monitoring-equipment-row", "monitoring-port");
            [...node.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => node.classList.remove(name));
            if (node.dataset.monitorBaseTitle != null) node.title = node.dataset.monitorBaseTitle;
        });
    }

    function linkPopup(properties) {
        const src = properties.source_binding;
        const dst = properties.destination_binding;
        return `<section class="monitor-link-popup">
            <strong>${escapeHtml(properties.name)}</strong>
            <span class="monitor-badge ${statusClass(properties.status)}">${escapeHtml(properties.status_label)}</span>
            <small>${escapeHtml(properties.link_type_label)}</small>
            <div>${escapeHtml(properties.source_element)}${src ? ` · ${escapeHtml(src.equipment_port || src.if_name)} (${escapeHtml(String(src.last_status || "").toUpperCase())})` : ""}</div>
            <div>↔ ${escapeHtml(properties.destination_element)}${dst ? ` · ${escapeHtml(dst.equipment_port || dst.if_name)} (${escapeHtml(String(dst.last_status || "").toUpperCase())})` : ""}</div>
            ${properties.cable ? `<div>Cabo: ${escapeHtml(properties.cable)}</div>` : ""}
            ${properties.last_message ? `<p>${escapeHtml(properties.last_message)}</p>` : ""}
            ${canEdit ? `<button type="button" data-open-monitor-links="${properties.id}">Editar enlace</button>` : ""}
        </section>`;
    }
    function renderLinks() {
        const layer = ensureLayer();
        if (!layer) return;
        layer.clearLayers();
        if (!state.snapshot?.monitoring_enabled) return;
        (state.snapshot?.links?.features || []).forEach((feature) => {
            if (!feature.geometry) return;
            const p = feature.properties || {};
            const polyline = L.geoJSON(feature, {
                style: {
                    color: statusColor(p),
                    weight: Number(p.weight || 5),
                    opacity: p.enabled === false ? 0.35 : 0.92,
                    dashArray: p.link_type === "wireless" ? (p.dash_array || "12 10") : (p.dash_array || null),
                    lineCap: "round",
                    lineJoin: "round",
                    interactive: true,
                },
            }).bindPopup(linkPopup(p));
            polyline.eachLayer((part) => {
                part.options.monitorLinkId = p.id;
                part.on("popupopen", installPopupActions);
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
        if (!map || !state.snapshot?.monitoring_enabled) return;
        const statuses = new Map((state.snapshot.element_statuses || []).map((row) => [Number(row.element_id), row]));
        const visited = new Set();
        const visit = (layer) => {
            if (!layer || visited.has(layer)) return;
            visited.add(layer);
            if (layer instanceof L.Marker) {
                const id = markerElementId(layer);
                const row = id ? statuses.get(id) : null;
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
        if (!state.snapshot?.monitoring_enabled) return;
        const equipmentRows = new Map((state.snapshot.equipment_statuses || []).filter((row) => row.equipment_id).map((row) => [String(row.equipment_id), row]));
        const portRows = new Map((state.snapshot.port_statuses || []).map((row) => [String(row.port_id), row]));
        equipmentRows.forEach((row, id) => {
            document.querySelectorAll(`[data-equipment-node="${CSS.escape(id)}"]`).forEach((node) => {
                [...node.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => node.classList.remove(name));
                node.classList.add("monitoring-enabled", statusClass(row.status));
                node.title = row.message || "";
            });
            document.querySelectorAll(`[data-equipment-id="${CSS.escape(id)}"]`).forEach((article) => {
                [...article.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => article.classList.remove(name));
                article.classList.add("monitoring-equipment-row", statusClass(row.status));
            });
        });
        portRows.forEach((row, id) => {
            document.querySelectorAll(`[data-port-id="${CSS.escape(id)}"]`).forEach((port) => {
                [...port.classList].filter((name) => name.startsWith("monitor-status-")).forEach((name) => port.classList.remove(name));
                port.classList.add("monitoring-port", statusClass(row.status));
                const base = port.dataset.monitorBaseTitle ?? (port.dataset.monitorBaseTitle = port.title || port.textContent.trim());
                port.title = `${base} · SNMP ${String(row.status).toUpperCase()}`;
            });
        });
    }
    function applySnapshot() {
        window.requestAnimationFrame(() => {
            if (!state.snapshot?.monitoring_enabled) clearDecorations();
            else {
                renderLinks();
                decorateMapElements();
                decorateEquipmentAndPorts();
            }
            injectEquipmentButtons();
            injectCablePopupActions();
        });
    }
    async function refreshSnapshot({ silent = true, force = false } = {}) {
        const projectId = String(projectSelect.value || "");
        if (!projectId || document.hidden) return;
        if (state.busy && !force) return;
        state.busy = true;
        const generation = ++state.generation;
        state.requestController?.abort();
        state.requestController = new AbortController();
        try {
            const snapshot = await request(`${apiRoot()}/projects/${encodeURIComponent(projectId)}/snapshot/`, {
                signal: state.requestController.signal,
            });
            if (generation !== state.generation || projectId !== String(projectSelect.value || "")) return;
            state.projectId = projectId;
            state.lastFetchAt = Date.now();
            const signature = snapshotSignature(snapshot);
            state.snapshot = snapshot;
            if (force || signature !== state.snapshotSignature) {
                state.snapshotSignature = signature;
                applySnapshot();
            }
            startTimer();
        } catch (error) {
            if (error.name !== "AbortError" && !silent) notify(`Falha no monitoramento: ${error.message}`, true);
            stopTimer();
        } finally {
            if (generation === state.generation) state.busy = false;
        }
    }

    function equipmentTypeFromArticle(article) {
        const explicit = String(article?.dataset?.equipmentType || "").toLowerCase();
        if (explicit) return explicit;
        const text = String(article?.querySelector("small")?.textContent || "").toLowerCase();
        const labels = { switch: "switch", roteador: "router", firewall: "firewall", "access point": "access_point", "rádio ptp": "ptp", onu: "onu" };
        return Object.entries(labels).find(([label]) => text.includes(label))?.[1] || "";
    }
    function injectEquipmentButtons(root = document) {
        if (!canEdit) return;
        root.querySelectorAll("[data-edit-equipment], [data-edit-container-equipment]").forEach((edit) => {
            const id = edit.dataset.editEquipment || edit.dataset.editContainerEquipment;
            const article = edit.closest("article");
            const type = equipmentTypeFromArticle(article);
            if (!id || !article || !SUPPORTED_TYPES.has(type)) return;
            if (article.querySelector(`[data-equipment-monitoring="${CSS.escape(String(id))}"]`)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.equipmentMonitoring = String(id);
            button.className = "monitoring-button";
            const configured = article.dataset.monitoringConfigured === "true";
            button.textContent = "SNMP";
            button.title = configured ? "Configurar monitoramento SNMP" : "Cadastrar este equipamento no monitoramento SNMP";
            button.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                loadEquipmentProfile(id, true);
            };
            edit.insertAdjacentElement("beforebegin", button);
        });
    }

    function ensureProfileDialog() {
        let dialog = document.getElementById("equipment-monitoring-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "equipment-monitoring-dialog";
        dialog.className = "editor-dialog monitoring-dialog monitoring-dialog-v074";
        dialog.innerHTML = `<section>
            <header><div><h2>Monitoramento SNMP</h2><p data-monitor-subtitle></p><small>O mapa exibe o último estado consolidado e consulta novamente somente a cada 5 minutos.</small></div><button type="button" data-close>×</button></header>
            <form data-profile-form>
                <div class="monitor-form-grid">
                    <label>IP de gerência<input name="management_ip" required></label>
                    <label>Porta SNMP<input name="port" type="number" min="1" max="65535" value="161"></label>
                    <label>Community<input name="community" type="password" autocomplete="new-password" placeholder="Obrigatória na ativação"></label>
                    <label>Coleta<select name="polling_interval_seconds"><option value="30" selected>30 segundos</option><option value="60">60 segundos</option><option value="120">2 minutos</option></select></label>
                </div>
                <label class="monitor-check"><input name="enabled" type="checkbox" checked> Monitoramento ativo</label>
                <div class="monitor-actions"><button type="button" data-delete-profile class="danger">Remover monitoramento</button><button type="button" data-poll-now>Consultar agora</button><button type="submit" class="primary-button">Salvar perfil</button></div>
            </form>
            <details class="monitor-interface-section">
                <summary>Portas detectadas e vínculos</summary>
                <div class="monitor-section-heading"><p>Associe ifName/ifIndex à porta física criada no equipamento.</p><button type="button" data-refresh-profile>Atualizar</button></div>
                <div data-interface-list></div>
                <div class="monitor-actions"><button type="button" class="primary-button" data-save-bindings>Salvar vínculos</button></div>
            </details>
            <p data-monitor-status role="status"></p>
        </section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-refresh-profile]").onclick = () => loadEquipmentProfile(state.profileEquipmentId, false);
        dialog.querySelector("[data-poll-now]").onclick = pollEquipmentNow;
        dialog.querySelector("[data-delete-profile]").onclick = deleteEquipmentProfile;
        dialog.querySelector("[data-save-bindings]").onclick = saveBindings;
        dialog.querySelector("[data-profile-form]").onsubmit = saveEquipmentProfile;
        return dialog;
    }
    function setDialogStatus(text, error = false) {
        const target = document.querySelector("#equipment-monitoring-dialog [data-monitor-status]");
        if (!target) return;
        target.textContent = text || "";
        target.classList.toggle("error", error);
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
        const ports = data.ports || [];
        const interfaces = data.interfaces || [];
        if (!data.profile) {
            list.innerHTML = '<p class="monitor-empty">Salve o perfil para iniciar a descoberta das interfaces.</p>';
            dialog.querySelector("[data-save-bindings]").disabled = true;
            return;
        }
        dialog.querySelector("[data-save-bindings]").disabled = false;
        const rows = interfaces.length ? interfaces : (data.bindings || []).map((binding) => ({ if_name: binding.if_name, if_index: binding.if_index, status: binding.last_status, status_label: String(binding.last_status).toUpperCase() }));
        list.innerHTML = rows.length ? rows.map((item) => {
            const key = item.if_index != null ? `index:${item.if_index}` : `name:${String(item.if_name).toLowerCase()}`;
            const binding = bindings.get(key) || {};
            return `<article class="monitor-interface-row ${statusClass(item.status)}" data-interface-row data-binding-id="${binding.id || ""}" data-if-name="${escapeHtml(item.if_name)}" data-if-index="${item.if_index ?? ""}">
                <div class="monitor-interface-name"><strong>${escapeHtml(item.if_name)}</strong><small>${item.if_index != null ? `ifIndex ${item.if_index}` : "sem ifIndex"}${item.if_alias ? ` · ${escapeHtml(item.if_alias)}` : ""}</small></div>
                <span class="monitor-badge ${statusClass(item.status)}">${escapeHtml(item.status_label || item.status)}</span>
                <label>Porta interna<select data-binding-port><option value="">Sem porta vinculada</option>${ports.map((port) => `<option value="${port.id}" ${String(binding.equipment_port_id || "") === String(port.id) ? "selected" : ""}>${escapeHtml(port.label)} · ${escapeHtml(port.type_label)}</option>`).join("")}</select></label>
                <label>Função<select data-binding-role>${[["backbone","Backbone"],["uplink","Uplink"],["access","Acesso"],["wireless","Wireless/PTP"],["management","Gerência"],["other","Outro"]].map(([value,label]) => `<option value="${value}" ${(binding.role || "other") === value ? "selected" : ""}>${label}</option>`).join("")}</select></label>
                <label class="monitor-check"><input type="checkbox" data-binding-enabled ${binding.enabled !== false ? "checked" : ""}> Usar</label>
                <label class="monitor-check"><input type="checkbox" data-binding-alert ${binding.alert_enabled !== false ? "checked" : ""}> Alertar</label>
            </article>`;
        }).join("") : '<p class="monitor-empty">Nenhuma interface SNMP encontrada.</p>';
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
            form.elements.community.required = !data.profile;
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
        const form = event.currentTarget;
        const payload = Object.fromEntries(new FormData(form));
        payload.enabled = form.elements.enabled.checked;
        payload.polling_interval_seconds = Number(payload.polling_interval_seconds || 30);
        payload.port = Number(payload.port || 161);
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/`, { method: "PUT", body: JSON.stringify(payload) });
            setDialogStatus("Perfil SNMP salvo. Somente agora este equipamento entra na coleta.");
            await loadEquipmentProfile(state.profileEquipmentId, false);
            await refreshSnapshot({ silent: true, force: true });
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
            await refreshSnapshot({ silent: true, force: true });
        } catch (error) { setDialogStatus(error.message, true); }
    }
    async function pollEquipmentNow() {
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/poll/`, { method: "POST", body: "{}" });
            setDialogStatus("Consulta enfileirada.");
            window.setTimeout(() => loadEquipmentProfile(state.profileEquipmentId, false), 5000);
        } catch (error) { setDialogStatus(error.message, true); }
    }
    async function deleteEquipmentProfile() {
        if (!confirm("Remover o monitoramento SNMP deste equipamento?")) return;
        try {
            await request(`${apiRoot()}/equipment/${state.profileEquipmentId}/`, { method: "DELETE", body: "{}" });
            setDialogStatus("Monitoramento removido. O equipamento voltou ao modo manual.");
            await loadEquipmentProfile(state.profileEquipmentId, false);
            await refreshSnapshot({ silent: true, force: true });
        } catch (error) { setDialogStatus(error.message, true); }
    }

    function ensureLinkDialog() {
        let dialog = document.getElementById("monitor-link-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "monitor-link-dialog";
        dialog.className = "editor-dialog monitor-link-dialog monitor-link-dialog-v074";
        dialog.innerHTML = `<section>
            <header><div><h2>Enlaces monitorados</h2><p>Somente portas de equipamentos SNMP configurados.</p></div><button type="button" data-close>×</button></header>
            <form data-link-form>
                <div class="monitor-form-grid">
                    <label>Tipo<select name="link_type"><option value="backbone">Backbone óptico</option><option value="fiber">Fibra óptica</option><option value="copper">Cobre</option><option value="wireless">PTP wireless</option></select></label>
                    <label>Nome<input name="name" placeholder="Cidade A ↔ Cidade B"></label>
                    <label>Cabo<select name="cable_id"><option value="">Sem cabo</option></select></label>
                    <label>Cor normal<input name="normal_color" type="color" value="#38bdf8"></label>
                    <label>Porta origem<select name="source_binding_id" required></select></label>
                    <label>Porta destino<select name="destination_binding_id" required></select></label>
                    <label>Confirmar queda após<input name="outage_persistence_seconds" type="number" min="0" value="30"></label>
                    <label>Confirmar retorno após<input name="recovery_seconds" type="number" min="0" value="30"></label>
                </div>
                <label class="monitor-check"><input name="alert_enabled" type="checkbox" checked> Gerar alerta</label>
                <footer><button type="submit" class="primary-button">Criar enlace</button></footer>
            </form>
            <div data-link-list class="monitor-link-list"></div><p data-link-status></p>
        </section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-link-form]").onsubmit = saveMonitoredLink;
        dialog.querySelector("select[name='link_type']").onchange = syncLinkTypeForm;
        return dialog;
    }
    function bindingOption(binding) {
        return `<option value="${binding.id}">${escapeHtml(binding.element)} · ${escapeHtml(binding.equipment)} · ${escapeHtml(binding.equipment_port || binding.if_name)} [${escapeHtml(String(binding.last_status || "unknown").toUpperCase())}]</option>`;
    }
    function syncLinkTypeForm() {
        const form = ensureLinkDialog().querySelector("[data-link-form]");
        const wireless = form.elements.link_type.value === "wireless";
        form.elements.cable_id.closest("label").hidden = wireless;
        if (wireless) { form.elements.cable_id.value = ""; form.elements.normal_color.value = "#a855f7"; }
    }
    function renderLinkList() {
        const dialog = ensureLinkDialog();
        const list = dialog.querySelector("[data-link-list]");
        const links = state.snapshot?.links?.features || [];
        list.innerHTML = links.length ? links.map((feature) => {
            const p = feature.properties || {};
            return `<article><span class="monitor-link-swatch" style="--monitor-color:${statusColor(p)}"></span><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.link_type_label)} · ${escapeHtml(p.status_label)}${p.cable ? ` · ${escapeHtml(p.cable)}` : ""}</small><p>${escapeHtml(p.last_message || "")}</p></div>${canEdit ? `<button type="button" class="danger" data-delete-monitor-link="${p.id}">Excluir</button>` : ""}</article>`;
        }).join("") : '<p class="monitor-empty">Nenhum enlace monitorado.</p>';
        list.querySelectorAll("[data-delete-monitor-link]").forEach((button) => button.onclick = async () => {
            if (!confirm("Excluir este enlace monitorado?")) return;
            try {
                await request(`${apiRoot()}/links/${button.dataset.deleteMonitorLink}/`, { method: "DELETE", body: "{}" });
                await refreshSnapshot({ silent: false, force: true });
                populateLinkDialog();
            } catch (error) { dialog.querySelector("[data-link-status]").textContent = error.message; }
        });
    }
    function populateLinkDialog(focusLinkId = null) {
        const dialog = ensureLinkDialog();
        const form = dialog.querySelector("[data-link-form]");
        const bindings = state.snapshot?.bindings || [];
        const cables = state.snapshot?.cables || [];
        form.elements.source_binding_id.innerHTML = '<option value="">Escolha a origem</option>' + bindings.map(bindingOption).join("");
        form.elements.destination_binding_id.innerHTML = '<option value="">Escolha o destino</option>' + bindings.map(bindingOption).join("");
        form.elements.cable_id.innerHTML = '<option value="">Sem cabo</option>' + cables.map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${escapeHtml(cable.type)}</option>`).join("");
        if (state.preselectedCableId) form.elements.cable_id.value = String(state.preselectedCableId);
        renderLinkList();
        syncLinkTypeForm();
        if (!dialog.open) dialog.showModal();
        if (focusLinkId) dialog.querySelector(`[data-delete-monitor-link="${CSS.escape(String(focusLinkId))}"]`)?.closest("article")?.scrollIntoView({ block: "center" });
    }
    async function openLinkDialog(focusLinkId = null) {
        if (!projectSelect.value) return notify("Selecione um projeto.", true);
        await refreshSnapshot({ silent: false, force: true });
        if (!state.snapshot?.monitoring_enabled) return notify("Cadastre ao menos dois equipamentos SNMP e vincule suas portas.", true);
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
            status.textContent = "Enlace criado.";
            await refreshSnapshot({ silent: true, force: true });
            populateLinkDialog();
        } catch (error) { status.textContent = error.message; status.classList.add("error"); }
    }
    function injectCablePopupActions() {
        if (!canEdit || !state.snapshot?.monitoring_enabled) return;
        document.querySelectorAll(".leaflet-popup-content [data-edit-cable]").forEach((edit) => {
            const cableId = edit.dataset.editCable;
            const content = edit.closest(".leaflet-popup-content");
            if (!content || content.querySelector(`[data-monitor-cable="${CSS.escape(String(cableId))}"]`)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.monitorCable = cableId;
            button.className = "monitoring-button";
            button.textContent = "Monitorar enlace";
            button.onclick = () => { state.preselectedCableId = cableId; openLinkDialog().catch((error) => notify(error.message, true)); };
            edit.insertAdjacentElement("afterend", button);
        });
    }
    function installPopupActions() {
        document.querySelectorAll("[data-open-monitor-links]").forEach((button) => {
            if (button.dataset.monitorInstalled === "true") return;
            button.dataset.monitorInstalled = "true";
            button.onclick = () => openLinkDialog(button.dataset.openMonitorLinks);
        });
        injectCablePopupActions();
    }
    function ensureToolbarButton() {
        if (!canEdit) return;
        const toolbar = document.querySelector(".map-mode-control");
        if (!toolbar || toolbar.querySelector("[data-monitor-links-toggle]")) return;
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.monitorLinksToggle = "true";
        button.title = "Enlaces monitorados";
        button.setAttribute("aria-label", "Enlaces monitorados");
        button.innerHTML = '<svg viewBox="0 0 24 24"><path d="M5 12h4m6 0h4M9 8l3 4-3 4m6-8-3 4 3 4"></path><circle cx="4" cy="12" r="2"></circle><circle cx="20" cy="12" r="2"></circle></svg>';
        button.onclick = () => openLinkDialog().catch((error) => notify(error.message, true));
        toolbar.appendChild(button);
    }

    projectSelect.addEventListener("change", () => {
        state.projectId = String(projectSelect.value || "");
        state.snapshot = null;
        state.snapshotSignature = "";
        state.generation += 1;
        state.requestController?.abort();
        stopTimer();
        clearDecorations();
        if (state.projectId) refreshSnapshot({ silent: true, force: true });
    });
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopTimer();
            return;
        }
        if (!projectSelect.value) return;
        if (Date.now() - Number(state.lastFetchAt || 0) >= REFRESH_MS) {
            refreshSnapshot({ silent: true, force: true });
        } else {
            startTimer();
        }
    });
    document.addEventListener("popupopen", installPopupActions);
    document.addEventListener("map:container-rendered", (event) => {
        injectEquipmentButtons(event.detail?.root || document);
        decorateEquipmentAndPorts();
    });

    function start() {
        ensureToolbarButton();
        injectEquipmentButtons();
        if (projectSelect.value) refreshSnapshot({ silent: true, force: true });
    }
    window.mapLinkMonitoring = {
        refresh: (options = {}) => refreshSnapshot({ silent: true, force: true, ...options }),
        openEquipment: (id) => loadEquipmentProfile(id, true),
        openLinks: openLinkDialog,
        stop: () => { stopTimer(); state.requestController?.abort(); clearDecorations(); },
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
    else start();
}());
