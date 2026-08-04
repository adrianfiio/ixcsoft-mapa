// MAP_V07526_CTO_SUITE: Canvas 2D da CTO/CDO/CEO extraído de map-editor.js
// pra este arquivo próprio -- mesma ideia arquitetural do Rack/Torre
// (map-master-suite.js é o dono do Canvas do Rack/Torre; este arquivo é o
// dono do Canvas da CTO/CDO/CEO). Pedido explícito do usuário: "mudar a
// arquitetura, copiar da torre e levar pra elas mas com outro nome no
// sistema, pois depois iremos remover/adicionar funções" -- ter um
// arquivo próprio permite editar a CTO/CDO/CEO sem nenhum risco de
// quebrar o Rack/Torre (e vice-versa).
//
// Esta versão é uma extração MECÂNICA (recorta e cola, sem reescrever
// nenhuma lógica) do bloco `if (element.splice_box)` que antes vivia
// dentro de showUnifilar() em map-editor.js -- mesmo comportamento,
// mesmos IDs/classes DOM (por isso os 3 scripts decoradores que dependem
// de .unifilar-zoom/.ceo-instructions/.optical-links continuam
// funcionando sem nenhuma mudança), só a localização do código mudou.
(function () {
    "use strict";

    // MAP_V07532_OPTICAL_BOX_SESSION: cada abertura/renderização da
    // CTO/CEO/CDO possui uma sessão exclusiva. Fechar, trocar de caixa ou
    // atualizar invalida a sessão anterior e remove TODOS os listeners
    // globais/locais registrados por ela. Isso evita o segundo open usar DOM
    // removido, listeners antigos ou respostas assíncronas atrasadas.
    let activeSession = null;
    let renderGeneration = 0;

    function dispose() {
        const session = activeSession;
        if (!session) return;
        session.disposed = true;
        session.cleanups.splice(0).reverse().forEach((cleanup) => {
            try { cleanup(); } catch (_error) {}
        });
        if (session.content?.dataset.opticalBoxSession === String(session.generation)) {
            delete session.content.dataset.opticalBoxSession;
        }
        if (activeSession === session) activeSession = null;
    }

    function createSession(content, elementId) {
        dispose();
        const session = {
            generation: ++renderGeneration,
            elementId: String(elementId),
            content,
            cleanups: [],
            disposed: false,
        };
        content.dataset.opticalBoxSession = String(session.generation);
        activeSession = session;
        return session;
    }

    function isActive(session) {
        return Boolean(
            session
            && !session.disposed
            && activeSession === session
            && session.content?.isConnected
            && session.content.dataset.opticalBoxSession === String(session.generation)
        );
    }

    function listen(session, target, type, handler, options) {
        if (!target) return;
        target.addEventListener(type, handler, options);
        session.cleanups.push(() => target.removeEventListener(type, handler, options));
    }

    async function render(element, content, options = {}) {
        const deps = window.networkMap || {};
        const {
            api, notify, escapeHtml, askValue, centerWithin,
            formatBudgetTooltip, splitterLossLabel, openRouteInfoDialog,
            showUnifilar, unifilarDialog,
        } = deps;
        if (!api || (!options.embedded && !unifilarDialog)) {
            throw new Error("map-cto-suite: dependências de map-editor.js ainda não carregaram (window.networkMap incompleto).");
        }
        const session = createSession(content, element.id);
        const ensureActive = () => isActive(session);
        // MAP_V07530_CTO_EMBEDDED_CANVAS: quando embutido no Canvas do
        // Rack/Torre (options.embedded), o refresh depois de qualquer ação
        // não pode fechar/reabrir #unifilar-dialog (era isso que abria a
        // janela flutuante "Editor técnico" antiga por cima do Canvas --
        // bug reportado pelo usuário). Em vez disso, chama de volta
        // options.onRefresh, que re-renderiza no mesmo lugar.
        const refreshCtoView = async () => {
            if (!ensureActive()) return;
            if (options.onRefresh) {
                await options.onRefresh();
                return;
            }
            if (unifilarDialog?.open) unifilarDialog.close();
            await showUnifilar?.(element.id);
        };
        const [optical, savedLayout] = await Promise.all([
            api(`/api/map/elements/${element.id}/splices/`),
            api(`/api/map/elements/${element.id}/layout/`),
        ]);
        if (!ensureActive()) return;
        const layout = savedLayout.layout || {};
            const notes = layout.notes || [];
            const fiberById = new Map(optical.cables.flatMap((cable) => cable.fibers.map((fiber) => [String(fiber.id), fiber])));
            const trayId = element.splice_box.trays[0]?.id || null;
            const allSplitters = element.splice_box.trays.flatMap((tray) => tray.splitters);
            const legacySubtitle = options.embedded ? null : document.getElementById("unifilar-subtitle");
            if (legacySubtitle) legacySubtitle.textContent = `${element.code || "Sem código"} · ${allSplitters.length} splitter(s)`;
            const splitterRatioOptions = [
                { value: "1:2", label: "1:2 (balanceado)" }, { value: "1:4", label: "1:4 (balanceado)" },
                { value: "1:8", label: "1:8 (balanceado)" }, { value: "1:16", label: "1:16 (balanceado)" },
                { value: "1:32", label: "1:32 (balanceado)" }, { value: "1:64", label: "1:64 (balanceado)" },
                { value: "10:90", label: "10/90 (desbalanceado)" }, { value: "15:85", label: "15/85 (desbalanceado)" },
                { value: "20:80", label: "20/80 (desbalanceado)" }, { value: "30:70", label: "30/70 (desbalanceado)" },
                { value: "40:60", label: "40/60 (desbalanceado)" }, { value: "45:55", label: "45/55 (desbalanceado)" },
            ];
            const usedFiberIds = new Set([
                ...optical.splices.flatMap((splice) => [splice.input_fiber_id, splice.output_fiber_id]),
                ...optical.splitter_links.flatMap((link) => [
                    link.input_fiber_id,
                    ...link.ports.map((port) => port.output_fiber_id),
                ]),
            ].filter(Boolean));
            const cascadeUsedPortIds = new Set(
                optical.splitter_links.map((link) => link.input_splitter_port_id).filter(Boolean)
            );
            const incomingCables = optical.cables.filter((cable) => String(cable.destination_id) === String(element.id));
            const outgoingCables = optical.cables.filter((cable) => String(cable.origin_id) === String(element.id));
            const otherCables = optical.cables.filter((cable) => !incomingCables.includes(cable) && !outgoingCables.includes(cable));
            const orderedCables = [...incomingCables, ...outgoingCables, ...otherCables];
            const cableColumns = orderedCables.map((cable) => {
                const incomingIndex = incomingCables.indexOf(cable);
                const outgoingIndex = outgoingCables.indexOf(cable);
                const otherIndex = otherCables.indexOf(cable);
                const defaultPosition = incomingIndex >= 0
                    ? { x: 20, y: 30 + incomingIndex * 330 }
                    : outgoingIndex >= 0
                        ? { x: 900, y: 30 + outgoingIndex * 330 }
                        : { x: 20 + (otherIndex % 2) * 880, y: 30 + Math.floor(otherIndex / 2) * 330 };
                const position = layout[`cable-${cable.id}`] || defaultPosition;
                const usedCount = cable.fibers.filter((fiber) => usedFiberIds.has(fiber.id)).length;
                const hasUsedFiber = usedCount > 0;
                const explicit = (layout.cardState || {})[`cable-${cable.id}`];
                const isExpanded = explicit ? explicit === "expanded" : true;
                const toggleButton = `<button class="expand-fibers" type="button" data-expand-cable="${cable.id}" title="Expandir ou recolher todas as fibras">${isExpanded ? "−" : "+"}</button>`;
                const summary = !isExpanded && hasUsedFiber ? `<small>${usedCount}/${cable.fibers.length} em uso</small>` : "";
                const visibleFibers = isExpanded ? cable.fibers : cable.fibers.filter((fiber) => !usedFiberIds.has(fiber.id));
                const cutControl = cable.requires_cut
                    ? `<button type="button" class="fusion-cut-passing-cable" data-cut-passing-cable="${cable.id}">Cortar na caixa</button>`
                    : "";
                const passNote = cable.requires_cut
                    ? '<span class="fusion-pass-note">Este cabo apenas passa pela caixa. Corte-o aqui antes de criar fusões.</span>'
                    : "";
                return `<section class="fiber-cable-node graph-node master-canvas-node master-cable-node-v07519 ${isExpanded ? "expanded" : ""}" data-node-key="cable-${cable.id}" data-cable-node-id="${cable.id}" data-requires-cut="${cable.requires_cut ? "true" : "false"}" style="left:${position.x}px;top:${position.y}px"><header>${escapeHtml(cable.name)}${summary}${cutControl}<span>${toggleButton}<span class="drag-grip">⋮⋮</span></span></header>
                ${passNote}<div class="fiber-port-list">${visibleFibers.map((fiber) => `<button type="button" class="fiber-port ${usedFiberIds.has(fiber.id) ? "used" : ""}" ${usedFiberIds.has(fiber.id) ? "" : 'draggable="true"'} data-used="${usedFiberIds.has(fiber.id)}" data-fiber-id="${fiber.id}" data-cable-id="${cable.id}" style="--fiber-color:${escapeHtml(fiber.color_hex)}"><i></i>F${fiber.number} · ${escapeHtml(fiber.color_name)}${usedFiberIds.has(fiber.id) ? " · Em uso" : ""}</button>`).join("") || `<span>${isExpanded ? "Sem fibras geradas" : "Todas as fibras em uso"}</span>`}</div></section>`;
            }).join("");
            const splitterNodes = allSplitters.map((splitter, index) => {
                const position = layout[`splitter-${splitter.id}`] || { x: 470 + (index % 2) * 260, y: 40 + Math.floor(index / 2) * 220 };
                return `<div class="graph-splitter-node graph-node master-canvas-node master-splitter-node-v07519" data-node-key="splitter-${splitter.id}" style="left:${position.x}px;top:${position.y}px">
                <div class="graph-splitter"><button type="button" class="splitter-input-port master-node-port ${splitter.input_fiber_id || splitter.input_splitter_port_id ? "linked used" : ""}" data-linked="${splitter.input_fiber_id || splitter.input_splitter_port_id || ""}" data-splitter-id="${splitter.id}" title="${splitter.input_splitter_port_id ? "Alimentado por outro splitter (cascata)" : ""}">ENT</button><b title="Perda estimada">${escapeHtml(splitter.ratio)}<small>${splitterLossLabel(splitter.ratio)}</small></b><div class="splitter-output-grid">${splitter.ports.map((port) => `<button type="button" class="splitter-output-port master-node-port ${port.output_fiber_id || cascadeUsedPortIds.has(port.id) ? "linked used" : ""}" data-linked="${port.output_fiber_id || (cascadeUsedPortIds.has(port.id) ? "cascade" : "")}" data-port-id="${port.id}" title="${cascadeUsedPortIds.has(port.id) ? "Alimenta outro splitter (cascata)" : `Fibra ${port.number} de saída do splitter`}">F${port.number}</button>`).join("")}</div></div>
                <div class="splitter-actions"><span class="drag-grip">⋮⋮</span><button type="button" data-edit-splitter="${splitter.id}" data-ratio="${escapeHtml(splitter.ratio)}">Editar</button><button type="button" data-delete-splitter="${splitter.id}">×</button></div></div>`;
            }).join("");
            const noteNodes = notes.map((note) => `<div class="note-node graph-node" data-node-key="note-${note.id}" style="left:${note.x}px;top:${note.y}px">
                <header><span class="drag-grip">⋮⋮</span><button type="button" class="note-delete" data-delete-note="${note.id}">×</button></header>
                <div class="note-text" data-note-id="${note.id}">${escapeHtml(note.text)}</div></div>`).join("");
            // MAP_V07523_CTO_TOWER_TOOLBAR: barra de ferramentas copiada do
            // Rack/Torre (mesmas classes CSS .tower-workspace-*/.tower-popover-v0750,
            // reaproveitadas sem duplicar CSS). Diferente do Rack/Torre, aqui
            // NÃO existe "+ Adicionar equipamento" nem "Ligar portas"/"Editar
            // linhas" — a CTO/CDO/CEO não tem equipamento genérico, só
            // splitter e cabo. "Estrutura" mostra o que já existe (splitters
            // e cabos), "Fibras" destaca portas livres/usadas, "Atualizar"
            // recarrega. Ferramentas só tem o que faz sentido aqui (estilo de
            // linha) — sem "Importar YAML"/"Organizar equipamentos", que são
            // conceitos de equipamento genérico que a CTO/CDO não tem.
            const structureSplitterItems = allSplitters.map((splitter) => `<button type="button" data-cto-structure-jump="splitter-${splitter.id}"><span><strong>${escapeHtml(splitter.name)}</strong><small>${escapeHtml(splitter.ratio)} · ${splitter.ports.filter((port) => port.output_fiber_id).length}/${splitter.ports.length} saídas em uso</small></span><i>›</i></button>`).join("");
            const structureCableItems = orderedCables.map((cable) => `<button type="button" data-cto-structure-jump="cable-${cable.id}"><span><strong>${escapeHtml(cable.name)}</strong><small>${cable.fibers.filter((fiber) => usedFiberIds.has(fiber.id)).length}/${cable.fibers.length} fibras em uso</small></span><i>›</i></button>`).join("");
            content.innerHTML = `<div class="tower-workspace-toolbar-v0750 ceo-quick-toolbar-v07521">
                <div class="tower-workspace-title-v0750"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="4"></rect><path d="M8 7h8M8 10h8M8 13h8M8 16h8"></path></svg><span><strong>Editor técnico · ${escapeHtml(element.name)}</strong><small>Splitter, cabos e fusões</small></span></div>
                <div class="tower-workspace-actions-v0750">
                    <button type="button" data-cto-structure-v07523><span>Estrutura</span></button>
                    <button type="button" data-ceo-quick-add="add-splitter">+ Splitter</button>
                    <button type="button" data-ceo-quick-add="add-note">+ Nota</button>
                    <button type="button" data-cto-fiber-focus-v07523><span>Fibras</span></button>
                    <button type="button" data-cto-refresh-v07523><span>Atualizar</span></button>
                    <div class="tower-toolbar-menu-v0750">
                        <button type="button" data-cto-tools-toggle-v07523 aria-controls="cto-tools-menu-v07523" aria-expanded="false"><span>Ferramentas</span></button>
                        <div id="cto-tools-menu-v07523" class="tower-popover-v0750 tower-tools-menu-v0750" role="menu">
                            <label class="cto-tools-line-style-v07523">Estilo de linha<select id="connection-style"><option value="curve">Curvas</option><option value="straight">Retas</option><option value="orthogonal">Ortogonal</option></select></label>
                        </div>
                    </div>
                    <span class="unifilar-zoom"><button id="unifilar-zoom-out" type="button" title="Diminuir">−</button><output id="unifilar-zoom-value">100%</output><button id="unifilar-zoom-in" type="button" title="Ampliar">+</button><button id="unifilar-zoom-reset" type="button" title="Ajustar">Ajustar</button></span>
                    <button type="button" class="tower-workspace-close-v0758" data-cto-close-v07527 title="Fechar editor técnico" aria-label="Fechar editor técnico"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"></path></svg></button>
                </div>
            </div>
            <div id="unifilar-feedback" class="cto-feedback-v07523">Clique em duas fibras para ligar, ou nas portas do splitter. Botão direito no fundo do quadro para adicionar splitter ou nota. Clique numa linha para excluir.</div>
            <div class="tower-drawer-v0750 cto-structure-drawer-v07523" hidden>
                <header><div><strong>Estrutura</strong><small>O que já existe nesta caixa</small></div><button type="button" data-cto-structure-close-v07523 aria-label="Fechar">×</button></header>
                <div class="tower-drawer-body-v0750">
                    <section class="tower-structure-info-v0750 active">
                        <div class="tower-structure-hero-v0750"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="4"></rect><path d="M8 7h8M8 10h8M8 13h8M8 16h8"></path></svg><div><strong>${escapeHtml(element.name)}</strong><span>${escapeHtml(element.code || "Sem código")}</span></div></div>
                        <h3>Splitters</h3>
                        <div class="tower-structure-list-v0750">${structureSplitterItems || "<p>Nenhum splitter.</p>"}</div>
                        <h3>Cabos</h3>
                        <div class="tower-structure-list-v0750">${structureCableItems || "<p>Nenhum cabo conectado.</p>"}</div>
                    </section>
                </div>
            </div>
                <div class="optical-graph"><div class="graph-nodes"><svg class="optical-links"></svg>${cableColumns || '<p>Nenhum cabo conectado à CEO.</p>'}${splitterNodes}${noteNodes}</div><div class="map-context-menu ceo-canvas-menu" hidden><button type="button" data-canvas-action="add-splitter">+ Adicionar splitter</button><button type="button" data-canvas-action="add-note">+ Adicionar nota</button></div><div class="map-context-menu link-action-menu" hidden><button type="button" data-link-action="info">Informações de rota</button><button type="button" class="danger" data-link-action="delete">Excluir</button></div></div>`;
            const localCloseButton = content.querySelector("[data-cto-close-v07527]");
            if (localCloseButton) {
                localCloseButton.hidden = Boolean(options.embedded);
                localCloseButton.onclick = () => unifilarDialog?.close();
            }
            content.querySelector("[data-cto-structure-v07523]").onclick = () => {
                content.querySelector(".cto-structure-drawer-v07523").hidden = false;
            };
            content.querySelector("[data-cto-structure-close-v07523]").onclick = () => {
                content.querySelector(".cto-structure-drawer-v07523").hidden = true;
            };
            content.querySelectorAll("[data-cto-structure-jump]").forEach((button) => {
                button.onclick = () => {
                    content.querySelector(".cto-structure-drawer-v07523").hidden = true;
                    const target = content.querySelector(`[data-node-key="${button.dataset.ctoStructureJump}"]`);
                    if (!target) return;
                    target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
                    target.classList.add("structure-highlight-v07523");
                    window.setTimeout(() => target.classList.remove("structure-highlight-v07523"), 1400);
                };
            });
            content.querySelector("[data-cto-fiber-focus-v07523]").onclick = (event) => {
                const graph = content.querySelector(".optical-graph");
                graph.classList.toggle("fiber-focus-v07523");
                event.currentTarget.classList.toggle("active", graph.classList.contains("fiber-focus-v07523"));
            };
            content.querySelector("[data-cto-refresh-v07523]").onclick = async () => {
                await refreshCtoView(); notify("Dados atualizados.");
            };
            const ctoToolsToggle = content.querySelector("[data-cto-tools-toggle-v07523]");
            const ctoToolsMenu = content.querySelector("#cto-tools-menu-v07523");
            ctoToolsToggle.onclick = (event) => {
                event.preventDefault();
                event.stopPropagation();
                const open = !ctoToolsMenu.classList.contains("open");
                ctoToolsMenu.classList.toggle("open", open);
                ctoToolsToggle.setAttribute("aria-expanded", String(open));
            };
            const closeCtoToolsMenu = (event) => {
                if (!ctoToolsMenu.classList.contains("open")) return;
                if (event.target.closest(".tower-toolbar-menu-v0750")) return;
                ctoToolsMenu.classList.remove("open");
                ctoToolsToggle.setAttribute("aria-expanded", "false");
            };
            listen(session, document, "click", closeCtoToolsMenu);
            let draggedFiber = null;
            let selectedFiber = null;
            let selectedSplitterPort = null;
            const createSplice = async (input, output) => {
                if (!input || input === output) return;
                const inputNode = content.querySelector(`[data-fiber-id="${input}"]`);
                const outputNode = content.querySelector(`[data-fiber-id="${output}"]`);
                if (inputNode.dataset.cableId === outputNode.dataset.cableId) return notify("Escolha fibras de cabos diferentes.", true);
                await api(`/api/map/elements/${element.id}/splices/`, {
                    method: "POST",
                    body: JSON.stringify({ tray_id: trayId, input_fiber_id: input, output_fiber_id: output }),
                });
                await refreshCtoView(); notify("Fusão criada na caixa.");
            };
            content.querySelectorAll(".fiber-port").forEach((chip) => {
                chip.ondragstart = (event) => {
                    if (chip.dataset.used === "true") {
                        event.preventDefault();
                        return notify("Esta fibra já está em uso. Clique na linha atual para removê-la antes de reutilizar.", true);
                    }
                    draggedFiber = chip.dataset.fiberId;
                };
                chip.ondragover = (event) => event.preventDefault();
                chip.ondrop = async (event) => {
                    event.preventDefault();
                    try { await createSplice(draggedFiber, chip.dataset.fiberId); }
                    catch (error) { notify(error.message, true); }
                };
                chip.onclick = async () => {
                    if (chip.dataset.used === "true") {
                        return notify("Esta fibra já está em uso. Clique na linha atual para excluir a ligação antes de reutilizar.", true);
                    }
                    if (selectedSplitterPort) {
                        try {
                            await api(`/api/map/elements/${element.id}/splices/`, {
                                method: "POST",
                                body: JSON.stringify({ connection_type: "splitter_output", port_id: selectedSplitterPort, fiber_id: chip.dataset.fiberId }),
                            });
                            await refreshCtoView(); notify("Saída do splitter conectada à fibra.");
                        } catch (error) { notify(error.message, true); }
                        return;
                    }
                    if (!selectedFiber) {
                        selectedFiber = chip.dataset.fiberId; chip.classList.add("selected");
                        notify("Primeira porta selecionada. Clique na porta de destino.");
                        return;
                    }
                    try { await createSplice(selectedFiber, chip.dataset.fiberId); }
                    catch (error) { notify(error.message, true); }
                };
            });
            content.querySelectorAll(".splitter-input-port").forEach((button) => {
                button.onclick = async () => {
                    if (button.dataset.linked) return notify("A entrada já está ligada. Clique na linha para removê-la antes de trocar.", true);
                    if (selectedSplitterPort) {
                        try {
                            await api(`/api/map/elements/${element.id}/splices/`, {
                                method: "POST",
                                body: JSON.stringify({ connection_type: "splitter_cascade", splitter_id: button.dataset.splitterId, source_port_id: selectedSplitterPort }),
                            });
                            await refreshCtoView(); notify("Splitters conectados em cascata.");
                        } catch (error) { notify(error.message, true); }
                        return;
                    }
                    if (!selectedFiber) return notify("Selecione primeiro a fibra ou a saída de outro splitter que alimentará este splitter.", true);
                    try {
                        await api(`/api/map/elements/${element.id}/splices/`, {
                            method: "POST",
                            body: JSON.stringify({ connection_type: "splitter_input", splitter_id: button.dataset.splitterId, fiber_id: selectedFiber }),
                        });
                        await refreshCtoView(); notify("Fibra conectada à entrada do splitter.");
                    } catch (error) { notify(error.message, true); }
                };
                button.oncontextmenu = async (event) => {
                    event.preventDefault();
                    if (!button.dataset.linked || !confirm("Remover a fibra da entrada deste splitter?")) return;
                    await api(`/api/map/elements/${element.id}/splices/`, {
                        method: "POST",
                        body: JSON.stringify({ connection_type: "clear_splitter_input", splitter_id: button.dataset.splitterId }),
                    });
                    await refreshCtoView(); notify("Ligação removida.");
                };
            });
            content.querySelectorAll(".splitter-output-port").forEach((button) => {
                button.onclick = () => {
                    if (button.dataset.linked) return notify(`A saída ${button.textContent} já está ligada. Clique na linha para removê-la antes de trocar.`, true);
                    selectedFiber = null;
                    selectedSplitterPort = button.dataset.portId;
                    content.querySelectorAll(".splitter-output-port").forEach((item) => item.classList.remove("selected"));
                    button.classList.add("selected");
                    notify("Saída do splitter selecionada. Clique numa fibra de destino ou no ENT de outro splitter para cascatear.");
                };
                button.oncontextmenu = async (event) => {
                    event.preventDefault();
                    if (!button.dataset.linked || !confirm("Remover esta ligação de saída?")) return;
                    await api(`/api/map/elements/${element.id}/splices/`, {
                        method: "POST",
                        body: JSON.stringify({ connection_type: "clear_splitter_output", port_id: button.dataset.portId }),
                    });
                    await refreshCtoView(); notify("Ligação removida.");
                };
            });
            const budgetByLink = new Map();
            const redrawOpticalLinks = () => {
                if (!ensureActive()) return;
                budgetByLink.clear();
                const graphNodesEl = content.querySelector(".graph-nodes");
                const svg = content.querySelector(".optical-links");
                if (!graphNodesEl || !svg) return;
                const width = graphNodesEl.scrollWidth, height = graphNodesEl.scrollHeight;
                svg.innerHTML = "";
                svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
                svg.style.width = `${width}px`;
                svg.style.height = `${height}px`;
                const lineStyle = content.querySelector("#connection-style")?.value
                    || layout.connectionStyle
                    || "curve";
                let gradientIndex = 0;
                const drawLink = (source, target, colors, action = null, budget = null) => {
                    if (!source || !target) return;
                    const { x: x1, y: y1 } = centerWithin(source, graphNodesEl);
                    const { x: x2, y: y2 } = centerWithin(target, graphNodesEl);
                    let path = `M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`;
                    if (lineStyle === "straight") path = `M${x1},${y1} L${x2},${y2}`;
                    if (lineStyle === "orthogonal") path = `M${x1},${y1} H${(x1+x2)/2} V${y2} H${x2}`;
                    const palette = (Array.isArray(colors) ? colors : [colors]).filter(Boolean);
                    let stroke = escapeHtml(palette[0] || "#94a3b8");
                    if (palette.length > 1 && palette[0] !== palette[1]) {
                        const gradientId = `fiber-gradient-${element.id}-${gradientIndex++}`;
                        svg.insertAdjacentHTML("beforeend", `<defs><linearGradient id="${gradientId}" gradientUnits="userSpaceOnUse" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"><stop offset="0%" stop-color="${escapeHtml(palette[0])}"></stop><stop offset="46%" stop-color="${escapeHtml(palette[0])}"></stop><stop offset="54%" stop-color="${escapeHtml(palette[1])}"></stop><stop offset="100%" stop-color="${escapeHtml(palette[1])}"></stop></linearGradient></defs>`);
                        stroke = `url(#${gradientId})`;
                    }
                    const actionData = action ? `data-link-type="${action.type}" data-link-id="${action.id}"` : "";
                    const tooltip = budget ? formatBudgetTooltip(budget) : "";
                    if (action) budgetByLink.set(`${action.type}:${action.id}`, budget || null);
                    svg.insertAdjacentHTML("beforeend", `<path d="${path}" stroke="${stroke}" ${actionData}>${tooltip ? `<title>${escapeHtml(tooltip)}</title>` : ""}</path>`);
                };
                optical.splices.forEach((splice) => drawLink(
                    content.querySelector(`[data-fiber-id="${splice.input_fiber_id}"]`),
                    content.querySelector(`[data-fiber-id="${splice.output_fiber_id}"]`),
                    [splice.input.color_hex, splice.output.color_hex],
                    { type: "splice", id: splice.id },
                    splice.budget
                ));
                optical.splitter_links.forEach((link) => {
                    const inputColor = fiberById.get(String(link.input_fiber_id))?.color_hex;
                    if (link.input_fiber_id) drawLink(
                        content.querySelector(`[data-fiber-id="${link.input_fiber_id}"]`),
                        content.querySelector(`[data-splitter-id="${link.splitter_id}"]`),
                        inputColor,
                        { type: "splitter_input", id: link.splitter_id },
                        link.input_budget
                    );
                    if (link.input_splitter_port_id) drawLink(
                        content.querySelector(`[data-port-id="${link.input_splitter_port_id}"]`),
                        content.querySelector(`[data-splitter-id="${link.splitter_id}"]`),
                        "#2dd4bf",
                        { type: "splitter_input", id: link.splitter_id },
                        link.input_budget
                    );
                    link.ports.forEach((port) => {
                        if (port.output_fiber_id) drawLink(
                            content.querySelector(`[data-port-id="${port.id}"]`),
                            content.querySelector(`[data-fiber-id="${port.output_fiber_id}"]`),
                            [inputColor, fiberById.get(String(port.output_fiber_id))?.color_hex],
                            { type: "splitter_output", id: port.id },
                            port.budget
                        );
                    });
                });
                svg.querySelectorAll("[data-link-type]").forEach((path) => {
                    path.onclick = (event) => {
                        activeLinkPath = path;
                        const graphRect = content.querySelector(".optical-graph").getBoundingClientRect();
                        linkActionMenu.style.left = `${event.clientX - graphRect.left}px`;
                        linkActionMenu.style.top = `${event.clientY - graphRect.top}px`;
                        linkActionMenu.hidden = false;
                    };
                });
            };
            const linkActionMenu = content.querySelector(".link-action-menu");
            let activeLinkPath = null;
            const removeActiveLink = async () => {
                if (activeLinkPath.dataset.linkType === "splice") {
                    await api(`/api/map/elements/${element.id}/splices/${activeLinkPath.dataset.linkId}/`, { method: "DELETE" });
                } else {
                    await api(`/api/map/elements/${element.id}/splices/`, {
                        method: "POST",
                        body: JSON.stringify({
                            connection_type: `clear_${activeLinkPath.dataset.linkType}`,
                            [activeLinkPath.dataset.linkType === "splitter_input" ? "splitter_id" : "port_id"]: activeLinkPath.dataset.linkId,
                        }),
                    });
                }
                await refreshCtoView(); notify("Ligação removida.");
            };
            linkActionMenu.querySelector('[data-link-action="info"]').onclick = () => {
                linkActionMenu.hidden = true;
                const key = activeLinkPath ? `${activeLinkPath.dataset.linkType}:${activeLinkPath.dataset.linkId}` : "";
                openRouteInfoDialog(budgetByLink.get(key) || null);
            };
            linkActionMenu.querySelector('[data-link-action="delete"]').onclick = async () => {
                linkActionMenu.hidden = true;
                if (activeLinkPath) await removeActiveLink();
            };
            listen(session, content, "click", (event) => {
                if (!event.target.closest(".link-action-menu") && !event.target.closest("[data-link-type]")) linkActionMenu.hidden = true;
            });
            const styleSelect = content.querySelector("#connection-style");
            if (!styleSelect) throw new Error("Canvas óptico sem seletor local de estilo de linha.");
            styleSelect.value = layout.connectionStyle || "curve";
            styleSelect.onchange = async () => {
                layout.connectionStyle = styleSelect.value;
                redrawOpticalLinks();
                await api(`/api/map/elements/${element.id}/layout/`, {
                    method: "PATCH", body: JSON.stringify({ layout }),
                });
            };
            const graphNodes = content.querySelector(".graph-nodes");
            const zoomOutput = content.querySelector("#unifilar-zoom-value");
            const fitZoom = () => {
                const graph = content.querySelector(".optical-graph");
                const widthZoom = (graph.clientWidth - 48) / Math.max(1, graphNodes.scrollWidth);
                const heightZoom = (graph.clientHeight - 48) / Math.max(1, graphNodes.scrollHeight);
                return Math.max(.4, Math.min(1.15, widthZoom, heightZoom));
            };
            let graphZoom = layout.zoom ? Math.max(.4, Math.min(1.6, Number(layout.zoom))) : .7;
            // Layouts antigos ficaram persistidos em 50%. A nova base visual é
            // 70%, mantendo os cartões legíveis sem perder a visão geral.
            if (graphZoom < .65) graphZoom = .7;
            const applyGraphZoom = () => {
                if (graphZoom === null) graphZoom = fitZoom();
                graphNodes.style.transform = `scale(${graphZoom})`;
                graphNodes.style.transformOrigin = "top left";
                if (zoomOutput) zoomOutput.value = `${Math.round(graphZoom * 100)}%`;
                requestAnimationFrame(redrawOpticalLinks);
            };
            const saveZoom = () => {
                layout.zoom = graphZoom;
                return api(`/api/map/elements/${element.id}/layout/`, {
                    method: "PATCH", body: JSON.stringify({ layout }),
                });
            };
            const zoomOutButton = content.querySelector("#unifilar-zoom-out");
            const zoomInButton = content.querySelector("#unifilar-zoom-in");
            const zoomResetButton = content.querySelector("#unifilar-zoom-reset");
            if (zoomOutButton) zoomOutButton.onclick = () => {
                graphZoom = Math.max(.5, graphZoom - .1); applyGraphZoom(); saveZoom();
            };
            if (zoomInButton) zoomInButton.onclick = () => {
                graphZoom = Math.min(1.6, graphZoom + .1); applyGraphZoom(); saveZoom();
            };
            if (zoomResetButton) zoomResetButton.onclick = () => {
                graphZoom = fitZoom(); applyGraphZoom(); saveZoom();
            };
            applyGraphZoom();
            // MAP_V07518_OPTICAL_CANVAS_PARITY: zoom com Ctrl+roda do mouse e
            // pan arrastando o fundo — mesma sensação do Canvas 2D de
            // Rack/Torre. Não mexe no zoom por botão nem no clique-para-ligar
            // (cabo/splitter/porta) que já existe; só soma outro jeito de
            // navegar no mesmo `.optical-graph`.
            const opticalGraph = content.querySelector(".optical-graph");
            if (opticalGraph) {
                listen(session, opticalGraph, "wheel", (event) => {
                    if (!event.ctrlKey) return;
                    event.preventDefault();
                    graphZoom = Math.max(.4, Math.min(1.6, graphZoom + (event.deltaY < 0 ? .1 : -.1)));
                    applyGraphZoom();
                    saveZoom();
                }, { passive: false });
                listen(session, opticalGraph, "pointerdown", (event) => {
                    if (event.button !== 0 || event.target.closest(".graph-node, button, select, input, textarea, a")) return;
                    opticalGraph.setPointerCapture?.(event.pointerId);
                    const startX = event.clientX;
                    const startY = event.clientY;
                    const scrollStartX = opticalGraph.scrollLeft;
                    const scrollStartY = opticalGraph.scrollTop;
                    opticalGraph.classList.add("panning-v07518");
                    const move = (moveEvent) => {
                        opticalGraph.scrollLeft = scrollStartX - (moveEvent.clientX - startX);
                        opticalGraph.scrollTop = scrollStartY - (moveEvent.clientY - startY);
                    };
                    const up = () => {
                        opticalGraph.removeEventListener("pointermove", move);
                        opticalGraph.classList.remove("panning-v07518");
                    };
                    opticalGraph.addEventListener("pointermove", move);
                    opticalGraph.addEventListener("pointerup", up, { once: true });
                });
            }
            content.querySelectorAll("[data-expand-cable]").forEach((button) => {
                button.onclick = async () => {
                    const cableId = String(button.dataset.expandCable);
                    const cableNode = content.querySelector(`[data-cable-node-id="${cableId}"]`);
                    const nowExpanded = !cableNode.classList.contains("expanded");
                    layout.cardState = { ...(layout.cardState || {}), [`cable-${cableId}`]: nowExpanded ? "expanded" : "collapsed" };
                    await api(`/api/map/elements/${element.id}/layout/`, {
                        method: "PATCH", body: JSON.stringify({ layout }),
                    });
                    await refreshCtoView();
                };
            });
            content.querySelectorAll(".graph-node").forEach((node) => {
                const grip = node.querySelector(".drag-grip");
                grip.onpointerdown = (event) => {
                    event.preventDefault();
                    const startX = event.clientX, startY = event.clientY;
                    const originX = parseFloat(node.style.left), originY = parseFloat(node.style.top);
                    grip.setPointerCapture(event.pointerId);
                    const isNote = node.dataset.nodeKey.startsWith("note-");
                    grip.onpointermove = (move) => {
                        const candidateX = originX + (move.clientX - startX) / graphZoom;
                        const candidateY = originY + (move.clientY - startY) / graphZoom;
                        const width = node.offsetWidth, height = node.offsetHeight;
                        const collides = !isNote && [...content.querySelectorAll(".graph-node")].some((other) => {
                            if (other === node || other.dataset.nodeKey.startsWith("note-")) return false;
                            const ox = parseFloat(other.style.left) || 0, oy = parseFloat(other.style.top) || 0;
                            return candidateX < ox + other.offsetWidth && candidateX + width > ox
                                && candidateY < oy + other.offsetHeight && candidateY + height > oy;
                        });
                        if (collides) return;
                        node.style.left = `${candidateX}px`;
                        node.style.top = `${candidateY}px`;
                        redrawOpticalLinks();
                    };
                    grip.onpointerup = async () => {
                        grip.onpointermove = null;
                        const x = Math.round(parseFloat(node.style.left));
                        const y = Math.round(parseFloat(node.style.top));
                        if (node.dataset.nodeKey.startsWith("note-")) {
                            const noteId = node.dataset.nodeKey.slice("note-".length);
                            layout.notes = notes.map((note) => String(note.id) === noteId ? { ...note, x, y } : note);
                        } else {
                            layout[node.dataset.nodeKey] = { x, y };
                        }
                        await api(`/api/map/elements/${element.id}/layout/`, {
                            method: "PATCH", body: JSON.stringify({ layout }),
                        });
                        notify("Posição salva.");
                    };
                };
            });
            const graphEl = content.querySelector(".optical-graph");
            const canvasMenu = content.querySelector(".ceo-canvas-menu");
            let canvasMenuPoint = null;
            listen(session, graphEl, "contextmenu", (event) => {
                if (event.target.closest(".graph-node") || event.target.closest(".ceo-canvas-menu")) return;
                event.preventDefault();
                const graphRect = graphEl.getBoundingClientRect();
                canvasMenuPoint = {
                    x: (event.clientX - graphRect.left + graphEl.scrollLeft) / graphZoom,
                    y: (event.clientY - graphRect.top + graphEl.scrollTop) / graphZoom,
                };
                canvasMenu.style.left = `${event.clientX - graphRect.left}px`;
                canvasMenu.style.top = `${event.clientY - graphRect.top}px`;
                canvasMenu.hidden = false;
            });
            listen(session, content, "click", (event) => {
                if (!event.target.closest(".ceo-canvas-menu")) canvasMenu.hidden = true;
            });
            canvasMenu.querySelector('[data-canvas-action="add-splitter"]').onclick = async () => {
                canvasMenu.hidden = true;
                if (!canvasMenuPoint || !trayId) return;
                const ratio = await askValue({ title: "Adicionar splitter", label: "Proporção", value: "1:8", options: splitterRatioOptions });
                if (!ratio) return;
                try {
                    const result = await api(`/api/map/elements/${element.id}/splitters/`, {
                        method: "POST",
                        body: JSON.stringify({ tray_id: trayId, ratio }),
                    });
                    layout[`splitter-${result.splitter_id}`] = { x: Math.round(canvasMenuPoint.x), y: Math.round(canvasMenuPoint.y) };
                    await api(`/api/map/elements/${element.id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
                    await refreshCtoView(); notify("Splitter adicionado.");
                } catch (error) { notify(error.message, true); }
            };
            canvasMenu.querySelector('[data-canvas-action="add-note"]').onclick = async () => {
                canvasMenu.hidden = true;
                if (!canvasMenuPoint) return;
                const text = await window.mapV0758?.editLongText?.({ title: "Adicionar nota", label: "Texto da nota" });
                if (!text) return;
                layout.notes = [...notes, { id: `n${Date.now()}`, x: Math.round(canvasMenuPoint.x), y: Math.round(canvasMenuPoint.y), text }];
                await api(`/api/map/elements/${element.id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
                await refreshCtoView(); notify("Nota adicionada.");
            };
            // MAP_V07521_CEO_QUICK_TOOLBAR: os botões da barra nova só
            // reaproveitam os MESMOS handlers do menu de contexto (fundo do
            // quadro, botão direito) — nada de lógica nova, só um atalho
            // que simula o ponto de clique no centro da área visível.
            content.querySelectorAll("[data-ceo-quick-add]").forEach((button) => {
                button.onclick = () => {
                    const rect = graphEl.getBoundingClientRect();
                    canvasMenuPoint = {
                        x: (graphEl.scrollLeft + rect.width / 2) / graphZoom,
                        y: (graphEl.scrollTop + rect.height / 2) / graphZoom,
                    };
                    canvasMenu.querySelector(`[data-canvas-action="${button.dataset.ceoQuickAdd}"]`)?.click();
                };
            });
            content.querySelectorAll("[data-delete-note]").forEach((button) => {
                button.onclick = async () => {
                    const accepted = await window.mapV0758?.confirmAction?.({
                        title: "Excluir nota",
                        message: "A nota será removida do diagrama de fusões.",
                        confirmLabel: "Excluir nota",
                        cancelLabel: "Cancelar",
                        danger: true,
                    });
                    if (!accepted) return;
                    layout.notes = notes.filter((note) => String(note.id) !== String(button.dataset.deleteNote));
                    await api(`/api/map/elements/${element.id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
                    await refreshCtoView(); notify("Nota excluída.");
                };
            });
            content.querySelectorAll("[data-note-id]").forEach((textEl) => {
                textEl.onclick = async () => {
                    const note = notes.find((item) => String(item.id) === String(textEl.dataset.noteId));
                    const text = await window.mapV0758?.editLongText?.({ title: "Editar nota", label: "Texto da nota", value: note?.text || "" });
                    if (text === null || text === undefined) return;
                    layout.notes = notes.map((item) => String(item.id) === String(textEl.dataset.noteId) ? { ...item, text } : item);
                    await api(`/api/map/elements/${element.id}/layout/`, { method: "PATCH", body: JSON.stringify({ layout }) });
                    await refreshCtoView(); notify("Nota atualizada.");
                };
            });
            content.querySelectorAll("[data-edit-splitter]").forEach((button) => {
                button.onclick = async () => {
                    const ratio = await askValue({ title: "Editar splitter", label: "Nova proporção", value: button.dataset.ratio, options: splitterRatioOptions });
                    if (!ratio) return;
                    try {
                        await api(`/api/map/elements/${element.id}/splitters/${button.dataset.editSplitter}/`, {
                            method: "PATCH",
                            body: JSON.stringify({ ratio }),
                        });
                        await refreshCtoView(); notify("Splitter atualizado.");
                    } catch (error) { notify(error.message, true); }
                };
            });
            content.querySelectorAll("[data-delete-splitter]").forEach((button) => {
                button.onclick = async () => {
                    if (!confirm("Excluir este splitter e suas ligações?")) return;
                    await api(`/api/map/elements/${element.id}/splitters/${button.dataset.deleteSplitter}/`, { method: "DELETE" });
                    await refreshCtoView(); notify("Splitter excluído.");
                };
            });
            if (options.embedded) {
                content.classList.add("cto-embedded-canvas-v07530");
            } else {
                unifilarDialog.classList.add("map-v0758-optical-workspace");
                if (!unifilarDialog.open) unifilarDialog.showModal();
            }
            requestAnimationFrame(redrawOpticalLinks);
            window.setTimeout(redrawOpticalLinks, 150);
            listen(session, window, "resize", redrawOpticalLinks);
            listen(session, graphEl, "scroll", redrawOpticalLinks);
            listen(session, content, "scroll", redrawOpticalLinks);
            if (!options.embedded) listen(session, unifilarDialog, "close", dispose, { once: true });
    }

    window.mapCtoSuite = Object.freeze({ render, dispose });
})();
