(function () {
    "use strict";

    const dialog = document.getElementById("container-dialog");
    if (!dialog) return;

    let initialized = false;
    let currentData = null;
    let currentTab = "summary";
    let selectedPort = null;
    let diagramZoom = 1;
    let refreshTimer = null;
    let resizeObserver = null;

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (item) return decodeURIComponent(item.split("=")[1]);
        return document.querySelector("[name='csrfmiddlewaretoken']")?.value
            || document.querySelector("meta[name='csrf-token']")?.content
            || "";
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    async function request(path, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(path, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        if (!response.ok) throw new Error(data.error || data.detail || `HTTP ${response.status}`);
        return data;
    }

    function containerId() {
        return dialog.dataset.elementId || "";
    }

    function message(text, isError = false) {
        const target = document.getElementById("container-extension-message");
        if (!target) return;
        target.textContent = text || "";
        target.classList.toggle("error", isError);
    }

    function panel(name) {
        return dialog.querySelector(`[data-container-panel="${name}"]`);
    }

    function setTab(name) {
        currentTab = name;
        dialog.querySelectorAll("[data-container-tab]").forEach((button) => {
            const active = button.dataset.containerTab === name;
            button.classList.toggle("active", active);
            button.setAttribute("aria-selected", String(active));
        });
        dialog.querySelectorAll("[data-container-panel]").forEach((item) => {
            item.hidden = item.dataset.containerPanel !== name;
        });
        if (name === "diagram") {
            renderDiagram();
            window.setTimeout(drawDiagramLinks, 80);
        }
    }

    function createPanel(name, label) {
        const section = document.createElement("section");
        section.className = "container-tab-panel-v09";
        section.dataset.containerPanel = name;
        section.setAttribute("aria-label", label);
        section.hidden = name !== currentTab;
        return section;
    }

    function ensureOnuFields() {
        const form = document.getElementById("container-equipment-form");
        if (!form || document.getElementById("container-onu-fields")) return;
        const footer = form.querySelector("footer");
        const fieldset = document.createElement("fieldset");
        fieldset.id = "container-onu-fields";
        fieldset.className = "cto-fields";
        fieldset.hidden = true;
        fieldset.innerHTML = `
            <legend>Estrutura da ONU / ONT</legend>
            <label>Quantidade de portas LAN
                <select name="onu_lan_count">
                    <option value="1">1 LAN Gigabit</option>
                    <option value="2">2 LAN Gigabit</option>
                    <option value="4" selected>4 LAN Gigabit</option>
                    <option value="8">8 LAN Gigabit</option>
                </select>
            </label>
            <p class="field-help">A porta PON óptica SC/APC é criada automaticamente. Você só informa a quantidade de LANs.</p>`;
        form.insertBefore(fieldset, footer);

        const select = form.elements.equipment_type;
        const sync = () => {
            const isOnu = select.value === "onu";
            fieldset.hidden = !isOnu;
            const management = document.getElementById("container-management-fields");
            const provisioning = document.getElementById("container-provisioning-field");
            const snmp = document.getElementById("container-snmp-fields");
            const model = document.getElementById("container-model-field");
            const serial = document.getElementById("container-serial-field");
            if (isOnu) {
                if (management) management.hidden = false;
                if (provisioning) provisioning.hidden = true;
                if (snmp) snmp.hidden = true;
                if (model) model.hidden = false;
                if (serial) serial.hidden = false;
                form.elements.name.placeholder = "Ex.: ONU TORRE 01";
            }
            if (select.value === "dio" && form.elements.connector_type && !form.elements.connector_type.value) {
                form.elements.connector_type.value = "sc_apc";
            }
        };
        select.addEventListener("change", () => window.setTimeout(sync, 0));
        sync();
    }

    function ensureShell() {
        if (initialized) return;
        const root = dialog.querySelector(":scope > section");
        const header = root?.querySelector(":scope > header");
        const workspace = root?.querySelector(":scope > .container-workspace");
        const optical = document.getElementById("container-optical-links");
        const extensionGrid = root?.querySelector(":scope > .container-extension-grid");
        const equipmentForm = document.getElementById("container-equipment-form");
        const status = document.getElementById("container-extension-message");
        if (!root || !header || !workspace || !optical || !extensionGrid || !equipmentForm) return;

        const nav = document.createElement("nav");
        nav.className = "container-tabs-v09";
        nav.setAttribute("role", "tablist");
        const tabs = [
            ["summary", "Resumo"],
            ["equipment", "Equipamentos"],
            ["diagram", "Diagrama interno"],
            ["fibers", "Fibras / terminações"],
            ["yaml", "YAML / modelos"],
        ];
        nav.innerHTML = tabs.map(([name, label]) => `<button type="button" role="tab" data-container-tab="${name}">${label}</button>`).join("");
        header.insertAdjacentElement("afterend", nav);

        const panels = document.createElement("div");
        panels.className = "container-tab-panels-v09";
        const summary = createPanel("summary", "Resumo da estrutura");
        summary.id = "container-summary-v09";
        const equipment = createPanel("equipment", "Equipamentos cadastrados");
        const diagram = createPanel("diagram", "Diagrama interno");
        const fibers = createPanel("fibers", "Fibras e terminações");
        const yaml = createPanel("yaml", "YAML e modelos de equipamento");

        const topologyHeading = workspace.querySelector(".topology-heading h3");
        if (topologyHeading) topologyHeading.textContent = "Equipamentos cadastrados";
        const topologyHelp = workspace.querySelector(".field-help");
        if (topologyHelp) topologyHelp.textContent = "Cadastre, edite e adicione portas. As ligações visuais ficam na aba Diagrama interno.";
        workspace.querySelector(".topology-heading .unifilar-zoom")?.setAttribute("hidden", "hidden");
        equipment.append(workspace, equipmentForm);

        diagram.innerHTML = `
            <header class="container-diagram-header-v09">
                <div><h3>Diagrama interno da estrutura</h3><p>Selecione uma porta e depois outra para criar a ligação. Fibra, cobre ou wireless são escolhidos pela compatibilidade.</p></div>
                <div class="container-diagram-tools-v09">
                    <button type="button" data-diagram-zoom="out">−</button>
                    <output id="container-diagram-zoom-v09">100%</output>
                    <button type="button" data-diagram-zoom="in">+</button>
                    <button type="button" data-diagram-organize>Organizar</button>
                    <button type="button" data-diagram-fit>Ajustar</button>
                    <button type="button" data-diagram-fullscreen>Tela cheia</button>
                </div>
            </header>
            <div class="container-diagram-status-v09" id="container-diagram-status-v09">Clique em uma porta livre para iniciar uma ligação.</div>
            <div class="container-diagram-scroll-v09" id="container-diagram-scroll-v09">
                <svg id="container-diagram-links-v09" class="container-diagram-links-v09"></svg>
                <div id="container-diagram-nodes-v09" class="container-diagram-nodes-v09"></div>
            </div>`;

        const cards = [...extensionGrid.querySelectorAll(":scope > .container-extension-card")];
        const yamlCard = cards.find((card) => card.querySelector("#container-device-type-form"));
        const fiberCard = cards.find((card) => card.querySelector("#container-fiber-termination-form"));
        fibers.append(optical);
        if (fiberCard) fibers.append(fiberCard);
        if (yamlCard) yaml.append(yamlCard);
        extensionGrid.remove();

        panels.append(summary, equipment, diagram, fibers, yaml);
        root.insertBefore(panels, status || null);
        if (status) status.classList.add("container-global-message-v09");

        nav.querySelectorAll("[data-container-tab]").forEach((button) => {
            button.addEventListener("click", () => setTab(button.dataset.containerTab));
        });
        diagram.querySelector('[data-diagram-zoom="out"]').onclick = () => setDiagramZoom(diagramZoom - 0.1);
        diagram.querySelector('[data-diagram-zoom="in"]').onclick = () => setDiagramZoom(diagramZoom + 0.1);
        diagram.querySelector("[data-diagram-organize]").onclick = () => { diagramZoom = 1; renderDiagram(); };
        diagram.querySelector("[data-diagram-fit]").onclick = fitDiagram;
        diagram.querySelector("[data-diagram-fullscreen]").onclick = toggleDiagramFullscreen;

        ensureOnuFields();
        setTab("summary");
        initialized = true;

        const list = document.getElementById("container-equipment-list");
        if (list) {
            const listObserver = new MutationObserver(() => {
                // manageContainer() recria artigos diretos. O agrupamento v0.9.2
                // move esses artigos para <details>; não deve disparar novo fetch.
                if ([...list.children].some((node) => node.tagName === "ARTICLE")) {
                    scheduleRefresh(60);
                }
            });
            listObserver.observe(list, { childList: true, subtree: true });
        }
    }

    function summaryCard(label, value, hint = "") {
        return `<article><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${hint ? `<small>${escapeHtml(hint)}</small>` : ""}</article>`;
    }

    function renderSummary() {
        const target = document.getElementById("container-summary-v09");
        if (!target || !currentData) return;
        const equipment = currentData.equipment || [];
        const ports = equipment.flatMap((item) => item.ports || []);
        const cables = currentData.cables || [];
        const opticalTerminations = ports.filter((port) => port.fusion_used).length;
        const internalLinks = currentData.links || [];
        target.innerHTML = `
            <div class="container-summary-grid-v09">
                ${summaryCard("Equipamentos", equipment.length)}
                ${summaryCard("Portas cadastradas", ports.length)}
                ${summaryCard("Cabos que chegam", cables.length)}
                ${summaryCard("Terminações ópticas", opticalTerminations)}
                ${summaryCard("Ligações internas", internalLinks.length)}
            </div>
            <div class="container-summary-list-v09">
                <h3>Conteúdo da estrutura</h3>
                ${equipment.length ? equipment.map((item) => `<div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.type_label)} · ${(item.ports || []).length} porta(s)${item.management_ip ? ` · ${escapeHtml(item.management_ip)}` : ""}</span></div>`).join("") : '<p>Nenhum equipamento cadastrado.</p>'}
            </div>`;
    }

    const equipmentGroupOrder = ["olt", "dio", "switch", "ptp", "access_point", "onu", "other"];
    const equipmentGroupLabels = {
        olt: "OLTs",
        dio: "DIOs",
        switch: "Switches",
        ptp: "Rádios PTP",
        access_point: "Access points",
        onu: "ONUs / ONTs",
        other: "Outros equipamentos",
    };

    function organizeEquipmentList() {
        const list = document.getElementById("container-equipment-list");
        if (!list || !currentData) return;
        const directArticles = [...list.children].filter((node) => node.tagName === "ARTICLE");
        if (!directArticles.length) return;
        const groups = new Map();
        directArticles.forEach((article, index) => {
            const item = (currentData.equipment || [])[index];
            const type = item?.type || "other";
            if (!groups.has(type)) groups.set(type, []);
            groups.get(type).push(article);
            article.classList.add("container-equipment-compact-v092");
            article.querySelectorAll(".equipment-port-grid, .equipment-card-list").forEach((node) => {
                node.classList.add("container-equipment-details-v092");
            });
        });
        list.innerHTML = "";
        equipmentGroupOrder.forEach((type, order) => {
            const items = groups.get(type) || [];
            if (!items.length) return;
            const details = document.createElement("details");
            details.className = "container-equipment-group-v092";
            details.dataset.equipmentGroup = type;
            if (order === 0) details.open = true;
            details.innerHTML = `<summary><span>${escapeHtml(equipmentGroupLabels[type] || type)}</span><b>${items.length}</b></summary><div class="container-equipment-group-list-v092"></div>`;
            const body = details.querySelector(".container-equipment-group-list-v092");
            items.forEach((article) => body.appendChild(article));
            list.appendChild(details);
        });
    }

    function portClass(port) {
        const optical = ["dio", "pon", "sfp_1g", "sfp_plus_10g"].includes(port.type);
        return `${optical ? "optical" : port.type === "wireless" ? "wireless" : "copper"} ${port.used ? "used" : ""} ${port.fusion_used ? "fusion-used" : ""}`;
    }

    function renderDiagram() {
        const nodes = document.getElementById("container-diagram-nodes-v09");
        if (!nodes || !currentData) return;
        const equipmentPriority = {
            olt: 10,
            dio: 20,
            switch: 30,
            onu: 40,
            ptp: 50,
            access_point: 60,
            other: 70,
        };
        const equipmentColumn = {
            olt: 1,
            dio: 1,
            switch: 2,
            other: 2,
            onu: 3,
            ptp: 3,
            access_point: 3,
        };
        const equipment = [...(currentData.equipment || [])].sort((a, b) => (
            (equipmentPriority[a.type] || 99) - (equipmentPriority[b.type] || 99)
            || String(a.name).localeCompare(String(b.name), "pt-BR")
        ));
        nodes.innerHTML = equipment.length ? equipment.map((item, index) => `
            <article class="container-diagram-node-v09" data-equipment-id="${item.id}" data-equipment-type="${item.type}" style="--node-order:${index};--node-column:${equipmentColumn[item.type] || 2}">
                <header><div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.type_label)}</span></div><small>${(item.ports || []).length} porta(s)</small></header>
                <div class="container-diagram-ports-v09">
                    ${(item.ports || []).map((port) => `<button type="button" class="container-diagram-port-v09 ${portClass(port)}" data-diagram-port="${port.id}" data-equipment="${item.id}" data-port-type="${port.type}" data-link-id="${port.link_id || ""}" title="${escapeHtml(port.label)}"><span>${escapeHtml(port.label)}</span><i aria-hidden="true"></i></button>`).join("") || '<span class="container-empty-v09">Sem portas. Use + Portas na aba Equipamentos.</span>'}
                </div>
            </article>`).join("") : '<p class="container-empty-v09">Cadastre equipamentos na aba Equipamentos.</p>';
        nodes.querySelectorAll("[data-diagram-port]").forEach((button) => button.addEventListener("click", () => selectDiagramPort(button)));
        applyDiagramZoom();
        window.setTimeout(drawDiagramLinks, 60);
    }

    function findPort(portId) {
        for (const equipment of currentData?.equipment || []) {
            const port = (equipment.ports || []).find((item) => String(item.id) === String(portId));
            if (port) return { ...port, equipment };
        }
        return null;
    }

    function compatibleLinkType(first, second) {
        const optical = new Set(["dio", "pon", "sfp_1g", "sfp_plus_10g"]);
        const copper = new Set(["rj45_100m", "rj45_1g"]);
        if (optical.has(first.type) && optical.has(second.type)) return "fiber";
        if (copper.has(first.type) && copper.has(second.type)) return "copper";
        if (first.type === "wireless" && second.type === "wireless") return "wireless";
        return null;
    }

    function diagramStatus(text, error = false) {
        const target = document.getElementById("container-diagram-status-v09");
        if (!target) return;
        target.textContent = text;
        target.classList.toggle("error", error);
    }

    async function selectDiagramPort(button) {
        const port = findPort(button.dataset.diagramPort);
        if (!port) return;
        if (button.dataset.linkId) {
            if (!confirm(`Desligar a ligação da porta ${port.label}?`)) return;
            try {
                await request(`/api/map/elements/${containerId()}/equipment-links/${button.dataset.linkId}/`, { method: "DELETE" });
                selectedPort = null;
                await refresh();
                diagramStatus("Ligação removida.");
            } catch (error) { diagramStatus(error.message, true); }
            return;
        }
        if (!selectedPort) {
            selectedPort = port;
            dialog.querySelectorAll(".container-diagram-port-v09.selected").forEach((node) => node.classList.remove("selected"));
            button.classList.add("selected");
            diagramStatus(`${port.equipment.name} · ${port.label} selecionada. Clique na porta de destino.`);
            return;
        }
        if (String(selectedPort.equipment.id) === String(port.equipment.id)) {
            selectedPort = null;
            renderDiagram();
            diagramStatus("Escolha portas de equipamentos diferentes.", true);
            return;
        }
        const linkType = compatibleLinkType(selectedPort, port);
        if (!linkType) {
            selectedPort = null;
            renderDiagram();
            diagramStatus("Portas incompatíveis. Use óptica com óptica, RJ45 com RJ45 ou wireless com wireless.", true);
            return;
        }
        try {
            diagramStatus("Criando ligação...");
            await request(`/api/map/elements/${containerId()}/equipment-links/`, {
                method: "POST",
                body: JSON.stringify({
                    source_port_id: selectedPort.id,
                    destination_port_id: port.id,
                    link_type: linkType,
                }),
            });
            selectedPort = null;
            await refresh();
            diagramStatus("Ligação criada. Clique em outra porta para continuar.");
        } catch (error) {
            selectedPort = null;
            renderDiagram();
            diagramStatus(error.message, true);
        }
    }

    function drawDiagramLinks() {
        const scroll = document.getElementById("container-diagram-scroll-v09");
        const nodes = document.getElementById("container-diagram-nodes-v09");
        const svg = document.getElementById("container-diagram-links-v09");
        if (!scroll || !nodes || !svg || !currentData) return;
        const box = scroll.getBoundingClientRect();
        const width = Math.max(scroll.scrollWidth, scroll.clientWidth);
        const height = Math.max(scroll.scrollHeight, scroll.clientHeight);
        svg.setAttribute("width", width);
        svg.setAttribute("height", height);
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.innerHTML = "";
        (currentData.links || []).forEach((link, index) => {
            const source = nodes.querySelector(`[data-diagram-port="${link.source_port_id}"]`);
            const destination = nodes.querySelector(`[data-diagram-port="${link.destination_port_id}"]`);
            if (!source || !destination) return;
            const a = source.getBoundingClientRect();
            const b = destination.getBoundingClientRect();
            const sourceCard = source.closest(".container-diagram-node-v09")?.getBoundingClientRect();
            const destinationCard = destination.closest(".container-diagram-node-v09")?.getBoundingClientRect();
            if (!sourceCard || !destinationCard) return;
            const destinationAtRight = destinationCard.left >= sourceCard.left;
            const sameColumn = Math.abs(destinationCard.left - sourceCard.left) < Math.min(sourceCard.width, destinationCard.width) * 0.55;
            const x1 = (destinationAtRight ? a.right : a.left) - box.left + scroll.scrollLeft;
            const y1 = a.top - box.top + scroll.scrollTop + a.height / 2;
            const x2 = (destinationAtRight ? b.left : b.right) - box.left + scroll.scrollLeft;
            const y2 = b.top - box.top + scroll.scrollTop + b.height / 2;
            let d;
            if (sameColumn) {
                const outside = Math.max(sourceCard.right, destinationCard.right) - box.left + scroll.scrollLeft + 34 + (index % 5) * 10;
                const sx = sourceCard.right - box.left + scroll.scrollLeft;
                const dx = destinationCard.right - box.left + scroll.scrollLeft;
                d = `M${x1},${y1} H${sx + 12} H${outside} V${y2} H${dx + 12} H${x2}`;
            } else {
                const middleX = (x1 + x2) / 2 + ((index % 5) - 2) * 10;
                d = `M${x1},${y1} H${middleX} V${y2} H${x2}`;
            }
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", d);
            path.setAttribute("class", `container-diagram-link-v09 ${link.link_type || "fiber"}`);
            path.setAttribute("data-link-id", link.id || "");
            svg.appendChild(path);
            [ [x1, y1], [x2, y2] ].forEach(([cx, cy]) => {
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", cx);
                dot.setAttribute("cy", cy);
                dot.setAttribute("r", 4);
                dot.setAttribute("class", `container-diagram-link-end-v092 ${link.link_type || "fiber"}`);
                svg.appendChild(dot);
            });
        });
    }

    function setDiagramZoom(value) {
        diagramZoom = Math.max(0.5, Math.min(1.5, Number(value)));
        applyDiagramZoom();
    }

    function applyDiagramZoom() {
        const nodes = document.getElementById("container-diagram-nodes-v09");
        const output = document.getElementById("container-diagram-zoom-v09");
        if (nodes) nodes.style.transform = `scale(${diagramZoom})`;
        if (output) output.value = `${Math.round(diagramZoom * 100)}%`;
        window.setTimeout(drawDiagramLinks, 50);
    }

    function fitDiagram() {
        const scroll = document.getElementById("container-diagram-scroll-v09");
        const nodes = document.getElementById("container-diagram-nodes-v09");
        if (!scroll || !nodes) return;
        const widthRatio = (scroll.clientWidth - 40) / Math.max(nodes.scrollWidth, 1);
        const heightRatio = (scroll.clientHeight - 40) / Math.max(nodes.scrollHeight, 1);
        setDiagramZoom(Math.min(1, widthRatio, heightRatio));
    }

    function syncDiagramFullscreenButton() {
        const panelEl = panel("diagram");
        const button = panelEl?.querySelector("[data-diagram-fullscreen]");
        const active = document.fullscreenElement === panelEl || panelEl?.classList.contains("is-fullscreen");
        if (button) {
            button.textContent = active ? "Desmaximizar" : "Tela cheia";
            button.setAttribute("aria-pressed", String(Boolean(active)));
        }
        window.setTimeout(() => {
            fitDiagram();
            drawDiagramLinks();
        }, 80);
    }

    async function toggleDiagramFullscreen() {
        const panelEl = panel("diagram");
        if (!panelEl) return;
        try {
            if (document.fullscreenElement === panelEl) {
                await document.exitFullscreen();
            } else if (panelEl.requestFullscreen) {
                await panelEl.requestFullscreen();
            } else {
                panelEl.classList.toggle("is-fullscreen");
            }
        } catch (_error) {
            panelEl.classList.toggle("is-fullscreen");
        }
        syncDiagramFullscreenButton();
    }

    async function refresh() {
        const id = containerId();
        if (!id || !dialog.open) return;
        try {
            currentData = await request(`/api/map/elements/${id}/equipment/`);
            renderSummary();
            organizeEquipmentList();
            if (currentTab === "diagram") renderDiagram();
        } catch (error) {
            message(error.message, true);
        }
    }

    function scheduleRefresh(delay = 100) {
        window.clearTimeout(refreshTimer);
        refreshTimer = window.setTimeout(refresh, delay);
    }

    const observer = new MutationObserver(() => {
        if (!dialog.open) return;
        ensureShell();
        ensureOnuFields();
        scheduleRefresh(100);
    });
    observer.observe(dialog, { attributes: true, attributeFilter: ["open", "data-element-id"] });

    dialog.addEventListener("close", () => {
        selectedPort = null;
        currentData = null;
        currentTab = "summary";
    });
    document.addEventListener("fullscreenchange", syncDiagramFullscreenButton);
    window.addEventListener("resize", () => window.setTimeout(drawDiagramLinks, 80));

    resizeObserver = new ResizeObserver(() => {
        if (dialog.open && currentTab === "diagram") drawDiagramLinks();
    });
    resizeObserver.observe(dialog);

    ensureShell();
    window.containerStructureV09 = { refresh, setTab, organizeEquipmentList };
}());
