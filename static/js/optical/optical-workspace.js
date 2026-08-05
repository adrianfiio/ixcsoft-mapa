(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    let currentSession = null;

    function dependencies() {
        const { api, state, renderer } = namespace;
        if (!api || !state || !renderer) {
            throw new Error("Módulo óptico incompleto. Recarregue a página após o deploy.");
        }
        return { api, state, renderer };
    }

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function isCurrent(session) {
        return currentSession === session && !session.disposed;
    }

    function canEdit() {
        return document.body.dataset.canEdit === "true";
    }

    function setStatus(session, message, error = false) {
        if (!isCurrent(session)) return;
        session.status = message || "";
        session.statusError = error;
        const node = session.root?.querySelector("[data-optical-status]");
        if (node) {
            node.textContent = session.status;
            node.classList.toggle("is-error", error);
        }
        if (message && global.networkMap?.notify) global.networkMap.notify(message, error);
    }

    function shellMarkup() {
        return `
            <section class="ixc-optical-shell" role="dialog" aria-modal="true" aria-labelledby="ixc-optical-title">
                <header class="ixc-optical-header">
                    <div>
                        <span class="ixc-optical-kicker" data-optical-kind>CAIXA ÓPTICA</span>
                        <h2 id="ixc-optical-title" data-optical-title>Carregando…</h2>
                        <p data-optical-subtitle>Preparando cabos, bandejas, fusões e splitters.</p>
                    </div>
                    <div class="ixc-optical-header-actions">
                        <button type="button" data-action="refresh" title="Recarregar dados">↻</button>
                        <button type="button" data-action="close" class="ixc-optical-close" title="Fechar">×</button>
                    </div>
                </header>
                <div class="ixc-optical-toolbar" aria-label="Ferramentas do Canvas óptico">
                    <button type="button" data-action="reset-view">Centralizar</button>
                    <button type="button" data-action="zoom-out">− Zoom</button>
                    <button type="button" data-action="zoom-in">+ Zoom</button>
                    <button type="button" data-action="add-note" data-edit-only>+ Nota</button>
                    <button type="button" data-action="add-tray" data-edit-only>+ Bandeja</button>
                    <button type="button" data-action="add-splitter" data-edit-only>+ Splitter</button>
                    <button type="button" data-action="save-layout" data-edit-only>Salvar layout</button>
                    <span class="ixc-optical-toolbar-hint">Arraste cabos, splitters e notas. A edição de fibras fica nos painéis laterais.</span>
                </div>
                <div class="ixc-optical-body">
                    <aside class="ixc-optical-panel ixc-optical-panel-left">
                        <div class="ixc-optical-panel-title"><strong>Cabos e fibras</strong><span data-cable-count>0</span></div>
                        <div class="ixc-optical-cable-list" data-cable-list></div>
                        <div class="ixc-optical-fiber-list" data-fiber-list></div>
                        <div class="ixc-optical-nearby" data-nearby-cables></div>
                    </aside>
                    <main class="ixc-optical-stage">
                        <div class="ixc-optical-loading" data-loading>
                            <span class="ixc-optical-spinner"></span>
                            <strong>Carregando editor óptico…</strong>
                        </div>
                        <canvas data-optical-canvas tabindex="0" aria-label="Canvas 2D da caixa óptica"></canvas>
                    </main>
                    <aside class="ixc-optical-panel ixc-optical-panel-right">
                        <div data-editor-controls></div>
                        <div data-splitter-controls></div>
                        <div data-splice-list></div>
                        <div data-service-ports></div>
                        <div data-note-list></div>
                    </aside>
                </div>
                <footer class="ixc-optical-footer">
                    <span data-optical-status>Inicializando…</span>
                    <span data-optical-session></span>
                </footer>
            </section>`;
    }

    function createRoot(session) {
        const root = document.createElement("div");
        root.className = "ixc-optical-workspace";
        root.dataset.opticalSession = session.id;
        root.innerHTML = shellMarkup();
        document.body.appendChild(root);
        document.body.classList.add("ixc-optical-workspace-open");
        session.root = root;
        session.canvas = root.querySelector("[data-optical-canvas]");
        root.querySelectorAll("[data-edit-only]").forEach((item) => {
            item.hidden = !canEdit();
        });
        root.querySelector("[data-optical-session]").textContent = `sessão ${session.id.slice(-6)}`;
        return root;
    }

    async function open(elementId) {
        const { api, state } = dependencies();
        close();
        const session = state.createSession(elementId);
        currentSession = session;
        createRoot(session);
        bindEvents(session);
        try {
            const payload = await api.loadWorkspace(session.elementId, session.controller.signal);
            if (!isCurrent(session)) return;
            state.hydrate(session, payload);
            renderWorkspace(session);
            setStatus(session, "Editor óptico carregado.");
        } catch (error) {
            if (!isCurrent(session) || error.name === "AbortError") return;
            showFatal(session, error.message);
            setStatus(session, error.message, true);
            throw error;
        }
    }

    function close() {
        if (!currentSession) return;
        const { state } = dependencies();
        const session = currentSession;
        currentSession = null;
        state.dispose(session);
    }

    function showFatal(session, message) {
        const loading = session.root?.querySelector("[data-loading]");
        if (!loading) return;
        loading.classList.add("is-error");
        loading.innerHTML = `<strong>Não foi possível abrir a caixa.</strong><span>${escapeHtml(message)}</span><button type="button" data-action="refresh">Tentar novamente</button>`;
    }

    function reconcileSelection(session) {
        const { state } = dependencies();
        const trays = state.trays(session);
        const trayIds = new Set(trays.map((item) => Number(item.id)));
        if (!trayIds.has(Number(session.selection.trayId))) {
            session.selection.trayId = trays[0]?.id || null;
        }
        const splitters = state.splitters(session);
        const splitterIds = new Set(splitters.map((item) => Number(item.id)));
        if (!splitterIds.has(Number(session.selection.splitterId))) {
            session.selection.splitterId = splitters[0]?.id || null;
        }
        const cableIds = new Set((session.optical.cables || []).map((item) => Number(item.id)));
        if (!cableIds.has(Number(session.selection.cableId))) {
            session.selection.cableId = session.optical.cables[0]?.id || null;
        }
        for (const key of ["fiberA", "fiberB"]) {
            if (session.selection[key] && !state.fiberById(session, session.selection[key])) {
                session.selection[key] = null;
            }
        }
        const allPortIds = new Set(splitters.flatMap((item) => (item.ports || []).map((port) => Number(port.id))));
        if (session.selection.cascadePortId && !allPortIds.has(Number(session.selection.cascadePortId))) {
            session.selection.cascadePortId = null;
        }
    }

    function renderWorkspace(session) {
        if (!isCurrent(session)) return;
        const { state, renderer } = dependencies();
        reconcileSelection(session);
        const kind = state.subtypeLabel(session.element);
        session.root.querySelector("[data-optical-kind]").textContent = kind;
        session.root.querySelector("[data-optical-title]").textContent = session.element.name || `${kind} ${session.element.id}`;
        session.root.querySelector("[data-optical-subtitle]").textContent = [
            session.element.code || "Sem código",
            `${state.trays(session).length} bandeja(s)`,
            `${session.optical.cables.length} cabo(s)`,
        ].join(" · ");
        session.root.querySelector("[data-loading]").hidden = true;
        renderCablePanel(session);
        renderEditorControls(session);
        renderSplitterControls(session);
        renderSpliceList(session);
        renderServicePorts(session);
        renderNearbyCables(session);
        renderNotes(session);
        const shouldFit = !session.initialFitDone && Object.keys(session.layout.nodes || {}).length === 0;
        renderer.render(session);
        if (shouldFit) renderer.fitView(session);
        session.initialFitDone = true;
        if (!session.resizeObserver && "ResizeObserver" in global) {
            session.resizeObserver = new global.ResizeObserver(() => renderer.render(session));
            session.resizeObserver.observe(session.canvas.parentElement);
        }
    }

    function renderCablePanel(session) {
        const { state } = dependencies();
        const list = session.root.querySelector("[data-cable-list]");
        const fibers = session.root.querySelector("[data-fiber-list]");
        session.root.querySelector("[data-cable-count]").textContent = String(session.optical.cables.length);
        list.innerHTML = session.optical.cables.length
            ? session.optical.cables.map((cable) => {
                const selected = Number(session.selection.cableId) === Number(cable.id);
                const cut = cable.requires_cut ? '<span class="ixc-optical-warning">corte necessário</span>' : "";
                return `<button type="button" class="ixc-optical-cable-card ${selected ? "is-selected" : ""}" data-action="select-cable" data-cable-id="${cable.id}">
                    <strong>${escapeHtml(cable.name)}</strong>
                    <small>${cable.fibers.length} fibras · ${escapeHtml(cable.relation_action || "conectado")}</small>${cut}
                </button>`;
            }).join("")
            : '<p class="ixc-optical-empty">Nenhum cabo conectado ou em passagem.</p>';

        const cable = state.cableById(session, session.selection.cableId);
        if (!cable) {
            fibers.innerHTML = '<p class="ixc-optical-empty">Selecione um cabo.</p>';
            return;
        }
        fibers.innerHTML = `<div class="ixc-optical-subtitle"><strong>${escapeHtml(cable.name)}</strong><small>Clique em duas fibras para criar uma fusão.</small></div>
            <div class="ixc-optical-fiber-grid">${cable.fibers.map((fiber) => {
                const used = state.isFiberUsed(session, fiber.id);
                const selectedA = Number(session.selection.fiberA) === Number(fiber.id);
                const selectedB = Number(session.selection.fiberB) === Number(fiber.id);
                return `<button type="button" data-action="select-fiber" data-fiber-id="${fiber.id}" class="ixc-optical-fiber ${used ? "is-used" : ""} ${selectedA || selectedB ? "is-selected" : ""}" title="${escapeHtml(fiber.color_name)} · ${escapeHtml(fiber.status)}">
                    <i style="--fiber-color:${escapeHtml(fiber.color_hex || "#aaa")}"></i><span>${fiber.number}</span>${selectedA ? "<b>A</b>" : selectedB ? "<b>B</b>" : ""}
                </button>`;
            }).join("")}</div>`;
    }

    function selectionDescription(session, fiberId) {
        const fiber = dependencies().state.fiberById(session, fiberId);
        return fiber
            ? `${fiber.cableName} · fibra ${fiber.number} · ${fiber.color_name}`
            : "Nenhuma fibra selecionada";
    }

    function renderEditorControls(session) {
        const { state } = dependencies();
        const trays = state.trays(session);
        const target = session.root.querySelector("[data-editor-controls]");
        target.innerHTML = `<section class="ixc-optical-card">
            <div class="ixc-optical-card-heading"><h3>Nova fusão</h3><div class="ixc-optical-mini-actions"><button type="button" data-action="edit-tray" ${!canEdit() || !session.selection.trayId ? "disabled" : ""}>Editar bandeja</button><button type="button" data-action="delete-tray" ${!canEdit() || !session.selection.trayId ? "disabled" : ""}>Excluir</button></div></div>
            <label>Bandeja
                <select data-field="tray-id" ${!canEdit() ? "disabled" : ""}>${trays.map((tray) => `<option value="${tray.id}" ${Number(session.selection.trayId) === Number(tray.id) ? "selected" : ""}>${escapeHtml(tray.name || `Bandeja ${tray.number}`)}</option>`).join("")}</select>
            </label>
            <div class="ixc-optical-selection"><span>A</span><p>${escapeHtml(selectionDescription(session, session.selection.fiberA))}</p></div>
            <div class="ixc-optical-selection"><span>B</span><p>${escapeHtml(selectionDescription(session, session.selection.fiberB))}</p></div>
            <div class="ixc-optical-row">
                <button type="button" data-action="clear-fiber-selection">Limpar</button>
                <button type="button" class="is-primary" data-action="create-splice" ${!canEdit() ? "disabled" : ""}>Criar fusão</button>
            </div>
        </section>`;
    }

    function renderSplitterControls(session) {
        const { state } = dependencies();
        const splitters = state.splitters(session);
        const selected = state.splitterById(session, session.selection.splitterId) || splitters[0];
        if (selected) session.selection.splitterId = selected.id;
        const target = session.root.querySelector("[data-splitter-controls]");
        if (!selected) {
            target.innerHTML = '<section class="ixc-optical-card"><h3>Splitters</h3><p class="ixc-optical-empty">Nenhum splitter cadastrado.</p></section>';
            return;
        }
        const selectedFiber = state.fiberById(session, session.selection.fiberA);
        const usedCascadePorts = new Set((session.optical.splitter_links || [])
            .filter((item) => Number(item.splitter_id) !== Number(selected.id))
            .map((item) => Number(item.input_splitter_port_id))
            .filter(Boolean));
        const cascadePorts = splitters
            .filter((item) => Number(item.id) !== Number(selected.id))
            .flatMap((item) => (item.ports || [])
                .filter((port) => !port.output_fiber_id && !usedCascadePorts.has(Number(port.id)))
                .map((port) => ({
                    id: port.id,
                    label: `${item.trayName} · ${item.ratio} · P${port.number}`,
                })));
        if (!cascadePorts.some((item) => Number(item.id) === Number(session.selection.cascadePortId))) {
            session.selection.cascadePortId = cascadePorts[0]?.id || null;
        }
        target.innerHTML = `<section class="ixc-optical-card">
            <div class="ixc-optical-card-heading"><h3>Splitter</h3><div class="ixc-optical-mini-actions"><button type="button" data-action="edit-splitter" ${!canEdit() ? "disabled" : ""}>Relação</button><button type="button" data-action="delete-splitter" ${!canEdit() ? "disabled" : ""}>Excluir</button></div></div>
            <label>Selecionado
                <select data-field="splitter-id">${splitters.map((item) => `<option value="${item.id}" ${Number(item.id) === Number(selected.id) ? "selected" : ""}>${escapeHtml(item.trayName)} · ${escapeHtml(item.ratio)}</option>`).join("")}</select>
            </label>
            <div class="ixc-optical-splitter-input">
                <span>Entrada</span>
                <strong>${selected.input_fiber_id ? `Fibra ${selected.input_fiber_id}` : selected.input_splitter_port_id ? `Cascata P${selected.input_splitter_port_id}` : "Livre"}</strong>
                <button type="button" data-action="connect-splitter-input" ${!canEdit() || !selectedFiber ? "disabled" : ""}>Ligar fibra A</button>
                ${cascadePorts.length ? `<select data-field="cascade-port-id" ${!canEdit() ? "disabled" : ""}>${cascadePorts.map((item) => `<option value="${item.id}" ${Number(item.id) === Number(session.selection.cascadePortId) ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}</select><button type="button" data-action="connect-splitter-cascade" ${!canEdit() || !session.selection.cascadePortId ? "disabled" : ""}>Ligar em cascata</button>` : ""}
                <button type="button" data-action="clear-splitter-input" ${!canEdit() ? "disabled" : ""}>Desligar</button>
            </div>
            <div class="ixc-optical-port-list">${(selected.ports || []).map((port) => `<div class="ixc-optical-port-row">
                <span>P${port.number}</span><strong>${port.output_fiber_id ? `Fibra ${port.output_fiber_id}` : "Livre"}</strong>
                <button type="button" data-action="connect-splitter-output" data-port-id="${port.id}" ${!canEdit() || !selectedFiber ? "disabled" : ""}>Ligar A</button>
                <button type="button" data-action="clear-splitter-output" data-port-id="${port.id}" ${!canEdit() ? "disabled" : ""}>×</button>
            </div>`).join("")}</div>
            <small class="ixc-optical-help">A fibra A selecionada no painel esquerdo é usada nas ligações do splitter.</small>
        </section>`;
    }

    function renderSpliceList(session) {
        const target = session.root.querySelector("[data-splice-list]");
        target.innerHTML = `<section class="ixc-optical-card">
            <h3>Fusões (${session.optical.splices.length})</h3>
            <div class="ixc-optical-splice-list">${session.optical.splices.length ? session.optical.splices.map((splice) => `<div class="ixc-optical-splice-row">
                <span><i style="--fiber-color:${escapeHtml(splice.input.color_hex)}"></i>${escapeHtml(splice.input.cable)} F${splice.input.number}</span>
                <b>→</b>
                <span><i style="--fiber-color:${escapeHtml(splice.output.color_hex)}"></i>${escapeHtml(splice.output.cable)} F${splice.output.number}</span>
                <button type="button" data-action="delete-splice" data-splice-id="${splice.id}" ${!canEdit() ? "disabled" : ""}>×</button>
            </div>`).join("") : '<p class="ixc-optical-empty">Nenhuma fusão cadastrada.</p>'}</div>
        </section>`;
    }

    function renderServicePorts(session) {
        const target = session.root.querySelector("[data-service-ports]");
        if (!session.servicePorts) {
            target.innerHTML = "";
            return;
        }
        const rows = (session.servicePorts.splitters || []).flatMap((splitter) => (
            (splitter.ports || []).map((port) => ({ ...port, splitter: splitter.name || splitter.ratio }))
        ));
        target.innerHTML = `<section class="ixc-optical-card">
            <h3>Portas de atendimento (${rows.length})</h3>
            <div class="ixc-optical-service-list">${rows.map((port) => `<div class="ixc-optical-service-row" data-service-row data-port-id="${port.id}">
                <div><strong>${escapeHtml(port.splitter)} · P${port.number}</strong><small>${escapeHtml(port.access_point || "Sem cliente vinculado")}</small></div>
                <select data-service-status ${!canEdit() ? "disabled" : ""}>
                    ${[["free", "Livre"], ["occupied", "Ocupada"], ["reserved", "Reservada"], ["defective", "Defeituosa"]].map(([value, label]) => `<option value="${value}" ${port.status === value ? "selected" : ""}>${label}</option>`).join("")}
                </select>
                <input data-service-notes value="${escapeHtml(port.notes || "")}" placeholder="Observação" ${!canEdit() ? "disabled" : ""}>
                <button type="button" data-action="save-service-port" ${!canEdit() ? "disabled" : ""}>Salvar</button>
            </div>`).join("")}</div>
        </section>`;
    }

    function renderNearbyCables(session) {
        const target = session.root.querySelector("[data-nearby-cables]");
        const candidates = session.cableState.cables || [];
        target.innerHTML = `<div class="ixc-optical-subtitle"><strong>Cabos próximos</strong><small>Associação manual de passagem</small></div>
            ${candidates.length ? candidates.map((cable) => {
                const mode = cable.endpoint ? "fixed" : cable.passage && !cable.excluded ? "remove" : "include";
                const label = mode === "fixed" ? "Ponta física" : mode === "remove" ? "Remover" : cable.excluded ? "Reincluir" : "Associar";
                return `<div class="ixc-optical-nearby-row">
                    <span><strong>${escapeHtml(cable.name)}</strong><small>${cable.distance_m == null ? "distância indisponível" : `${cable.distance_m} m`} · ${escapeHtml(cable.route || "sem rota")}</small></span>
                    <button type="button" data-action="toggle-cable-membership" data-cable-id="${cable.id}" data-mode="${mode}" ${!canEdit() || mode === "fixed" ? "disabled" : ""}>${label}</button>
                </div>`;
            }).join("") : '<p class="ixc-optical-empty">Nenhum cabo próximo encontrado.</p>'}`;
    }

    function renderNotes(session) {
        const target = session.root.querySelector("[data-note-list]");
        target.innerHTML = session.layout.notes.length ? `<section class="ixc-optical-card"><h3>Notas</h3>${session.layout.notes.map((note) => `<div class="ixc-optical-note-row"><span>${escapeHtml(note.text)}</span><button type="button" data-action="delete-note" data-note-id="${escapeHtml(note.id)}" ${!canEdit() ? "disabled" : ""}>×</button></div>`).join("")}</section>` : "";
    }

    async function reload(session, message = "Dados atualizados.") {
        const { api, state } = dependencies();
        if (!isCurrent(session)) return;
        setStatus(session, "Atualizando…");
        const oldSelection = { ...session.selection };
        const oldLayout = session.layout;
        const payload = await api.loadWorkspace(session.elementId, session.controller.signal);
        if (!isCurrent(session)) return;
        state.hydrate(session, payload);
        session.selection = { ...session.selection, ...oldSelection };
        session.layout = oldLayout;
        renderWorkspace(session);
        setStatus(session, message);
    }

    function scheduleLayoutSave(session) {
        if (!canEdit() || !isCurrent(session)) return;
        if (session.saveTimer) clearTimeout(session.saveTimer);
        session.saveTimer = setTimeout(() => saveLayout(session, true), 650);
    }

    async function saveLayout(session, silent = false) {
        const { api } = dependencies();
        if (!canEdit() || !isCurrent(session)) return;
        if (session.saveTimer) {
            clearTimeout(session.saveTimer);
            session.saveTimer = null;
        }
        try {
            await api.saveLayout(session.elementId, session.layout, session.controller.signal);
            if (!silent) setStatus(session, "Layout salvo.");
        } catch (error) {
            if (error.name !== "AbortError") setStatus(session, `Falha ao salvar layout: ${error.message}`, true);
        }
    }

    async function runMutation(session, action, successMessage) {
        if (!isCurrent(session) || session.mutating) return;
        session.mutating = true;
        session.root?.setAttribute("aria-busy", "true");
        try {
            setStatus(session, "Salvando alteração…");
            await action();
            await reload(session, successMessage);
        } catch (error) {
            if (error.name !== "AbortError") setStatus(session, error.message, true);
        } finally {
            session.mutating = false;
            session.root?.removeAttribute("aria-busy");
        }
    }

    function bindEvents(session) {
        const root = session.root;
        root.addEventListener("click", (event) => handleClick(session, event));
        root.addEventListener("change", (event) => handleChange(session, event));
        root.addEventListener("keydown", (event) => {
            if (event.key === "Escape") close();
        });
        bindCanvas(session);
    }

    async function handleClick(session, event) {
        const button = event.target.closest("[data-action]");
        if (!button || !isCurrent(session)) return;
        const action = button.dataset.action;
        const { api, state, renderer } = dependencies();
        if (action === "close") return close();
        if (action === "refresh") {
            try { await reload(session); } catch (error) { setStatus(session, error.message, true); }
            return;
        }
        if (action === "reset-view") {
            renderer.resetView(session);
            scheduleLayoutSave(session);
            return;
        }
        if (action === "zoom-in" || action === "zoom-out") {
            const rect = session.canvas.getBoundingClientRect();
            renderer.zoomAt(session, { x: rect.width / 2, y: rect.height / 2 }, action === "zoom-in" ? 1.18 : 0.84);
            scheduleLayoutSave(session);
            return;
        }
        if (action === "save-layout") return saveLayout(session);
        if (action === "select-cable") {
            session.selection.cableId = Number(button.dataset.cableId);
            renderCablePanel(session);
            renderer.render(session);
            return;
        }
        if (action === "select-fiber") {
            const fiberId = Number(button.dataset.fiberId);
            if (Number(session.selection.fiberA) === fiberId) session.selection.fiberA = null;
            else if (Number(session.selection.fiberB) === fiberId) session.selection.fiberB = null;
            else if (!session.selection.fiberA) session.selection.fiberA = fiberId;
            else if (!session.selection.fiberB) session.selection.fiberB = fiberId;
            else {
                session.selection.fiberA = session.selection.fiberB;
                session.selection.fiberB = fiberId;
            }
            renderCablePanel(session);
            renderEditorControls(session);
            renderSplitterControls(session);
            renderer.render(session);
            return;
        }
        if (action === "clear-fiber-selection") {
            session.selection.fiberA = null;
            session.selection.fiberB = null;
            renderCablePanel(session);
            renderEditorControls(session);
            renderSplitterControls(session);
            renderer.render(session);
            return;
        }
        if (action === "create-splice") {
            const fiberA = state.fiberById(session, session.selection.fiberA);
            const fiberB = state.fiberById(session, session.selection.fiberB);
            if (!fiberA || !fiberB) return setStatus(session, "Selecione duas fibras.", true);
            if (Number(fiberA.cableId) === Number(fiberB.cableId)) return setStatus(session, "A fusão precisa ligar cabos diferentes.", true);
            if (!session.selection.trayId) return setStatus(session, "Selecione uma bandeja.", true);
            return runMutation(session, () => api.createSplice(session.elementId, {
                tray_id: session.selection.trayId,
                input_fiber_id: fiberA.id,
                output_fiber_id: fiberB.id,
            }, session.controller.signal), "Fusão criada.");
        }
        if (action === "delete-splice") {
            if (!global.confirm("Excluir esta fusão?")) return;
            return runMutation(session, () => api.deleteSplice(session.elementId, Number(button.dataset.spliceId), session.controller.signal), "Fusão removida.");
        }
        if (action === "add-tray") {
            const existing = state.trays(session);
            const nextNumber = existing.reduce((max, item) => Math.max(max, Number(item.number) || 0), 0) + 1;
            const name = String(global.prompt("Nome da bandeja:", `Bandeja ${nextNumber}`) || "").trim();
            if (!name) return;
            const capacity = Number(global.prompt("Capacidade de fusões:", "12"));
            if (!Number.isInteger(capacity) || capacity < 1 || capacity > 288) return setStatus(session, "Capacidade inválida (1 a 288).", true);
            return runMutation(session, () => api.createTray(session.elementId, {
                number: nextNumber,
                name,
                capacity,
            }, session.controller.signal), "Bandeja criada.");
        }
        if (action === "edit-tray") {
            const tray = state.trays(session).find((item) => Number(item.id) === Number(session.selection.trayId));
            if (!tray) return setStatus(session, "Selecione uma bandeja válida.", true);
            const number = Number(global.prompt("Número da bandeja:", String(tray.number)));
            if (!Number.isInteger(number) || number < 1) return setStatus(session, "Número da bandeja inválido.", true);
            const name = String(global.prompt("Nome da bandeja:", tray.name || `Bandeja ${tray.number}`) || "").trim();
            if (!name) return;
            const capacity = Number(global.prompt("Capacidade de fusões:", String(tray.capacity || 12)));
            if (!Number.isInteger(capacity) || capacity < 1 || capacity > 288) return setStatus(session, "Capacidade inválida (1 a 288).", true);
            return runMutation(session, () => api.updateTray(session.elementId, tray.id, {
                number,
                name,
                capacity,
            }, session.controller.signal), "Bandeja atualizada.");
        }
        if (action === "delete-tray") {
            if (!session.selection.trayId || !global.confirm("Excluir a bandeja selecionada? Só bandejas vazias podem ser removidas.")) return;
            return runMutation(session, () => api.deleteTray(session.elementId, session.selection.trayId, session.controller.signal), "Bandeja removida.");
        }
        if (action === "add-splitter") {
            const trays = state.trays(session);
            if (!trays.length) return setStatus(session, "A caixa não possui bandejas.", true);
            const trayId = Number(global.prompt(`ID da bandeja (${trays.map((item) => `${item.id}=${item.name || `Bandeja ${item.number}`}`).join(", ")}):`, session.selection.trayId || trays[0].id));
            if (!trays.some((item) => Number(item.id) === trayId)) return setStatus(session, "Bandeja inválida.", true);
            const ratio = String(global.prompt("Relação do splitter (ex.: 1:8):", "1:8") || "").trim();
            if (!ratio) return;
            return runMutation(session, () => api.createSplitter(session.elementId, trayId, ratio, session.controller.signal), "Splitter criado.");
        }
        if (action === "edit-splitter") {
            const splitter = state.splitterById(session, session.selection.splitterId);
            if (!splitter) return setStatus(session, "Selecione um splitter válido.", true);
            const ratio = String(global.prompt("Nova relação do splitter:", splitter.ratio || "1:8") || "").trim();
            if (!ratio || ratio === splitter.ratio) return;
            return runMutation(session, () => api.updateSplitter(session.elementId, splitter.id, ratio, session.controller.signal), "Relação do splitter atualizada.");
        }
        if (action === "delete-splitter") {
            if (!session.selection.splitterId || !global.confirm("Excluir o splitter selecionado? Ligações associadas poderão ser removidas.")) return;
            return runMutation(session, () => api.deleteSplitter(session.elementId, session.selection.splitterId, session.controller.signal), "Splitter removido.");
        }
        if (action === "connect-splitter-input") {
            if (!session.selection.fiberA || !session.selection.splitterId) return;
            return runMutation(session, () => api.connectSplitterInput(session.elementId, session.selection.splitterId, session.selection.fiberA, session.controller.signal), "Entrada do splitter ligada.");
        }
        if (action === "connect-splitter-cascade") {
            if (!session.selection.splitterId || !session.selection.cascadePortId) return;
            return runMutation(session, () => api.connectSplitterCascade(
                session.elementId,
                session.selection.splitterId,
                session.selection.cascadePortId,
                session.controller.signal,
            ), "Cascata entre splitters criada.");
        }
        if (action === "clear-splitter-input") {
            if (!session.selection.splitterId) return;
            return runMutation(session, () => api.clearSplitterInput(session.elementId, session.selection.splitterId, session.controller.signal), "Entrada do splitter desligada.");
        }
        if (action === "connect-splitter-output") {
            if (!session.selection.fiberA) return;
            return runMutation(session, () => api.connectSplitterOutput(session.elementId, Number(button.dataset.portId), session.selection.fiberA, session.controller.signal), "Saída do splitter ligada.");
        }
        if (action === "clear-splitter-output") {
            return runMutation(session, () => api.clearSplitterOutput(session.elementId, Number(button.dataset.portId), session.controller.signal), "Saída do splitter desligada.");
        }
        if (action === "toggle-cable-membership") {
            const cableId = Number(button.dataset.cableId);
            const mode = button.dataset.mode;
            if (mode === "fixed") return;
            return runMutation(session, () => mode === "remove"
                ? api.excludeCable(session.elementId, cableId, session.controller.signal)
                : api.includeCable(session.elementId, cableId, session.controller.signal), "Associação do cabo atualizada.");
        }
        if (action === "save-service-port") {
            const row = button.closest("[data-service-row]");
            return runMutation(session, () => api.updateServicePort(session.elementId, {
                port_id: Number(row.dataset.portId),
                status: row.querySelector("[data-service-status]").value,
                notes: row.querySelector("[data-service-notes]").value,
            }, session.controller.signal), "Porta de atendimento atualizada.");
        }
        if (action === "add-note") {
            const text = String(global.prompt("Texto da nota:", "") || "").trim();
            if (!text) return;
            session.layout.notes.push({
                id: `note-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                x: 390,
                y: 70,
                text: text.slice(0, 240),
            });
            renderNotes(session);
            renderer.render(session);
            scheduleLayoutSave(session);
            return;
        }
        if (action === "delete-note") {
            session.layout.notes = session.layout.notes.filter((item) => item.id !== button.dataset.noteId);
            renderNotes(session);
            renderer.render(session);
            scheduleLayoutSave(session);
        }
    }

    function handleChange(session, event) {
        if (!isCurrent(session)) return;
        const field = event.target.dataset.field;
        if (field === "tray-id") session.selection.trayId = Number(event.target.value);
        if (field === "splitter-id") {
            session.selection.splitterId = Number(event.target.value);
            renderSplitterControls(session);
            dependencies().renderer.render(session);
        }
        if (field === "cascade-port-id") {
            session.selection.cascadePortId = Number(event.target.value) || null;
        }
    }

    function bindCanvas(session) {
        const canvas = session.canvas;
        const { renderer } = dependencies();
        canvas.addEventListener("pointerdown", (event) => {
            if (!isCurrent(session)) return;
            canvas.setPointerCapture(event.pointerId);
            const rect = canvas.getBoundingClientRect();
            const screen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            const hit = renderer.hitTest(session, screen);
            const world = renderer.screenToWorld(session, screen);
            if (hit && canEdit()) {
                session.dragging = {
                    type: "node",
                    hit,
                    offset: { x: world.x - hit.x, y: world.y - hit.y },
                };
                if (hit.type === "cable") session.selection.cableId = Number(hit.id);
                if (hit.type === "splitter") session.selection.splitterId = Number(hit.id);
                renderCablePanel(session);
                renderSplitterControls(session);
            } else {
                session.dragging = {
                    type: "pan",
                    start: screen,
                    panX: session.layout.viewport.panX,
                    panY: session.layout.viewport.panY,
                };
            }
        });
        canvas.addEventListener("pointermove", (event) => {
            if (!session.dragging || !isCurrent(session)) return;
            const rect = canvas.getBoundingClientRect();
            const screen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            if (session.dragging.type === "node") {
                renderer.moveNode(session, session.dragging.hit, screen, session.dragging.offset);
            } else {
                session.layout.viewport.panX = session.dragging.panX + screen.x - session.dragging.start.x;
                session.layout.viewport.panY = session.dragging.panY + screen.y - session.dragging.start.y;
            }
            renderer.render(session);
        });
        const finish = () => {
            if (!session.dragging) return;
            session.dragging = null;
            scheduleLayoutSave(session);
        };
        canvas.addEventListener("pointerup", finish);
        canvas.addEventListener("pointercancel", finish);
        canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            renderer.zoomAt(session, { x: event.clientX - rect.left, y: event.clientY - rect.top }, event.deltaY < 0 ? 1.12 : 0.89);
            scheduleLayoutSave(session);
        }, { passive: false });
    }

    global.IXCOpticalWorkspace = Object.freeze({
        open,
        close,
        isOpen() {
            return Boolean(currentSession && !currentSession.disposed);
        },
        version: "0.75.34",
    });
})(window);
