(function () {
    "use strict";

    const VERSION = "0.72.1";
    const body = document.body;
    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
    const canEdit = body.dataset.canEdit === "true";
    const state = {
        map: null,
        toolbarTimer: null,
        popupTimers: new WeakMap(),
        popupObservers: new WeakMap(),
        currentMode: "view",
    };

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function notify(message, error = false) {
        if (window.networkMap?.notify) {
            window.networkMap.notify(message, error);
            return;
        }
        const toast = qs("#map-ui-toast-v072") || document.body.appendChild(Object.assign(document.createElement("div"), {
            id: "map-ui-toast-v072",
            className: "map-ui-toast-v072",
        }));
        toast.textContent = message || "";
        toast.classList.toggle("error", error);
        toast.classList.add("show");
        clearTimeout(toast._timer);
        toast._timer = setTimeout(() => toast.classList.remove("show"), 3800);
    }

    function icon(name) {
        const icons = {
            view: '<svg viewBox="0 0 24 24"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"></path><circle cx="12" cy="12" r="2.8"></circle></svg>',
            edit: '<svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"></path><path d="m13.5 6.5 3.5 3.5"></path></svg>',
            box: '<svg viewBox="0 0 24 24"><path d="M7 3h10l4 5v8l-4 5H7l-4-5V8z"></path><path d="M8 9h8M8 13h8M8 17h8"></path></svg>',
            pole: '<svg viewBox="0 0 24 24"><path d="M4 7h16M12 3v18M7 21h10M8 7l4 5 4-5"></path></svg>',
            cable: '<svg viewBox="0 0 24 24"><path d="M3 17c5 0 5-10 10-10s4 7 8 7"></path><circle cx="3" cy="17" r="2"></circle><circle cx="21" cy="14" r="2"></circle></svg>',
            ruler: '<svg viewBox="0 0 24 24"><path d="m4 17 13-13 3 3L7 20H4z"></path><path d="m13 8 3 3m-6 0 3 3m-6 0 3 3"></path></svg>',
            area: '<svg viewBox="0 0 24 24"><path d="m4 17 4-11 10-2 2 12-8 5z"></path><circle cx="4" cy="17" r="1.5"></circle><circle cx="8" cy="6" r="1.5"></circle><circle cx="18" cy="4" r="1.5"></circle><circle cx="20" cy="16" r="1.5"></circle><circle cx="12" cy="21" r="1.5"></circle></svg>',
            more: '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"></circle><circle cx="12" cy="12" r="1.5"></circle><circle cx="19" cy="12" r="1.5"></circle></svg>',
            route: '<svg viewBox="0 0 24 24"><circle cx="5" cy="18" r="2"></circle><circle cx="19" cy="6" r="2"></circle><path d="M7 18h4a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3"></path></svg>',
            links: '<svg viewBox="0 0 24 24"><circle cx="4" cy="12" r="2"></circle><circle cx="20" cy="12" r="2"></circle><path d="M6 12h12M9 8l3 4-3 4m6-8-3 4 3 4"></path></svg>',
            search: '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m15.5 15.5 5 5"></path></svg>',
        };
        return icons[name] || icons.more;
    }

    function projectSelected() {
        return Boolean(qs("#project-select")?.value);
    }

    function setSidebarCollapsed(collapsed) {
        const sidebar = qs("#map-sidebar");
        if (!sidebar) return;
        sidebar.classList.toggle("v072-collapsed", collapsed);
        body.classList.toggle("map-sidebar-collapsed-v0721", collapsed);
        const toggle = qs("#collapse-sidebar", sidebar);
        if (toggle) {
            toggle.textContent = collapsed ? "›" : "‹";
            toggle.title = collapsed ? "Abrir menu" : "Recolher menu";
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }
        localStorage.setItem("mapSidebarV072Collapsed", collapsed ? "1" : "0");
        setTimeout(() => state.map?.invalidateSize?.(), 50);
        setTimeout(() => state.map?.invalidateSize?.(), 240);
    }

    function fixSidebar() {
        const sidebar = qs("#map-sidebar");
        const oldToggle = qs("#collapse-sidebar", sidebar);
        if (!sidebar || !oldToggle || oldToggle.dataset.v0721 === "1") return;
        const toggle = oldToggle.cloneNode(true);
        toggle.dataset.v0721 = "1";
        oldToggle.replaceWith(toggle);
        const saved = localStorage.getItem("mapSidebarV072Collapsed") === "1";
        setSidebarCollapsed(saved || sidebar.classList.contains("v072-collapsed"));
        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            setSidebarCollapsed(!sidebar.classList.contains("v072-collapsed"));
        });
    }

    function ensureSearchShell() {
        let shell = qs("#map-search-shell-v0721");
        if (shell) return shell;
        const legacy = qs("#map-search");
        if (!legacy) return null;
        shell = document.createElement("section");
        shell.id = "map-search-shell-v0721";
        shell.className = "map-search-shell-v0721";
        shell.hidden = true;
        shell.innerHTML = `<header><div>${icon("search")}<span><strong>Buscar no mapa</strong><small>Endereço ou item do projeto</small></span></div><button type="button" data-search-close aria-label="Fechar">×</button></header><div data-search-host></div>`;
        qs("#map")?.appendChild(shell);
        qs("[data-search-host]", shell).appendChild(legacy);
        legacy.classList.add("map-search-v0721");
        legacy.hidden = false;
        qs("[data-search-close]", shell).onclick = closeSearch;
        if (window.L?.DomEvent) {
            L.DomEvent.disableClickPropagation(shell);
            L.DomEvent.disableScrollPropagation(shell);
        }
        return shell;
    }

    function openSearch() {
        const shell = ensureSearchShell();
        if (!shell) return notify("A pesquisa do mapa não está disponível.", true);
        shell.hidden = false;
        requestAnimationFrame(() => shell.classList.add("open"));
        setTimeout(() => qs("#map-search-query")?.focus(), 40);
    }

    function closeSearch() {
        const shell = qs("#map-search-shell-v0721");
        if (!shell) return;
        shell.classList.remove("open");
        setTimeout(() => { shell.hidden = true; }, 150);
    }

    function fixSearchTriggers() {
        const sidebarSearch = qs("[data-v072-search]");
        if (sidebarSearch) sidebarSearch.onclick = openSearch;
        const oldToggle = qs("#map-search-toggle");
        if (oldToggle && oldToggle.dataset.v0721 !== "1") {
            const replacement = oldToggle.cloneNode(true);
            replacement.dataset.v0721 = "1";
            oldToggle.replaceWith(replacement);
            replacement.onclick = openSearch;
        }
    }

    function setMode(mode) {
        const target = qs(`[data-map-mode="${mode}"]`);
        if (!target) return;
        if (mode === "edit" && !canEdit) return notify("Seu acesso é somente visualização.", true);
        target.click();
        state.currentMode = mode;
        body.dataset.mapUiMode = mode;
        syncModeButtons();
        state.map?.closePopup?.();
        if (mode === "edit") {
            notify("Modo de edição ativado. Clique no item para ver todas as ações.");
        }
    }

    function syncModeButtons() {
        const originalEdit = qs('[data-map-mode="edit"]');
        const originalView = qs('[data-map-mode="view"]');
        let mode = state.currentMode;
        if (originalEdit?.classList.contains("active")) mode = "edit";
        else if (originalView?.classList.contains("active")) mode = "view";
        state.currentMode = mode;
        body.dataset.mapUiMode = mode;
        qsa("#map-toolbar-v072 [data-v0721-mode]").forEach((button) => {
            const active = button.dataset.v0721Mode === mode;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function activateTool(name) {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        if (!canEdit) return notify("Seu acesso é somente visualização.", true);
        setMode("edit");
        const original = qs(`[data-tool="${CSS.escape(name)}"]`) || qs(`[data-quick-tool="${CSS.escape(name)}"]`);
        if (!original) return notify(`Ferramenta ${name} não encontrada.`, true);
        original.click();
        closeMenus();
    }

    function closeMenus() {
        qsa("#map-toolbar-v072 [data-v0721-menu]").forEach((menu) => menu.classList.remove("open"));
        qsa("#map-toolbar-v072 [data-v0721-menu-toggle]").forEach((button) => button.setAttribute("aria-expanded", "false"));
    }

    function openRoutes() {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        const drawer = qs("#map-master-route-drawer");
        const rows = drawer ? qsa(".route-master-item", drawer) : [];
        if (!drawer || drawer.hidden || rows.length === 0) {
            return notify("Ainda não existe uma rota óptica conectada neste projeto.", true);
        }
        drawer.hidden = false;
        drawer.classList.remove("collapsed");
        drawer.setAttribute("aria-hidden", "false");
    }

    function openLinks() {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        const source = qs("[data-monitor-links-toggle]");
        if (!source) return notify("O editor de enlaces não está disponível.", true);
        source.click();
    }

    function rebuildToolbar() {
        const toolbar = qs("#map-toolbar-v072");
        if (!toolbar || toolbar.dataset.v0721 === "1") return;
        toolbar.dataset.v0721 = "1";
        toolbar.classList.add("map-toolbar-v0721");
        toolbar.innerHTML = `
            <div class="map-mode-switch-v0721" role="group" aria-label="Modo do mapa">
                <button type="button" data-v0721-mode="view">${icon("view")}<span>Visualizar</span></button>
                ${canEdit ? `<button type="button" data-v0721-mode="edit">${icon("edit")}<span>Editar</span></button>` : ""}
            </div>
            ${canEdit ? `
            <div class="map-tool-menu-v072 map-tool-menu-v0721">
                <button type="button" data-v0721-menu-toggle="boxes">${icon("box")}<span>Caixa</span><b>⌄</b></button>
                <div data-v0721-menu="boxes"><button type="button" data-v0721-tool="cto">CTO</button><button type="button" data-v0721-tool="splice_box">CEO</button><button type="button" data-v0721-tool="cdo">CDO</button></div>
            </div>
            <button type="button" data-v0721-tool="pole">${icon("pole")}<span>Poste</span></button>
            <button type="button" data-v0721-tool="cable">${icon("cable")}<span>Cabo</span></button>
            <button type="button" data-v0721-ruler>${icon("ruler")}<span>Régua</span></button>
            <button type="button" data-v0721-area>${icon("area")}<span>Área</span></button>
            <div class="map-tool-menu-v072 map-tool-menu-v0721">
                <button type="button" data-v0721-menu-toggle="more">${icon("more")}<span>Mais</span><b>⌄</b></button>
                <div data-v0721-menu="more"><button type="button" data-v0721-tool="cpd">CPD/POP</button><button type="button" data-v0721-tool="rack">Rack</button><button type="button" data-v0721-tool="tower">Torre</button></div>
            </div>` : ""}
            <button type="button" data-v0721-routes hidden>${icon("route")}<span>Rotas</span></button>
            <button type="button" data-v0721-links hidden>${icon("links")}<span>Enlaces</span></button>`;

        qsa("[data-v0721-mode]", toolbar).forEach((button) => button.onclick = () => setMode(button.dataset.v0721Mode));
        qsa("[data-v0721-tool]", toolbar).forEach((button) => button.onclick = () => activateTool(button.dataset.v0721Tool));
        qs("[data-v0721-ruler]", toolbar)?.addEventListener("click", () => {
            if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
            setMode("edit");
            window.mapUiV072?.startRuler?.();
        });
        qs("[data-v0721-area]", toolbar)?.addEventListener("click", () => {
            if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
            setMode("edit");
            window.mapUiV072?.startArea?.();
        });
        qsa("[data-v0721-menu-toggle]", toolbar).forEach((button) => {
            button.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                const menu = qs(`[data-v0721-menu="${CSS.escape(button.dataset.v0721MenuToggle)}"]`, toolbar);
                const open = menu?.classList.toggle("open");
                qsa("[data-v0721-menu]", toolbar).forEach((item) => { if (item !== menu) item.classList.remove("open"); });
                button.setAttribute("aria-expanded", open ? "true" : "false");
            };
        });
        qs("[data-v0721-routes]", toolbar).onclick = openRoutes;
        qs("[data-v0721-links]", toolbar).onclick = openLinks;
        document.addEventListener("click", closeMenus);
        syncModeButtons();
        syncToolbar();
    }

    function syncToolbar() {
        const routeButton = qs("[data-v0721-routes]");
        const drawer = qs("#map-master-route-drawer");
        const hasRoutes = Boolean(drawer && !drawer.hidden && qs(".route-master-item", drawer));
        if (routeButton) routeButton.hidden = !projectSelected() || !hasRoutes;
        const linkButton = qs("[data-v0721-links]");
        if (linkButton) linkButton.hidden = !projectSelected() || !qs("[data-monitor-links-toggle]");
        syncModeButtons();
        clearTimeout(state.toolbarTimer);
        state.toolbarTimer = setTimeout(syncToolbar, 700);
    }

    function textLines(content) {
        const clone = content.cloneNode(true);
        qsa("button, a, .leaflet-popup-close-button", clone).forEach((node) => node.remove());
        clone.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
        return clone.textContent.split("\n").map((line) => line.trim()).filter(Boolean);
    }

    function popupIdentity(popup, content) {
        const hud = qs(".map-popup-hud-v072, .map-popup-hud-v0721", content);
        const lines = textLines(content);
        const name = qs("h3", hud || content)?.textContent.trim() || qs("strong", content)?.textContent.trim() || lines[0] || "Elemento";
        const meta = qs(".map-popup-meta-v072 span", hud || content)?.textContent.trim();
        const filtered = lines.filter((line) => line !== name);
        const type = meta || filtered[0] || "ELEMENTO";
        const code = qs("header small", hud || content)?.textContent.trim() || filtered[1] || "";
        const html = typeof popup?.getContent?.() === "string" ? popup.getContent() : content.outerHTML;
        const match = html.match(/data-(?:edit-element|show-element-cables|manage-container|asset-id)=["'](\d+)["']/i);
        return { name, type, code, id: match ? Number(match[1]) : null };
    }

    function statusMarkup(popup) {
        const root = popup?._source?.getElement?.();
        const monitored = root?.matches?.(".monitoring-enabled") ? root : root?.querySelector?.(".monitoring-enabled");
        if (!monitored) return "";
        const statusClass = [...monitored.classList].find((name) => name.startsWith("monitor-status-"));
        const status = statusClass ? statusClass.replace("monitor-status-", "") : "no-data";
        const labels = { normal: "ONLINE", offline: "OFFLINE", degraded: "DEGRADADO", warning: "ATENÇÃO", recovering: "RECUPERANDO", "no-data": "SEM DADOS" };
        return `<b class="status-${escapeHtml(status.replace(/-/g, "_"))}" title="${escapeHtml(monitored.title || "")}"><i></i>${escapeHtml(labels[status] || status.toUpperCase())}</b>`;
    }

    function popupIcon(type) {
        const normalized = String(type || "").toLowerCase();
        if (normalized.includes("torre") || normalized.includes("tower")) return '<svg viewBox="0 0 24 24"><path d="M12 2 6 22m6-20 6 20M8 15h8M9 10h6M5 22h14"></path></svg>';
        if (normalized.includes("rack") || normalized.includes("cpd") || normalized.includes("pop")) return '<svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"></rect><path d="M8 6h8M8 11h8M8 16h8"></path></svg>';
        if (normalized.includes("cto")) return '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="14" rx="3"></rect><path d="M8 8h8M8 12h8M8 18v3m8-3v3"></path></svg>';
        if (normalized.includes("ceo") || normalized.includes("cdo") || normalized.includes("caixa")) return icon("box");
        if (normalized.includes("poste")) return icon("pole");
        if (normalized.includes("cabo") || normalized.includes("backbone")) return icon("cable");
        return '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><path d="M12 8v4l3 2"></path></svg>';
    }

    function actionKey(button) {
        const datasets = ["showElementCables", "manageContainer", "editElement", "deleteElement", "masterAssetSheet", "showUnifilar", "openMonitorLinks"];
        for (const key of datasets) if (button.dataset?.[key] !== undefined) return `${key}:${button.dataset[key]}`;
        return button.textContent.trim().toLowerCase().replace(/\s+/g, " ");
    }

    function decorateAction(button) {
        const text = button.textContent.trim();
        button.classList.remove("map-popup-action-v072");
        button.classList.add("map-popup-action-v0721");
        button.classList.toggle("danger", /excluir|remover|apagar/i.test(text));
        button.classList.toggle("primary", /cabos e ligações|abrir fusões/i.test(text));
        button.classList.toggle("full", /cabos e ligações|abrir fusões/i.test(text));
        let symbol = "›";
        if (/cabos|ligações/i.test(text)) symbol = "⚡";
        else if (/equip/i.test(text)) symbol = "▣";
        else if (/ficha|qr/i.test(text)) symbol = "▦";
        else if (/editar/i.test(text)) symbol = "✎";
        else if (/excluir|remover/i.test(text)) symbol = "⌫";
        else if (/fus/i.test(text)) symbol = "⇄";
        else if (/monitor/i.test(text)) symbol = "◉";
        let iconNode = qs(".map-popup-button-icon-v072, .map-popup-button-icon-v0721", button);
        if (!iconNode) {
            iconNode = document.createElement("span");
            button.prepend(iconNode);
        }
        iconNode.className = "map-popup-button-icon-v0721";
        iconNode.textContent = symbol;
    }

    function addFallbackActions(actions, identity) {
        if (!identity.id) return actions;
        const type = identity.type.toLowerCase();
        const container = /tower|torre|rack|cpd|pop/.test(type);
        const has = (regex) => actions.some((button) => regex.test(button.textContent || ""));
        if (container && !has(/equipamentos/i)) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.manageContainer = String(identity.id);
            button.textContent = "Equipamentos";
            button.onclick = () => window.networkMap?.manageContainer?.(identity.id);
            actions.push(button);
        }
        if (!has(/ficha|qr/i)) {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.masterAssetSheet = "element";
            button.dataset.assetId = String(identity.id);
            button.textContent = "Ficha / QR";
            actions.push(button);
        }
        return actions;
    }

    function normalizePopup(popup) {
        const element = popup?.getElement?.();
        const content = qs(".leaflet-popup-content", element);
        if (!content || qs(".monitor-link-popup", content)) return;
        const identity = popupIdentity(popup, content);
        let actions = qsa("button, a", content).filter((node) => !node.closest("header") && !node.classList.contains("leaflet-popup-close-button"));
        actions = addFallbackActions(actions, identity);
        const unique = [];
        const keys = new Set();
        actions.forEach((button) => {
            const key = actionKey(button);
            if (!key || keys.has(key)) return;
            keys.add(key);
            unique.push(button);
        });
        const signature = `${identity.name}|${identity.type}|${identity.code}|${[...keys].join("|")}|${statusMarkup(popup)}`;
        if (content.dataset.uiV0721 === "1" && content.dataset.uiV0721Signature === signature && qs(".map-popup-hud-v0721", content)) return;
        const shell = document.createElement("section");
        shell.className = "map-popup-hud-v0721";
        shell.innerHTML = `<header><span class="map-popup-icon-v0721">${popupIcon(identity.type)}</span><div><h3>${escapeHtml(identity.name)}</h3><div class="map-popup-meta-v0721"><span>${escapeHtml(identity.type)}</span>${statusMarkup(popup)}</div>${identity.code && identity.code !== identity.name && identity.code !== identity.type ? `<small>${escapeHtml(identity.code)}</small>` : ""}</div></header><div class="map-popup-actions-v0721"></div>`;
        const target = qs(".map-popup-actions-v0721", shell);
        unique.forEach((button) => {
            decorateAction(button);
            target.appendChild(button);
        });
        content.replaceChildren(shell);
        content.dataset.uiV072 = "1";
        content.dataset.uiV0721 = "1";
        content.dataset.uiV0721Signature = signature;
        element.classList.add("leaflet-popup-v072", "leaflet-popup-v0721");
    }

    function schedulePopup(popup) {
        const old = state.popupTimers.get(popup) || [];
        old.forEach(clearTimeout);
        const timers = [80, 260, 650].map((delay) => setTimeout(() => normalizePopup(popup), delay));
        state.popupTimers.set(popup, timers);
        const content = qs(".leaflet-popup-content", popup?.getElement?.());
        if (content && !state.popupObservers.has(content)) {
            let scheduled = false;
            const observer = new MutationObserver(() => {
                if (scheduled) return;
                scheduled = true;
                setTimeout(() => {
                    scheduled = false;
                    normalizePopup(popup);
                }, 80);
            });
            observer.observe(content, { childList: true, subtree: true });
            state.popupObservers.set(content, observer);
        }
    }

    async function waitForMap() {
        for (let attempt = 0; attempt < 120; attempt += 1) {
            if (window.networkMap?.map) {
                state.map = window.networkMap.map;
                return true;
            }
            await new Promise((resolve) => setTimeout(resolve, 50));
        }
        return false;
    }

    function installPopupConsistency() {
        state.map?.on("popupopen", (event) => schedulePopup(event.popup));
    }

    function installKeyboard() {
        window.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                openSearch();
            }
            if (event.key === "Escape") closeSearch();
        });
    }

    async function init() {
        body.classList.add("map-ui-v0721");
        fixSidebar();
        fixSearchTriggers();
        ensureSearchShell();
        rebuildToolbar();
        installKeyboard();
        if (!await waitForMap()) return notify("Mapa não ficou disponível para o hotfix v0.72.1.", true);
        installPopupConsistency();
        qs("#project-select")?.addEventListener("change", () => setTimeout(syncToolbar, 120));
        new MutationObserver(() => {
            fixSidebar();
            fixSearchTriggers();
            rebuildToolbar();
        }).observe(document.body, { childList: true, subtree: true });
        window.mapUiV0721 = {
            version: VERSION,
            openSearch,
            closeSearch,
            openRoutes,
            setMode,
            refresh() {
                fixSidebar();
                fixSearchTriggers();
                rebuildToolbar();
                syncToolbar();
            },
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
