(function () {
    "use strict";
    const VERSION = "0.77.1";

    function qs(selector, root = document) { return root?.querySelector?.(selector) || null; }
    function qsa(selector, root = document) { return [...(root?.querySelectorAll?.(selector) || [])]; }

    function expandSidebarOnLoad() {
        try { localStorage.setItem("mapSidebarV072Collapsed", "0"); } catch (_error) {}
        const sidebar = qs("#map-sidebar");
        if (!sidebar) return;
        sidebar.classList.remove("collapsed", "master-minimized", "v072-collapsed");
        document.body.classList.remove("map-sidebar-collapsed-v0722");
        const toggle = qs("#collapse-sidebar");
        if (toggle) {
            toggle.textContent = "‹";
            toggle.title = "Recolher menu";
            toggle.setAttribute("aria-label", "Recolher menu");
        }
    }

    function removeLegacyLinksShortcut() {
        qsa("[data-v072-links], [data-v0722-links]").forEach((button) => {
            button.hidden = true;
            button.setAttribute("aria-hidden", "true");
            button.remove();
        });
    }

    function syncCtoForm() {
        const form = qs("#element-form");
        if (!form || String(form.elements.element_type?.value || "") !== "cto") return;
        const capacity = form.elements.cto_capacity;
        if (!capacity) return;
        let value = Number(capacity.value || 8);
        value = value >= 16 ? 16 : 8;
        capacity.value = String(value);
        if (form.elements.splitter_ratio) form.elements.splitter_ratio.value = value === 16 ? "1:16" : "1:8";
        if (form.elements.splitter_ports) form.elements.splitter_ports.value = String(value);
        if (form.elements.splitter_input_cable_id) form.elements.splitter_input_cable_id.value = "";
        if (form.elements.splitter_input_fiber_id) form.elements.splitter_input_fiber_id.value = "";
    }

    function syncPoleForm() {
        const form = qs("#element-form");
        if (!form) return;
        const isPole = String(form.elements.element_type?.value || "") === "pole";
        const status = form.elements.status;
        const statusLabel = status?.closest("label");
        if (statusLabel) statusLabel.hidden = isPole;
        if (isPole && status) status.value = "no_data";
    }

    function protectEquipmentDialogBackdrop(event) {
        const dialog = event.target;
        if (!(dialog instanceof HTMLDialogElement) || !dialog.open || event.target !== dialog) return;
        const protectedDialog = dialog.matches(
            ".map-master-equipment-dialog, #map-master-equipment-create, #map-master-equipment-edit, #map-rack-equipment-v07542, .v07542-equipment-dialog"
        ) || (dialog.id === "map-v07539-modal" && Boolean(dialog.querySelector("[data-equipment-form], [data-equipment-create-form]")));
        if (!protectedDialog) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation?.();
    }

    function decorateContainer() {
        const dialog = qs("#container-dialog");
        const root = qs("#map-master-container", dialog);
        if (!dialog || !root) return;
        const type = String(dialog.dataset.containerType || "").toLowerCase();
        root.dataset.v077Container = type;
        qsa(".master-canvas-node", root).forEach((node) => {
            const count = qsa("[data-port-id]", node).length;
            node.style.setProperty("--v077-port-count", String(count));
        });
    }

    function installDialogSync() {
        const dialog = qs("#element-dialog");
        const form = qs("#element-form");
        if (!dialog || !form) return;
        form.elements.cto_capacity?.addEventListener("change", syncCtoForm);
        const refresh = () => window.setTimeout(() => { syncCtoForm(); syncPoleForm(); }, 0);
        new MutationObserver(refresh).observe(dialog, { attributes: true, attributeFilter: ["open"] });
        document.addEventListener("map:element-dialog-opened", refresh);
        dialog.addEventListener("click", () => window.setTimeout(() => { syncCtoForm(); syncPoleForm(); }, 0));
    }

    function installRuntimeObserver() {
        const observer = new MutationObserver(() => {
            removeLegacyLinksShortcut();
            decorateContainer();
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    document.addEventListener("map:container-rendered", decorateContainer);
    document.addEventListener("map:container-opening", () => window.setTimeout(decorateContainer, 0));
    document.addEventListener("pointerdown", protectEquipmentDialogBackdrop, true);
    document.addEventListener("click", protectEquipmentDialogBackdrop, true);

    function init() {
        expandSidebarOnLoad();
        removeLegacyLinksShortcut();
        installDialogSync();
        installRuntimeObserver();
        decorateContainer();
        document.body.dataset.mapV077 = VERSION;
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})();
