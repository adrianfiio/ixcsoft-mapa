(function () {
    "use strict";

    const VERSION = "0.72.0";
    const body = document.body;
    const projectSelect = document.getElementById("project-select");
    const canEdit = body.dataset.canEdit === "true";
    const state = {
        map: null,
        ruler: {
            active: false,
            points: [],
            group: null,
            line: null,
            markers: [],
            clickHandler: null,
        },
        area: {
            active: false,
            points: [],
            group: null,
            polygon: null,
            clickHandler: null,
        },
        popupTimer: null,
        toolbarSyncTimer: null,
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function csrfToken() {
        const row = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
        if (row) return decodeURIComponent(row.split("=")[1]);
        return qs("#map-csrf-token [name='csrfmiddlewaretoken']")?.value || "";
    }

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    async function request(path, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(path, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const details = data.detail || data.error || Object.values(data.errors || {}).flat().join(" ");
            throw new Error(details || `HTTP ${response.status}`);
        }
        return data;
    }

    function notify(message, error = false) {
        if (window.networkMap?.notify) window.networkMap.notify(message, error);
        let toast = qs("#map-ui-toast-v072");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "map-ui-toast-v072";
            toast.className = "map-ui-toast-v072";
            document.body.appendChild(toast);
        }
        toast.textContent = message || "";
        toast.classList.toggle("error", error);
        toast.classList.add("show");
        window.clearTimeout(toast._timer);
        toast._timer = window.setTimeout(() => toast.classList.remove("show"), 3800);
    }

    function svg(name) {
        const icons = {
            home: '<svg viewBox="0 0 24 24"><path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z"></path></svg>',
            search: '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m15.5 15.5 5 5"></path></svg>',
            equipment: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="7" rx="2"></rect><rect x="3" y="14" width="18" height="7" rx="2"></rect><path d="M7 6.5h.01M7 17.5h.01"></path></svg>',
            import: '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4"></path><path d="M4 17v3h16v-3"></path></svg>',
            alerts: '<svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M10 21h4"></path></svg>',
            settings: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3V9.6h.1A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.1A1.7 1.7 0 0 0 15.4 4a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.17.36.48.66.84.84.35.17.74.26 1.13.26H21v4h-.1a1.7 1.7 0 0 0-1.5.9z"></path></svg>',
            logout: '<svg viewBox="0 0 24 24"><path d="M10 17l5-5-5-5"></path><path d="M15 12H3"></path><path d="M14 3h7v18h-7"></path></svg>',
            select: '<svg viewBox="0 0 24 24"><path d="m4 3 7.5 17 2.2-6.3L20 11.5z"></path></svg>',
            cto: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="14" rx="3"></rect><path d="M8 8h8M8 12h8M8 18v3m8-3v3"></path></svg>',
            box: '<svg viewBox="0 0 24 24"><path d="M7 3h10l4 5v8l-4 5H7l-4-5V8z"></path><path d="M8 9h8M8 13h8M8 17h8"></path></svg>',
            pole: '<svg viewBox="0 0 24 24"><path d="M4 7h16M12 3v18M7 21h10M8 7l4 5 4-5"></path></svg>',
            cable: '<svg viewBox="0 0 24 24"><path d="M3 17c5 0 5-10 10-10s4 7 8 7"></path><circle cx="3" cy="17" r="2"></circle><circle cx="21" cy="14" r="2"></circle></svg>',
            ruler: '<svg viewBox="0 0 24 24"><path d="m4 17 13-13 3 3L7 20H4z"></path><path d="m13 8 3 3m-6 0 3 3m-6 0 3 3"></path></svg>',
            area: '<svg viewBox="0 0 24 24"><path d="m4 17 4-11 10-2 2 12-8 5z"></path><circle cx="4" cy="17" r="1.5"></circle><circle cx="8" cy="6" r="1.5"></circle><circle cx="18" cy="4" r="1.5"></circle><circle cx="20" cy="16" r="1.5"></circle><circle cx="12" cy="21" r="1.5"></circle></svg>',
            more: '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"></circle><circle cx="12" cy="12" r="1.5"></circle><circle cx="19" cy="12" r="1.5"></circle></svg>',
            route: '<svg viewBox="0 0 24 24"><circle cx="5" cy="18" r="2"></circle><circle cx="19" cy="6" r="2"></circle><path d="M7 18h4a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3"></path></svg>',
            links: '<svg viewBox="0 0 24 24"><circle cx="4" cy="12" r="2"></circle><circle cx="20" cy="12" r="2"></circle><path d="M6 12h12M9 8l3 4-3 4m6-8-3 4 3 4"></path></svg>',
            theme: '<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"></path></svg>',
        };
        return icons[name] || icons.more;
    }

    function buildSidebar() {
        const sidebar = qs("#map-sidebar");
        const content = qs(".sidebar-content", sidebar);
        if (!sidebar || !content || qs("#map-nav-v072", sidebar)) return;
        body.classList.add("map-ui-v072");
        sidebar.classList.remove("collapsed", "master-minimized");
        sidebar.classList.add("map-sidebar-v072");

        const brand = qs(".map-brand", content);
        const back = qs(".back-link", content);
        if (back) back.hidden = true;

        const nav = document.createElement("nav");
        nav.id = "map-nav-v072";
        nav.className = "map-nav-v072";
        const dashboardUrl = body.dataset.urlDashboard || "/";
        const equipmentUrl = body.dataset.urlEquipment || "#";
        const alertsUrl = body.dataset.urlAlerts || "";
        const accountUrl = body.dataset.urlAccount || "/painel/";
        nav.innerHTML = `
            <a href="${escapeHtml(dashboardUrl)}">${svg("home")}<span>Início</span></a>
            <button type="button" data-v072-search>${svg("search")}<span>Buscar no mapa</span><kbd>Ctrl K</kbd></button>
            <a href="${escapeHtml(equipmentUrl)}">${svg("equipment")}<span>Equipamentos</span></a>
            <button type="button" data-v072-import>${svg("import")}<span>Importar KMZ/KML</span></button>
            ${alertsUrl ? `<a href="${escapeHtml(alertsUrl)}">${svg("alerts")}<span>Alertas</span></a>` : ""}
            <a href="${escapeHtml(accountUrl)}">${svg("settings")}<span>Configurações</span></a>
            <button type="button" data-v072-theme>${svg("theme")}<span>Alternar tema</span></button>`;
        if (brand) brand.insertAdjacentElement("afterend", nav);
        else content.prepend(nav);

        nav.querySelector("[data-v072-search]").onclick = () => qs("#map-search-toggle")?.click();
        nav.querySelector("[data-v072-import]").onclick = () => qs("#import-button")?.click();
        nav.querySelector("[data-v072-theme]").onclick = () => toggleTheme();

        const sections = qsa(":scope > .editor-section", content);
        sections.forEach((section) => {
            const title = qs(".section-heading span", section)?.textContent.trim().toLowerCase() || "";
            if (title === "camadas") section.classList.add("v072-hidden-section", "v072-layer-section");
            if (title === "adicionar ao mapa") section.classList.add("v072-hidden-section", "v072-tools-section");
            if (title === "resumo") section.classList.add("v072-hidden-section", "v072-summary-section");
            if (title === "projeto de rede") section.classList.add("v072-project-section");
        });

        const company = document.createElement("div");
        company.className = "map-company-card-v072";
        const logo = qs(".map-brand img", content);
        const companyName = body.dataset.companyName || logo?.alt || "AFService Map";
        const companyMode = body.dataset.companyMode || "Plataforma de rede";
        const mapVersion = body.dataset.mapVersion || "";
        company.innerHTML = `
            <div class="map-company-card-main">
                ${logo ? `<img src="${escapeHtml(logo.src)}" alt="">` : ""}
                <span><strong>${escapeHtml(companyName)}</strong><small>${escapeHtml(companyMode)}</small></span>
                ${mapVersion ? `<small class="map-version-menu-v072" title="Versão instalada do MAPA">v${escapeHtml(mapVersion)}</small>` : ""}
            </div>
            <form method="post" action="${escapeHtml(body.dataset.urlLogout || "/sair/")}">
                <input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(csrfToken())}">
                <button type="submit">${svg("logout")}<span>Sair</span></button>
            </form>`;
        content.appendChild(company);

        const oldToggle = qs("#collapse-sidebar", sidebar);
        if (oldToggle) {
            const toggle = oldToggle.cloneNode(true);
            oldToggle.replaceWith(toggle);
            toggle.textContent = "‹";
            toggle.title = "Recolher menu";
            toggle.onclick = () => {
                const collapsed = sidebar.classList.toggle("v072-collapsed");
                toggle.textContent = collapsed ? "›" : "‹";
                toggle.title = collapsed ? "Abrir menu" : "Recolher menu";
                localStorage.setItem("mapSidebarV072Collapsed", collapsed ? "1" : "0");
                window.setTimeout(() => state.map?.invalidateSize?.(), 180);
            };
            const saved = localStorage.getItem("mapSidebarV072Collapsed") === "1";
            sidebar.classList.toggle("v072-collapsed", saved);
            toggle.textContent = saved ? "›" : "‹";
        }
        qs(".collapsed-tools", sidebar)?.remove();
    }

    function setTheme(theme) {
        const light = theme === "light";
        body.classList.toggle("map-theme-light-v072", light);
        localStorage.setItem("mapThemeV072", light ? "light" : "dark");
    }

    function toggleTheme() {
        setTheme(body.classList.contains("map-theme-light-v072") ? "dark" : "light");
    }

    function toolClick(name) {
        stopRuler();
        stopArea();
        const button = qs(`[data-tool="${CSS.escape(name)}"]`) || qs(`[data-quick-tool="${CSS.escape(name)}"]`);
        if (!button) return notify(`Ferramenta ${name} não disponível.`, true);
        if (!projectSelect?.value) return notify("Selecione um projeto primeiro.", true);
        qs('[data-map-mode="edit"]')?.click();
        button.click();
    }

    function buildTopToolbar() {
        const mapRoot = qs("#map");
        if (!mapRoot || qs("#map-toolbar-v072")) return;
        const toolbar = document.createElement("nav");
        toolbar.id = "map-toolbar-v072";
        toolbar.className = "map-toolbar-v072";
        toolbar.innerHTML = `
            <button type="button" data-v072-tool="select" title="Selecionar">${svg("select")}<span>Selecionar</span></button>
            ${canEdit ? `<button type="button" data-v072-tool="cto" title="Adicionar CTO">${svg("cto")}<span>CTO</span></button>
            <div class="map-tool-menu-v072"><button type="button" data-menu-toggle="boxes">${svg("box")}<span>Caixa</span><b>⌄</b></button><div data-menu="boxes"><button type="button" data-v072-tool="splice_box">CEO</button><button type="button" data-v072-tool="cdo">CDO</button></div></div>
            <button type="button" data-v072-tool="pole">${svg("pole")}<span>Poste</span></button>
            <button type="button" data-v072-tool="cable">${svg("cable")}<span>Cabo</span></button>
            <button type="button" data-v072-ruler>${svg("ruler")}<span>Régua</span></button>
            <button type="button" data-v072-area>${svg("area")}<span>Área</span></button>
            <div class="map-tool-menu-v072"><button type="button" data-menu-toggle="more">${svg("more")}<span>Mais</span><b>⌄</b></button><div data-menu="more"><button type="button" data-v072-tool="cpd">CPD/POP</button><button type="button" data-v072-tool="rack">Rack</button><button type="button" data-v072-tool="tower">Torre</button></div></div>` : ""}
            <button type="button" data-v072-routes hidden>${svg("route")}<span>Rotas</span></button>
            <button type="button" data-v072-links hidden>${svg("links")}<span>Enlaces</span></button>`;
        mapRoot.appendChild(toolbar);

        qsa("[data-v072-tool]", toolbar).forEach((button) => {
            button.onclick = () => {
                if (button.dataset.v072Tool === "select") {
                    stopRuler();
                    stopArea();
                    qs('[data-map-mode="view"]')?.click();
                    state.map?.closePopup?.();
                    return;
                }
                toolClick(button.dataset.v072Tool);
                closeToolMenus();
            };
        });
        qs("[data-v072-ruler]", toolbar)?.addEventListener("click", () => startRuler());
        qs("[data-v072-area]", toolbar)?.addEventListener("click", () => startArea());
        qsa("[data-menu-toggle]", toolbar).forEach((button) => {
            button.onclick = (event) => {
                event.stopPropagation();
                const menu = qs(`[data-menu="${CSS.escape(button.dataset.menuToggle)}"]`, toolbar);
                const open = menu?.classList.toggle("open");
                qsa("[data-menu]", toolbar).forEach((item) => { if (item !== menu) item.classList.remove("open"); });
                button.setAttribute("aria-expanded", open ? "true" : "false");
            };
        });
        qs("[data-v072-routes]", toolbar).onclick = () => qs("[data-master-routes]")?.click();
        qs("[data-v072-links]", toolbar).onclick = () => qs("[data-monitor-links-toggle]")?.click();
        document.addEventListener("click", closeToolMenus);
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(toolbar);
            L.DomEvent.disableScrollPropagation(toolbar);
        }
        syncToolbarAvailability();
    }

    function closeToolMenus() {
        qsa("#map-toolbar-v072 [data-menu]").forEach((menu) => menu.classList.remove("open"));
    }

    function syncToolbarAvailability() {
        const routeSource = qs("[data-master-routes]");
        const routeTarget = qs("[data-v072-routes]");
        const linkSource = qs("[data-monitor-links-toggle]");
        const linkTarget = qs("[data-v072-links]");
        if (routeTarget) routeTarget.hidden = !routeSource || routeSource.hidden;
        if (linkTarget) linkTarget.hidden = !linkSource || !projectSelect?.value;
        window.clearTimeout(state.toolbarSyncTimer);
        state.toolbarSyncTimer = window.setTimeout(syncToolbarAvailability, 700);
    }

    function ensureRulerPanel() {
        let panel = qs("#map-ruler-panel-v072");
        if (panel) return panel;
        panel = document.createElement("section");
        panel.id = "map-ruler-panel-v072";
        panel.className = "map-ruler-panel-v072";
        panel.hidden = true;
        panel.innerHTML = `
            <div><strong>Régua</strong><span data-ruler-distance>0 m</span></div>
            <p>Clique no mapa para marcar o trajeto.</p>
            <footer><button type="button" data-ruler-undo>Desfazer ponto</button><button type="button" data-ruler-cancel>Cancelar</button><button type="button" data-ruler-finish class="primary">Concluir</button></footer>`;
        qs("#map")?.appendChild(panel);
        panel.querySelector("[data-ruler-undo]").onclick = () => undoRulerPoint();
        panel.querySelector("[data-ruler-cancel]").onclick = () => stopRuler();
        panel.querySelector("[data-ruler-finish]").onclick = () => finishRuler();
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(panel);
            L.DomEvent.disableScrollPropagation(panel);
        }
        return panel;
    }

    function ensureRulerLayer() {
        if (!state.map || !window.L) return null;
        if (!state.ruler.group) state.ruler.group = L.layerGroup().addTo(state.map);
        return state.ruler.group;
    }

    function startRuler() {
        if (!projectSelect?.value) return notify("Selecione um projeto antes de medir.", true);
        qs('[data-map-mode="view"]')?.click();
        stopRuler(false);
        state.ruler.active = true;
        state.ruler.points = [];
        ensureRulerLayer()?.clearLayers();
        const panel = ensureRulerPanel();
        panel.hidden = false;
        panel.classList.add("active");
        state.map.getContainer().classList.add("ruler-active-v072");
        state.ruler.clickHandler = (event) => addRulerPoint(event.latlng);
        state.map.on("click", state.ruler.clickHandler);
        updateRuler();
        notify("Régua ativa: clique no mapa para desenhar o trajeto.");
    }

    function addRulerPoint(latlng) {
        if (!state.ruler.active) return;
        state.ruler.points.push(latlng);
        updateRuler();
    }

    function undoRulerPoint() {
        state.ruler.points.pop();
        updateRuler();
    }

    function distanceMeters() {
        let total = 0;
        for (let index = 1; index < state.ruler.points.length; index += 1) {
            total += state.map.distance(state.ruler.points[index - 1], state.ruler.points[index]);
        }
        return total;
    }

    function formatDistance(meters) {
        if (meters >= 1000) return `${(meters / 1000).toFixed(meters >= 10000 ? 1 : 2)} km`;
        return `${meters.toFixed(meters >= 100 ? 0 : 1)} m`;
    }

    function updateRuler() {
        const group = ensureRulerLayer();
        if (!group) return;
        group.clearLayers();
        state.ruler.markers = state.ruler.points.map((point, index) => L.circleMarker(point, {
            radius: 5,
            weight: 2,
            color: "#e2e8f0",
            fillColor: "#22d3ee",
            fillOpacity: 1,
            interactive: false,
        }).bindTooltip(String(index + 1), { permanent: true, direction: "top", className: "ruler-index-v072" }).addTo(group));
        if (state.ruler.points.length >= 2) {
            state.ruler.line = L.polyline(state.ruler.points, {
                color: "#22d3ee",
                weight: 4,
                opacity: .95,
                dashArray: "10 8",
                lineCap: "round",
            }).addTo(group);
        } else state.ruler.line = null;
        const distance = distanceMeters();
        const target = qs("#map-ruler-panel-v072 [data-ruler-distance]");
        if (target) target.textContent = formatDistance(distance);
        const finish = qs("#map-ruler-panel-v072 [data-ruler-finish]");
        if (finish) finish.disabled = state.ruler.points.length < 2;
    }

    function stopRuler(clear = true) {
        if (state.map && state.ruler.clickHandler) state.map.off("click", state.ruler.clickHandler);
        state.ruler.clickHandler = null;
        state.ruler.active = false;
        state.map?.getContainer?.().classList.remove("ruler-active-v072");
        const panel = qs("#map-ruler-panel-v072");
        if (panel) panel.hidden = true;
        if (clear) {
            state.ruler.points = [];
            state.ruler.group?.clearLayers();
        }
    }

    function ensureRulerResultDialog() {
        let dialog = qs("#map-ruler-result-v072");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-ruler-result-v072";
        dialog.className = "map-dialog-v072 map-ruler-result-v072";
        dialog.innerHTML = `<section><header><div><small>MEDIÇÃO</small><h2>Trajeto medido</h2></div><button type="button" data-close>×</button></header><div class="ruler-result-distance-v072" data-result-distance></div><p>O traçado permanece em prévia até você descartar ou transformar em cabo.</p><footer><button type="button" data-continue>Continuar editando</button><button type="button" data-discard>Descartar</button>${canEdit ? '<button type="button" class="primary" data-convert>Transformar em cabo</button>' : ""}</footer></section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-continue]").onclick = () => { dialog.close(); resumeRuler(); };
        dialog.querySelector("[data-discard]").onclick = () => { dialog.close(); stopRuler(true); };
        dialog.querySelector("[data-convert]")?.addEventListener("click", () => openCableFromRuler().catch((error) => notify(error.message, true)));
        return dialog;
    }

    function finishRuler() {
        if (state.ruler.points.length < 2) return notify("Marque ao menos dois pontos.", true);
        if (state.map && state.ruler.clickHandler) state.map.off("click", state.ruler.clickHandler);
        state.ruler.clickHandler = null;
        state.ruler.active = false;
        qs("#map-ruler-panel-v072").hidden = true;
        state.map.getContainer().classList.remove("ruler-active-v072");
        const dialog = ensureRulerResultDialog();
        dialog.querySelector("[data-result-distance]").textContent = formatDistance(distanceMeters());
        dialog.showModal();
    }

    function resumeRuler() {
        state.ruler.active = true;
        ensureRulerPanel().hidden = false;
        state.map.getContainer().classList.add("ruler-active-v072");
        state.ruler.clickHandler = (event) => addRulerPoint(event.latlng);
        state.map.on("click", state.ruler.clickHandler);
    }

    async function cableFormData() {
        const projectId = projectSelect.value;
        const [models, elements] = await Promise.all([
            request("/api/map/cable-models/"),
            request(`/api/map/elements/?project_id=${encodeURIComponent(projectId)}`),
        ]);
        return { models: models.models || [], elements: elements.features || [] };
    }

    function ensureCableFromRulerDialog() {
        let dialog = qs("#map-ruler-cable-dialog-v072");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-ruler-cable-dialog-v072";
        dialog.className = "map-dialog-v072 map-ruler-cable-dialog-v072";
        dialog.innerHTML = `<form><header><div><small>CONVERTER MEDIÇÃO</small><h2>Novo cabo</h2></div><button type="button" data-close>×</button></header><div class="map-form-grid-v072"><label>Nome<input name="name" required maxlength="180" placeholder="Ex.: Backbone Cidade A → Cidade B"></label><label>Código<input name="code" maxlength="100"></label><label>Tipo<select name="cable_type"><option value="backbone">Backbone</option><option value="feeder">Alimentador</option><option value="distribution">Distribuição</option><option value="drop">Drop</option></select></label><label>Modelo / fibras<select name="cable_model_id" required></select></label><label>Origem<select name="origin_id"><option value="">Sem conexão</option></select></label><label>Destino<select name="destination_id"><option value="">Sem conexão</option></select></label></div><label>Descrição<textarea name="description" rows="3" placeholder="Trajeto criado a partir da régua"></textarea></label><p data-cable-status></p><footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary">Criar cabo</button></footer></form>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-cancel]").onclick = () => dialog.close();
        dialog.querySelector("form").onsubmit = saveCableFromRuler;
        return dialog;
    }

    async function openCableFromRuler() {
        if (state.ruler.points.length < 2) throw new Error("A medição não possui pontos suficientes.");
        const dialog = ensureCableFromRulerDialog();
        const form = qs("form", dialog);
        const data = await cableFormData();
        form.elements.cable_model_id.innerHTML = '<option value="">Selecione</option>' + data.models.map((item) => `<option value="${item.id}" data-fibers="${item.fiber_count}">${escapeHtml(item.name)} · ${item.fiber_count}F</option>`).join("");
        const options = '<option value="">Sem conexão</option>' + data.elements.map((feature) => `<option value="${feature.properties.id}">${escapeHtml(feature.properties.nome)} · ${escapeHtml(feature.properties.tipo)}</option>`).join("");
        form.elements.origin_id.innerHTML = options;
        form.elements.destination_id.innerHTML = options;
        form.elements.name.value = `Cabo medido · ${formatDistance(distanceMeters())}`;
        qs("#map-ruler-result-v072")?.close();
        dialog.showModal();
    }

    async function saveCableFromRuler(event) {
        event.preventDefault();
        const form = event.currentTarget;
        const status = qs("[data-cable-status]", form);
        status.textContent = "Criando cabo...";
        const selectedModel = form.elements.cable_model_id.selectedOptions[0];
        const payload = {
            project_id: projectSelect.value,
            name: form.elements.name.value,
            code: form.elements.code.value,
            description: form.elements.description.value,
            cable_type: form.elements.cable_type.value,
            cable_model_id: form.elements.cable_model_id.value,
            fiber_count: Number(selectedModel?.dataset.fibers || 12),
            origin_id: form.elements.origin_id.value,
            destination_id: form.elements.destination_id.value,
            status: "no_data",
            generate_fibers: true,
            coordinates: state.ruler.points.map((point) => [point.lng, point.lat]),
        };
        try {
            const result = await request("/api/map/cables/create/", { method: "POST", body: JSON.stringify(payload) });
            qs("#map-ruler-cable-dialog-v072")?.close();
            stopRuler(true);
            await window.networkMap?.loadStructure?.();
            notify(`Cabo ${result.cable?.name || payload.name} criado com sucesso.`);
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("error");
        }
    }


    function ensureAreaPanel() {
        let panel = qs("#map-area-panel-v072");
        if (panel) return panel;
        panel = document.createElement("section");
        panel.id = "map-area-panel-v072";
        panel.className = "map-ruler-panel-v072 map-area-panel-v072";
        panel.hidden = true;
        panel.innerHTML = `
            <div><strong>Medir área</strong><span data-area-value>0 m²</span></div>
            <p>Marque pelo menos três vértices no mapa.</p>
            <footer><button type="button" data-area-undo>Desfazer ponto</button><button type="button" data-area-cancel>Cancelar</button><button type="button" data-area-finish class="primary">Concluir</button></footer>`;
        qs("#map")?.appendChild(panel);
        panel.querySelector("[data-area-undo]").onclick = () => { state.area.points.pop(); updateArea(); };
        panel.querySelector("[data-area-cancel]").onclick = () => stopArea();
        panel.querySelector("[data-area-finish]").onclick = () => finishArea();
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(panel);
            L.DomEvent.disableScrollPropagation(panel);
        }
        return panel;
    }

    function ensureAreaLayer() {
        if (!state.map || !window.L) return null;
        if (!state.area.group) state.area.group = L.layerGroup().addTo(state.map);
        return state.area.group;
    }

    function startArea() {
        if (!projectSelect?.value) return notify("Selecione um projeto antes de medir a área.", true);
        stopRuler();
        stopArea(false);
        qs('[data-map-mode="view"]')?.click();
        state.area.active = true;
        state.area.points = [];
        ensureAreaLayer()?.clearLayers();
        ensureAreaPanel().hidden = false;
        state.map.getContainer().classList.add("ruler-active-v072");
        state.area.clickHandler = (event) => { state.area.points.push(event.latlng); updateArea(); };
        state.map.on("click", state.area.clickHandler);
        updateArea();
        notify("Medição de área ativa: marque os vértices no mapa.");
    }

    function areaSquareMeters() {
        const points = state.area.points;
        if (points.length < 3) return 0;
        const radius = 6378137;
        let sum = 0;
        for (let index = 0; index < points.length; index += 1) {
            const current = points[index];
            const next = points[(index + 1) % points.length];
            const lonDelta = (next.lng - current.lng) * Math.PI / 180;
            sum += lonDelta * (2 + Math.sin(current.lat * Math.PI / 180) + Math.sin(next.lat * Math.PI / 180));
        }
        return Math.abs(sum * radius * radius / 2);
    }

    function formatArea(squareMeters) {
        if (squareMeters >= 1_000_000) return `${(squareMeters / 1_000_000).toFixed(2)} km²`;
        if (squareMeters >= 10_000) return `${(squareMeters / 10_000).toFixed(2)} ha`;
        return `${squareMeters.toFixed(squareMeters >= 100 ? 0 : 1)} m²`;
    }

    function updateArea() {
        const group = ensureAreaLayer();
        if (!group) return;
        group.clearLayers();
        state.area.points.forEach((point, index) => L.circleMarker(point, {
            radius: 5, weight: 2, color: "#e2e8f0", fillColor: "#a855f7", fillOpacity: 1, interactive: false,
        }).bindTooltip(String(index + 1), { permanent: true, direction: "top", className: "ruler-index-v072" }).addTo(group));
        if (state.area.points.length >= 2) {
            state.area.polygon = L.polygon(state.area.points, {
                color: "#a855f7", weight: 3, opacity: .95, fillColor: "#a855f7", fillOpacity: .17, dashArray: "9 7",
            }).addTo(group);
        } else state.area.polygon = null;
        const value = qs("#map-area-panel-v072 [data-area-value]");
        if (value) value.textContent = formatArea(areaSquareMeters());
        const finish = qs("#map-area-panel-v072 [data-area-finish]");
        if (finish) finish.disabled = state.area.points.length < 3;
    }

    function stopArea(clear = true) {
        if (state.map && state.area.clickHandler) state.map.off("click", state.area.clickHandler);
        state.area.clickHandler = null;
        state.area.active = false;
        state.map?.getContainer?.().classList.remove("ruler-active-v072");
        const panel = qs("#map-area-panel-v072");
        if (panel) panel.hidden = true;
        if (clear) {
            state.area.points = [];
            state.area.group?.clearLayers();
        }
    }

    function areaGeoJson() {
        const coordinates = state.area.points.map((point) => [point.lng, point.lat]);
        if (coordinates.length) coordinates.push([...coordinates[0]]);
        return {
            type: "Feature",
            properties: { project_id: projectSelect?.value || null, area_m2: Number(areaSquareMeters().toFixed(2)) },
            geometry: { type: "Polygon", coordinates: [coordinates] },
        };
    }

    function downloadAreaGeoJson() {
        const blob = new Blob([JSON.stringify(areaGeoJson(), null, 2)], { type: "application/geo+json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `area-projeto-${projectSelect?.value || "mapa"}.geojson`;
        link.click();
        URL.revokeObjectURL(url);
    }

    function ensureAreaResultDialog() {
        let dialog = qs("#map-area-result-v072");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-area-result-v072";
        dialog.className = "map-dialog-v072 map-ruler-result-v072";
        dialog.innerHTML = `<section><header><div><small>ÁREA MEDIDA</small><h2>Polígono concluído</h2></div><button type="button" data-close>×</button></header><div class="ruler-result-distance-v072" data-area-result></div><p>A prévia permanece no mapa enquanto você exporta ou revisa os vértices.</p><footer><button type="button" data-continue>Continuar editando</button><button type="button" data-discard>Descartar</button><button type="button" class="primary" data-export>Exportar GeoJSON</button></footer></section>`;
        document.body.appendChild(dialog);
        dialog.querySelector("[data-close]").onclick = () => dialog.close();
        dialog.querySelector("[data-continue]").onclick = () => { dialog.close(); startAreaFromExisting(); };
        dialog.querySelector("[data-discard]").onclick = () => { dialog.close(); stopArea(true); };
        dialog.querySelector("[data-export]").onclick = () => downloadAreaGeoJson();
        return dialog;
    }

    function startAreaFromExisting() {
        state.area.active = true;
        ensureAreaPanel().hidden = false;
        state.map.getContainer().classList.add("ruler-active-v072");
        state.area.clickHandler = (event) => { state.area.points.push(event.latlng); updateArea(); };
        state.map.on("click", state.area.clickHandler);
        updateArea();
    }

    function finishArea() {
        if (state.area.points.length < 3) return notify("Marque ao menos três vértices.", true);
        if (state.map && state.area.clickHandler) state.map.off("click", state.area.clickHandler);
        state.area.clickHandler = null;
        state.area.active = false;
        qs("#map-area-panel-v072").hidden = true;
        state.map.getContainer().classList.remove("ruler-active-v072");
        const dialog = ensureAreaResultDialog();
        dialog.querySelector("[data-area-result]").textContent = formatArea(areaSquareMeters());
        dialog.showModal();
    }

    function popupTextLines(content) {
        const clone = content.cloneNode(true);
        qsa("button, a, .leaflet-popup-close-button", clone).forEach((node) => node.remove());
        clone.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
        return clone.textContent.split("\n").map((line) => line.trim()).filter(Boolean);
    }

    function elementIcon(type) {
        const normalized = String(type || "").toLowerCase();
        if (normalized.includes("torre") || normalized.includes("tower")) return '<svg viewBox="0 0 24 24"><path d="M12 2 6 22m6-20 6 20M8 15h8M9 10h6M5 22h14"></path></svg>';
        if (normalized.includes("rack") || normalized.includes("cpd") || normalized.includes("pop")) return '<svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"></rect><path d="M8 6h8M8 11h8M8 16h8"></path></svg>';
        if (normalized.includes("cto")) return svg("cto");
        if (normalized.includes("ceo") || normalized.includes("cdo") || normalized.includes("caixa")) return svg("box");
        if (normalized.includes("poste")) return svg("pole");
        if (normalized.includes("cabo") || normalized.includes("backbone")) return svg("cable");
        return '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><path d="M12 8v4l3 2"></path></svg>';
    }

    function statusFromSource(source) {
        const root = source?.getElement?.();
        if (!root) return null;
        const monitored = root.matches?.(".monitoring-enabled") ? root : root.querySelector?.(".monitoring-enabled");
        if (!monitored) return null;
        const classes = [...monitored.classList];
        const found = classes.find((name) => name.startsWith("monitor-status-"));
        const status = found ? found.replace("monitor-status-", "").replace(/-/g, "_") : "no_data";
        const labels = { normal: "ONLINE", recovering: "RECUPERANDO", warning: "ATENÇÃO", degraded: "DEGRADADO", offline: "OFFLINE", no_data: "SEM DADOS" };
        return { status, label: labels[status] || status.toUpperCase(), title: monitored.title || "" };
    }

    function buttonIcon(button) {
        const text = button.textContent.trim().toLowerCase();
        if (button.dataset.showElementCables !== undefined || text.includes("cabos")) return "⚡";
        if (button.dataset.manageContainer !== undefined || text.includes("equip")) return "▣";
        if (text.includes("ficha") || text.includes("qr")) return "▦";
        if (text.includes("editar")) return "✎";
        if (text.includes("excluir")) return "⌫";
        if (text.includes("fus")) return "⇄";
        if (text.includes("monitor")) return "◉";
        return "›";
    }

    function decoratePopup(eventOrPopup) {
        const popup = eventOrPopup?.popup || eventOrPopup;
        const element = popup?.getElement?.();
        const content = element?.querySelector(".leaflet-popup-content");
        if (!content || content.dataset.uiV072 === "1" || content.querySelector(".monitor-link-popup")) return;
        const lines = popupTextLines(content);
        const originalStrong = qs("strong", content)?.textContent.trim();
        const name = originalStrong || lines[0] || "Elemento";
        const filtered = lines.filter((line) => line !== name);
        const type = filtered[0] || "ELEMENTO";
        const code = filtered[1] || "";
        const sourceStatus = statusFromSource(popup._source);
        const actions = qsa("button, a", content);

        const shell = document.createElement("section");
        shell.className = "map-popup-hud-v072";
        shell.innerHTML = `<header><span class="map-popup-icon-v072">${elementIcon(type)}</span><div><h3>${escapeHtml(name)}</h3><div class="map-popup-meta-v072"><span>${escapeHtml(type)}</span>${sourceStatus ? `<b class="status-${escapeHtml(sourceStatus.status)}" title="${escapeHtml(sourceStatus.title)}"><i></i>${escapeHtml(sourceStatus.label)}</b>` : ""}</div>${code ? `<small>${escapeHtml(code)}</small>` : ""}</div></header><div class="map-popup-actions-v072"></div>`;
        const target = qs(".map-popup-actions-v072", shell);
        actions.forEach((button) => {
            const text = button.textContent.trim();
            button.classList.add("map-popup-action-v072");
            if (button.classList.contains("danger") || /excluir|remover/i.test(text)) button.classList.add("danger");
            if (button.dataset.showElementCables !== undefined || /cabos e ligações/i.test(text)) button.classList.add("primary", "full");
            if (!qs(".map-popup-button-icon-v072", button)) {
                const icon = document.createElement("span");
                icon.className = "map-popup-button-icon-v072";
                icon.textContent = buttonIcon(button);
                button.prepend(icon);
            }
            target.appendChild(button);
        });
        content.innerHTML = "";
        content.appendChild(shell);
        content.dataset.uiV072 = "1";
        element.classList.add("leaflet-popup-v072");
    }

    function installPopupDecoration() {
        if (!state.map) return;
        state.map.on("popupopen", (event) => {
            window.clearTimeout(state.popupTimer);
            state.popupTimer = window.setTimeout(() => decoratePopup(event), 30);
        });
        qsa(".leaflet-popup").forEach((node) => {
            const content = qs(".leaflet-popup-content", node);
            if (content) content.classList.add("pending-v072");
        });
    }

    function cleanContainerUi() {
        const dialog = qs("#container-dialog");
        if (!dialog) return;
        dialog.classList.add("container-dialog-v072");
        qsa(".container-tabs-v09, .container-tab-panels-v09", dialog).forEach((node) => node.classList.add("legacy-container-ui-v072"));
        const master = qs("#map-master-container", dialog);
        if (master) {
            master.classList.add("map-master-container-v072");
            qsa(":scope > section > .container-workspace, :scope > section > #container-optical-links, :scope > section > .container-extension-grid, :scope > section > #container-equipment-form", dialog)
                .forEach((node) => node.classList.add("master-legacy-hidden"));
        }
    }

    function installObservers() {
        const mapRoot = qs("#map");
        if (mapRoot) {
            let scheduled = false;
            const observer = new MutationObserver((mutations) => {
                const relevant = mutations.some((mutation) => [...mutation.addedNodes].some((node) => node.nodeType === 1 && (
                    node.matches?.(".leaflet-popup, .leaflet-marker-icon, #map-master-route-drawer")
                    || node.querySelector?.(".leaflet-popup, .leaflet-marker-icon, #map-master-route-drawer")
                )));
                if (!relevant || scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => {
                    scheduled = false;
                    syncToolbarAvailability();
                });
            });
            observer.observe(mapRoot, { childList: true, subtree: true });
        }
        const container = qs("#container-dialog");
        if (container) {
            // cleanContainerUi() só adiciona classe (classList.add), mas isso
            // ainda dispara mutação do tipo "attributes" — como o próprio
            // observer escuta "class", sem essa trava ele reagia à própria
            // mutação e reagendava a si mesmo indefinidamente (mesma família
            // de bug do laço corrigido na v0.71.1).
            let containerScheduled = false;
            const observer = new MutationObserver(() => {
                if (containerScheduled) return;
                containerScheduled = true;
                requestAnimationFrame(() => {
                    containerScheduled = false;
                    cleanContainerUi();
                });
            });
            observer.observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ["open", "class"] });
        }
    }

    function applyCompatibilityCleanup() {
        qs("#route-filter-v092")?.classList.add("legacy-route-filter-v072");
        qs("#map-master-controls")?.classList.add("legacy-master-controls-v072");
        qs(".map-mode-control")?.classList.add("legacy-map-mode-v072");
        qs(".collapsed-tools")?.classList.add("legacy-collapsed-tools-v072");
        cleanContainerUi();
    }

    async function waitForMap() {
        for (let attempt = 0; attempt < 120; attempt += 1) {
            if (window.networkMap?.map) {
                state.map = window.networkMap.map;
                return true;
            }
            await new Promise((resolve) => window.setTimeout(resolve, 50));
        }
        return false;
    }

    async function init() {
        setTheme(localStorage.getItem("mapThemeV072") || "dark");
        buildSidebar();
        buildTopToolbar();
        applyCompatibilityCleanup();
        installObservers();
        if (!await waitForMap()) return notify("Mapa não ficou disponível para a interface v0.72.0.", true);
        installPopupDecoration();
        projectSelect?.addEventListener("change", () => {
            stopRuler(true);
            stopArea(true);
            window.setTimeout(syncToolbarAvailability, 100);
        });
        window.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                qs("#map-search-toggle")?.click();
            }
            if (event.key === "Escape" && state.ruler.active) stopRuler(true);
            if (event.key === "Escape" && state.area.active) stopArea(true);
        });
        window.addEventListener("resize", () => state.map?.invalidateSize?.());
        window.mapUiV072 = {
            version: VERSION,
            startRuler,
            stopRuler,
            startArea,
            stopArea,
            decoratePopup,
            refresh: () => {
                buildSidebar(); buildTopToolbar(); applyCompatibilityCleanup(); syncToolbarAvailability(); cleanContainerUi();
            },
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
