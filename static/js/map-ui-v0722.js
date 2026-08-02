(function () {
    "use strict";

    const VERSION = "0.72.2";
    const body = document.body;
    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
    const canEdit = body.dataset.canEdit === "true";
    const ELEMENT_TOOLS = new Set(["cto", "splice_box", "cdo", "pole", "cpd", "rack", "tower"]);
    const state = {
        map: null,
        currentMode: "view",
        activeTool: "",
        popupTimers: new WeakMap(),
        toolbarTimer: null,
        routeDrawerOpen: false,
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
            cancel: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"></path></svg>',
        };
        return icons[name] || icons.more;
    }

    function projectSelected() {
        return Boolean(qs("#project-select")?.value);
    }

    // ------------------------------------------------------------------
    // Sidebar
    // ------------------------------------------------------------------

    function setSidebarCollapsed(collapsed) {
        const sidebar = qs("#map-sidebar");
        if (!sidebar) return;
        sidebar.classList.toggle("v072-collapsed", collapsed);
        body.classList.toggle("map-sidebar-collapsed-v0722", collapsed);
        const toggle = qs("#collapse-sidebar", sidebar);
        if (toggle) {
            toggle.textContent = collapsed ? "›" : "‹";
            toggle.title = collapsed ? "Abrir menu" : "Recolher menu";
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }
        localStorage.setItem("mapSidebarV072Collapsed", collapsed ? "1" : "0");
        setTimeout(() => state.map?.invalidateSize?.(), 60);
        setTimeout(() => state.map?.invalidateSize?.(), 260);
    }

    function fixSidebar() {
        const sidebar = qs("#map-sidebar");
        const oldToggle = qs("#collapse-sidebar", sidebar);
        if (!sidebar || !oldToggle) return;
        if (oldToggle.dataset.v0722 !== "1") {
            const toggle = oldToggle.cloneNode(true);
            toggle.dataset.v0722 = "1";
            oldToggle.replaceWith(toggle);
            toggle.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                setSidebarCollapsed(!sidebar.classList.contains("v072-collapsed"));
            });
        }
        const saved = localStorage.getItem("mapSidebarV072Collapsed") === "1";
        setSidebarCollapsed(saved);
    }

    // ------------------------------------------------------------------
    // Search — keep the proven legacy handlers, reset only its layout.
    // ------------------------------------------------------------------

    function ensureSearchShell() {
        let shell = qs("#map-search-shell-v0722");
        const legacy = qs("#map-search");
        if (!legacy) return null;
        if (!shell) {
            shell = document.createElement("section");
            shell.id = "map-search-shell-v0722";
            shell.className = "map-search-shell-v0722";
            shell.hidden = true;
            shell.innerHTML = `
                <header>
                    <div>${icon("search")}<span><strong>Buscar no mapa</strong><small>Endereço ou item do projeto</small></span></div>
                    <button type="button" data-search-close aria-label="Fechar">×</button>
                </header>
                <div class="map-search-host-v0722"></div>`;
            qs("#map")?.appendChild(shell);
            qs("[data-search-close]", shell).onclick = closeSearch;
            if (window.L?.DomEvent) {
                L.DomEvent.disableClickPropagation(shell);
                L.DomEvent.disableScrollPropagation(shell);
            }
        }
        const host = qs(".map-search-host-v0722", shell);
        if (legacy.parentElement !== host) host.appendChild(legacy);
        legacy.classList.add("map-search-v0722");
        legacy.hidden = false;
        return shell;
    }

    function openSearch() {
        const shell = ensureSearchShell();
        if (!shell) return notify("A pesquisa do mapa não está disponível.", true);
        closeMenus();
        shell.hidden = false;
        requestAnimationFrame(() => shell.classList.add("open"));
        setTimeout(() => qs("#map-search-query")?.focus(), 60);
    }

    function closeSearch() {
        const shell = qs("#map-search-shell-v0722");
        if (!shell) return;
        shell.classList.remove("open");
        setTimeout(() => { shell.hidden = true; }, 150);
    }

    function fixSearchTriggers() {
        const sidebarSearch = qs("[data-v072-search]");
        if (sidebarSearch) {
            sidebarSearch.onclick = (event) => {
                event.preventDefault();
                openSearch();
            };
        }
        const oldToggle = qs("#map-search-toggle");
        if (oldToggle && oldToggle.dataset.v0722 !== "1") {
            const replacement = oldToggle.cloneNode(true);
            replacement.dataset.v0722 = "1";
            oldToggle.replaceWith(replacement);
            replacement.onclick = openSearch;
        }
    }

    // ------------------------------------------------------------------
    // Modes, tools, cancel and toolbar
    // ------------------------------------------------------------------

    function syncModeButtons() {
        const originalEdit = qs('[data-map-mode="edit"]');
        const originalView = qs('[data-map-mode="view"]');
        let mode = state.currentMode;
        if (originalEdit?.classList.contains("active")) mode = "edit";
        else if (originalView?.classList.contains("active")) mode = "view";
        state.currentMode = mode;
        body.dataset.mapUiMode = mode;
        qsa("#map-toolbar-v072 [data-v0722-mode]").forEach((button) => {
            const active = button.dataset.v0722Mode === mode;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function setMode(mode, announce = true) {
        const target = qs(`[data-map-mode="${mode}"]`);
        if (!target) return;
        if (mode === "edit" && !canEdit) return notify("Seu acesso é somente visualização.", true);
        target.click();
        state.currentMode = mode;
        body.dataset.mapUiMode = mode;
        if (mode === "view") clearActiveTool();
        syncModeButtons();
        state.map?.closePopup?.();
        if (announce && mode === "edit") notify("Modo de edição ativado.");
    }

    function toolLabel(name) {
        return ({
            cto: "CTO", splice_box: "CEO", cdo: "CDO", pole: "Poste",
            cable: "Cabo", cpd: "CPD/POP", rack: "Rack", tower: "Torre",
            ruler: "Régua", area: "Área", reserve: "Reserva", insert: "Inserir caixa",
        })[name] || name;
    }

    function setActiveTool(name) {
        state.activeTool = name || "";
        const cancel = qs("#map-toolbar-v072 [data-v0722-cancel]");
        if (cancel) {
            cancel.hidden = !state.activeTool;
            const label = qs("span", cancel);
            if (label) label.textContent = state.activeTool ? `Cancelar ${toolLabel(state.activeTool)}` : "Cancelar";
        }
        qsa("#map-toolbar-v072 [data-v0722-tool], #map-toolbar-v072 [data-v0722-ruler], #map-toolbar-v072 [data-v0722-area]").forEach((button) => {
            const buttonTool = button.dataset.v0722Tool || (button.hasAttribute("data-v0722-ruler") ? "ruler" : button.hasAttribute("data-v0722-area") ? "area" : "");
            button.classList.toggle("tool-active", Boolean(state.activeTool) && buttonTool === state.activeTool);
        });
    }

    function clearActiveTool() {
        setActiveTool("");
        body.classList.remove("map-tool-active-v0722");
    }

    function cancelActiveTool(announce = true) {
        window.mapUiV072?.stopRuler?.(true);
        window.mapUiV072?.stopArea?.(true);
        // Re-clicking the active native mode invokes map-editor.clearTool()
        // without forcing the operator out of Edit mode.
        const nativeMode = qs(`[data-map-mode="${state.currentMode === "edit" ? "edit" : "view"}"]`)
            || qs('[data-map-mode="view"]');
        nativeMode?.click();
        clearActiveTool();
        closeMenus();
        if (announce) notify("Ferramenta cancelada.");
    }

    function activateTool(name) {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        if (!canEdit) return notify("Seu acesso é somente visualização.", true);
        cancelActiveTool(false);
        setMode("edit", false);
        const original = qs(`[data-tool="${CSS.escape(name)}"]`) || qs(`[data-quick-tool="${CSS.escape(name)}"]`);
        if (!original) return notify(`Ferramenta ${toolLabel(name)} não encontrada.`, true);
        original.click();
        body.classList.add("map-tool-active-v0722");
        setActiveTool(name);
        closeMenus();
        notify(`${toolLabel(name)} ativo. Clique no mapa ou use Cancelar.`);
    }

    function closeMenus() {
        qsa("#map-toolbar-v072 [data-v0722-menu]").forEach((menu) => menu.classList.remove("open"));
        qsa("#map-toolbar-v072 [data-v0722-menu-toggle]").forEach((button) => button.setAttribute("aria-expanded", "false"));
    }

    function openRoutes() {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        const drawer = qs("#map-master-route-drawer");
        const rows = drawer ? qsa(".route-master-item", drawer) : [];
        if (!drawer || rows.length === 0) {
            return notify("Ainda não existe uma rota óptica conectada neste projeto.", true);
        }
        const currentlyOpen = !drawer.hidden && !drawer.classList.contains("collapsed");
        drawer.hidden = false;
        drawer.classList.toggle("collapsed", currentlyOpen);
        drawer.setAttribute("aria-hidden", currentlyOpen ? "true" : "false");
        state.routeDrawerOpen = !currentlyOpen;
    }

    function openLinks() {
        if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
        const source = qs("[data-monitor-links-toggle]");
        if (!source) return notify("O editor de enlaces não está disponível.", true);
        source.click();
    }

    function rebuildToolbar() {
        const toolbar = qs("#map-toolbar-v072");
        if (!toolbar || toolbar.dataset.v0722 === "1") return;
        toolbar.dataset.v0722 = "1";
        toolbar.classList.add("map-toolbar-v0722");
        toolbar.innerHTML = `
            <div class="map-mode-switch-v0722" role="group" aria-label="Modo do mapa">
                <button type="button" data-v0722-mode="view">${icon("view")}<span>Visualizar</span></button>
                ${canEdit ? `<button type="button" data-v0722-mode="edit">${icon("edit")}<span>Editar</span></button>` : ""}
            </div>
            ${canEdit ? `
            <div class="map-tool-menu-v0722">
                <button type="button" data-v0722-menu-toggle="boxes" aria-expanded="false">${icon("box")}<span>Caixas</span><b>⌄</b></button>
                <div data-v0722-menu="boxes" role="menu"><button type="button" data-v0722-tool="cto">CTO</button><button type="button" data-v0722-tool="splice_box">CEO</button><button type="button" data-v0722-tool="cdo">CDO</button></div>
            </div>
            <button type="button" data-v0722-tool="pole">${icon("pole")}<span>Poste</span></button>
            <button type="button" data-v0722-tool="cable">${icon("cable")}<span>Cabo</span></button>
            <button type="button" data-v0722-ruler>${icon("ruler")}<span>Régua</span></button>
            <button type="button" data-v0722-area>${icon("area")}<span>Área</span></button>
            <div class="map-tool-menu-v0722">
                <button type="button" data-v0722-menu-toggle="more" aria-expanded="false">${icon("more")}<span>Mais</span><b>⌄</b></button>
                <div data-v0722-menu="more" role="menu"><button type="button" data-v0722-tool="cpd">CPD/POP</button><button type="button" data-v0722-tool="rack">Rack</button><button type="button" data-v0722-tool="tower">Torre</button></div>
            </div>` : ""}
            <button type="button" data-v0722-routes hidden>${icon("route")}<span>Rotas</span></button>
            <button type="button" data-v0722-links hidden>${icon("links")}<span>Enlaces</span></button>
            <button type="button" class="map-cancel-tool-v0722" data-v0722-cancel hidden>${icon("cancel")}<span>Cancelar</span></button>`;

        qsa("[data-v0722-mode]", toolbar).forEach((button) => {
            button.onclick = () => setMode(button.dataset.v0722Mode);
        });
        qsa("[data-v0722-tool]", toolbar).forEach((button) => {
            button.onclick = () => activateTool(button.dataset.v0722Tool);
        });
        qs("[data-v0722-ruler]", toolbar)?.addEventListener("click", () => {
            if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
            cancelActiveTool(false);
            setMode("edit", false);
            window.mapUiV072?.startRuler?.();
            body.classList.add("map-tool-active-v0722");
            setActiveTool("ruler");
        });
        qs("[data-v0722-area]", toolbar)?.addEventListener("click", () => {
            if (!projectSelected()) return notify("Selecione um projeto primeiro.", true);
            cancelActiveTool(false);
            setMode("edit", false);
            window.mapUiV072?.startArea?.();
            body.classList.add("map-tool-active-v0722");
            setActiveTool("area");
        });
        qsa("[data-v0722-menu-toggle]", toolbar).forEach((button) => {
            button.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                const menu = qs(`[data-v0722-menu="${CSS.escape(button.dataset.v0722MenuToggle)}"]`, toolbar);
                const open = !menu?.classList.contains("open");
                qsa("[data-v0722-menu]", toolbar).forEach((item) => item.classList.remove("open"));
                qsa("[data-v0722-menu-toggle]", toolbar).forEach((item) => item.setAttribute("aria-expanded", "false"));
                if (open && menu) {
                    menu.classList.add("open");
                    button.setAttribute("aria-expanded", "true");
                }
            };
        });
        qs("[data-v0722-routes]", toolbar).onclick = openRoutes;
        qs("[data-v0722-links]", toolbar).onclick = openLinks;
        qs("[data-v0722-cancel]", toolbar).onclick = () => cancelActiveTool();
        document.addEventListener("click", closeMenus);
        syncModeButtons();
        syncToolbar();
    }

    function syncToolbar() {
        const routeButton = qs("[data-v0722-routes]");
        const drawer = qs("#map-master-route-drawer");
        const hasRoutes = Boolean(drawer && qs(".route-master-item", drawer));
        if (routeButton) routeButton.hidden = !projectSelected() || !hasRoutes;
        const linkButton = qs("[data-v0722-links]");
        if (linkButton) linkButton.hidden = !projectSelected() || !qs("[data-monitor-links-toggle]");
        syncModeButtons();
        clearTimeout(state.toolbarTimer);
        state.toolbarTimer = setTimeout(syncToolbar, 1000);
    }

    function installToolLifecycle() {
        document.addEventListener("click", (event) => {
            const button = event.target.closest?.("[data-insert-cable], [data-reserve-cable]");
            if (!button) return;
            const type = button.hasAttribute("data-insert-cable") ? "insert" : "reserve";
            setTimeout(() => {
                body.classList.add("map-tool-active-v0722");
                setActiveTool(type);
            }, 0);
        }, true);
        qs("#cancel-drawing")?.addEventListener("click", () => clearActiveTool());
        qs("#element-dialog")?.addEventListener("close", () => {
            if (ELEMENT_TOOLS.has(state.activeTool)) cancelActiveTool(false);
        });
        qs("#cable-dialog")?.addEventListener("close", () => {
            if (state.activeTool === "cable") cancelActiveTool(false);
        });
    }

    // ------------------------------------------------------------------
    // Stable HUD popups. No MutationObserver: it was the source of the
    // endless text growth, flicker and clicks lost while the DOM moved.
    // ------------------------------------------------------------------

    function cleanText(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function popupTextLines(content) {
        const clone = content.cloneNode(true);
        qsa("button, a, .leaflet-popup-close-button", clone).forEach((node) => node.remove());
        qsa(".map-popup-button-icon-v072, .map-popup-button-icon-v0721, .map-popup-button-icon-v0722", clone).forEach((node) => node.remove());
        clone.querySelectorAll("br").forEach((node) => node.replaceWith("\n"));
        return clone.textContent.split("\n").map(cleanText).filter(Boolean);
    }

    function popupIdentity(content) {
        if (content._uiV0722Identity) return content._uiV0722Identity;
        const hud = qs(".map-popup-hud-v0722, .map-popup-hud-v0721, .map-popup-hud-v072", content);
        let name = cleanText(qs("h3", hud || content)?.textContent || qs("strong", content)?.textContent);
        let type = cleanText(qs(".map-popup-meta-v0722 > span, .map-popup-meta-v0721 > span, .map-popup-meta-v072 > span", hud || content)?.textContent);
        let code = cleanText(qs("header small", hud || content)?.textContent);
        if (!name || !type) {
            const lines = popupTextLines(content);
            name = name || lines[0] || "Elemento";
            const remaining = lines.filter((line) => line !== name);
            type = type || remaining[0] || "ELEMENTO";
            code = code || remaining[1] || "";
        }
        // Never accept a concatenated old HUD as identity metadata.
        if (type.length > 80) type = type.split(/(?=[A-Z_]{3,})/)[0] || "ELEMENTO";
        if (code.length > 140) code = code.slice(0, 140);
        const html = typeof content.innerHTML === "string" ? content.innerHTML : "";
        const match = html.match(/data-(?:edit-element|show-element-cables|manage-container|asset-id)=["'](\d+)["']/i);
        const identity = { name: name.slice(0, 180), type: type.slice(0, 80), code, id: match ? Number(match[1]) : null };
        content._uiV0722Identity = identity;
        return identity;
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

    function actionLabel(button) {
        if (button.dataset.uiV0722Label) return button.dataset.uiV0722Label;
        const clone = button.cloneNode(true);
        qsa(".map-popup-button-icon-v072, .map-popup-button-icon-v0721, .map-popup-button-icon-v0722", clone).forEach((node) => node.remove());
        const label = cleanText(clone.textContent);
        button.dataset.uiV0722Label = label;
        return label;
    }

    function actionKey(button) {
        const data = Object.entries(button.dataset || {})
            .filter(([key]) => !key.startsWith("uiV072"))
            .sort(([left], [right]) => left.localeCompare(right));
        if (data.length) return data.map(([key, value]) => `${key}:${value}`).join("|");
        return actionLabel(button).toLowerCase();
    }

    function actionSymbol(label) {
        if (/cabos|ligações/i.test(label)) return "⚡";
        if (/equip/i.test(label)) return "▣";
        if (/ficha|qr/i.test(label)) return "▦";
        if (/editar/i.test(label)) return "✎";
        if (/excluir|remover|apagar/i.test(label)) return "⌫";
        if (/fus/i.test(label)) return "⇄";
        if (/monitor/i.test(label)) return "◉";
        if (/reserva/i.test(label)) return "+";
        if (/rota/i.test(label)) return "⌁";
        if (/inserir/i.test(label)) return "+";
        return "›";
    }

    function decorateAction(button) {
        const label = actionLabel(button);
        qsa(".map-popup-button-icon-v072, .map-popup-button-icon-v0721, .map-popup-button-icon-v0722", button).forEach((node) => node.remove());
        const iconNode = document.createElement("span");
        iconNode.className = "map-popup-button-icon-v0722";
        iconNode.textContent = actionSymbol(label);
        button.replaceChildren(iconNode, document.createTextNode(label));
        button.classList.remove("map-popup-action-v072", "map-popup-action-v0721");
        button.classList.add("map-popup-action-v0722");
        button.classList.toggle("danger", /excluir|remover|apagar/i.test(label));
        button.classList.toggle("primary", /cabos e ligações/i.test(label));
        button.classList.toggle("full", /cabos e ligações/i.test(label));
    }

    function normalizePopup(popup) {
        const element = popup?.getElement?.();
        const content = qs(".leaflet-popup-content", element);
        if (!content || qs(".monitor-link-popup", content)) return;
        const identity = popupIdentity(content);
        const actions = qsa("button, a", content).filter((node) => (
            !node.closest("header")
            && !node.classList.contains("leaflet-popup-close-button")
            && !node.hasAttribute("data-search-close")
        ));
        const unique = [];
        const keys = new Set();
        actions.forEach((button) => {
            const key = actionKey(button);
            if (!key || keys.has(key)) return;
            keys.add(key);
            unique.push(button);
        });
        const status = statusMarkup(popup);
        const signature = `${identity.name}|${identity.type}|${identity.code}|${[...keys].join("|")}|${status}`;
        if (content.dataset.uiV0722Signature === signature && qs(".map-popup-hud-v0722", content)) return;
        const shell = document.createElement("section");
        shell.className = "map-popup-hud-v0722";
        shell.innerHTML = `
            <header>
                <span class="map-popup-icon-v0722">${popupIcon(identity.type)}</span>
                <div class="map-popup-title-v0722">
                    <h3 title="${escapeHtml(identity.name)}">${escapeHtml(identity.name)}</h3>
                    <div class="map-popup-meta-v0722"><span title="${escapeHtml(identity.type)}">${escapeHtml(identity.type)}</span>${status}</div>
                    ${identity.code && identity.code !== identity.name && identity.code !== identity.type ? `<small title="${escapeHtml(identity.code)}">${escapeHtml(identity.code)}</small>` : ""}
                </div>
            </header>
            <div class="map-popup-actions-v0722"></div>`;
        const target = qs(".map-popup-actions-v0722", shell);
        unique.forEach((button) => {
            decorateAction(button);
            target.appendChild(button);
        });
        content.replaceChildren(shell);
        content.dataset.uiV072 = "1";
        content.dataset.uiV0722 = "1";
        content.dataset.uiV0722Signature = signature;
        element.classList.add("leaflet-popup-v072", "leaflet-popup-v0722");
    }

    function schedulePopup(popup) {
        const previous = state.popupTimers.get(popup) || [];
        previous.forEach(clearTimeout);
        // Finite retries only. They allow Master Suite/monitoring to append
        // their actions, but never observe and rewrite the popup forever.
        const timers = [100, 420].map((delay) => setTimeout(() => normalizePopup(popup), delay));
        state.popupTimers.set(popup, timers);
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
        state.map?.on("popupclose", (event) => {
            const timers = state.popupTimers.get(event.popup) || [];
            timers.forEach(clearTimeout);
            state.popupTimers.delete(event.popup);
        });
    }

    function installKeyboard() {
        window.addEventListener("keydown", (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                openSearch();
                return;
            }
            if (event.key !== "Escape") return;
            const search = qs("#map-search-shell-v0722");
            if (search && !search.hidden) {
                closeSearch();
                return;
            }
            if (!qs("dialog[open]") && state.activeTool) cancelActiveTool();
            closeMenus();
        });
    }

    async function init() {
        body.classList.add("map-ui-v0722");
        body.classList.remove("map-ui-v0721");
        fixSidebar();
        fixSearchTriggers();
        ensureSearchShell();
        rebuildToolbar();
        installKeyboard();
        installToolLifecycle();
        if (!await waitForMap()) return notify("Mapa não ficou disponível para o hotfix v0.72.2.", true);
        installPopupConsistency();
        qs("#project-select")?.addEventListener("change", () => {
            cancelActiveTool(false);
            setTimeout(syncToolbar, 120);
        });
        window.mapUiV0722 = {
            version: VERSION,
            openSearch,
            closeSearch,
            openRoutes,
            setMode,
            cancelActiveTool,
            refresh() {
                fixSidebar();
                fixSearchTriggers();
                ensureSearchShell();
                rebuildToolbar();
                syncToolbar();
            },
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
