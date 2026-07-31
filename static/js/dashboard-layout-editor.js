(function () {
    "use strict";

    const saveButton = document.getElementById("editor-save");
    const bannerInput = document.getElementById("editor-banner-text");
    const status = document.getElementById("editor-status");
    if (!saveButton) return;

    const zones = ["widget-zone-metrics", "widget-zone-col-1", "widget-zone-col-2"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);

    // O CSS "order" fica desligado em modo de edição (ver .dashboard-edit-mode
    // em app.css) porque ele brigaria com o SortableJS: o Sortable move nós de
    // verdade no DOM ao arrastar, mas se "order" continuasse fixo por CSS o
    // item voltaria pra posição antiga visualmente ao soltar. Por isso a ordem
    // salva (guardada em --order) precisa ser aplicada aqui, reordenando o DOM
    // de verdade antes de inicializar o arrastar.
    zones.forEach((zone) => {
        const items = Array.from(zone.querySelectorAll(":scope > [data-widget]"));
        items
            .sort((a, b) => {
                const orderA = parseInt(a.style.getPropertyValue("--order"), 10) || 0;
                const orderB = parseInt(b.style.getPropertyValue("--order"), 10) || 0;
                return orderA - orderB;
            })
            .forEach((item) => zone.appendChild(item));
    });

    if (window.Sortable) {
        zones.forEach((zone) => {
            Sortable.create(zone, {
                animation: 150,
                handle: ".widget-drag-handle",
                ghostClass: "sortable-ghost",
            });
        });
    } else if (status) {
        status.textContent = "Não foi possível carregar a biblioteca de arrastar (SortableJS). Mostrar/esconder e salvar continuam funcionando.";
        status.classList.add("error");
    }

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
