(function () {
    "use strict";

    const VERSION = "0.75.7";
    const state = {
        containerData: null,
        containerMenuPoint: null,
        fusionMenuPoint: null,
        activeElementMenu: null,
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function csrfToken() {
        const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
    }

    async function request(path, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(path, { credentials: "same-origin", ...options, headers });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function notify(message, error = false) {
        window.networkMap?.notify?.(message, error);
    }

    function ensureConfirmDialog() {
        let dialog = qs("#map-v0757-confirm-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-v0757-confirm-dialog";
        dialog.className = "editor-dialog map-v0757-action-dialog";
        dialog.innerHTML = `
            <form method="dialog">
                <header><div><h2 data-title>Confirmar ação</h2><p data-message></p></div><button type="button" data-close aria-label="Fechar">×</button></header>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button" data-confirm>Confirmar</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        return dialog;
    }

    function confirmAction({ title = "Confirmar ação", message = "Deseja continuar?", confirmLabel = "Confirmar", cancelLabel = "Cancelar", danger = false } = {}) {
        const dialog = ensureConfirmDialog();
        qs("[data-title]", dialog).textContent = title;
        qs("[data-message]", dialog).textContent = message;
        const confirm = qs("[data-confirm]", dialog);
        const cancel = qs("[data-cancel]", dialog);
        confirm.textContent = confirmLabel;
        cancel.textContent = cancelLabel;
        confirm.classList.toggle("danger", danger);
        if (!dialog.open) dialog.showModal();
        return new Promise((resolve) => {
            let completed = false;
            const finish = (value) => {
                if (completed) return;
                completed = true;
                if (dialog.open) dialog.close();
                resolve(value);
            };
            qs("form", dialog).onsubmit = (event) => { event.preventDefault(); finish(true); };
            cancel.onclick = () => finish(false);
            qs("[data-close]", dialog).onclick = () => finish(false);
            dialog.oncancel = (event) => { event.preventDefault(); finish(false); };
        });
    }

    function ensureTextDialog() {
        let dialog = qs("#map-v0757-text-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-v0757-text-dialog";
        dialog.className = "editor-dialog map-v0757-note-dialog";
        dialog.innerHTML = `
            <form>
                <header><div><h2 data-title>Nota técnica</h2><p data-help>Escreva livremente. Quebras de linha são preservadas.</p></div><button type="button" data-close aria-label="Fechar">×</button></header>
                <label><span data-label>Texto da nota</span><textarea name="text" rows="12" maxlength="20000" required></textarea></label>
                <small data-counter>0 caracteres</small>
                <footer><button type="button" data-cancel>Cancelar</button><button type="submit" class="primary-button">Salvar nota</button></footer>
            </form>`;
        document.body.appendChild(dialog);
        const textarea = qs("textarea", dialog);
        textarea.addEventListener("input", () => { qs("[data-counter]", dialog).textContent = `${textarea.value.length} caracteres`; });
        return dialog;
    }

    function editLongText({ title = "Nota técnica", label = "Texto da nota", value = "" } = {}) {
        const dialog = ensureTextDialog();
        qs("[data-title]", dialog).textContent = title;
        qs("[data-label]", dialog).textContent = label;
        const textarea = qs("textarea", dialog);
        textarea.value = value || "";
        qs("[data-counter]", dialog).textContent = `${textarea.value.length} caracteres`;
        if (!dialog.open) dialog.showModal();
        window.setTimeout(() => { textarea.focus(); textarea.setSelectionRange(textarea.value.length, textarea.value.length); }, 30);
        return new Promise((resolve) => {
            let completed = false;
            const finish = (result) => {
                if (completed) return;
                completed = true;
                if (dialog.open) dialog.close();
                resolve(result);
            };
            qs("form", dialog).onsubmit = (event) => {
                event.preventDefault();
                const text = textarea.value.trim();
                if (!text) return textarea.focus();
                finish(text);
            };
            qs("[data-cancel]", dialog).onclick = () => finish(null);
            qs("[data-close]", dialog).onclick = () => finish(null);
            dialog.oncancel = (event) => { event.preventDefault(); finish(null); };
        });
    }

    function elementKind(feature) {
        const properties = feature?.properties || feature || {};
        const type = String(properties.tipo || properties.element_type || "").toLowerCase();
        const subtype = String(properties.subtype || properties.element_subtype || properties.metadata?.import_subtype || "").toLowerCase();
        if (["cpd", "pop"].includes(subtype)) return "core";
        if (["rack", "tower"].includes(type)) return "core";
        if (type === "splice_box") return "splice";
        if (type === "cto") return "cto";
        if (type === "pto") return "pto";
        return "unknown";
    }

    async function reviewCableDirection({ origin, destination } = {}) {
        const rank = { core: 0, splice: 1, cto: 2, pto: 3, unknown: 99 };
        const originKind = elementKind(origin);
        const destinationKind = elementKind(destination);
        if (originKind === "unknown" || destinationKind === "unknown") return false;
        if (rank[originKind] <= rank[destinationKind]) return false;
        const originName = origin?.properties?.nome || origin?.properties?.name || "origem";
        const destinationName = destination?.properties?.nome || destination?.properties?.name || "destino";
        return confirmAction({
            title: "Rota possivelmente invertida",
            message: `O cabo foi desenhado de ${originName} para ${destinationName}. Pela hierarquia óptica, a direção mais provável é o contrário. Deseja inverter origem, destino e todo o traçado?`,
            confirmLabel: "Inverter rota",
            cancelLabel: "Manter como desenhei",
        });
    }

    function containerIdentity(data = state.containerData) {
        const dialog = qs("#container-dialog");
        const type = String(data?.container?.type || dialog?.dataset.containerType || "tower").toLowerCase();
        const name = data?.container?.name || dialog?.dataset.containerName || "Estrutura";
        return { type: type === "rack" ? "rack" : "tower", name };
    }

    function structureIcon(type) {
        return type === "rack"
            ? '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="1"></rect><path d="M4 9h16M4 15h16M8 6h8M8 12h8M8 18h8"></path></svg>'
            : '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="2"></circle><path d="M12 9 7 22m5-13 5 13M9 16h6M7 5a7 7 0 0 0 0 5m10-5a7 7 0 0 1 0 5M4 3a11 11 0 0 0 0 9m16-9a11 11 0 0 1 0 9"></path></svg>';
    }

    function updateContainerIdentity(data = state.containerData) {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        if (!root || !dialog) return;
        const identity = containerIdentity(data);
        dialog.dataset.containerType = identity.type;
        dialog.dataset.containerName = identity.name;
        dialog.classList.toggle("map-v0757-rack", identity.type === "rack");
        dialog.classList.toggle("map-v0757-tower", identity.type === "tower");

        const title = qs(".tower-workspace-title-v0750", root);
        if (title) {
            const strong = qs("strong", title);
            const small = qs("small", title);
            const icon = qs(":scope > svg", title);
            if (icon) icon.outerHTML = structureIcon(identity.type);
            if (strong) strong.textContent = identity.type === "rack" ? "Editor técnico do Rack" : "Editor técnico da Torre";
            if (small) small.textContent = `${identity.name} · Canvas 2D, portas, cabos e conexões`;
        }

        let close = qs("[data-workspace-close-v0757]", root);
        if (!close) {
            close = document.createElement("button");
            close.type = "button";
            close.dataset.workspaceCloseV0757 = "true";
            close.className = "tower-workspace-close-v0757";
            close.title = "Fechar editor técnico";
            close.setAttribute("aria-label", "Fechar editor técnico");
            close.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"></path></svg>';
            qs(".tower-workspace-actions-v0750", root)?.appendChild(close);
            close.onclick = () => dialog.close();
        }

        const backdrop = qs(".tower-structure-backdrop-v0750", root);
        if (backdrop) {
            backdrop.classList.toggle("rack", identity.type === "rack");
            backdrop.innerHTML = `${structureIcon(identity.type)}<span>${identity.type === "rack" ? "ESTRUTURA DO RACK" : "ESTRUTURA DA TORRE"}</span>`;
        }

        const empty = qs(".tower-empty-v0750", root);
        if (empty) {
            const heading = qs("h3", empty);
            const paragraph = qs("p", empty);
            const emptyIcon = qs(":scope > svg", empty);
            if (emptyIcon) emptyIcon.outerHTML = structureIcon(identity.type);
            if (heading) heading.textContent = identity.type === "rack" ? "Monte o rack diretamente no Canvas 2D" : "Monte a torre diretamente no Canvas 2D";
            if (paragraph) paragraph.textContent = identity.type === "rack"
                ? "Comece adicionando uma OLT, um DIO ou os equipamentos internos permitidos no rack."
                : "Comece adicionando um DIO, uma PTO ou os equipamentos ativos da torre.";
            const buttons = qs("div", empty);
            if (buttons && identity.type === "rack") buttons.innerHTML = '<button type="button" data-empty-add="olt">Adicionar OLT</button><button type="button" data-empty-add="dio">Adicionar DIO</button><button type="button" data-empty-add="switch">Adicionar Switch</button>';
        }

        const addMenu = qs("#tower-add-menu-v0750", root);
        const extraTypes = [
            ["olt", "OLT", "Chassi óptico do rack"],
            ["firewall", "Firewall", "Segurança e borda"],
            ["other", "Outro", "Equipamento personalizado"],
        ];
        extraTypes.forEach(([type, label, help]) => {
            if (!addMenu || qs(`[data-quick-add="${type}"]`, addMenu)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.quickAdd = type;
            button.innerHTML = `<span class="map-v0757-generic-equipment">＋</span><span><strong>${label}</strong><small>${help}</small></span>`;
            button.onclick = () => {
                qs("[data-container-add]", root)?.click();
                window.setTimeout(() => {
                    const dialog = qs("#map-master-equipment-create");
                    const select = qs("select[name='equipment_type']", dialog);
                    if (!select || ![...select.options].some((option) => option.value === type)) return;
                    select.value = type;
                    select.dispatchEvent(new Event("change"));
                }, 0);
            };
            addMenu.appendChild(button);
        });
        const rackAllowed = new Set(["olt", "dio", "switch", "router", "firewall", "pto", "other"]);
        qsa("[data-quick-add]", root).forEach((button) => {
            button.hidden = identity.type === "rack" && !rackAllowed.has(String(button.dataset.quickAdd));
        });
        qsa("[data-empty-add]", empty || document.createElement("div")).forEach((button) => {
            button.onclick = () => qs(`[data-quick-add="${button.dataset.emptyAdd}"]`, root)?.click();
        });
    }

    async function refreshContainer() {
        const id = Number(qs("#container-dialog")?.dataset.elementId || 0);
        if (id && window.networkMap?.manageContainer) await window.networkMap.manageContainer(id);
    }

    async function loadContainerLayout() {
        const id = Number(qs("#container-dialog")?.dataset.elementId || 0);
        if (!id) throw new Error("Estrutura não identificada.");
        const data = await request(`/api/map/elements/${id}/container-layout-v3/`);
        return { id, layout: { ...(data.layout || {}), notes: [...(data.layout?.notes || [])] } };
    }

    async function saveContainerLayout(id, layout) {
        await request(`/api/map/elements/${id}/container-layout-v3/`, { method: "PATCH", body: JSON.stringify({ layout }) });
        await refreshContainer();
    }

    async function editContainerNote(index) {
        const { id, layout } = await loadContainerLayout();
        const note = layout.notes[index];
        if (!note) return;
        const text = await editLongText({ title: "Editar nota técnica", value: note.text || "" });
        if (text === null) return;
        layout.notes[index] = { ...note, text };
        await saveContainerLayout(id, layout);
        notify("Nota atualizada.");
    }

    async function deleteContainerNote(index) {
        const accepted = await confirmAction({ title: "Excluir nota", message: "A nota será removida deste Canvas.", confirmLabel: "Excluir nota", danger: true });
        if (!accepted) return;
        const { id, layout } = await loadContainerLayout();
        if (!layout.notes[index]) return;
        layout.notes.splice(index, 1);
        await saveContainerLayout(id, layout);
        notify("Nota excluída.");
    }

    async function addContainerNote() {
        if (!state.containerMenuPoint) return;
        const text = await editLongText({ title: "Nova nota técnica" });
        if (text === null) return;
        const { id, layout } = await loadContainerLayout();
        layout.notes.push({ id: `n${Date.now()}`, text, x: Math.round(state.containerMenuPoint.x), y: Math.round(state.containerMenuPoint.y) });
        await saveContainerLayout(id, layout);
        notify("Nota adicionada ao Canvas.");
    }

    async function loadFusionLayout() {
        const dialog = qs("#unifilar-dialog");
        const id = Number(dialog?.dataset.elementId || 0);
        if (!id) throw new Error("Caixa óptica não identificada.");
        const data = await request(`/api/map/elements/${id}/layout/`);
        return { id, layout: { ...(data.layout || {}), notes: [...(data.layout?.notes || [])] } };
    }

    async function refreshFusion(id) {
        const dialog = qs("#unifilar-dialog");
        if (dialog?.open) dialog.close();
        await window.networkMap?.showUnifilar?.(id);
    }

    async function editFusionNote(noteId) {
        const { id, layout } = await loadFusionLayout();
        const note = layout.notes.find((item) => String(item.id) === String(noteId));
        if (!note) return;
        const text = await editLongText({ title: "Editar nota da fusão", value: note.text || "" });
        if (text === null) return;
        layout.notes = layout.notes.map((item) => String(item.id) === String(noteId) ? { ...item, text } : item);
        await request(`/api/map/elements/${id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
        await refreshFusion(id);
        notify("Nota da fusão atualizada.");
    }

    async function deleteFusionNote(noteId) {
        const accepted = await confirmAction({ title: "Excluir nota", message: "A nota será removida do diagrama de fusões.", confirmLabel: "Excluir nota", danger: true });
        if (!accepted) return;
        const { id, layout } = await loadFusionLayout();
        layout.notes = layout.notes.filter((item) => String(item.id) !== String(noteId));
        await request(`/api/map/elements/${id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
        await refreshFusion(id);
        notify("Nota excluída.");
    }

    async function addFusionNote() {
        if (!state.fusionMenuPoint) return;
        const text = await editLongText({ title: "Nova nota da fusão" });
        if (text === null) return;
        const { id, layout } = await loadFusionLayout();
        layout.notes.push({ id: `n${Date.now()}`, text, x: Math.round(state.fusionMenuPoint.x), y: Math.round(state.fusionMenuPoint.y) });
        await request(`/api/map/elements/${id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
        await refreshFusion(id);
        notify("Nota adicionada ao diagrama.");
    }

    function ensureElementMenu() {
        let menu = qs("#map-v0757-element-menu");
        if (menu) return menu;
        menu = document.createElement("div");
        menu.id = "map-v0757-element-menu";
        menu.className = "map-context-menu map-v0757-element-menu";
        menu.hidden = true;
        menu.innerHTML = '<strong data-title>Equipamento</strong><button type="button" data-action="edit">Editar informações</button><button type="button" data-action="fusions">Abrir fusões</button><button type="button" class="danger" data-action="delete">Excluir equipamento</button>';
        document.body.appendChild(menu);
        document.addEventListener("pointerdown", (event) => { if (!event.target.closest("#map-v0757-element-menu")) menu.hidden = true; }, true);
        return menu;
    }

    function openElementMenu({ originalEvent, element, edit, fusions, remove } = {}) {
        const menu = ensureElementMenu();
        const event = originalEvent || {};
        state.activeElementMenu = { element, edit, fusions, remove };
        qs("[data-title]", menu).textContent = element?.nome || element?.name || "Equipamento";
        qs('[data-action="fusions"]', menu).hidden = !fusions;
        menu.style.left = `${Math.min(window.innerWidth - 230, Number(event.clientX || 20))}px`;
        menu.style.top = `${Math.min(window.innerHeight - 180, Number(event.clientY || 20))}px`;
        menu.hidden = false;
        qs('[data-action="edit"]', menu).onclick = () => { menu.hidden = true; edit?.(); };
        qs('[data-action="fusions"]', menu).onclick = () => { menu.hidden = true; fusions?.(); };
        qs('[data-action="delete"]', menu).onclick = async () => {
            menu.hidden = true;
            const accepted = await confirmAction({ title: "Excluir equipamento", message: `Excluir ${element?.nome || "este equipamento"} do projeto?`, confirmLabel: "Excluir", danger: true });
            if (accepted) remove?.();
        };
    }

    function prepareOpticalWorkspace() {
        const dialog = qs("#unifilar-dialog");
        const content = qs("#unifilar-content");
        if (!dialog?.open || !content) return;
        dialog.classList.add("map-v0757-optical-workspace");
        const title = qs("#unifilar-title")?.textContent || "Fusões ópticas";
        dialog.dataset.workspaceTitle = title;
        qsa(".graph-node[data-cable-node-id]", content).forEach((node) => {
            const parent = node.parentElement;
            const center = (parseFloat(node.style.left) || 0) + node.offsetWidth / 2;
            const middle = Math.max(parent?.scrollWidth || 0, parent?.clientWidth || 0, 900) / 2;
            node.classList.toggle("side-right-v0757", center >= middle);
            node.classList.toggle("side-left-v0757", center < middle);
        });
    }

    document.addEventListener("map:container-opening", (event) => {
        const dialog = event.detail?.dialog || qs("#container-dialog");
        if (dialog) dialog.dataset.elementId = String(event.detail?.elementId || dialog.dataset.elementId || "");
    });

    document.addEventListener("map:container-rendered", (event) => {
        if (event.detail?.data?.container) state.containerData = event.detail.data;
        window.requestAnimationFrame(() => updateContainerIdentity(event.detail?.data || state.containerData));
    });

    document.addEventListener("contextmenu", (event) => {
        const canvas = event.target.closest("#map-master-container .master-canvas");
        if (canvas && !event.target.closest(".master-canvas-node, .master-cable-node, .master-canvas-note")) {
            const rect = canvas.getBoundingClientRect();
            const scale = Number(canvas.dataset.v0741Scale || 1) || 1;
            state.containerMenuPoint = { x: (event.clientX - rect.left) / scale, y: (event.clientY - rect.top) / scale };
        }
        const graph = event.target.closest("#unifilar-content .optical-graph");
        if (graph && !event.target.closest(".graph-node")) {
            const graphNodes = qs(".graph-nodes", graph);
            const zoom = Number((graphNodes?.style.transform.match(/scale\(([^)]+)\)/) || [])[1] || 1) || 1;
            const rect = graph.getBoundingClientRect();
            state.fusionMenuPoint = { x: (event.clientX - rect.left + graph.scrollLeft) / zoom, y: (event.clientY - rect.top + graph.scrollTop) / zoom };
        }
    }, true);

    document.addEventListener("click", (event) => {
        const editNote = event.target.closest("#map-master-container [data-edit-note]");
        if (editNote) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            editContainerNote(Number(editNote.dataset.editNote)).catch((error) => notify(error.message, true));
            return;
        }
        const deleteNote = event.target.closest("#map-master-container [data-delete-note]");
        if (deleteNote) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            deleteContainerNote(Number(deleteNote.dataset.deleteNote)).catch((error) => notify(error.message, true));
            return;
        }
        const addNote = event.target.closest("#map-master-container [data-add-canvas-note]");
        if (addNote) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            addContainerNote().catch((error) => notify(error.message, true));
            return;
        }
        const editFusion = event.target.closest("#unifilar-content [data-edit-fusion-note]");
        if (editFusion) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            editFusionNote(editFusion.dataset.editFusionNote).catch((error) => notify(error.message, true));
            return;
        }
        const fusionText = event.target.closest("#unifilar-content [data-note-id]");
        if (fusionText) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            editFusionNote(fusionText.dataset.noteId).catch((error) => notify(error.message, true));
            return;
        }
        const deleteFusion = event.target.closest("#unifilar-content [data-delete-note]");
        if (deleteFusion) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            deleteFusionNote(deleteFusion.dataset.deleteNote).catch((error) => notify(error.message, true));
            return;
        }
        const addFusion = event.target.closest('#unifilar-content [data-canvas-action="add-note"]');
        if (addFusion) {
            event.preventDefault(); event.stopPropagation(); event.stopImmediatePropagation();
            addFusionNote().catch((error) => notify(error.message, true));
            return;
        }
        const addEquipment = event.target.closest("#map-master-container [data-container-add]");
        if (addEquipment) window.setTimeout(() => {
            const dialog = qs("#map-master-equipment-create");
            const identity = containerIdentity();
            const allowed = identity.type === "rack"
                ? new Set(["olt", "dio", "switch", "router", "firewall", "pto", "other"])
                : new Set(["olt", "dio", "switch", "router", "firewall", "pto", "other", "access_point", "ptp", "onu"]);
            qsa("option", qs("select[name='equipment_type']", dialog) || document.createElement("select")).forEach((option) => {
                if (option.value && !allowed.has(option.value)) option.remove();
            });
            qs("select[name='equipment_type']", dialog)?.dispatchEvent(new Event("change"));
        }, 0);
    }, true);

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const container = qs("#container-dialog");
        if (!container?.open) return;
        const nested = qsa("dialog[open]").filter((dialog) => dialog !== container).at(-1);
        if (!nested) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        nested.close();
    }, true);

    const opticalObserver = new MutationObserver(() => window.requestAnimationFrame(prepareOpticalWorkspace));
    const observeOptical = () => {
        const content = qs("#unifilar-content");
        if (content && content.dataset.v0757Observed !== "1") {
            content.dataset.v0757Observed = "1";
            opticalObserver.observe(content, { childList: true, subtree: true });
        }
        prepareOpticalWorkspace();
    };
    observeOptical();

    window.mapV0757 = {
        VERSION,
        confirmAction,
        editLongText,
        reviewCableDirection,
        openElementMenu,
        updateContainerIdentity,
    };
})();
