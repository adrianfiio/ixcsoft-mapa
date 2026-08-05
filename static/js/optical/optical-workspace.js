(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};
    let currentSession = null;

    function dependencies() {
        const { api, state, renderer } = namespace;
        const dialog = global.IXCMapDialog;
        if (!api || !state || !renderer || !dialog) {
            throw new Error("Editor óptico incompleto. Recarregue a página após o deploy.");
        }
        return { api, state, renderer, dialog };
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
                    <div class="ixc-optical-heading">
                        <span class="ixc-optical-kicker">CAIXA ÓPTICA</span>
                        <h2 id="ixc-optical-title" data-optical-title>Carregando…</h2>
                        <p data-optical-subtitle>Preparando cabos, fibras, splitters e ligações.</p>
                    </div>
                    <div class="ixc-optical-header-actions">
                        <button type="button" data-action="refresh" title="Recarregar dados">↻</button>
                        <button type="button" data-action="close" class="ixc-optical-close" title="Fechar">×</button>
                    </div>
                </header>
                <div class="ixc-optical-toolbar" aria-label="Ferramentas da caixa óptica">
                    <button type="button" data-action="organize">Organizar vertical</button>
                    <button type="button" data-action="fit-view">Enquadrar</button>
                    <button type="button" data-action="zoom-out">−</button>
                    <button type="button" data-action="zoom-in">+</button>
                    <span class="ixc-optical-divider"></span>
                    <button type="button" data-action="add-note" data-edit-only>+ Nota</button>
                    <button type="button" data-action="add-splitter" data-edit-only>+ Splitter</button>
                    <button type="button" data-action="save-layout" data-edit-only>Salvar</button>
                    <span class="ixc-optical-toolbar-hint">Clique em duas pontas ou arraste uma linha entre elas. Arraste o corpo dos blocos para mover.</span>
                </div>
                <div class="ixc-optical-body">
                    <aside class="ixc-optical-panel ixc-optical-panel-left">
                        <div class="ixc-optical-panel-title"><strong>Cabos</strong><span data-cable-count>0</span></div>
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
                        <div data-connection-controls></div>
                        <div data-splitter-controls></div>
                        <div data-splice-list></div>
                        <div data-service-ports></div>
                        <div data-note-list></div>
                    </aside>
                </div>
                <footer class="ixc-optical-footer">
                    <span data-optical-status>Inicializando…</span>
                    <span>ligações ponta a ponta · sessão <b data-optical-session></b></span>
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
        root.querySelectorAll("[data-edit-only]").forEach((item) => { item.hidden = !canEdit(); });
        root.querySelector("[data-optical-session]").textContent = session.id.slice(-6);
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
            setStatus(session, "Editor óptico carregado. Selecione ou arraste entre duas pontas.");
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
        const splitters = state.splitters(session);
        if (!splitters.some((item) => Number(item.id) === Number(session.selection.splitterId))) {
            session.selection.splitterId = splitters[0]?.id || null;
        }
        if (!(session.optical.cables || []).some((item) => Number(item.id) === Number(session.selection.cableId))) {
            session.selection.cableId = session.optical.cables[0]?.id || null;
        }
        const pending = session.selection.pendingEndpoint;
        if (pending?.kind === "fiber" && !state.fiberById(session, pending.id)) session.selection.pendingEndpoint = null;
        if (pending?.kind === "splitter-input" && !state.splitterById(session, pending.id)) session.selection.pendingEndpoint = null;
        if (pending?.kind === "splitter-output" && !state.splitterPortById(session, pending.id)) session.selection.pendingEndpoint = null;
    }

    function renderWorkspace(session) {
        if (!isCurrent(session)) return;
        const { state, renderer } = dependencies();
        reconcileSelection(session);
        const splitterCount = state.splitters(session).length;
        session.root.querySelector("[data-optical-title]").textContent = session.element.name || `Caixa ${session.element.id}`;
        session.root.querySelector("[data-optical-subtitle]").textContent = [
            session.element.code || "Sem código",
            `${session.optical.cables.length} cabo(s)`,
            `${session.optical.splices.length} fusão(ões)`,
            `${splitterCount} splitter(s)`,
        ].join(" · ");
        session.root.querySelector("[data-loading]").hidden = true;
        renderCablePanel(session);
        renderConnectionControls(session);
        renderSplitterControls(session);
        renderSpliceList(session);
        renderServicePorts(session);
        renderNearbyCables(session);
        renderNotes(session);
        const shouldFit = !session.initialFitDone && Object.keys(session.layout.nodes || {}).length === 0;
        renderer.render(session);
        if (shouldFit) renderer.fitView(session);
        session.initialFitDone = true;
        if (session.layoutMigrated) {
            session.layoutMigrated = false;
            scheduleLayoutSave(session);
        }
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
        const pendingKey = state.endpointKey(session.selection.pendingEndpoint);
        fibers.innerHTML = `<div class="ixc-optical-subtitle"><strong>${escapeHtml(cable.name)}</strong><small>Clique numa fibra e depois em outra ponta. A segunda seleção liga automaticamente.</small></div>
            <div class="ixc-optical-fiber-grid">${cable.fibers.map((fiber) => {
                const endpoint = { kind: "fiber", id: Number(fiber.id) };
                const selected = pendingKey === state.endpointKey(endpoint);
                const used = state.isFiberUsed(session, fiber.id);
                return `<button type="button" data-action="select-endpoint" data-endpoint-kind="fiber" data-endpoint-id="${fiber.id}" class="ixc-optical-fiber ${used ? "is-used" : ""} ${selected ? "is-selected" : ""}" title="${escapeHtml(fiber.color_name)} · ${escapeHtml(fiber.status)}">
                    <i style="--fiber-color:${escapeHtml(fiber.color_hex || "#aaa")}"></i><span>F${fiber.number}</span>${selected ? "<b>1</b>" : ""}
                </button>`;
            }).join("")}</div>`;
    }

    function renderConnectionControls(session) {
        const { state } = dependencies();
        const target = session.root.querySelector("[data-connection-controls]");
        const pending = session.selection.pendingEndpoint;
        target.innerHTML = `<section class="ixc-optical-card ixc-optical-connection-card">
            <div class="ixc-optical-card-heading"><h3>Ligação rápida</h3><span class="ixc-optical-live-dot"></span></div>
            <p>Selecione uma ponta no Canvas ou no painel de fibras. Depois selecione a ponta de destino. Também pode puxar a linha diretamente.</p>
            <div class="ixc-optical-pending-endpoint ${pending ? "has-value" : ""}">
                <span>${pending ? "1" : "·"}</span>
                <strong>${escapeHtml(state.endpointLabel(session, pending))}</strong>
            </div>
            <button type="button" data-action="clear-endpoint" ${pending ? "" : "disabled"}>Cancelar seleção</button>
        </section>`;
    }

    function renderSplitterControls(session) {
        const { state } = dependencies();
        const splitters = state.splitters(session);
        const selected = state.splitterById(session, session.selection.splitterId) || splitters[0];
        if (selected) session.selection.splitterId = selected.id;
        const target = session.root.querySelector("[data-splitter-controls]");
        if (!selected) {
            target.innerHTML = '<section class="ixc-optical-card"><h3>Splitters</h3><p class="ixc-optical-empty">Nenhum splitter cadastrado. Use “+ Splitter”.</p></section>';
            return;
        }
        const pendingKey = state.endpointKey(session.selection.pendingEndpoint);
        const inputEndpoint = { kind: "splitter-input", id: Number(selected.id) };
        target.innerHTML = `<section class="ixc-optical-card">
            <div class="ixc-optical-card-heading"><h3>Splitter</h3><div class="ixc-optical-mini-actions"><button type="button" data-action="edit-splitter" ${!canEdit() ? "disabled" : ""}>Relação</button><button type="button" data-action="delete-splitter" ${!canEdit() ? "disabled" : ""}>Excluir</button></div></div>
            <label>Selecionado
                <select data-field="splitter-id">${splitters.map((item) => `<option value="${item.id}" ${Number(item.id) === Number(selected.id) ? "selected" : ""}>Splitter ${escapeHtml(item.ratio)}</option>`).join("")}</select>
            </label>
            <button type="button" class="ixc-optical-endpoint-row ${pendingKey === state.endpointKey(inputEndpoint) ? "is-selected" : ""}" data-action="select-endpoint" data-endpoint-kind="splitter-input" data-endpoint-id="${selected.id}">
                <span class="ixc-optical-socket is-input"></span><span><strong>Entrada</strong><small>${selected.input_fiber_id ? `Fibra ${selected.input_fiber_id}` : selected.input_splitter_port_id ? "Cascata ligada" : "Livre"}</small></span><b>selecionar</b>
            </button>
            ${selected.input_fiber_id || selected.input_splitter_port_id ? `<button type="button" class="ixc-optical-inline-danger" data-action="clear-splitter-input" ${!canEdit() ? "disabled" : ""}>Desligar entrada</button>` : ""}
            <div class="ixc-optical-port-list">${(selected.ports || []).map((port) => {
                const endpoint = { kind: "splitter-output", id: Number(port.id), splitterId: Number(selected.id) };
                return `<div class="ixc-optical-port-row">
                    <button type="button" class="ixc-optical-endpoint-row ${pendingKey === state.endpointKey(endpoint) ? "is-selected" : ""}" data-action="select-endpoint" data-endpoint-kind="splitter-output" data-endpoint-id="${port.id}" data-splitter-id="${selected.id}">
                        <span class="ixc-optical-socket is-output"></span><span><strong>Saída ${port.number}</strong><small>${port.output_fiber_id ? `Fibra ${port.output_fiber_id}` : "Livre"}</small></span><b>selecionar</b>
                    </button>
                    ${state.endpointOccupied(session, endpoint) ? `<button type="button" class="ixc-optical-port-clear" data-action="clear-splitter-output" data-port-id="${port.id}" ${!canEdit() ? "disabled" : ""}>×</button>` : ""}
                </div>`;
            }).join("")}</div>
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
        target.innerHTML = session.layout.notes.length ? `<section class="ixc-optical-card"><h3>Notas do projeto</h3>${session.layout.notes.map((note) => `<div class="ixc-optical-note-row"><span>${escapeHtml(note.text)}</span><button type="button" data-action="edit-note" data-note-id="${escapeHtml(note.id)}" ${!canEdit() ? "disabled" : ""}>Editar</button><button type="button" data-action="delete-note" data-note-id="${escapeHtml(note.id)}" ${!canEdit() ? "disabled" : ""}>×</button></div>`).join("")}</section>` : "";
    }

    async function reload(session, message = "Dados atualizados.") {
        const { api, state } = dependencies();
        if (!isCurrent(session)) return;
        setStatus(session, "Atualizando…");
        const oldSelection = { ...session.selection };
        const oldLayout = session.layout;
        const oldExpanded = session.expandedCables;
        const payload = await api.loadWorkspace(session.elementId, session.controller.signal);
        if (!isCurrent(session)) return;
        state.hydrate(session, payload);
        session.selection = { ...session.selection, ...oldSelection, pendingEndpoint: null };
        session.layout = oldLayout;
        session.expandedCables = oldExpanded;
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
            session.selection.pendingEndpoint = null;
            await reload(session, successMessage);
        } catch (error) {
            if (error.name !== "AbortError") setStatus(session, error.message, true);
        } finally {
            session.mutating = false;
            session.root?.removeAttribute("aria-busy");
        }
    }

    async function internalGroupId(session) {
        const { api, state } = dependencies();
        const existing = state.internalGroup(session);
        if (existing) return existing.id;
        const created = await api.createInternalGroup(session.elementId, session.controller.signal);
        return created.tray.id;
    }

    function endpointFromNode(node) {
        if (!node?.dataset.endpointKind || !node.dataset.endpointId) return null;
        const endpoint = {
            kind: node.dataset.endpointKind,
            id: Number(node.dataset.endpointId),
        };
        if (node.dataset.splitterId) endpoint.splitterId = Number(node.dataset.splitterId);
        return endpoint;
    }

    async function connectEndpoints(session, first, second) {
        const { api, state } = dependencies();
        if (!first || !second) return;
        if (state.endpointKey(first) === state.endpointKey(second)) {
            session.selection.pendingEndpoint = null;
            renderWorkspace(session);
            return;
        }
        const pair = [first.kind, second.kind].sort().join("+");
        if (pair === "fiber+fiber") {
            const a = state.fiberById(session, first.id);
            const b = state.fiberById(session, second.id);
            if (!a || !b) return setStatus(session, "Uma das fibras não está mais disponível.", true);
            if (Number(a.cableId) === Number(b.cableId)) return setStatus(session, "A fusão precisa ligar fibras de cabos diferentes.", true);
            return runMutation(session, async () => {
                const groupId = await internalGroupId(session);
                await api.createSplice(session.elementId, {
                    tray_id: groupId,
                    input_fiber_id: a.id,
                    output_fiber_id: b.id,
                }, session.controller.signal);
            }, "Fusão criada.");
        }
        const fiber = first.kind === "fiber" ? first : second.kind === "fiber" ? second : null;
        const splitterInput = first.kind === "splitter-input" ? first : second.kind === "splitter-input" ? second : null;
        const splitterOutput = first.kind === "splitter-output" ? first : second.kind === "splitter-output" ? second : null;
        if (fiber && splitterInput) {
            return runMutation(session, () => api.connectSplitterInput(
                session.elementId,
                splitterInput.id,
                fiber.id,
                session.controller.signal,
            ), "Entrada do splitter ligada.");
        }
        if (fiber && splitterOutput) {
            return runMutation(session, () => api.connectSplitterOutput(
                session.elementId,
                splitterOutput.id,
                fiber.id,
                session.controller.signal,
            ), "Saída do splitter ligada.");
        }
        if (splitterInput && splitterOutput) {
            return runMutation(session, () => api.connectSplitterCascade(
                session.elementId,
                splitterInput.id,
                splitterOutput.id,
                session.controller.signal,
            ), "Cascata entre splitters criada.");
        }
        setStatus(session, "Essas duas pontas não formam uma ligação válida.", true);
    }

    async function chooseEndpoint(session, endpoint) {
        const { state, renderer } = dependencies();
        if (!canEdit()) return setStatus(session, "Seu acesso é somente leitura.", true);
        const pending = session.selection.pendingEndpoint;
        if (!pending) {
            session.selection.pendingEndpoint = endpoint;
            renderCablePanel(session);
            renderConnectionControls(session);
            renderSplitterControls(session);
            renderer.render(session);
            setStatus(session, `Ponta selecionada: ${state.endpointLabel(session, endpoint)}. Escolha o destino.`);
            return;
        }
        session.selection.pendingEndpoint = null;
        renderConnectionControls(session);
        renderer.render(session);
        await connectEndpoints(session, pending, endpoint);
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
        const { api, state, renderer, dialog } = dependencies();
        if (action === "close") return close();
        if (action === "refresh") {
            try { await reload(session); } catch (error) { setStatus(session, error.message, true); }
            return;
        }
        if (action === "organize") {
            renderer.organizeVertical(session);
            renderer.fitView(session);
            scheduleLayoutSave(session);
            setStatus(session, "Cabos organizados em colunas verticais.");
            return;
        }
        if (action === "fit-view") {
            renderer.fitView(session);
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
        if (action === "select-endpoint") return chooseEndpoint(session, endpointFromNode(button));
        if (action === "clear-endpoint") {
            session.selection.pendingEndpoint = null;
            renderConnectionControls(session);
            renderCablePanel(session);
            renderSplitterControls(session);
            renderer.render(session);
            setStatus(session, "Seleção cancelada.");
            return;
        }
        if (action === "delete-splice") {
            const accepted = await dialog.confirm({
                title: "Excluir fusão",
                message: "A ligação entre as duas fibras será removida.",
                confirmLabel: "Excluir fusão",
                danger: true,
            });
            if (!accepted || !isCurrent(session)) return;
            return runMutation(session, () => api.deleteSplice(session.elementId, Number(button.dataset.spliceId), session.controller.signal), "Fusão removida.");
        }
        if (action === "add-splitter") {
            const ratio = await dialog.prompt({
                title: "Adicionar splitter",
                label: "Relação",
                value: "1:8",
                options: ["1:2", "1:4", "1:8", "1:16", "1:32", "1:64", "10:90", "15:85", "20:80", "30:70", "40:60", "45:55"],
                confirmLabel: "Adicionar",
            });
            if (!ratio || !isCurrent(session)) return;
            return runMutation(session, async () => {
                const groupId = await internalGroupId(session);
                await api.createSplitter(session.elementId, groupId, ratio, session.controller.signal);
            }, "Splitter criado.");
        }
        if (action === "edit-splitter") {
            const splitter = state.splitterById(session, session.selection.splitterId);
            if (!splitter) return setStatus(session, "Selecione um splitter válido.", true);
            const ratio = await dialog.prompt({
                title: "Alterar splitter",
                label: "Nova relação",
                value: splitter.ratio || "1:8",
                options: ["1:2", "1:4", "1:8", "1:16", "1:32", "1:64", "10:90", "15:85", "20:80", "30:70", "40:60", "45:55"],
                confirmLabel: "Salvar relação",
            });
            if (!ratio || ratio === splitter.ratio || !isCurrent(session)) return;
            return runMutation(session, () => api.updateSplitter(session.elementId, splitter.id, ratio, session.controller.signal), "Relação do splitter atualizada.");
        }
        if (action === "delete-splitter") {
            if (!session.selection.splitterId) return;
            const accepted = await dialog.confirm({
                title: "Excluir splitter",
                message: "As ligações associadas a este splitter poderão ser removidas pelo servidor.",
                confirmLabel: "Excluir splitter",
                danger: true,
            });
            if (!accepted || !isCurrent(session)) return;
            return runMutation(session, () => api.deleteSplitter(session.elementId, session.selection.splitterId, session.controller.signal), "Splitter removido.");
        }
        if (action === "clear-splitter-input") {
            if (!session.selection.splitterId) return;
            return runMutation(session, () => api.clearSplitterInput(session.elementId, session.selection.splitterId, session.controller.signal), "Entrada do splitter desligada.");
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
            const text = await dialog.prompt({
                title: "Nova nota do projeto",
                label: "Texto da nota",
                placeholder: "Descreva a orientação do projetista…",
                multiline: true,
                rows: 5,
                maxLength: 1200,
                confirmLabel: "Adicionar nota",
            });
            if (!text || !String(text).trim() || !isCurrent(session)) return;
            session.layout.notes.push({
                id: `note-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                x: 760,
                y: 70,
                text: String(text).trim().slice(0, 1200),
            });
            renderNotes(session);
            renderer.render(session);
            scheduleLayoutSave(session);
            return;
        }
        if (action === "edit-note") {
            const note = session.layout.notes.find((item) => item.id === button.dataset.noteId);
            if (!note) return;
            const text = await dialog.prompt({
                title: "Editar nota",
                label: "Texto da nota",
                value: note.text,
                multiline: true,
                rows: 5,
                maxLength: 1200,
                confirmLabel: "Salvar nota",
            });
            if (text === null || !isCurrent(session)) return;
            const cleaned = String(text).trim();
            if (!cleaned) return setStatus(session, "A nota não pode ficar vazia.", true);
            note.text = cleaned.slice(0, 1200);
            renderNotes(session);
            renderer.render(session);
            scheduleLayoutSave(session);
            return;
        }
        if (action === "delete-note") {
            const accepted = await dialog.confirm({
                title: "Excluir nota",
                message: "A nota será removida do layout desta caixa.",
                confirmLabel: "Excluir nota",
                danger: true,
            });
            if (!accepted || !isCurrent(session)) return;
            session.layout.notes = session.layout.notes.filter((item) => item.id !== button.dataset.noteId);
            renderNotes(session);
            renderer.render(session);
            scheduleLayoutSave(session);
        }
    }

    function handleChange(session, event) {
        if (!isCurrent(session)) return;
        const field = event.target.dataset.field;
        if (field === "splitter-id") {
            session.selection.splitterId = Number(event.target.value);
            renderSplitterControls(session);
            dependencies().renderer.render(session);
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
            if (hit?.type === "endpoint" && canEdit()) {
                session.dragging = {
                    type: "connection",
                    startEndpoint: hit.endpoint,
                    startScreen: screen,
                    moved: false,
                };
                renderer.setConnectionDraft(session, hit.endpoint, world);
                return;
            }
            if (hit && canEdit() && ["cable", "splitter", "note"].includes(hit.type)) {
                session.dragging = {
                    type: "node",
                    hit,
                    offset: { x: world.x - hit.x, y: world.y - hit.y },
                };
                if (hit.type === "cable") session.selection.cableId = Number(hit.id);
                if (hit.type === "splitter") session.selection.splitterId = Number(hit.id);
                renderCablePanel(session);
                renderSplitterControls(session);
                return;
            }
            session.dragging = {
                type: "pan",
                start: screen,
                panX: session.layout.viewport.panX,
                panY: session.layout.viewport.panY,
            };
        });
        canvas.addEventListener("pointermove", (event) => {
            if (!session.dragging || !isCurrent(session)) return;
            const rect = canvas.getBoundingClientRect();
            const screen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
            if (session.dragging.type === "connection") {
                const dx = screen.x - session.dragging.startScreen.x;
                const dy = screen.y - session.dragging.startScreen.y;
                session.dragging.moved = session.dragging.moved || Math.hypot(dx, dy) > 5;
                renderer.setConnectionDraft(session, session.dragging.startEndpoint, renderer.screenToWorld(session, screen));
            } else if (session.dragging.type === "node") {
                renderer.moveNode(session, session.dragging.hit, screen, session.dragging.offset);
                renderer.render(session);
            } else {
                session.layout.viewport.panX = session.dragging.panX + screen.x - session.dragging.start.x;
                session.layout.viewport.panY = session.dragging.panY + screen.y - session.dragging.start.y;
                renderer.render(session);
            }
        });
        const finish = async (event) => {
            if (!session.dragging || !isCurrent(session)) return;
            const dragging = session.dragging;
            session.dragging = null;
            if (dragging.type === "connection") {
                const rect = canvas.getBoundingClientRect();
                const screen = { x: event.clientX - rect.left, y: event.clientY - rect.top };
                const destination = renderer.hitTestEndpoint(session, screen);
                renderer.clearConnectionDraft(session);
                if (destination && dependencies().state.endpointKey(destination) !== dependencies().state.endpointKey(dragging.startEndpoint)) {
                    session.selection.pendingEndpoint = null;
                    await connectEndpoints(session, dragging.startEndpoint, destination);
                } else if (!dragging.moved) {
                    await chooseEndpoint(session, dragging.startEndpoint);
                } else {
                    session.selection.pendingEndpoint = dragging.startEndpoint;
                    renderConnectionControls(session);
                    renderer.render(session);
                    setStatus(session, "Linha iniciada. Selecione a ponta de destino.");
                }
                return;
            }
            scheduleLayoutSave(session);
        };
        canvas.addEventListener("pointerup", (event) => { finish(event); });
        canvas.addEventListener("pointercancel", (event) => { finish(event); });
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
        version: "0.75.35",
    });
})(window);
