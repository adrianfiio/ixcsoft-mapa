(function () {
    "use strict";

    const saveButton = document.getElementById("editor-save");
    const bannerInput = document.getElementById("editor-banner-text");
    const status = document.getElementById("editor-status");
    if (!saveButton || !window.Sortable) return;

    const zones = ["widget-zone-metrics", "widget-zone-col-1", "widget-zone-col-2"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);

    zones.forEach((zone) => {
        Sortable.create(zone, {
            animation: 150,
            handle: ".widget-drag-handle",
            ghostClass: "sortable-ghost",
        });
    });

    document.querySelectorAll(".widget-visibility-toggle").forEach((toggle) => {
        toggle.addEventListener("change", () => {
            const article = toggle.closest("[data-widget]");
            if (article) article.classList.toggle("widget-hidden", !toggle.checked);
        });
    });

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }

    function collectLayout() {
        const widgetOrder = [];
        const hiddenWidgets = [];
        zones.forEach((zone) => {
            zone.querySelectorAll("[data-widget]").forEach((article) => {
                const key = article.dataset.widget;
                widgetOrder.push(key);
                const toggle = article.querySelector(".widget-visibility-toggle");
                if (toggle && !toggle.checked) hiddenWidgets.push(key);
            });
        });
        return {
            widget_order: widgetOrder,
            hidden_widgets: hiddenWidgets,
            banner_text: (bannerInput?.value || "").trim(),
        };
    }

    function setStatus(message, kind) {
        status.textContent = message;
        status.classList.remove("success", "error");
        if (kind) status.classList.add(kind);
    }

    saveButton.addEventListener("click", async () => {
        saveButton.disabled = true;
        setStatus("Salvando...", "");
        try {
            const response = await fetch(window.location.pathname, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken(),
                    Accept: "application/json",
                },
                body: JSON.stringify(collectLayout()),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || !data.success) throw new Error(data.error || `Erro HTTP ${response.status}`);
            setStatus("Layout salvo.", "success");
        } catch (error) {
            setStatus(error.message, "error");
        } finally {
            saveButton.disabled = false;
        }
    });
})();
