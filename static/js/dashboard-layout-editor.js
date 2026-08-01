(function () {
    "use strict";

    const saveButton = document.getElementById("editor-save");
    const bannerInput = document.getElementById("editor-banner-text");
    const status = document.getElementById("editor-status");
    if (!saveButton) return;

    const gridEl = document.getElementById("widget-zone-grid");

    // Cada item já sai do servidor com gs-x/gs-y/gs-w/gs-h (posição/tamanho
    // salvos, ou padrão calculado por auto-flow) e um gs-id igual ao
    // data-widget — o Gridstack lê esses atributos sozinho ao inicializar.
    let grid = null;
    if (gridEl && window.GridStack) {
        grid = GridStack.init({
            column: 12,
            cellHeight: 90,
            margin: 8,
            handle: ".widget-drag-handle",
            resizable: { handles: "se" },
        }, gridEl);
    } else if (status) {
        status.textContent = "Não foi possível carregar a biblioteca de arrastar/redimensionar (Gridstack). Mostrar/esconder e salvar continuam funcionando.";
        status.classList.add("error");
    }

    document.querySelectorAll(".widget-visibility-toggle").forEach((toggle) => {
        toggle.addEventListener("change", () => {
            const content = toggle.closest(".grid-stack-item-content");
            if (content) content.classList.toggle("widget-hidden", !toggle.checked);
        });
    });

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }

    // Sem Gridstack carregado (falha de CDN), não dá pra ler posição/tamanho
    // em tempo real — preserva o que já veio do servidor pra não perder o
    // layout salvo só porque a lib de arrastar não carregou.
    function currentNodesFallback() {
        const result = [];
        if (!gridEl) return result;
        gridEl.querySelectorAll(":scope > .grid-stack-item").forEach((item) => {
            result.push({
                id: item.dataset.widget,
                x: parseInt(item.getAttribute("gs-x"), 10) || 0,
                y: parseInt(item.getAttribute("gs-y"), 10) || 0,
                w: parseInt(item.getAttribute("gs-w"), 10) || 1,
                h: parseInt(item.getAttribute("gs-h"), 10) || 1,
            });
        });
        return result;
    }

    function collectLayout() {
        const widgetLayout = {};
        const nodes = grid ? grid.save(false) : currentNodesFallback();
        nodes.forEach((node) => {
            const key = node.id;
            if (!key) return;
            widgetLayout[key] = { x: node.x, y: node.y, w: node.w, h: node.h, hidden: false };
        });
        document.querySelectorAll(".widget-visibility-toggle").forEach((toggle) => {
            const item = toggle.closest(".grid-stack-item");
            const key = item?.dataset.widget;
            if (key && widgetLayout[key]) widgetLayout[key].hidden = !toggle.checked;
        });
        return {
            widget_layout: widgetLayout,
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
