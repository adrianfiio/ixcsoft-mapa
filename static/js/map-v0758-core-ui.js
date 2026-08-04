(function () {
    "use strict";

    const VERSION = "0.75.9";
    const state = {
        containerData: null,
        activeElementMenu: null,
    };

    // Criado vazio já na primeira linha executável do arquivo: se qualquer
    // erro acontecer mais adiante na inicialização, window.mapV0758 continua
    // existindo (mesmo que incompleto) em vez de ficar undefined pro resto
    // da sessão da página — isso importa porque o handler de contextmenu dos
    // markers (map-editor.js) depende de window.mapV0758?.openElementMenu
    // existir pra decidir se deve interceptar o clique.
    window.mapV0758 = window.mapV0758 || {};

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

    function notify(message, error = false) {
        window.networkMap?.notify?.(message, error);
    }

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function ensureConfirmDialog() {
        let dialog = qs("#map-v0758-confirm-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-v0758-confirm-dialog";
        dialog.className = "editor-dialog map-v0758-action-dialog";
        dialog.innerHTML = `
            <form method="dialog">
                <header>
                    <div><h2 data-title>Confirmar ação</h2><p data-message></p></div>
                    <button type="button" data-close aria-label="Fechar">×</button>
                </header>
                <footer>
                    <button type="button" data-cancel>Cancelar</button>
                    <button type="submit" class="primary-button" data-confirm>Confirmar</button>
                </footer>
            </form>`;
        document.body.appendChild(dialog);
        return dialog;
    }

    function confirmAction({
        title = "Confirmar ação",
        message = "Deseja continuar?",
        confirmLabel = "Confirmar",
        cancelLabel = "Cancelar",
        danger = false,
    } = {}) {
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
            qs("form", dialog).onsubmit = (event) => {
                event.preventDefault();
                finish(true);
            };
            cancel.onclick = () => finish(false);
            qs("[data-close]", dialog).onclick = () => finish(false);
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(false);
            };
        });
    }

    function ensureTextDialog() {
        let dialog = qs("#map-v0758-text-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-v0758-text-dialog";
        dialog.className = "editor-dialog map-v0758-note-dialog";
        dialog.innerHTML = `
            <form>
                <header>
                    <div><h2 data-title>Nota técnica</h2><p>Escreva livremente. As quebras de linha são preservadas.</p></div>
                    <button type="button" data-close aria-label="Fechar">×</button>
                </header>
                <label><span data-label>Texto da nota</span><textarea name="text" rows="12" maxlength="20000" required></textarea></label>
                <small data-counter>0 caracteres</small>
                <footer>
                    <button type="button" data-cancel>Cancelar</button>
                    <button type="submit" class="primary-button">Salvar nota</button>
                </footer>
            </form>`;
        document.body.appendChild(dialog);
        const textarea = qs("textarea", dialog);
        textarea.addEventListener("input", () => {
            qs("[data-counter]", dialog).textContent = `${textarea.value.length} caracteres`;
        });
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
        window.setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }, 30);
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
                if (!text) {
                    textarea.focus();
                    return;
                }
                finish(text);
            };
            qs("[data-cancel]", dialog).onclick = () => finish(null);
            qs("[data-close]", dialog).onclick = () => finish(null);
            dialog.oncancel = (event) => {
                event.preventDefault();
                finish(null);
            };
        });
    }

    function elementKind(feature) {
        const properties = feature?.properties || feature || {};
        const type = String(properties.tipo || properties.element_type || "").toLowerCase();
        const subtype = String(
            properties.subtype
            || properties.element_subtype
            || properties.metadata?.import_subtype
            || "",
        ).toLowerCase();
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

    function structureIcon(type) {
        return type === "rack"
            ? '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="1"></rect><path d="M4 9h16M4 15h16M8 6h8M8 12h8M8 18h8"></path></svg>'
            : '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="2"></circle><path d="M12 9 7 22m5-13 5 13M9 16h6M7 5a7 7 0 0 0 0 5m10-5a7 7 0 0 1 0 5M4 3a11 11 0 0 0 0 9m16-9a11 11 0 0 1 0 9"></path></svg>';
    }

    function containerIdentity(data = state.containerData) {
        const dialog = qs("#container-dialog");
        const type = String(data?.container?.type || dialog?.dataset.containerType || "tower").toLowerCase();
        const name = data?.container?.name || dialog?.dataset.containerName || "Estrutura";
        return { type: type === "rack" ? "rack" : "tower", name };
    }

    function updateContainerIdentity(data = state.containerData) {
        const root = qs("#map-master-container");
        const dialog = qs("#container-dialog");
        if (!root || !dialog) return;
        const identity = containerIdentity(data);
        dialog.dataset.containerType = identity.type;
        dialog.dataset.containerName = identity.name;
        dialog.classList.toggle("map-v0758-rack", identity.type === "rack");
        dialog.classList.toggle("map-v0758-tower", identity.type === "tower");

        const title = qs(".tower-workspace-title-v0750", root);
        if (title) {
            const strong = qs("strong", title);
            const small = qs("small", title);
            const icon = qs(":scope > svg", title);
            if (icon) icon.outerHTML = structureIcon(identity.type);
            if (strong) strong.textContent = identity.type === "rack" ? "Editor técnico do Rack" : "Editor técnico da Torre";
            if (small) small.textContent = `${identity.name} · Canvas 2D, portas, cabos e conexões`;
        }

        let close = qs("[data-workspace-close-v0758]", root);
        if (!close) {
            close = document.createElement("button");
            close.type = "button";
            close.dataset.workspaceCloseV0758 = "true";
            close.className = "tower-workspace-close-v0758";
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
            if (heading) {
                heading.textContent = identity.type === "rack"
                    ? "Monte o rack diretamente no Canvas 2D"
                    : "Monte a torre diretamente no Canvas 2D";
            }
            if (paragraph) {
                paragraph.textContent = identity.type === "rack"
                    ? "Comece adicionando uma OLT, um DIO ou os equipamentos internos permitidos no rack."
                    : "Comece adicionando um DIO, uma PTO ou os equipamentos ativos da torre.";
            }
        }

        const addMenu = qs("#tower-add-menu-v0750", root);
        const extraTypes = [
            ["olt", "OLT", "Chassi óptico"],
            ["firewall", "Firewall", "Segurança e borda"],
            ["server", "Servidor", "Servidor instalado no rack"],
            ["other", "Outro", "Equipamento personalizado"],
        ];
        extraTypes.forEach(([type, label, help]) => {
            if (!addMenu || qs(`[data-quick-add="${type}"]`, addMenu)) return;
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.quickAdd = type;
            button.innerHTML = `<span class="map-v0758-generic-equipment">＋</span><span><strong>${label}</strong><small>${help}</small></span>`;
            button.onclick = () => {
                qs("[data-container-add]", root)?.click();
                window.setTimeout(() => {
                    const createDialog = qs("#map-master-equipment-create");
                    const select = qs("select[name='equipment_type']", createDialog);
                    if (!select || ![...select.options].some((option) => option.value === type)) return;
                    select.value = type;
                    select.dispatchEvent(new Event("change"));
                }, 0);
            };
            addMenu.appendChild(button);
        });

        if (empty && identity.type === "rack") {
            const actions = qs("div", empty);
            if (actions) {
                actions.innerHTML = `
                    <button type="button" data-empty-add="olt">Adicionar OLT</button>
                    <button type="button" data-empty-add="dio">Adicionar DIO</button>
                    <button type="button" data-empty-add="switch">Adicionar Switch</button>`;
                qsa("[data-empty-add]", actions).forEach((button) => {
                    button.onclick = () => qs(`[data-quick-add="${button.dataset.emptyAdd}"]`, root)?.click();
                });
            }
        }

        const rackAllowed = new Set(["olt", "dio", "switch", "router", "firewall", "server", "pto", "other"]);
        const towerAllowed = new Set(["olt", "dio", "switch", "router", "firewall", "access_point", "ptp", "onu", "pto", "other"]);
        const allowed = identity.type === "rack" ? rackAllowed : towerAllowed;
        qsa("[data-quick-add]", root).forEach((button) => {
            button.hidden = !allowed.has(String(button.dataset.quickAdd));
        });
    }

    function ensureElementMenu() {
        let menu = qs("#map-v0758-element-menu");
        if (menu) return menu;
        menu = document.createElement("div");
        menu.id = "map-v0758-element-menu";
        menu.className = "map-context-menu map-v0758-element-menu";
        menu.hidden = true;
        menu.innerHTML = `
            <strong data-title>Elemento</strong>
            <button type="button" data-action="edit">Editar informações</button>
            <button type="button" data-action="open">Abrir editor</button>
            <button type="button" data-action="duplicates" hidden>Resolver duplicados</button>
            <button type="button" class="danger" data-action="delete">Excluir este registro</button>`;
        document.body.appendChild(menu);
        document.addEventListener("pointerdown", (event) => {
            if (!event.target.closest("#map-v0758-element-menu")) menu.hidden = true;
        }, true);
        return menu;
    }

    function ensureDuplicateDialog() {
        let dialog = qs("#map-v0758-duplicate-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "map-v0758-duplicate-dialog";
        dialog.className = "editor-dialog map-v0758-duplicate-dialog";
        dialog.innerHTML = `
            <section>
                <header>
                    <div><h2>Registros sobrepostos</h2><p>Estes registros têm o mesmo tipo, nome e coordenada. Nada será apagado automaticamente.</p></div>
                    <button type="button" data-close aria-label="Fechar">×</button>
                </header>
                <div data-list></div>
            </section>`;
        document.body.appendChild(dialog);
        qs("[data-close]", dialog).onclick = () => dialog.close();
        return dialog;
    }

    function duplicateLabel(item) {
        const properties = item?.properties || item || {};
        const id = properties.id ?? item?.id ?? "?";
        const code = properties.codigo || properties.code || "sem código";
        const type = properties.tipo || properties.element_type || "elemento";
        return `ID ${id} · ${code} · ${type}`;
    }

    function openDuplicateResolver({ duplicates = [], currentId, removeById } = {}) {
        const dialog = ensureDuplicateDialog();
        const list = qs("[data-list]", dialog);
        list.innerHTML = duplicates.map((item) => {
            const properties = item?.properties || item || {};
            const id = Number(properties.id ?? item?.id ?? 0);
            const current = String(id) === String(currentId);
            return `<article data-duplicate-id="${id}">
                <div><strong>${escapeHtml(duplicateLabel(item))}</strong><small>${current ? "Registro aberto agora" : "Registro sobreposto"}</small></div>
                <button type="button" class="danger" data-remove-duplicate="${id}">Excluir este ID</button>
            </article>`;
        }).join("");
        qsa("[data-remove-duplicate]", list).forEach((button) => {
            button.onclick = async () => {
                const id = Number(button.dataset.removeDuplicate);
                const accepted = await confirmAction({
                    title: `Excluir o registro ID ${id}?`,
                    message: "Exclua somente o registro vazio ou incorreto. Cabos, equipamentos internos e fusões vinculados a esse ID podem ser removidos junto.",
                    confirmLabel: "Excluir este ID",
                    cancelLabel: "Cancelar",
                    danger: true,
                });
                if (!accepted) return;
                button.disabled = true;
                try {
                    await removeById?.(id);
                    dialog.close();
                } catch (error) {
                    button.disabled = false;
                    notify(error.message, true);
                }
            };
        });
        if (!dialog.open) dialog.showModal();
    }

    function openElementMenu({
        originalEvent,
        element,
        edit,
        fusions,
        remove,
        duplicates = [],
        removeById,
    } = {}) {
        const menu = ensureElementMenu();
        const event = originalEvent || {};
        state.activeElementMenu = { element, edit, fusions, remove, duplicates, removeById };
        const elementName = element?.nome || element?.name || "Elemento";
        const currentId = element?.id;
        qs("[data-title]", menu).textContent = `${elementName} · ID ${currentId ?? "?"}`;
        qs('[data-action="open"]', menu).textContent = ["cto", "splice_box"].includes(String(element?.tipo))
            ? "Abrir fusões"
            : "Abrir editor técnico";
        const duplicateButton = qs('[data-action="duplicates"]', menu);
        duplicateButton.hidden = duplicates.length < 2;
        duplicateButton.textContent = `Resolver duplicados (${duplicates.length})`;
        menu.style.left = `${Math.min(window.innerWidth - 250, Number(event.clientX || 20))}px`;
        menu.style.top = `${Math.min(window.innerHeight - 220, Number(event.clientY || 20))}px`;
        menu.hidden = false;
        qs('[data-action="edit"]', menu).onclick = () => {
            menu.hidden = true;
            edit?.();
        };
        qs('[data-action="open"]', menu).onclick = () => {
            menu.hidden = true;
            fusions?.();
        };
        duplicateButton.onclick = () => {
            menu.hidden = true;
            openDuplicateResolver({ duplicates, currentId, removeById });
        };
        qs('[data-action="delete"]', menu).onclick = async () => {
            menu.hidden = true;
            const accepted = await confirmAction({
                title: `Excluir ${elementName}?`,
                message: `Você está prestes a excluir o registro ID ${currentId}. Confirme somente depois de verificar se este é o registro correto.`,
                confirmLabel: "Excluir este registro",
                danger: true,
            });
            if (accepted) remove?.();
        };
    }

    document.addEventListener("map:container-rendered", (event) => {
        if (event.detail?.data?.container) state.containerData = event.detail.data;
        window.requestAnimationFrame(() => updateContainerIdentity(event.detail?.data || state.containerData));
    });

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

    Object.assign(window.mapV0758, {
        VERSION,
        confirmAction,
        editLongText,
        reviewCableDirection,
        openElementMenu,
        updateContainerIdentity,
    });


    // MAP_V07510_TOOLTIP_CONTEXT_GUARD
    document.addEventListener("contextmenu", (event) => {
        if (!event.target.closest(".leaflet-tooltip, .network-name-label")) return;
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation?.();
        document.querySelectorAll(".map-context-menu").forEach((menu) => {
            menu.hidden = true;
            menu.classList.remove("open");
        });
    }, true);

    document.addEventListener("map:fusion-rendered", () => {
        const dialog = document.querySelector("#unifilar-dialog");
        if (!dialog) return;
        dialog.classList.add("map-v07510-optical-workspace");
        dialog.querySelectorAll(".graph-node[data-cable-node-id]").forEach((node) => {
            node.classList.add("vertical-v07510");
        });
        requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
    });



    // MAP_V07511_WORKSPACE_FIT
    function enforceWorkspaceFitV07511() {
        const dialog = document.querySelector("#container-dialog.tower-workspace-dialog-v0750");
        const section = dialog?.querySelector(":scope > section");
        const root = document.querySelector("#map-master-container");
        const panel = root?.querySelector('[data-panel="canvas"]');
        if (!dialog || !section || !root || !panel) return;
        section.style.setProperty("position", "relative", "important");
        section.style.setProperty("display", "block", "important");
        section.style.setProperty("width", "100%", "important");
        section.style.setProperty("height", "100%", "important");
        section.style.setProperty("min-height", "0", "important");
        section.style.setProperty("overflow", "hidden", "important");
        root.style.setProperty("position", "absolute", "important");
        root.style.setProperty("inset", "0", "important");
        root.style.setProperty("width", "auto", "important");
        root.style.setProperty("height", "auto", "important");
        root.style.setProperty("min-height", "0", "important");
        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("min-height", "0", "important");
        panel.style.setProperty("overflow", "hidden", "important");
    }

    let fitQueuedV07511 = false;
    let workspaceResizeObserverV07511 = null;
    let observedSectionV07511 = null;
    let observedRootV07511 = null;

    function installWorkspaceResizeObserverV07511() {
        if (typeof ResizeObserver === "undefined") return;
        const dialog = document.querySelector("#container-dialog.tower-workspace-dialog-v0750");
        const section = dialog?.querySelector(":scope > section");
        const root = document.querySelector("#map-master-container");
        if (!section || !root) return;
        if (!workspaceResizeObserverV07511) {
            workspaceResizeObserverV07511 = new ResizeObserver(() => queueWorkspaceFitV07511());
        }
        if (observedSectionV07511 !== section) {
            if (observedSectionV07511) workspaceResizeObserverV07511.unobserve(observedSectionV07511);
            workspaceResizeObserverV07511.observe(section);
            observedSectionV07511 = section;
        }
        if (observedRootV07511 !== root) {
            if (observedRootV07511) workspaceResizeObserverV07511.unobserve(observedRootV07511);
            workspaceResizeObserverV07511.observe(root);
            observedRootV07511 = root;
        }
    }

    function queueWorkspaceFitV07511() {
        if (fitQueuedV07511) return;
        fitQueuedV07511 = true;
        requestAnimationFrame(() => {
            fitQueuedV07511 = false;
            enforceWorkspaceFitV07511();
            installWorkspaceResizeObserverV07511();
        });
    }

    window.addEventListener("resize", queueWorkspaceFitV07511);
    document.addEventListener("map:container-opening", queueWorkspaceFitV07511);
    document.addEventListener("map:container-rendered", queueWorkspaceFitV07511);
    document.addEventListener("DOMContentLoaded", queueWorkspaceFitV07511);
    queueWorkspaceFitV07511();

}());
