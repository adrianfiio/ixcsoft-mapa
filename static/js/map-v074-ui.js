(function () {
    "use strict";

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
    const canEdit = document.body.dataset.canEdit === "true";
    const state = { contextLatLng: null };

    function icon(name) {
        const icons = {
            labels: '<svg viewBox="0 0 24 24"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"></path><circle cx="12" cy="12" r="2.8"></circle><path d="M4 4l16 16"></path></svg>',
            cto: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="14" rx="3"></rect><path d="M8 8h8M8 12h8M8 18v3m8-3v3"></path></svg>',
            box: '<svg viewBox="0 0 24 24"><path d="M7 3h10l4 5v8l-4 5H7l-4-5V8z"></path><path d="M8 9h8M8 13h8M8 17h8"></path></svg>',
            pop: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M7 8h10M7 12h10M7 16h6"></path></svg>',
            rack: '<svg viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"></rect><path d="M8 6h8M8 11h8M8 16h8"></path></svg>',
            tower: '<svg viewBox="0 0 24 24"><path d="M12 2 6 22m6-20 6 20M8 15h8M9 10h6M5 22h14"></path></svg>',
            pole: '<svg viewBox="0 0 24 24"><path d="M4 7h16M12 3v18M7 21h10M8 7l4 5 4-5"></path></svg>',
            cable: '<svg viewBox="0 0 24 24"><path d="M3 17c5 0 5-10 10-10s4 7 8 7"></path><circle cx="3" cy="17" r="2"></circle><circle cx="21" cy="14" r="2"></circle></svg>',
        };
        return icons[name] || icons.box;
    }

    function waitFor(selector, callback, attempts = 120) {
        const item = qs(selector);
        if (item) return callback(item);
        if (attempts <= 0) return;
        window.setTimeout(() => waitFor(selector, callback, attempts - 1), 50);
    }

    function syncLabelsButton(button) {
        const checkbox = qs("#layer-labels");
        const enabled = checkbox?.checked !== false;
        button.classList.toggle("active", enabled);
        button.setAttribute("aria-pressed", String(enabled));
        const label = qs("span", button);
        if (label) label.textContent = enabled ? "Ocultar nomes" : "Mostrar nomes";
        button.title = enabled ? "Ocultar nomes dos elementos e cabos" : "Mostrar nomes dos elementos e cabos";
    }

    function installSidebarEnhancements(nav) {
        if (nav.dataset.v074 === "1") return;
        nav.dataset.v074 = "1";
        // O controle de nomes pertence à barra inferior do mapa.
        qsa("[data-v074-labels]", nav).forEach((button) => button.remove());

        const colors = ["#38bdf8", "#22d3ee", "#a78bfa", "#34d399", "#fb7185", "#fbbf24", "#c084fc", "#2dd4bf"];
        qsa(":scope > a, :scope > button", nav).forEach((item, index) => {
            item.style.setProperty("--v074-nav-color", colors[index % colors.length]);
        });
    }

    function cleanupToolbar(toolbar) {
        qsa("[data-v0722-menu-toggle] b", toolbar).forEach((node) => node.remove());
        qsa("button", toolbar).forEach((button) => {
            if (!button.title) button.title = qs("span", button)?.textContent?.trim() || button.getAttribute("aria-label") || "Ferramenta";
        });
    }

    function contextItems() {
        return [
            ["cto", "CTO", "cto"],
            ["splice_box", "CEO", "box"],
            ["cdo", "CDO", "box"],
            ["cpd", "CPD/POP", "pop"],
            ["rack", "Rack", "rack"],
            ["tower", "Torre", "tower"],
            ["pole", "Poste", "pole"],
            ["cable", "Cabo", "cable"],
        ];
    }

    function ensureContextMenu() {
        let menu = qs("#map-context-v074");
        if (menu) return menu;
        menu = document.createElement("section");
        menu.id = "map-context-v074";
        menu.className = "map-context-v074";
        menu.hidden = true;
        menu.innerHTML = `<header><strong>Adicionar ao mapa</strong><button type="button" aria-label="Fechar">×</button></header><div>${contextItems().map(([tool, label, iconName]) => `<button type="button" data-context-tool="${tool}">${icon(iconName)}<span>${label}</span></button>`).join("")}</div>`;
        document.body.appendChild(menu);
        qs("header button", menu).onclick = closeContextMenu;
        qsa("[data-context-tool]", menu).forEach((button) => {
            button.onclick = () => {
                const tool = button.dataset.contextTool;
                const source = qs(`#map-toolbar-v072 [data-v0722-tool="${CSS.escape(tool)}"]`)
                    || qs(`[data-tool="${CSS.escape(tool)}"]`)
                    || qs(`[data-quick-tool="${CSS.escape(tool)}"]`);
                closeContextMenu();
                source?.click();
                const map = window.networkMap?.map;
                const latlng = state.contextLatLng;
                if (map && latlng) {
                    window.setTimeout(() => map.fire("click", { latlng, sourceTarget: map }), 80);
                }
            };
        });
        return menu;
    }

    function closeContextMenu() {
        const menu = qs("#map-context-v074");
        if (menu) menu.hidden = true;
    }

    function openContextMenu(event) {
        if (!canEdit || !qs("#project-select")?.value) return;
        if (event.target.closest("dialog, button, a, input, select, textarea, .leaflet-popup, .map-toolbar-v072, #map-sidebar")) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        qs("#map .map-context-menu")?.setAttribute("hidden", "hidden");
        const map = window.networkMap?.map;
        if (!map) return;
        state.contextLatLng = map.mouseEventToLatLng(event);
        const menu = ensureContextMenu();
        menu.hidden = false;
        const margin = 10;
        const width = menu.offsetWidth || 220;
        const height = menu.offsetHeight || 330;
        menu.style.left = `${Math.max(margin, Math.min(window.innerWidth - width - margin, event.clientX))}px`;
        menu.style.top = `${Math.max(margin, Math.min(window.innerHeight - height - margin, event.clientY))}px`;
    }

    function installContextMenu(mapRoot) {
        if (mapRoot.dataset.contextV074 === "1") return;
        mapRoot.dataset.contextV074 = "1";
        mapRoot.addEventListener("contextmenu", openContextMenu);
        document.addEventListener("click", (event) => {
            if (!event.target.closest("#map-context-v074")) closeContextMenu();
        });
        document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeContextMenu(); });
        window.networkMap?.map?.on?.("movestart zoomstart", closeContextMenu);
    }


    function syncContainerPanel(root) {
        const active = qs("[data-tab].active", root)?.dataset.tab
            || qs("[data-panel].active", root)?.dataset.panel
            || "equipment";
        root.dataset.activePanel = active;
    }

    function compactContainerWorkspace(root = qs("#map-master-container")) {
        if (!root) return;
        const toolbar = qs(".master-container-toolbar", root);
        const tabs = qs(".master-container-tabs", root);
        if (!toolbar || !tabs) return;

        if (root.dataset.compactV074 !== "1") {
            root.dataset.compactV074 = "1";
            const organize = qs("[data-container-organize]", toolbar);
            const lines = qs("[data-container-lines]", toolbar);
            [organize, lines].filter(Boolean).forEach((button) => button.dataset.panelScope = "canvas");

            const more = document.createElement("div");
            more.className = "master-container-more";
            more.innerHTML = '<button type="button" data-container-more-toggle>Mais</button><div class="master-container-more-menu"></div>';
            const menu = qs(".master-container-more-menu", more);
            const fullscreen = qs("[data-container-fullscreen]", toolbar);
            toolbar.insertBefore(more, fullscreen || null);

            [qs('[data-tab="matrix"]', root), qs('[data-tab="models"]', root), qs("[data-container-export]", toolbar), qs("[data-container-revision]", toolbar)]
                .filter(Boolean)
                .forEach((button) => menu.appendChild(button));

            qs("[data-container-more-toggle]", more).onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                menu.classList.toggle("open");
            };
            menu.addEventListener("click", () => menu.classList.remove("open"));
            document.addEventListener("click", (event) => {
                if (!event.target.closest(".master-container-more")) menu.classList.remove("open");
            });
            qsa("[data-tab]", root).forEach((button) => {
                button.addEventListener("click", () => window.setTimeout(() => syncContainerPanel(root), 0));
            });
        }
        syncContainerPanel(root);
    }

    function centerDialog(dialog) {
        if (!dialog?.open || dialog.classList.contains("is-fullscreen") || dialog.classList.contains("master-container-fullscreen")) return;
        dialog.removeAttribute("data-user-positioned");
        dialog.style.left = "50%";
        dialog.style.top = "50%";
        dialog.style.margin = "0";
        dialog.style.transform = "translate(-50%, -50%)";
    }

    function installDialogCentering() {
        ["#unifilar-dialog", "#container-dialog", "#map-master-asset-sheet"].forEach((selector) => {
            const dialog = qs(selector);
            if (!dialog || dialog.dataset.centerV074 === "1") return;
            dialog.dataset.centerV074 = "1";
            new MutationObserver(() => {
                if (!dialog.open) return;
                window.requestAnimationFrame(() => centerDialog(dialog));
                if (selector === "#container-dialog") {
                    window.setTimeout(() => compactContainerWorkspace(), 60);
                    window.setTimeout(() => compactContainerWorkspace(), 250);
                }
            }).observe(dialog, { attributes: true, attributeFilter: ["open"] });
            dialog.addEventListener("close", () => {
                dialog.removeAttribute("data-user-positioned");
                dialog.style.removeProperty("left");
                dialog.style.removeProperty("top");
                dialog.style.removeProperty("margin");
                dialog.style.removeProperty("transform");
            });
        });
    }

    function init() {
        waitFor("#map-nav-v072", installSidebarEnhancements);
        waitFor("#map-toolbar-v072", cleanupToolbar);
        waitFor("#map", installContextMenu);
        installDialogCentering();
        document.addEventListener("map:container-rendered", () => compactContainerWorkspace());
        window.setTimeout(() => compactContainerWorkspace(), 400);
        window.setTimeout(installDialogCentering, 600);
        window.setTimeout(installDialogCentering, 1600);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
}());
