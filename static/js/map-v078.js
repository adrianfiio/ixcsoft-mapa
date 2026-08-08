(function (global) {
    "use strict";

    const VERSION = "0.78.0-r2";
    const state = {
        routeMode: "none", // none = filtro desligado/mapa completo; all = união; selected = seleção.
        selectedRoutes: new Set(),
        routeTopology: null,
        routeProjectId: "",
        routeFilterInstalled: false,
        syncTimer: 0,
        snmpTimer: 0,
        portDialog: null,
        snmpDialog: null,
        poleSubtype: "",
    };

    const qs = (selector, root = document) => root?.querySelector?.(selector) || null;
    const qsa = (selector, root = document) => [...(root?.querySelectorAll?.(selector) || [])];

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

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

    function notify(message, error = false) {
        global.networkMap?.notify?.(message, error);
    }

    function currentContainerId() {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        return Number(root?.dataset.elementId || dialog?.dataset.elementId || dialog?.dataset.containerId || 0);
    }

    function currentContainerKind() {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        return String(root?.dataset.containerKindV07542 || root?.dataset.v077Container || dialog?.dataset.containerType || "").toLowerCase();
    }

    function currentProjectId() {
        return String(qs("#project-select")?.value || "");
    }

    function columnsForPortCount(count) {
        const total = Math.max(1, Number(count || 1));
        if (total <= 16) return total;
        if (total === 24) return 12;
        if (total === 48) return 24;
        return Math.ceil(total / 2);
    }

    function decoratePortLayout(root = qs("#map-master-container")) {
        if (!root) return;
        qsa('.master-canvas-node[data-equipment-type="switch"], .master-canvas-node[data-equipment-type="router"]', root).forEach((node) => {
            const buttons = qsa(".v07552-switch-port[data-port-id], .master-node-port[data-port-id]", node);
            const unique = new Map(buttons.map((button) => [String(button.dataset.portId || Math.random()), button]));
            const count = unique.size;
            if (!count) return;
            const columns = columnsForPortCount(count);
            const layoutLabel = count <= 16
                ? `19" · 1 LINHA · ${count} PORTAS`
                : count === 24
                    ? '19" · 12 + 12 PORTAS'
                    : count === 48
                        ? '19" · 24 + 24 PORTAS'
                        : `19" · ${columns} PORTAS POR LINHA`;
            node.classList.add("v078-network-device");
            node.dataset.v078PortCount = String(count);
            node.dataset.v078LayoutLabel = layoutLabel;
            node.style.setProperty("--v078-port-columns", String(columns));
            node.style.setProperty("--v078-port-count", String(count));
            // O runtime físico v0.75.42 substitui Router/Switch por
            // .v07542-switch-grid. O r1 só reconhecia o renderer v0.75.52 do
            // Switch, então o Router permanecia preso no legado de 12 colunas.
            const holder = qs(
                ".v07552-switch-ports, .v07542-switch-grid, :scope > .master-node-ports",
                node,
            );
            if (holder) {
                holder.classList.add("v078-port-grid");
                holder.dataset.v078PortCount = String(count);
                holder.style.setProperty("--v078-port-columns", String(columns));
                holder.style.setProperty("--v078-port-count", String(count));
            }
        });
    }

    function updateLegacyRackPortHints(root = document) {
        qsa(".v07542-form-hint", root).forEach((hint) => {
            if (/linhas? de no máximo 12/i.test(String(hint.textContent || ""))) {
                hint.textContent = "Layout automático: até 16 em 1 linha; 24 = 12+12; 48 = 24+24.";
            }
        });
    }

    function removeFirewallFromCreateUi(root = document) {
        qsa('select option[value="firewall"]', root).forEach((option) => option.remove());
        qsa('[data-quick-add="firewall"]', root).forEach((button) => button.remove());
        qsa("button, [role='menuitem']", root).forEach((button) => {
            if (/^\s*Firewall(?:\s|$)/i.test(String(button.textContent || ""))) button.hidden = true;
        });
    }

    function decorateDioTower(root = qs("#map-master-container")) {
        if (!root) return;
        const isTower = currentContainerKind() === "tower";
        root.classList.toggle("v078-tower", isTower);
        root.classList.toggle("v078-rack", currentContainerKind() === "rack");
        qsa(".v07539-dio-cavity > header strong, .master-dio-tray-v07510 > header strong", root).forEach((title) => {
            title.textContent = String(title.textContent || "").replace(/CAVIDADE/gi, "BANDEJA");
        });
        qsa(".v078-tower-dio-organizer", root).forEach((item) => item.remove());
        if (!isTower) return;
        qsa('.master-canvas-node[data-equipment-type="dio"]', root).forEach((dio) => {
            const trays = qsa(".v07539-dio-cavity, .master-dio-tray-v07510", dio);
            trays.forEach((tray, index) => {
                if (index >= trays.length - 1) return;
                const organizer = document.createElement("div");
                organizer.className = "v078-tower-dio-organizer";
                organizer.innerHTML = "<i></i><span>ORGANIZADOR</span><i></i>";
                tray.insertAdjacentElement("afterend", organizer);
            });
        });
    }

    function decorateTowerEquipment(root = qs("#map-master-container")) {
        if (!root || currentContainerKind() !== "tower") return;
        qsa('.master-canvas-node[data-equipment-type="switch"], .master-canvas-node[data-equipment-type="router"], .master-canvas-node[data-equipment-type="ptp"], .master-canvas-node[data-equipment-type="access_point"]', root)
            .forEach((node) => node.classList.add("v078-tower-bottom-ports"));
        qsa('.master-canvas-node[data-equipment-type="onu"]', root).forEach((node) => node.classList.add("v078-compact-onu"));
    }

    function ensureEquipmentActionButtons(root = qs("#map-master-container")) {
        if (!root) return;
        qsa('.master-canvas-node[data-equipment-node][data-equipment-type="switch"], .master-canvas-node[data-equipment-node][data-equipment-type="router"], .master-canvas-node[data-equipment-node][data-equipment-type="ptp"], .master-canvas-node[data-equipment-node][data-equipment-type="access_point"]', root).forEach((node) => {
            const header = qs(":scope > header", node) || node;
            const id = Number(node.dataset.equipmentNode || node.dataset.equipmentId || 0);
            if (!id) return;
            if (!qs("[data-v078-ports]", header)) {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.v078Ports = String(id);
                button.className = "v078-header-action";
                button.textContent = "Portas";
                button.title = "Adicionar, remover e configurar portas";
                button.onclick = (event) => {
                    event.preventDefault(); event.stopPropagation();
                    openPortEditor(id).catch((error) => notify(error.message, true));
                };
                header.appendChild(button);
            }
            if (!qs("[data-v078-snmp]", header)) {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.v078Snmp = String(id);
                button.className = "v078-header-action v078-snmp-action";
                button.textContent = "SNMP";
                button.title = "Configurar e sincronizar monitoramento SNMP";
                button.onclick = (event) => {
                    event.preventDefault(); event.stopPropagation();
                    openSnmpEditor(id).catch((error) => notify(error.message, true));
                };
                header.appendChild(button);
            }
        });
    }

    function scheduleDecorate() {
        global.clearTimeout(state.syncTimer);
        state.syncTimer = global.setTimeout(() => {
            removeFirewallFromCreateUi();
            updateLegacyRackPortHints();
            decoratePortLayout();
            decorateDioTower();
            decorateTowerEquipment();
            ensureEquipmentActionButtons();
            enhanceRouteDrawer();
            modernizePoleDialog();
        }, 30);
    }

    // -----------------------------------------------------------------
    // Portas de Switch / Router / AP / PTP
    // -----------------------------------------------------------------
    function ensurePortDialog() {
        if (state.portDialog?.isConnected) return state.portDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-v078-port-dialog";
        dialog.className = "v078-dialog v078-port-dialog";
        dialog.innerHTML = `<form><header><div><small>PORTAS FÍSICAS</small><h2 data-title>Portas</h2><p data-subtitle></p></div><button type="button" data-close>×</button></header><div class="v078-dialog-body"><div data-port-list></div><button type="button" data-add-port>+ Adicionar porta</button><p data-status></p></div><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary">Salvar portas</button></footer></form>`;
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        qs("[data-cancel]", dialog).onclick = () => dialog.close();
        state.portDialog = dialog;
        return dialog;
    }

    function portRowHtml(port, data) {
        const radio = ["access_point", "ptp"].includes(data.equipment.type);
        const options = radio
            ? data.radio_port_types.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === port.port_type ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")
            : data.connector_types.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === port.connector_type ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("");
        const speed = radio ? "" : `<select data-speed>${data.speed_options.map((value) => `<option value="${value}" ${Number(port.speed_gbps) === Number(value) ? "selected" : ""}>${value} Gbps</option>`).join("")}</select>`;
        return `<div class="v078-port-row" data-port-row data-port-id="${port.id || ""}" data-linked="${port.linked ? "1" : "0"}"><b data-order></b><input data-label maxlength="100" value="${escapeHtml(port.label || "")}" placeholder="Nome da porta"><select data-port-kind>${options}</select>${speed}<span class="${port.linked ? "linked" : "free"}">${port.linked ? "Ligada" : "Livre"}</span><button type="button" data-remove ${port.linked ? "disabled title=\"Desligue a porta antes de remover\"" : ""}>×</button></div>`;
    }

    function renumberPortRows(dialog) {
        qsa("[data-port-row]", dialog).forEach((row, index) => { qs("[data-order]", row).textContent = String(index + 1); });
    }

    function bindPortRows(dialog) {
        qsa("[data-remove]", dialog).forEach((button) => {
            button.onclick = () => {
                if (button.disabled) return;
                button.closest("[data-port-row]")?.remove();
                renumberPortRows(dialog);
            };
        });
    }

    async function openPortEditor(equipmentId) {
        const elementId = currentContainerId();
        if (!elementId) throw new Error("Rack/Torre não identificado.");
        const data = await request(`/api/map/v078/elements/${elementId}/equipment/${equipmentId}/ports/`);
        const dialog = ensurePortDialog();
        dialog.dataset.elementId = String(elementId);
        dialog.dataset.equipmentId = String(equipmentId);
        dialog.dataset.equipmentType = data.equipment.type;
        dialog.dataset.maximum = String(data.limits.maximum);
        qs("[data-title]", dialog).textContent = `${data.equipment.name} · Portas`;
        qs("[data-subtitle]", dialog).textContent = data.equipment.type === "switch" || data.equipment.type === "router"
            ? "Até 16: uma linha · 24: 12+12 · 48: 24+24. O Rack reduz o tamanho visual sem empilhar fora desse padrão."
            : "Configure as interfaces físicas do rádio/AP. Portas ligadas precisam ser desligadas antes da remoção.";
        const list = qs("[data-port-list]", dialog);
        list.innerHTML = data.ports.map((port) => portRowHtml(port, data)).join("");
        bindPortRows(dialog); renumberPortRows(dialog);
        qs("[data-status]", dialog).textContent = "";
        qs("[data-status]", dialog).classList.remove("error");
        qs("[data-add-port]", dialog).onclick = () => {
            if (qsa("[data-port-row]", list).length >= data.limits.maximum) return notify(`Máximo de ${data.limits.maximum} portas.`, true);
            const radio = ["access_point", "ptp"].includes(data.equipment.type);
            const fresh = radio
                ? { id: "", label: `Porta ${qsa("[data-port-row]", list).length + 1}`, port_type: "rj45_1g", linked: false }
                : { id: "", label: `ether${qsa("[data-port-row]", list).length + 1}`, connector_type: "rj45", speed_gbps: 1, linked: false };
            list.insertAdjacentHTML("beforeend", portRowHtml(fresh, data));
            bindPortRows(dialog); renumberPortRows(dialog);
        };
        qs("form", dialog).onsubmit = async (event) => {
            event.preventDefault();
            const rows = qsa("[data-port-row]", dialog).map((row) => ({
                id: row.dataset.portId || null,
                label: qs("[data-label]", row).value,
                ...(["access_point", "ptp"].includes(data.equipment.type)
                    ? { port_type: qs("[data-port-kind]", row).value }
                    : { connector_type: qs("[data-port-kind]", row).value, speed_gbps: qs("[data-speed]", row).value }),
            }));
            const status = qs("[data-status]", dialog);
            try {
                status.textContent = "Salvando…";
                await request(`/api/map/v078/elements/${elementId}/equipment/${equipmentId}/ports/`, { method: "PUT", body: JSON.stringify({ ports: rows }) });
                dialog.close();
                await global.mapMasterSuite?.openContainerWorkspace?.(elementId);
                notify("Portas atualizadas.");
            } catch (error) { status.textContent = error.message; status.classList.add("error"); }
        };
        if (!dialog.open) dialog.showModal();
    }

    // -----------------------------------------------------------------
    // SNMP universal, usando a community padrão da empresa já existente.
    // -----------------------------------------------------------------
    function ensureSnmpDialog() {
        if (state.snmpDialog?.isConnected) return state.snmpDialog;
        const dialog = document.createElement("dialog");
        dialog.id = "map-v078-snmp-dialog";
        dialog.className = "v078-dialog v078-snmp-dialog";
        dialog.innerHTML = `<section><header><div><small>MONITORAMENTO SNMP</small><h2 data-title>SNMP</h2><p>Usa a community padrão cadastrada no painel da empresa. A sincronização pode levar de 2 a 5 minutos.</p></div><button type="button" data-close>×</button></header><div class="v078-dialog-body"><div class="v078-snmp-config"><label>IP de gerência<input data-ip placeholder="192.0.2.10"></label><label><input type="checkbox" data-enabled checked> Monitoramento ativo</label><button type="button" data-save-profile>Salvar SNMP</button><button type="button" data-sync>Sincronizar agora</button><a href="/painel/snmp/" target="_blank" rel="noopener">Community padrão da empresa</a></div><p data-status></p><div data-snmp-summary></div><div data-interface-list></div></div></section>`;
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => { global.clearTimeout(state.snmpTimer); dialog.close(); };
        state.snmpDialog = dialog;
        return dialog;
    }

    function renderSnmpPayload(dialog, data) {
        const profile = data.profile;
        qs("[data-ip]", dialog).value = profile?.management_ip || data.equipment?.management_ip || "";
        qs("[data-enabled]", dialog).checked = profile?.enabled !== false;
        qs("[data-snmp-summary]", dialog).innerHTML = profile
            ? `<div class="v078-snmp-summary"><span>${escapeHtml(profile.last_status_label || profile.last_status || "Sem dados")}</span><small>Última coleta: ${escapeHtml(profile.last_poll_at || "ainda não executada")}</small><small>${escapeHtml(profile.last_poll_message || "")}</small></div>`
            : '<div class="v078-snmp-summary"><span>SNMP ainda não configurado</span><small>Salve o perfil para usar a community padrão da empresa.</small></div>';
        const bindingsByInterface = new Map((data.bindings || []).map((item) => [String(item.if_index || item.if_name), item]));
        const portOptions = (data.ports || []).map((port) => `<option value="${port.id}">${escapeHtml(port.label)} · ${escapeHtml(port.type_label)}</option>`).join("");
        qs("[data-interface-list]", dialog).innerHTML = (data.interfaces || []).length
            ? `<div class="v078-interface-table">${data.interfaces.map((item) => {
                const binding = bindingsByInterface.get(String(item.if_index || item.if_name));
                return `<div data-interface-row data-if-name="${escapeHtml(item.if_name)}" data-if-index="${item.if_index || ""}" data-binding-id="${binding?.id || ""}"><b>${escapeHtml(item.if_name)}</b><span>${escapeHtml(item.if_alias || "")}</span><em class="status-${escapeHtml(item.status)}">${escapeHtml(item.status_label || item.status)}</em><select data-physical-port><option value="">Sem vínculo físico</option>${portOptions}</select><button type="button" data-bind>Vincular</button><button type="button" data-create-physical>Criar porta</button></div>`;
            }).join("")}</div>`
            : '<p class="v078-empty">Nenhuma interface coletada ainda. Use “Sincronizar agora” e aguarde a primeira coleta.</p>';
        qsa("[data-interface-row]", dialog).forEach((row) => {
            const binding = (data.bindings || []).find((item) => String(item.id) === String(row.dataset.bindingId));
            if (binding?.equipment_port_id) qs("[data-physical-port]", row).value = String(binding.equipment_port_id);
            qs("[data-bind]", row).onclick = async () => {
                const portId = qs("[data-physical-port]", row).value;
                if (!portId) return notify("Selecione a porta física.", true);
                const keepBinding = (item, equipmentPortId = item.equipment_port_id) => ({
                    id: item.id,
                    equipment_port_id: equipmentPortId,
                    label: item.label || item.equipment_port || item.if_name,
                    if_name: item.if_name,
                    if_index: item.if_index,
                    role: item.role || "access",
                    enabled: item.enabled !== false,
                    expected_up: item.expected_up !== false,
                    alert_enabled: item.alert_enabled !== false,
                    severity: item.severity || "high",
                    outage_persistence_seconds: item.outage_persistence_seconds ?? 30,
                    recovery_seconds: item.recovery_seconds ?? 30,
                });
                const other = (data.bindings || []).filter((item) => String(item.id) !== String(binding?.id || "")).map((item) => keepBinding(item));
                other.push(binding
                    ? keepBinding(binding, Number(portId))
                    : { equipment_port_id: Number(portId), label: row.dataset.ifName, if_name: row.dataset.ifName, if_index: Number(row.dataset.ifIndex || 0) || null, role: "access", enabled: true, expected_up: true, alert_enabled: true, severity: "high", outage_persistence_seconds: 30, recovery_seconds: 30 });
                await request(`/api/monitoring/equipment/${dialog.dataset.equipmentId}/bindings/`, { method: "PUT", body: JSON.stringify({ bindings: other }) });
                notify("Interface SNMP vinculada à porta física.");
                openSnmpEditor(Number(dialog.dataset.equipmentId), true);
            };
            qs("[data-create-physical]", row).onclick = async () => {
                const equipmentId = Number(dialog.dataset.equipmentId);
                const elementId = Number(dialog.dataset.elementId);
                const ports = await request(`/api/map/v078/elements/${elementId}/equipment/${equipmentId}/ports/`);
                const rows = ports.ports.map((port) => ({ id: port.id, label: port.label, ...(ports.equipment.type === "ptp" || ports.equipment.type === "access_point" ? { port_type: port.port_type } : { connector_type: port.connector_type, speed_gbps: port.speed_gbps }) }));
                if (["ptp", "access_point"].includes(ports.equipment.type)) rows.push({ id: null, label: row.dataset.ifName, port_type: "rj45_1g" });
                else rows.push({ id: null, label: row.dataset.ifName, connector_type: "rj45", speed_gbps: 1 });
                await request(`/api/map/v078/elements/${elementId}/equipment/${equipmentId}/ports/`, { method: "PUT", body: JSON.stringify({ ports: rows }) });
                notify("Porta física criada. Agora vincule a interface.");
                openSnmpEditor(equipmentId, true);
            };
        });
    }

    async function openSnmpEditor(equipmentId, keepOpen = false) {
        const dialog = ensureSnmpDialog();
        const elementId = currentContainerId() || Number(dialog.dataset.elementId || 0);
        dialog.dataset.equipmentId = String(equipmentId);
        dialog.dataset.elementId = String(elementId);
        const data = await request(`/api/monitoring/equipment/${equipmentId}/`);
        qs("[data-title]", dialog).textContent = `${data.equipment.name} · SNMP`;
        renderSnmpPayload(dialog, data);
        qs("[data-status]", dialog).textContent = "";
        qs("[data-status]", dialog).classList.remove("error");
        qs("[data-save-profile]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            try {
                status.classList.remove("error");
                status.textContent = "Salvando perfil SNMP…";
                await request(`/api/monitoring/equipment/${equipmentId}/`, {
                    method: "PUT",
                    body: JSON.stringify({ management_ip: qs("[data-ip]", dialog).value, enabled: qs("[data-enabled]", dialog).checked }),
                });
                status.textContent = "Perfil salvo usando a community padrão da empresa.";
                await openSnmpEditor(equipmentId, true);
            } catch (error) {
                status.innerHTML = /community SNMP/i.test(error.message)
                    ? `Nenhuma community padrão foi encontrada. <a href="/painel/snmp/" target="_blank">Cadastre no painel da empresa</a> e tente novamente.`
                    : escapeHtml(error.message);
                status.classList.add("error");
            }
        };
        qs("[data-sync]", dialog).onclick = async () => {
            const status = qs("[data-status]", dialog);
            try {
                status.classList.remove("error");
                status.textContent = "Sincronização solicitada. A descoberta/coleta pode levar de 2 a 5 minutos…";
                await request(`/api/monitoring/equipment/${equipmentId}/poll/`, { method: "POST", body: "{}" });
                const started = Date.now();
                const refresh = async () => {
                    if (!dialog.open || Number(dialog.dataset.equipmentId) !== Number(equipmentId)) return;
                    const fresh = await request(`/api/monitoring/equipment/${equipmentId}/`);
                    renderSnmpPayload(dialog, fresh);
                    if ((fresh.interfaces || []).length || Date.now() - started > 5 * 60 * 1000) {
                        status.textContent = (fresh.interfaces || []).length ? `${fresh.interfaces.length} interface(s) recebida(s).` : "A coleta ainda não retornou interfaces. Verifique conectividade/SNMP e logs do coletor.";
                        return;
                    }
                    state.snmpTimer = global.setTimeout(refresh, 8000);
                };
                global.clearTimeout(state.snmpTimer);
                state.snmpTimer = global.setTimeout(refresh, 8000);
            } catch (error) { status.textContent = error.message; status.classList.add("error"); }
        };
        if (!dialog.open) dialog.showModal();
        else if (!keepOpen) dialog.focus();
    }

    // -----------------------------------------------------------------
    // Rotas: Nenhuma = filtro desligado; Todas = união das rotas.
    // -----------------------------------------------------------------
    async function loadRouteTopology(force = false) {
        const projectId = currentProjectId();
        if (!projectId) { state.routeTopology = null; state.routeProjectId = ""; return null; }
        if (!force && state.routeTopology && state.routeProjectId === projectId) return state.routeTopology;
        state.routeTopology = await request(`/api/map/master/projects/${projectId}/routes/`);
        state.routeProjectId = projectId;
        return state.routeTopology;
    }

    function routeRows() { return state.routeTopology?.routes || []; }
    function activeRouteRows() {
        const rows = routeRows();
        if (state.routeMode === "all") return rows;
        if (state.routeMode === "selected") return rows.filter((row) => state.selectedRoutes.has(String(row.id)));
        return [];
    }

    function masterLayerEnabled(name) {
        const input = qs(`#map-master-route-drawer [data-master-filter="${name}"]`);
        return !input || input.checked;
    }

    function installRouteVisibility() {
        const api = global.mapV092;
        if (!api || state.routeFilterInstalled) return;
        // Espera a suíte master terminar a própria instalação; nossa camada é a
        // última e define a semântica acordada para Todas/Nenhuma sem perder os
        // checkboxes de camadas que já existiam na suíte.
        if (!api.masterSuiteInstalled) return;
        api.isElementVisible = (feature) => {
            const p = feature?.properties || feature || {};
            const id = Number(p.id || feature?.id || 0);
            const type = String(p.tipo || p.element_type || "");
            if (type === "cto" && !masterLayerEnabled("cto")) return false;
            if (type === "splice_box" && !masterLayerEnabled("spliceBoxes")) return false;
            if (["rack", "tower"].includes(type) && !masterLayerEnabled("containers")) return false;
            if (state.routeMode === "none") return true;
            if (type === "rack") return true;
            return activeRouteRows().some((route) => (route.element_ids || []).map(Number).includes(id));
        };
        api.isCableVisible = (feature) => {
            if (!masterLayerEnabled("cables")) return false;
            if (state.routeMode === "none") return true;
            const id = Number(feature?.properties?.id || feature?.id || 0);
            return activeRouteRows().some((route) => (route.cable_ids || []).map(Number).includes(id));
        };
        api.isRouteVisible = (feature) => {
            if (state.routeMode === "none") return true;
            const id = Number(feature?.properties?.id || feature?.id || 0);
            return activeRouteRows().some((route) => Number(route.id) === id);
        };
        api.areReservesVisible = () => masterLayerEnabled("reserves");
        api.v078RouteSemantics = true;
        state.routeFilterInstalled = true;
    }

    function reloadMap() {
        global.networkMap?.loadStructure?.().catch((error) => notify(error.message, true));
    }

    function routeExportButton(routeId, kind, title, svg) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "v078-route-export";
        button.dataset.routeExport = kind;
        button.title = title;
        button.innerHTML = svg;
        button.onclick = (event) => {
            event.preventDefault(); event.stopPropagation();
            const url = kind === "kmz"
                ? `/api/map/v078/routes/${routeId}/export.kmz`
                : `/api/map/v078/routes/${routeId}/diagram.html`;
            global.location.href = url;
        };
        return button;
    }

    function enhanceRouteDrawer() {
        const drawer = qs("#map-master-route-drawer");
        if (!drawer) return;
        qsa(".route-master-item", drawer).forEach((item) => {
            const checkbox = qs('input[type="checkbox"]', item);
            if (!checkbox) return;
            const routeId = checkbox.value;
            let actions = qs(".v078-route-exports", item);
            if (!actions) {
                actions = document.createElement("span");
                actions.className = "v078-route-exports";
                actions.appendChild(routeExportButton(routeId, "kmz", "Exportar rota em KMZ", '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3c3 3 4 6 4 9s-1 6-4 9c-3-3-4-6-4-9s1-6 4-9"></path></svg>'));
                actions.appendChild(routeExportButton(routeId, "html", "Exportar diagrama HTML offline", '<svg viewBox="0 0 24 24"><circle cx="6" cy="6" r="2"></circle><circle cx="18" cy="6" r="2"></circle><circle cx="12" cy="18" r="2"></circle><path d="M8 6h8M7 8l4 8m6-8-4 8"></path></svg>'));
                item.appendChild(actions);
            }
        });
    }

    function installRouteEvents() {
        document.addEventListener("click", (event) => {
            const all = event.target.closest("[data-route-all]");
            const none = event.target.closest("[data-route-none]");
            const only = event.target.closest("[data-only-route]");
            if (none) {
                state.routeMode = "none";
                state.selectedRoutes.clear();
                global.setTimeout(reloadMap, 0);
            } else if (all) {
                state.routeMode = "all";
                state.selectedRoutes.clear();
                loadRouteTopology(true).then(() => global.setTimeout(reloadMap, 0));
            } else if (only) {
                state.routeMode = "selected";
                state.selectedRoutes = new Set([String(only.dataset.onlyRoute)]);
                loadRouteTopology(true).then(() => global.setTimeout(reloadMap, 0));
            }
        }, true);
        document.addEventListener("change", (event) => {
            const input = event.target.closest?.("#map-master-route-drawer .route-master-item input[type='checkbox']");
            if (!input) return;
            state.routeMode = "selected";
            const checked = qsa("#map-master-route-drawer .route-master-item input[type='checkbox']:checked").map((item) => String(item.value));
            state.selectedRoutes = new Set(checked);
            loadRouteTopology(true).then(() => global.setTimeout(reloadMap, 0));
        });
        qs("#project-select")?.addEventListener("change", () => {
            state.routeMode = "none"; state.selectedRoutes.clear(); state.routeTopology = null; state.routeProjectId = "";
            global.setTimeout(() => loadRouteTopology(true).catch(() => {}), 50);
        });
    }

    // -----------------------------------------------------------------
    // Poste: preserva backend existente, adiciona CDO e padroniza visual.
    // -----------------------------------------------------------------
    function modernizePoleDialog() {
        const dialog = qs("#pole-dialog");
        const actions = qs(".pole-actions", dialog);
        if (!dialog || !actions) return;
        dialog.classList.add("v078-pole-dialog");
        actions.classList.add("v078-infrastructure-actions");
        if (!qs("#pole-add-cdo", actions)) {
            const button = document.createElement("button");
            button.id = "pole-add-cdo";
            button.className = "secondary-button";
            button.type = "button";
            button.textContent = "+ CDO";
            const reserve = qs("#pole-add-reserve", actions);
            actions.insertBefore(button, reserve || null);
            button.onclick = () => {
                state.poleSubtype = "cdo";
                qs("#pole-add-ceo")?.click();
                global.setTimeout(() => {
                    const form = qs("#pole-action-form");
                    if (!form) return;
                    let subtype = form.elements.element_subtype;
                    if (!subtype) {
                        subtype = document.createElement("input"); subtype.type = "hidden"; subtype.name = "element_subtype"; form.appendChild(subtype);
                    }
                    subtype.value = "cdo";
                    qs("#pole-action-title").textContent = "Instalar CDO no poste";
                }, 0);
            };
        }
        const labels = [["#pole-add-cto", "+ CTO"], ["#pole-add-ceo", "+ CEO"], ["#pole-add-reserve", "+ Reserva"]];
        labels.forEach(([selector, text]) => { const button = qs(selector); if (button) button.textContent = text; });
        const actionForm = qs("#pole-action-form");
        if (actionForm && !actionForm.elements.element_subtype) {
            const input = document.createElement("input"); input.type = "hidden"; input.name = "element_subtype"; actionForm.appendChild(input);
        }
        qs("#pole-add-ceo")?.addEventListener("click", () => { state.poleSubtype = ""; global.setTimeout(() => { if (actionForm?.elements.element_subtype) actionForm.elements.element_subtype.value = ""; }, 0); });
    }

    // -----------------------------------------------------------------
    // YAML: direciona os tipos tipados para o importador correto.
    // -----------------------------------------------------------------
    function installYamlGuard() {
        if (global.fetch?.v078YamlGuard) return;
        const original = global.fetch.bind(global);
        const wrapped = function (input, options = {}) {
            let url = typeof input === "string" ? input : input?.url || "";
            const method = String(options.method || input?.method || "GET").toUpperCase();
            if (method === "POST" && /\/api\/map\/elements\/\d+\/equipment\/import-yaml\/?$/.test(new URL(url, global.location.href).pathname)) {
                const match = new URL(url, global.location.href).pathname.match(/\/elements\/(\d+)\/equipment\/import-yaml/);
                const form = options.body instanceof FormData ? options.body : null;
                const type = String(form?.get("equipment_type") || "auto");
                if (["switch", "router", "access_point", "ptp"].includes(type)) {
                    url = `/api/map/v07551/elements/${match[1]}/equipment/import-yaml/`;
                }
            }
            return original(url, options);
        };
        wrapped.v078YamlGuard = true;
        wrapped.originalFetch = original;
        global.fetch = wrapped;
    }

    function inspectPortLayout(node) {
        if (!node) return null;
        const holder = qs(".v07552-switch-ports, .v07542-switch-grid, :scope > .master-node-ports", node);
        if (!holder) return null;
        const ports = qsa(".master-node-port[data-port-id], .v07552-switch-port[data-port-id]", holder);
        const rows = new Map();
        ports.forEach((port) => {
            const y = Math.round(port.getBoundingClientRect().top);
            rows.set(y, (rows.get(y) || 0) + 1);
        });
        return {
            type: node.dataset.equipmentType || "",
            count: ports.length,
            expectedColumns: columnsForPortCount(ports.length),
            portsPerRow: [...rows.values()],
            gridTemplateColumns: global.getComputedStyle(holder).gridTemplateColumns,
            label: node.dataset.v078LayoutLabel || "",
        };
    }

    global.mapV078 = Object.assign(global.mapV078 || {}, {
        version: VERSION,
        columnsForPortCount,
        inspectPortLayout,
    });

    function init() {
        document.body.dataset.mapV078 = VERSION;
        installYamlGuard();
        installRouteEvents();
        loadRouteTopology(true).catch(() => {});
        scheduleDecorate();
        global.setInterval(() => {
            installRouteVisibility();
            scheduleDecorate();
        }, 700);
        const container = qs("#container-dialog");
        if (container) new MutationObserver(scheduleDecorate).observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ["open", "data-container-type"] });
        document.addEventListener("map:container-rendered", scheduleDecorate);
        document.addEventListener("map:container-opening", scheduleDecorate);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})(window);
