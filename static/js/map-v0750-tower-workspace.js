(function () {
    "use strict";

    const VERSION = "0.75.0";
    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
    const escapeHtml = (value) => {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    };
    const state = {
        activeMenu: null,
        inspectorEquipmentId: "",
        fusionFitTimer: null,
        workspaceResizeObserver: null,
    };

    function icon(name) {
        const icons = {
            tower: '<svg viewBox="0 0 24 24"><path d="M12 2 6 22m6-20 6 20M8 15h8M9 10h6M5 22h14"></path></svg>',
            dio: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M8 8h8M8 12h8M8 16h8"></path><circle cx="7" cy="8" r=".8"></circle><circle cx="7" cy="12" r=".8"></circle><circle cx="7" cy="16" r=".8"></circle></svg>',
            pto: '<svg viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="3"></rect><circle cx="12" cy="12" r="3"></circle><path d="M12 3v2M12 19v2"></path></svg>',
            active: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="M7 9h10M7 13h6M18 13h.01"></path></svg>',
            connect: '<svg viewBox="0 0 24 24"><circle cx="5" cy="18" r="2"></circle><circle cx="19" cy="6" r="2"></circle><path d="M7 18h4a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3"></path></svg>',
            fiber: '<svg viewBox="0 0 24 24"><path d="M3 12h5m8 0h5"></path><circle cx="10" cy="12" r="2"></circle><circle cx="14" cy="12" r="2"></circle><path d="M10 8V5m4 3V5m-4 11v3m4-3v3"></path></svg>',
            inventory: '<svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2"></rect><path d="M8 7h8M8 12h8M8 17h8"></path></svg>',
            yaml: '<svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"></path><path d="M14 3v5h5M9 12h6M9 16h6"></path></svg>',
            fit: '<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"></path><path d="M9 9h6v6H9z"></path></svg>',
            organize: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect></svg>',
            minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"></path></svg>',
            plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"></path></svg>',
            fullscreen: '<svg viewBox="0 0 24 24"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"></path></svg>',
            close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"></path></svg>',
            edit: '<svg viewBox="0 0 24 24"><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"></path><path d="m13.5 6.5 3.5 3.5"></path></svg>',
            sheet: '<svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2"></rect><path d="M8 8h8M8 12h8M8 16h5"></path></svg>',
            snmp: '<svg viewBox="0 0 24 24"><path d="M4 17h3l2-5 3 8 3-12 2 9h3"></path></svg>',
            menu: '<svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.5"></circle><circle cx="12" cy="12" r="1.5"></circle><circle cx="19" cy="12" r="1.5"></circle></svg>',
            chevron: '<svg viewBox="0 0 24 24"><path d="m7 10 5 5 5-5"></path></svg>',
        };
        return icons[name] || icons.menu;
    }

    function waitFor(selector, callback, attempts = 120, root = document) {
        const found = qs(selector, root);
        if (found) return callback(found);
        if (attempts <= 0) return;
        window.setTimeout(() => waitFor(selector, callback, attempts - 1, root), 50);
    }

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }

    async function request(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function notify(message, error = false) {
        if (window.networkMap?.notify) return window.networkMap.notify(message, error);
        let toast = qs("#map-v0750-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "map-v0750-toast";
            toast.className = "map-v0750-toast";
            document.body.appendChild(toast);
        }
        toast.textContent = message || "";
        toast.classList.toggle("error", error);
        toast.classList.add("show");
        clearTimeout(toast._timer);
        toast._timer = window.setTimeout(() => toast.classList.remove("show"), 3800);
    }

    function dialogRoot() {
        return qs("#container-dialog");
    }

    function workspaceRoot() {
        return qs("#map-master-container");
    }

    function lockWorkspacePosition() {
        const dialog = dialogRoot();
        if (!dialog?.open || !dialog.classList.contains("tower-workspace-dialog-v0750")) return;
        const sidebar = qs("#map-sidebar");
        const sidebarRight = sidebar && getComputedStyle(sidebar).display !== "none"
            ? Math.max(0, Math.round(sidebar.getBoundingClientRect().right))
            : 0;
        const left = Math.min(sidebarRight, Math.max(0, window.innerWidth - 320));
        dialog.style.setProperty("position", "fixed", "important");
        dialog.style.setProperty("top", "0", "important");
        dialog.style.setProperty("right", "0", "important");
        dialog.style.setProperty("bottom", "0", "important");
        dialog.style.setProperty("left", `${Math.max(0, left)}px`, "important");
        dialog.style.setProperty("width", "auto", "important");
        dialog.style.setProperty("height", "100dvh", "important");
        dialog.style.setProperty("max-width", "none", "important");
        dialog.style.setProperty("max-height", "none", "important");
        dialog.style.setProperty("margin", "0", "important");
        dialog.style.setProperty("transform", "none", "important");
        dialog.scrollTop = 0;
        const section = qs(":scope > section", dialog);
        if (section) section.scrollTop = 0;
    }

    function resetWorkspaceForOpen() {
        const dialog = dialogRoot();
        if (!dialog?.open) return;
        dialog.classList.remove("master-container-fullscreen", "map-v0750-css-fullscreen");
        dialog.scrollTop = 0;
        const root = workspaceRoot();
        if (root) {
            closeDrawer(root);
            ensureWorkspace(root);
        }
        lockWorkspacePosition();
        window.requestAnimationFrame(() => lockWorkspacePosition());
        window.setTimeout(() => lockWorkspacePosition(), 120);
    }

    function installWorkspacePositionLock() {
        const sidebar = qs("#map-sidebar");
        if (sidebar && !state.workspaceResizeObserver && window.ResizeObserver) {
            state.workspaceResizeObserver = new ResizeObserver(() => lockWorkspacePosition());
            state.workspaceResizeObserver.observe(sidebar);
        }
        if (document.body.dataset.v0750WorkspaceLock !== "1") {
            document.body.dataset.v0750WorkspaceLock = "1";
            window.addEventListener("resize", lockWorkspacePosition);
            document.addEventListener("keydown", (event) => {
                const dialog = dialogRoot();
                if (event.key !== "Escape" || !dialog?.open) return;
                event.preventDefault();
                dialog.close();
            });
        }
        lockWorkspacePosition();
    }

    function activateCanvas(root) {
        if (!root) return;
        const canvasTab = qs('[data-tab="canvas"]', root);
        const canvasPanel = qs('[data-panel="canvas"]', root);
        if (!canvasPanel) return;
        qsa("[data-tab]", root).forEach((item) => item.classList.toggle("active", item === canvasTab));
        qsa(":scope > [data-panel]", root).forEach((panel) => panel.classList.toggle("active", panel === canvasPanel));
        canvasPanel.classList.add("active");
        if (canvasTab && !canvasTab.classList.contains("active")) canvasTab.classList.add("active");
        window.setTimeout(() => qs("[data-canvas-zoom-fit]", root)?.click(), 70);
    }

    function panelTitle(mode) {
        return ({
            equipment: "Inventário da estrutura",
            fibers: "Fibras e terminações",
            models: "Importar YAML / modelos",
            matrix: "Relatório de ligações",
            structure: "Estrutura principal",
            inspector: "Propriedades do equipamento",
        })[mode] || "Detalhes";
    }

    function ensureDrawer(root) {
        let drawer = qs(".tower-drawer-v0750", root);
        if (drawer) return drawer;
        drawer = document.createElement("aside");
        drawer.className = "tower-drawer-v0750";
        drawer.hidden = true;
        drawer.innerHTML = `
            <header>
                <div><strong data-drawer-title>Detalhes</strong><small data-drawer-subtitle>Canvas 2D da estrutura</small></div>
                <button type="button" data-drawer-close aria-label="Fechar">${icon("close")}</button>
            </header>
            <div class="tower-drawer-body-v0750"></div>`;
        root.appendChild(drawer);
        qs("[data-drawer-close]", drawer).onclick = () => closeDrawer(root);
        return drawer;
    }

    function closeDrawer(root) {
        const drawer = ensureDrawer(root);
        drawer.hidden = true;
        root.classList.remove("drawer-open-v0750");
        state.activeMenu = null;
        activateCanvas(root);
    }

    function movePanelsIntoDrawer(root) {
        const drawer = ensureDrawer(root);
        const body = qs(".tower-drawer-body-v0750", drawer);
        ["equipment", "fibers", "models", "matrix"].forEach((name) => {
            const panel = qs(`[data-panel="${name}"]`, root);
            if (panel && panel.parentElement !== body) body.appendChild(panel);
            if (panel) panel.classList.remove("active");
        });
    }

    function openPanel(root, mode) {
        movePanelsIntoDrawer(root);
        const drawer = ensureDrawer(root);
        const body = qs(".tower-drawer-body-v0750", drawer);
        qsa(":scope > [data-panel]", body).forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === mode));
        qs("[data-drawer-title]", drawer).textContent = panelTitle(mode);
        qs("[data-drawer-subtitle]", drawer).textContent = mode === "models"
            ? "Pré-visualize e importe Device Type YAML"
            : "Ações sem sair do Canvas 2D";
        drawer.hidden = false;
        root.classList.add("drawer-open-v0750");
        state.activeMenu = mode;
        activateCanvas(root);
        lockWorkspacePosition();
    }

    function openStructureInfo(root) {
        const drawer = ensureDrawer(root);
        const body = qs(".tower-drawer-body-v0750", drawer);
        const dialog = dialogRoot();
        qsa(":scope > [data-panel]", body).forEach((panel) => panel.classList.remove("active"));
        let info = qs(".tower-structure-info-v0750", body);
        if (!info) {
            info = document.createElement("section");
            info.className = "tower-structure-info-v0750";
            body.appendChild(info);
        }
        const nodeItems = qsa(".master-canvas-node", root).map((node) => ({
            id: node.dataset.equipmentNode,
            name: qs("header strong", node)?.textContent || "Equipamento",
            type: qs("header small", node)?.textContent || node.dataset.equipmentType || "",
        }));
        info.innerHTML = `
            <div class="tower-structure-hero-v0750">${icon("tower")}<div><strong>${escapeHtml(dialog?.querySelector("h2")?.textContent || "Torre / Rack")}</strong><span>Elemento pai da estrutura interna</span></div></div>
            <h3>Equipamentos instalados</h3>
            <div class="tower-structure-list-v0750">${nodeItems.map((item) => `<button type="button" data-structure-equipment="${item.id}"><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.type)}</small></span><i>›</i></button>`).join("") || "<p>Nenhum equipamento instalado.</p>"}</div>`;
        qsa("[data-structure-equipment]", info).forEach((button) => button.onclick = () => {
            const node = qs(`[data-equipment-node="${CSS.escape(button.dataset.structureEquipment)}"]`, root);
            if (node) openInspector(root, node);
        });
        info.classList.add("active");
        qs("[data-drawer-title]", drawer).textContent = panelTitle("structure");
        qs("[data-drawer-subtitle]", drawer).textContent = "Hierarquia física e lógica da torre";
        drawer.hidden = false;
        root.classList.add("drawer-open-v0750");
        activateCanvas(root);
    }

    function nextDefaultName(root, type) {
        const labels = {
            dio: "DIO",
            pto: "PTO",
            access_point: "AP",
            ptp: "PTP",
            switch: "Switch",
            router: "Router",
            onu: "ONU-ONT",
        };
        const base = labels[type] || "Equipamento";
        const count = qsa(`.master-canvas-node[data-equipment-type="${type}"]`, root).length + 1;
        return `${base} ${String(count).padStart(2, "0")}`;
    }

    function quickAdd(root, type) {
        const source = qs("[data-container-add]", root);
        if (!source) return notify("A criação de equipamentos ainda não carregou.", true);
        source.click();
        waitFor("#map-master-equipment-create[open]", (dialog) => {
            const select = qs("select[name='equipment_type']", dialog);
            const name = qs("input[name='name']", dialog);
            if (select && [...select.options].some((option) => option.value === type)) {
                select.value = type;
                select.dispatchEvent(new Event("change", { bubbles: true }));
            }
            if (name && !name.value) name.value = nextDefaultName(root, type);
            const title = qs("h2", dialog);
            if (title) title.textContent = `Adicionar ${type === "onu" ? "ONU / ONT" : type.toUpperCase()}`;
            name?.focus();
        });
    }

    function closeActivePopover(root) {
        qsa(".tower-popover-v0750.open", root).forEach((menu) => menu.classList.remove("open"));
        qsa("[data-tower-menu]", root).forEach((button) => button.setAttribute("aria-expanded", "false"));
    }

    function toggleToolbarMenu(root, button) {
        const menu = qs(`#${CSS.escape(button.getAttribute("aria-controls"))}`, root);
        if (!menu) return;
        const open = !menu.classList.contains("open");
        closeActivePopover(root);
        menu.classList.toggle("open", open);
        button.setAttribute("aria-expanded", String(open));
    }

    function ensureToolbar(root) {
        let toolbar = qs(".tower-workspace-toolbar-v0750", root);
        if (toolbar) return toolbar;
        toolbar = document.createElement("div");
        toolbar.className = "tower-workspace-toolbar-v0750";
        toolbar.innerHTML = `
            <div class="tower-workspace-title-v0750">
                ${icon("tower")}
                <span><strong>Editor técnico da Torre</strong><small>Canvas 2D · portas, ativos e conexões</small></span>
            </div>
            <div class="tower-workspace-actions-v0750">
                <button type="button" data-structure-info>${icon("tower")}<span>Estrutura</span></button>
                <div class="tower-toolbar-menu-v0750">
                    <button type="button" class="primary" data-tower-menu aria-controls="tower-add-menu-v0750" aria-expanded="false">${icon("plus")}<span>Adicionar</span>${icon("chevron")}</button>
                    <div id="tower-add-menu-v0750" class="tower-popover-v0750 tower-add-menu-v0750" role="menu">
                        <small>INFRAESTRUTURA PASSIVA</small>
                        <button type="button" data-quick-add="dio">${icon("dio")}<span><strong>D.I.O</strong><small>Distribuidor interno óptico</small></span></button>
                        <button type="button" data-quick-add="pto">${icon("pto")}<span><strong>PTO</strong><small>Terminação de cabo DROP</small></span></button>
                        <small>EQUIPAMENTOS ATIVOS</small>
                        <button type="button" data-quick-add="access_point">${icon("active")}<span><strong>Access Point</strong><small>AP Wi-Fi</small></span></button>
                        <button type="button" data-quick-add="ptp">${icon("active")}<span><strong>Rádio PTP</strong><small>Enlace ponto a ponto</small></span></button>
                        <button type="button" data-quick-add="switch">${icon("active")}<span><strong>Switch</strong><small>Comutação Ethernet</small></span></button>
                        <button type="button" data-quick-add="router">${icon("active")}<span><strong>Router</strong><small>Roteamento da torre</small></span></button>
                        <button type="button" data-quick-add="onu">${icon("active")}<span><strong>ONU / ONT</strong><small>Terminação óptica ativa</small></span></button>
                    </div>
                </div>
                <button type="button" data-connect-ports>${icon("connect")}<span>Ligar portas</span></button>
                <button type="button" data-edit-lines>${icon("edit")}<span>Editar linhas</span></button>
                <button type="button" data-open-panel="fibers">${icon("fiber")}<span>Fibras</span></button>
                <div class="tower-toolbar-menu-v0750">
                    <button type="button" data-tower-menu aria-controls="tower-tools-menu-v0750" aria-expanded="false">${icon("menu")}<span>Ferramentas</span>${icon("chevron")}</button>
                    <div id="tower-tools-menu-v0750" class="tower-popover-v0750 tower-tools-menu-v0750" role="menu">
                        <button type="button" data-open-panel="equipment">${icon("inventory")}<span>Inventário</span></button>
                        <button type="button" data-open-panel="matrix">${icon("connect")}<span>Relatório de ligações</span></button>
                        <button type="button" data-open-panel="models">${icon("yaml")}<span>Importar YAML</span></button>
                        <button type="button" data-organize-canvas>${icon("organize")}<span>Organizar equipamentos</span></button>
                        <button type="button" data-fit-canvas>${icon("fit")}<span>Ajustar ao Canvas</span></button>
                        <button type="button" data-export-canvas="png">${icon("sheet")}<span>Exportar PNG</span></button>
                        <button type="button" data-export-canvas="pdf">${icon("sheet")}<span>Exportar PDF</span></button>
                        <button type="button" data-workspace-fullscreen>${icon("fullscreen")}<span>Tela cheia</span></button>
                    </div>
                </div>
            </div>`;
        root.insertBefore(toolbar, root.firstChild);

        qs("[data-structure-info]", toolbar).onclick = () => openStructureInfo(root);
        qsa("[data-quick-add]", toolbar).forEach((button) => {
            button.onclick = () => {
                closeActivePopover(root);
                quickAdd(root, button.dataset.quickAdd);
            };
        });
        qsa("[data-tower-menu]", toolbar).forEach((button) => button.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            toggleToolbarMenu(root, button);
        });
        qsa("[data-open-panel]", toolbar).forEach((button) => button.onclick = () => openPanel(root, button.dataset.openPanel));
        qs("[data-organize-canvas]", toolbar).onclick = () => qs("[data-container-organize]", root)?.click();
        qs("[data-fit-canvas]", toolbar).onclick = () => qs("[data-canvas-zoom-fit]", root)?.click();
        qsa("[data-export-canvas]", toolbar).forEach((button) => button.onclick = () => {
            closeActivePopover(root);
            qs(button.dataset.exportCanvas === "pdf" ? "[data-container-export-pdf]" : "[data-container-export]", root)?.click();
        });
        function setLineMode(active, mode = "") {
            const native = qs("[data-container-lines]", root);
            if (!native) return notify("Editor de conexões não carregado.", true);
            if (native.classList.contains("active") !== active) native.click();
            qs("[data-connect-ports]", toolbar)?.classList.toggle("active", active && mode === "connect");
            qs("[data-edit-lines]", toolbar)?.classList.toggle("active", active && mode === "edit");
            const editLabel = qs("[data-edit-lines] span", toolbar);
            const connectLabel = qs("[data-connect-ports] span", toolbar);
            if (editLabel) editLabel.textContent = active && mode === "edit" ? "Concluir e salvar" : "Editar linhas";
            if (connectLabel) connectLabel.textContent = active && mode === "connect" ? "Concluir ligação" : "Ligar portas";
        }
        qs("[data-connect-ports]", toolbar).onclick = () => {
            const active = !qs("[data-connect-ports]", toolbar).classList.contains("active");
            setLineMode(active, active ? "connect" : "");
            notify(active
                ? "Clique no conector da porta de origem e depois no conector da porta de destino."
                : "Modo de ligação concluído.");
        };
        qs("[data-edit-lines]", toolbar).onclick = () => {
            const active = !qs("[data-edit-lines]", toolbar).classList.contains("active");
            setLineMode(active, active ? "edit" : "");
            notify(active
                ? "Clique numa linha para selecionar. Dê dois cliques para criar um ponto e arraste-o."
                : "Traçado concluído e salvo.");
        };
        qs("[data-workspace-fullscreen]", toolbar).onclick = () => toggleContainerFullscreen(root);
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".tower-toolbar-menu-v0750")) closeActivePopover(root);
        });
        return toolbar;
    }

    function replaceNativeFullscreen(root) {
        const dialog = dialogRoot();
        const native = qs("[data-container-fullscreen]", root);
        if (!dialog || !native || native.dataset.v0750Stable === "1") return;
        const replacement = native.cloneNode(true);
        replacement.dataset.v0750Stable = "1";
        replacement.onclick = (event) => {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            toggleContainerFullscreen(root);
        };
        native.replaceWith(replacement);
    }

    async function toggleContainerFullscreen(root, force) {
        const dialog = dialogRoot();
        if (!dialog) return;
        const active = typeof force === "boolean" ? force : !dialog.classList.contains("master-container-fullscreen");
        dialog.classList.toggle("master-container-fullscreen", active);
        dialog.classList.toggle("map-v0750-css-fullscreen", active);
        try {
            if (active && document.fullscreenElement !== dialog && dialog.requestFullscreen) {
                await dialog.requestFullscreen({ navigationUI: "hide" });
            } else if (!active && document.fullscreenElement && document.exitFullscreen) {
                await document.exitFullscreen();
            }
        } catch (_error) {
            /* O CSS já mantém o modo tela cheia quando a API do navegador não estiver disponível. */
        }
        const label = qs("[data-workspace-fullscreen] span", root);
        if (label) label.textContent = active ? "Desmaximizar" : "Tela cheia";
        window.setTimeout(() => {
            window.dispatchEvent(new Event("resize"));
            qs("[data-canvas-zoom-fit]", root)?.click();
        }, 80);
    }

    function ensureStructureBackdrop(root) {
        const canvas = qs(".master-canvas", root);
        if (!canvas || qs(".tower-structure-backdrop-v0750", canvas)) return;
        const backdrop = document.createElement("div");
        backdrop.className = "tower-structure-backdrop-v0750";
        backdrop.innerHTML = `${icon("tower")}<span>ESTRUTURA DA TORRE</span>`;
        canvas.prepend(backdrop);
    }

    function nodeAction(row, matcher) {
        return qsa("button, a", row || document).find((item) => matcher.test((item.textContent || "").trim()));
    }

    function openInspector(root, node) {
        const id = String(node.dataset.equipmentNode || "");
        if (!id) return;
        movePanelsIntoDrawer(root);
        const drawer = ensureDrawer(root);
        const body = qs(".tower-drawer-body-v0750", drawer);
        qsa(":scope > [data-panel]", body).forEach((panel) => panel.classList.remove("active"));
        let inspector = qs(".tower-inspector-v0750", body);
        if (!inspector) {
            inspector = document.createElement("section");
            inspector.className = "tower-inspector-v0750";
            body.appendChild(inspector);
        }
        const row = qs(`[data-equipment-id="${CSS.escape(id)}"]`, root);
        const name = qs("header strong", node)?.textContent || "Equipamento";
        const type = qs("header small", node)?.textContent || node.dataset.equipmentType || "";
        const ports = qsa("[data-port-id]", node);
        const monitoring = node.dataset.monitoringConfigured === "true";
        inspector.innerHTML = `
            <div class="tower-inspector-title-v0750">${icon("active")}<div><strong>${name}</strong><span>${type}</span></div></div>
            <dl>
                <div><dt>Portas</dt><dd>${ports.length}</dd></div>
                <div><dt>Monitoramento</dt><dd>${monitoring ? "SNMP configurado" : "Não configurado"}</dd></div>
                <div><dt>Modo</dt><dd>${node.dataset.provisioningMode || "manual"}</dd></div>
            </dl>
            <div class="tower-inspector-actions-v0750">
                <button type="button" data-inspector-edit>${icon("edit")}<span>Editar</span></button>
                <button type="button" data-inspector-sheet>${icon("sheet")}<span>Ficha técnica</span></button>
                <button type="button" data-inspector-snmp>${icon("snmp")}<span>SNMP</span></button>
            </div>
            <p>Clique em uma porta no Canvas para iniciar ou concluir uma conexão física.</p>`;
        inspector.classList.add("active");
        qs("[data-inspector-edit]", inspector).onclick = () => nodeAction(row, /^Editar$/i)?.click();
        qs("[data-inspector-sheet]", inspector).onclick = () => nodeAction(row, /^Ficha/i)?.click();
        const snmpSource = qsa("button", row || document).find((button) => /SNMP|monitor/i.test(button.textContent || ""));
        const snmpButton = qs("[data-inspector-snmp]", inspector);
        snmpButton.disabled = !snmpSource;
        snmpButton.onclick = () => snmpSource?.click();
        qs("[data-drawer-title]", drawer).textContent = panelTitle("inspector");
        qs("[data-drawer-subtitle]", drawer).textContent = "Dados, portas e monitoramento SNMP";
        drawer.hidden = false;
        root.classList.add("drawer-open-v0750");
        state.inspectorEquipmentId = id;
        activateCanvas(root);
    }

    function decorateNodes(root) {
        qsa(".master-canvas-node", root).forEach((node) => {
            if (!qs(".tower-node-icon-v0750", node)) {
                const badge = document.createElement("span");
                badge.className = "tower-node-icon-v0750";
                const type = node.dataset.equipmentType || "active";
                badge.innerHTML = icon(type === "dio" ? "dio" : type === "pto" ? "pto" : "active");
                qs("header", node)?.prepend(badge);
            }
            if (node.dataset.v0750Inspector === "1") return;
            node.dataset.v0750Inspector = "1";
            node.addEventListener("click", (event) => {
                if (event.target.closest("[data-port-id], [data-node-edit]")) return;
                qsa(".master-canvas-node.selected-v0750", root).forEach((item) => item.classList.remove("selected-v0750"));
                node.classList.add("selected-v0750");
            });
        });
        const nodes = qsa(".master-canvas-node", root);
        let empty = qs(".tower-empty-v0750", root);
        if (!nodes.length) {
            if (!empty) {
                empty = document.createElement("section");
                empty.className = "tower-empty-v0750";
                empty.innerHTML = `
                    ${icon("tower")}
                    <h3>Monte a estrutura diretamente no Canvas 2D</h3>
                    <p>Comece adicionando um D.I.O, uma PTO e os equipamentos ativos da torre.</p>
                    <div><button type="button" data-empty-add="dio">Adicionar D.I.O</button><button type="button" data-empty-add="pto">Adicionar PTO</button><button type="button" data-empty-add="switch">Adicionar Switch</button></div>`;
                qs('[data-panel="canvas"]', root)?.appendChild(empty);
                qsa("[data-empty-add]", empty).forEach((button) => button.onclick = () => quickAdd(root, button.dataset.emptyAdd));
            }
            empty.hidden = false;
        } else if (empty) {
            empty.hidden = true;
        }
    }

    function ensureWorkspace(root) {
        if (!root) return;
        root.dataset.v0750Workspace = "1";
        root.closest("#container-dialog")?.classList.add("tower-workspace-dialog-v0750");
        installWorkspacePositionLock();
        ensureToolbar(root);
        ensureDrawer(root);
        movePanelsIntoDrawer(root);
        replaceNativeFullscreen(root);
        activateCanvas(root);
        ensureStructureBackdrop(root);
        decorateNodes(root);
        lockWorkspacePosition();
        window.setTimeout(() => qs("[data-canvas-zoom-fit]", root)?.click(), 100);
    }

    function stableFusionFullscreen(dialog) {
        const content = qs("#unifilar-content", dialog);
        const native = qs("[data-fusion-fullscreen]", content || dialog);
        if (!native || native.dataset.v0750Stable === "1") return;
        const replacement = native.cloneNode(true);
        replacement.dataset.v0750Stable = "1";
        replacement.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            const active = !dialog.classList.contains("is-fullscreen");
            dialog.classList.toggle("is-fullscreen", active);
            dialog.classList.toggle("map-v0750-css-fullscreen", active);
            replacement.textContent = active ? "Desmaximizar" : "Tela cheia";
            replacement.setAttribute("aria-pressed", String(active));
            window.setTimeout(() => {
                window.dispatchEvent(new Event("resize"));
                fitFusion(dialog);
            }, 80);
        }, true);
        native.replaceWith(replacement);
    }

    function fitFusion(dialog) {
        const content = qs("#unifilar-content", dialog);
        if (!content) return;
        const buttons = qsa("button", content);
        const fit = buttons.find((button) => /^(Ajustar|Auto)$/i.test((button.textContent || "").trim()));
        fit?.click();
    }

    function compactFusion(dialog) {
        if (!dialog?.open) return;
        dialog.classList.add("fusion-v0750");
        const content = qs("#unifilar-content", dialog);
        if (content) content.dataset.v0750Compact = "1";
        stableFusionFullscreen(dialog);
        clearTimeout(state.fusionFitTimer);
        state.fusionFitTimer = window.setTimeout(() => fitFusion(dialog), 140);
        document.dispatchEvent(new CustomEvent("map:fusion-rendered", {
            detail: { root: dialog },
        }));
    }

    function installDialogGuards() {
        const container = dialogRoot();
        if (container && container.dataset.v0750Guard !== "1") {
            container.dataset.v0750Guard = "1";
            container.addEventListener("cancel", (event) => {
                if (!container.classList.contains("master-container-fullscreen")) return;
                event.preventDefault();
                toggleContainerFullscreen(workspaceRoot(), false);
            });
            container.addEventListener("close", () => {
                container.classList.remove("master-container-fullscreen", "map-v0750-css-fullscreen");
                container.scrollTop = 0;
                const root = workspaceRoot();
                if (root) closeDrawer(root);
            });
        }
        const fusion = qs("#unifilar-dialog");
        if (fusion && fusion.dataset.v0750Guard !== "1") {
            fusion.dataset.v0750Guard = "1";
            fusion.addEventListener("cancel", (event) => {
                if (!fusion.classList.contains("is-fullscreen")) return;
                event.preventDefault();
                fusion.classList.remove("is-fullscreen", "map-v0750-css-fullscreen");
                window.setTimeout(() => fitFusion(fusion), 60);
            });
            fusion.addEventListener("close", () => {
                fusion.classList.remove("is-fullscreen", "map-v0750-css-fullscreen");
            });
        }
    }

    function wrapFusionLoader() {
        const networkMap = window.networkMap;
        if (!networkMap?.showUnifilar || networkMap.showUnifilar.v0750Wrapped) return false;
        const original = networkMap.showUnifilar.bind(networkMap);
        const wrapped = async (...args) => {
            const result = await original(...args);
            window.requestAnimationFrame(() => compactFusion(qs("#unifilar-dialog")));
            return result;
        };
        wrapped.v0750Wrapped = true;
        networkMap.showUnifilar = wrapped;
        return true;
    }

    function init() {
        installDialogGuards();
        document.addEventListener("map:container-rendered", () => {
            ensureWorkspace(workspaceRoot());
        });
        document.addEventListener("map:container-opening", resetWorkspaceForOpen);
        wrapFusionLoader();
        window.setTimeout(() => ensureWorkspace(workspaceRoot()), 450);
        window.setTimeout(() => {
            installDialogGuards();
            wrapFusionLoader();
        }, 900);
        window.mapTowerWorkspaceV0750 = {
            version: VERSION,
            refresh: () => ensureWorkspace(workspaceRoot()),
            openPanel: (mode) => openPanel(workspaceRoot(), mode),
        };
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
