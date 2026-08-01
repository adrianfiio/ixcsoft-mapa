(function () {
    "use strict";

    const dialog = document.getElementById("kmz-import-dialog");
    const openButton = document.getElementById("import-button");
    if (!dialog || !openButton) return;

    const content = document.getElementById("kmz-import-content");
    const status = document.getElementById("kmz-import-status");
    const backButton = document.getElementById("kmz-back");
    const nextButton = document.getElementById("kmz-next");
    const executeButton = document.getElementById("kmz-execute");
    const returnButton = document.getElementById("kmz-preview-return");

    const POINT_TYPES = [
        ["review", "Revisar"],
        ["cto", "CTO"],
        ["splice_box", "CEO/CDO · caixa de emenda"],
        ["technical_reserve", "Reserva técnica"],
        ["dio", "DIO"],
        ["pole", "Poste"],
        ["pop", "POP/CPD"],
        ["olt", "OLT"],
        ["rack", "Rack"],
        ["tower", "Torre"],
        ["other", "Outro"],
        ["ignore", "Ignorar"],
    ];
    const LINE_ACTIONS = [
        ["review", "Revisar"],
        ["cable", "Cabo óptico"],
        ["reserve_line", "Reserva de cabo desenhada"],
        ["route", "Traçado de rota"],
        ["ignore", "Ignorar"],
    ];
    const CABLE_TYPES = [
        ["distribution", "Distribuição"],
        ["feeder", "Alimentador"],
        ["backbone", "Backbone"],
        ["drop", "Drop"],
    ];
    const JUNCTION_ACTIONS = [
        ["connect", "Conectar na ponta"],
        ["cut", "Cortar e criar segmentos"],
        ["pass", "Passar sem cortar"],
        ["branch", "Criar derivação"],
        ["ignore", "Ignorar relação"],
    ];

    const state = {
        step: 1,
        file: null,
        analysis: null,
        topologyJunctions: [],
        topologySummary: null,
        topologyCalculated: false,
        previewLayer: null,
        returnStep: 6,
        cleanup: null,
        batches: [],
        completedImport: null,
        decisions: freshDecisions(),
    };

    function freshDecisions() {
        return {
            line_groups: {},
            line_items: {},
            point_groups: {},
            point_items: {},
            routes: [],
            topology: { proximity_m: 30, endpoint_tolerance_m: 40 },
            topology_defaults: {
                cto: "cut",
                splice_box: "cut",
                pop: "connect",
                dio: "connect",
                olt: "connect",
                other: "pass",
            },
            junctions: {},
            naming: { project_prefix: "", preserve_source_names: true },
            reserve_max_distance_m: 150,
            preview_token: "",
        };
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function formatMeters(value) {
        return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(Number(value || 0));
    }

    function formatBytes(value) {
        const bytes = Number(value || 0);
        if (!bytes) return "0 KB";
        if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
    }

    function numberControl({ label, attributes, value, min = 0, max = "", step = 1, suffix = "" }) {
        const safeMax = max === "" ? "" : ` max="${escapeHtml(max)}"`;
        return `<label class="kmz-number-field"><span>${escapeHtml(label)}</span>
            <span class="kmz-number-control">
                <button type="button" data-number-step="-1" aria-label="Diminuir ${escapeHtml(label)}">−</button>
                <input ${attributes} type="number" inputmode="decimal" min="${escapeHtml(min)}"${safeMax} step="${escapeHtml(step)}" value="${escapeHtml(value)}">
                <button type="button" data-number-step="1" aria-label="Aumentar ${escapeHtml(label)}">+</button>
            </span>${suffix ? `<small>${escapeHtml(suffix)}</small>` : ""}</label>`;
    }

    function applyPointTypeDefaults(rule, type) {
        rule.type = type;
        if (type === "cto" && !rule.capacity) rule.capacity = 16;
        if (type === "technical_reserve" && !rule.length_m) rule.length_m = 20;
        if (type === "dio" && !rule.port_capacity) rule.port_capacity = 24;
        if (type === "splice_box" && !rule.subtype) rule.subtype = "ceo";
        return rule;
    }

    function normalizedPointRule(rule) {
        const normalized = { ...(rule || {}) };
        return applyPointTypeDefaults(normalized, normalized.type || "review");
    }

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }

    function projectId() {
        return document.getElementById("project-select")?.value || "";
    }

    function selectedProject() {
        const select = document.getElementById("project-select");
        return select?.selectedOptions?.[0] || null;
    }

    function setStatus(message, isError = false) {
        status.textContent = message || "";
        status.classList.toggle("error", isError);
    }

    function optionList(options, selected) {
        return options.map(([value, label]) => (
            `<option value="${escapeHtml(value)}" ${String(selected) === String(value) ? "selected" : ""}>${escapeHtml(label)}</option>`
        )).join("");
    }

    function invalidatePreview() {
        state.decisions.preview_token = "";
        clearPreview();
    }

    function invalidateTopology() {
        state.topologyCalculated = false;
        state.topologyJunctions = [];
        state.topologySummary = null;
        state.decisions.junctions = {};
        invalidatePreview();
    }

    function clearPreview() {
        if (state.previewLayer && window.networkMap?.map) {
            window.networkMap.map.removeLayer(state.previewLayer);
        }
        state.previewLayer = null;
        returnButton.hidden = true;
    }

    function lineGroupRule(groupKey) {
        return state.decisions.line_groups[groupKey] || {};
    }

    function effectiveLineRule(line) {
        return {
            ...lineGroupRule(line.group_key),
            ...(state.decisions.line_items[line.source_id] || {}),
        };
    }

    function pointGroupRule(groupKey) {
        return state.decisions.point_groups[groupKey] || {};
    }

    function effectivePointRule(point) {
        return normalizedPointRule({
            ...pointGroupRule(point.group_key),
            ...(state.decisions.point_items[point.source_id] || {}),
        });
    }

    function firstPendingStep() {
        if (!state.analysis) return 1;
        const linePending = state.analysis.lines.some((line) => {
            const rule = effectiveLineRule(line);
            return ["review", "", "unknown", "pending"].includes(rule.action || "review")
                || (rule.action === "cable" && !rule.fiber_count);
        });
        if (linePending) return 2;
        const pointPending = state.analysis.points.some((point) => {
            const rule = effectivePointRule(point);
            return ["review", "", "unknown", "pending"].includes(rule.type || "review")
                || (rule.type === "cto" && !rule.capacity)
                || (rule.type === "technical_reserve" && !(rule.length_m || point.length_hint_m))
                || (rule.type === "dio" && !rule.port_capacity);
        });
        return pointPending ? 3 : 5;
    }

    function goToPending() {
        const target = firstPendingStep();
        setStep(target);
        setStatus("Revise os campos destacados. As regras do grupo valem para todos os itens, salvo exceções individuais.", true);
        content.scrollTo({ top: 0, behavior: "smooth" });
    }

    function unresolvedItems() {
        if (!state.analysis) return ["Analise um arquivo."];
        const errors = [];
        state.analysis.lines.forEach((line) => {
            const rule = effectiveLineRule(line);
            const action = rule.action || "review";
            if (["review", "", "unknown", "pending"].includes(action)) {
                errors.push(`Linha: ${line.name}`);
            } else if (action === "cable" && !rule.fiber_count) {
                errors.push(`Fibras do cabo: ${line.name}`);
            }
        });
        state.analysis.points.forEach((point) => {
            const rule = effectivePointRule(point);
            const type = rule.type || "review";
            if (["review", "", "unknown", "pending"].includes(type)) {
                errors.push(`Ponto: ${point.name}`);
            } else if (type === "cto" && !rule.capacity) {
                errors.push(`Portas da CTO: ${point.name}`);
            } else if (type === "technical_reserve" && !(rule.length_m || point.length_hint_m)) {
                errors.push(`Metragem da RT: ${point.name}`);
            } else if (type === "dio" && !rule.port_capacity) {
                errors.push(`Portas do DIO: ${point.name}`);
            }
        });
        return errors;
    }

    function resetAfterAnalysis(analysis) {
        state.analysis = analysis;
        state.topologyJunctions = [];
        state.topologySummary = null;
        state.topologyCalculated = false;
        state.completedImport = null;
        state.decisions = freshDecisions();
        const prefix = selectedProject()?.textContent?.trim().split("·")[0]?.trim() || "PROJ";
        state.decisions.naming.project_prefix = prefix;

        analysis.line_groups.forEach((group) => {
            state.decisions.line_groups[group.key] = {
                action: group.default_action,
                fiber_count: group.suggested_fibers || "",
                cable_type: group.suggested_cable_type || "distribution",
                length_m: group.suggested_reserve_length_m || "",
                cable_model_id: "",
            };
        });
        analysis.point_groups.forEach((group) => {
            const explicitConfirmation = group.key === "numeric_name" || group.suggested_type === "unknown";
            const type = explicitConfirmation ? "review" : (group.suggested_type || "review");
            state.decisions.point_groups[group.key] = applyPointTypeDefaults({
                type,
                capacity: type === "cto" ? 16 : "",
                length_m: type === "technical_reserve" ? (group.length_hint_m || 20) : "",
                subtype: group.subtype_hint || (group.key.includes("cdo") ? "cdo" : "ceo"),
                port_capacity: type === "dio" ? 24 : "",
            }, type);
        });
        state.decisions.routes = analysis.folders.filter((folder) => folder.route_candidate).map((folder) => folder.path);
    }

    async function apiPost(path, includeFile = true) {
        const formData = new FormData();
        if (includeFile) formData.append("file", state.file);
        formData.append("decisions", JSON.stringify(state.decisions));
        const response = await fetch(path, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" },
            body: formData,
        });
        const data = await response.json().catch(() => ({ error: "Resposta inválida." }));
        if (!response.ok) {
            const detail = data.errors?.join("\n") || data.error || data.detail || `HTTP ${response.status}`;
            throw new Error(detail);
        }
        return data;
    }

    async function analyze() {
        if (!state.file) throw new Error("Selecione um arquivo KML/KMZ.");
        if (!projectId()) throw new Error("Selecione um projeto antes de importar.");
        setStatus(`Analisando ${state.file.name}...`);
        const formData = new FormData();
        formData.append("file", state.file);
        const response = await fetch(`/api/map/projects/${projectId()}/import/analyze/`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" },
            body: formData,
        });
        const data = await response.json().catch(() => ({ error: "Resposta inválida." }));
        if (!response.ok) throw new Error(data.error || data.detail || `HTTP ${response.status}`);
        resetAfterAnalysis(data.analysis);
        setStatus(`Análise concluída: ${data.analysis.summary.points} pontos e ${data.analysis.summary.lines} linhas.`);
        setStep(2);
    }

    function setStep(step) {
        state.step = Math.max(1, Math.min(7, Number(step) || 1));
        document.querySelectorAll(".kmz-steps button").forEach((button) => {
            button.classList.toggle("active", Number(button.dataset.step) === state.step);
        });
        backButton.hidden = state.step === 1;
        nextButton.hidden = state.step === 7;
        executeButton.hidden = state.step !== 7;
        render();
    }

    function summaryCards() {
        const summary = state.analysis?.summary;
        if (!summary) return "";
        return `<div class="kmz-summary-grid">
            <article><strong>${summary.placemarks}</strong><span>objetos</span></article>
            <article><strong>${summary.points}</strong><span>pontos</span></article>
            <article><strong>${summary.lines}</strong><span>linhas</span></article>
            <article><strong>${formatMeters(summary.total_line_length_m)} m</strong><span>metragem</span></article>
        </div>`;
    }

    function step1() {
        const fileName = state.file?.name || "Nenhum arquivo selecionado";
        const fileMeta = state.file ? `${formatBytes(state.file.size)} · KML/KMZ pronto para análise` : "Arraste o arquivo aqui ou use o botão abaixo";
        return `<h3>Arquivo de origem</h3>
            <p>O arquivo é analisado sem gravar. A importação definitiva só será liberada depois da prévia topológica.</p>
            <div class="kmz-file-drop ${state.file ? "has-file" : ""}" data-kmz-dropzone>
                <input id="kmz-file" type="file" accept=".kml,.kmz,application/vnd.google-earth.kml+xml,application/vnd.google-earth.kmz" hidden>
                <div class="kmz-file-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24"><path d="M12 16V4m0 0-4 4m4-4 4 4"></path><path d="M4 14v5h16v-5"></path></svg>
                </div>
                <div class="kmz-file-copy">
                    <strong>${escapeHtml(fileName)}</strong>
                    <span>${escapeHtml(fileMeta)}</span>
                </div>
                <div class="kmz-file-actions">
                    <button id="kmz-choose-file" class="secondary-button" type="button">${state.file ? "Trocar arquivo" : "Selecionar arquivo"}</button>
                    <button id="kmz-analyze" class="primary-button" type="button" ${state.file ? "" : "disabled"}>Analisar arquivo</button>
                </div>
            </div>
            ${state.analysis ? summaryCards() : ""}
            <div class="kmz-management">
                <button id="kmz-load-batches" class="secondary-button" type="button">Ver histórico de importações</button>
                <button id="kmz-check-cleanup" class="danger-button" type="button">Limpar teste antigo</button>
            </div>
            ${cleanupHtml()}
            ${state.batches.length ? batchesHtml() : ""}`;
    }

    function cableModelOptions(rule) {
        const models = state.analysis.cable_models || [];
        const compatible = models.filter((model) => String(model.fiber_count) === String(rule.fiber_count));
        return `<option value="">Automático pela quantidade</option>${compatible.map((model) => (
            `<option value="${model.id}" ${String(rule.cable_model_id) === String(model.id) ? "selected" : ""}>${escapeHtml(`${model.manufacturer || ""} ${model.model || model.name}`.trim())}</option>`
        )).join("")}`;
    }

    function lineFields(rule, key, scope) {
        const prefix = scope === "item" ? "data-line-item" : "data-line-group";
        const cableFields = () => `<label>Tipo<select ${prefix}-cable-type="${escapeHtml(key)}">${optionList(CABLE_TYPES, rule.cable_type)}</select></label>
                <label>Fibras<select ${prefix}-fibers="${escapeHtml(key)}"><option value="">Definir</option>${state.analysis.supported_fiber_counts.map((count) => `<option value="${count}" ${String(rule.fiber_count) === String(count) ? "selected" : ""}>${count} fibra${count === 1 ? "" : "s"}</option>`).join("")}</select></label>
                <label>Modelo<select ${prefix}-model="${escapeHtml(key)}">${cableModelOptions(rule)}</select></label>`;
        const reserveField = () => numberControl({
            label: "Metragem da reserva",
            attributes: `${prefix}-length="${escapeHtml(key)}"`,
            value: rule.length_m || 20,
            min: 0.1,
            step: 0.1,
            suffix: "m",
        });
        // Nas exceções individuais (tabela), os campos ficam agrupados numa
        // célula só. No card do grupo ("group"), retornam soltos — viram
        // colunas do grid de 4 colunas de `.kmz-rule-controls`, com
        // placeholders pra manter a mesma altura entre cards de ações
        // diferentes (ver B2 no handoff v0.7).
        if (scope === "item") {
            if (rule.action === "cable") return `<div class="kmz-inline-fields">${cableFields()}</div>`;
            if (rule.action === "reserve_line") return reserveField();
            return '<span class="kmz-muted">Sem dados adicionais</span>';
        }
        if (rule.action === "cable") return cableFields();
        if (rule.action === "reserve_line") {
            return `<span class="kmz-field-empty" aria-hidden="true"></span>${reserveField()}<span class="kmz-field-empty" aria-hidden="true"></span>`;
        }
        return '<span class="kmz-field-empty" aria-hidden="true"></span><span class="kmz-muted kmz-field-empty">Sem dados adicionais</span><span class="kmz-field-empty" aria-hidden="true"></span>';
    }

    function lineItemRows(group) {
        return state.analysis.lines.filter((line) => line.group_key === group.key).map((line) => {
            const override = state.decisions.line_items[line.source_id];
            const rule = effectiveLineRule(line);
            return `<tr class="${(rule.action || "review") === "review" ? "kmz-review" : ""}">
                <td>${escapeHtml(line.name)}<div class="kmz-samples">${escapeHtml(line.folder || "Sem pasta")} · ${formatMeters(line.length_m)} m</div></td>
                <td><select data-line-item-action="${escapeHtml(line.source_id)}">
                    <option value="inherit" ${override ? "" : "selected"}>Usar regra do grupo</option>
                    ${optionList(LINE_ACTIONS, override?.action)}
                </select></td>
                <td>${override ? lineFields(rule, line.source_id, "item") : '<span class="kmz-muted">Herdando grupo</span>'}</td>
            </tr>`;
        }).join("");
    }

    function step2() {
        const cards = state.analysis.line_groups.map((group) => {
            const rule = lineGroupRule(group.key);
            const label = group.profile === "drop" ? "DROP detectado" : (group.profile === "reserve" ? "Reserva desenhada" : "Cabo comum");
            return `<article class="kmz-rule-card ${rule.action === "review" ? "kmz-review" : ""}">
                <header class="kmz-rule-card-header">
                    <div><span class="kmz-color-chip" style="--kmz-color:${group.hex || "#64748b"}"></span><strong>${escapeHtml(group.hex || "Sem cor")}</strong><span class="kmz-card-subtitle">${escapeHtml(label)}</span></div>
                    <span class="kmz-count-pill">${group.count} trecho${group.count === 1 ? "" : "s"}</span>
                </header>
                <div class="kmz-card-metrics"><span><strong>${formatMeters(group.total_length_m)} m</strong> de cabo</span><span class="kmz-clamp-1" title="${escapeHtml(group.folders.join(" · ") || "Sem pasta")}">${escapeHtml(group.folders.join(" · ") || "Sem pasta")}</span></div>
                <div class="kmz-card-samples kmz-clamp-2" title="${escapeHtml(group.samples.join(", "))}">${escapeHtml(group.samples.join(", "))}</div>
                <div class="kmz-rule-controls">
                    <label>Ação<select data-line-group-action="${escapeHtml(group.key)}">${optionList(LINE_ACTIONS, rule.action)}</select></label>
                    ${lineFields(rule, group.key, "group")}
                </div>
                <details class="kmz-details"><summary>Exceções individuais (${group.count})</summary><div class="kmz-subtable"><table><thead><tr><th>Trecho</th><th>Regra</th><th>Dados</th></tr></thead><tbody>${lineItemRows(group)}</tbody></table></div></details>
            </article>`;
        }).join("");
        return `${summaryCards()}<div class="kmz-section-heading"><div><h3>Cabos, DROP e reservas desenhadas</h3><p>As decisões abaixo são aplicadas ao grupo inteiro. Abra “Exceções individuais” apenas para alterar um trecho específico.</p></div><button id="kmz-raw-preview" class="secondary-button" type="button">Ver arquivo bruto no mapa</button></div>
            <div class="kmz-rule-list">${cards}</div>`;
    }

    function pointExtra(rule, key, scope) {
        const prefix = scope === "item" ? "data-point-item" : "data-point-group";
        if (rule.type === "cto") {
            return numberControl({
                label: "Portas da CTO",
                attributes: `${prefix}-capacity="${escapeHtml(key)}"`,
                value: rule.capacity || 16,
                min: 1,
                max: 128,
                step: 1,
            });
        }
        if (rule.type === "technical_reserve") {
            return numberControl({
                label: "Metragem da RT",
                attributes: `${prefix}-length="${escapeHtml(key)}"`,
                value: rule.length_m || 20,
                min: 0.1,
                step: 0.1,
                suffix: "m",
            });
        }
        if (rule.type === "splice_box") {
            return `<label>Subtipo <select ${prefix}-subtype="${escapeHtml(key)}"><option value="ceo" ${rule.subtype === "ceo" ? "selected" : ""}>CEO</option><option value="cdo" ${rule.subtype === "cdo" ? "selected" : ""}>CDO</option><option value="generic" ${rule.subtype === "generic" ? "selected" : ""}>Genérica</option></select></label>`;
        }
        if (rule.type === "dio") {
            return numberControl({
                label: "Portas do DIO",
                attributes: `${prefix}-ports="${escapeHtml(key)}"`,
                value: rule.port_capacity || 24,
                min: 1,
                max: 576,
                step: 1,
            });
        }
        return '<span class="kmz-muted">Sem dado obrigatório</span>';
    }

    function pointItemRows(group) {
        return state.analysis.points.filter((point) => point.group_key === group.key).map((point) => {
            const override = state.decisions.point_items[point.source_id];
            const rule = effectivePointRule(point);
            return `<tr class="${(rule.type || "review") === "review" ? "kmz-review" : ""}">
                <td>${escapeHtml(point.name)}<div class="kmz-samples">${escapeHtml(point.folder || "Sem pasta")}</div></td>
                <td><select data-point-item-type="${escapeHtml(point.source_id)}"><option value="inherit" ${override ? "" : "selected"}>Usar regra do grupo</option>${optionList(POINT_TYPES, override?.type)}</select></td>
                <td>${override ? pointExtra(rule, point.source_id, "item") : '<span class="kmz-muted">Herdando grupo</span>'}</td>
            </tr>`;
        }).join("");
    }

    function step3() {
        const cards = state.analysis.point_groups.map((group) => {
            const rule = normalizedPointRule(pointGroupRule(group.key));
            const resolvedByGroup = state.analysis.points.filter((point) => point.group_key === group.key && !state.decisions.point_items[point.source_id]).length;
            return `<article class="kmz-rule-card ${rule.type === "review" ? "kmz-review" : ""}">
                <header class="kmz-rule-card-header">
                    <div><strong>${escapeHtml(group.key)}</strong><span class="kmz-card-subtitle">confiança ${Math.round((group.confidence || 0) * 100)}%</span></div>
                    <span class="kmz-count-pill">${group.count} ponto${group.count === 1 ? "" : "s"}</span>
                </header>
                <div class="kmz-card-samples">${escapeHtml(group.samples.join(", "))}</div>
                <div class="kmz-rule-controls">
                    <label>Tipo<select data-point-group-type="${escapeHtml(group.key)}">${optionList(POINT_TYPES, rule.type)}</select></label>
                    <div class="kmz-rule-data">${pointExtra(rule, group.key, "group")}</div>
                </div>
                <div class="kmz-group-application"><strong>Regra do grupo:</strong> aplicada automaticamente a ${resolvedByGroup} item(ns). As exceções abaixo substituem somente os pontos editados.</div>
                <details class="kmz-details"><summary>Exceções individuais (${group.count})</summary><div class="kmz-subtable"><table><thead><tr><th>Ponto</th><th>Regra</th><th>Dados</th></tr></thead><tbody>${pointItemRows(group)}</tbody></table></div></details>
            </article>`;
        }).join("");
        return `<div class="kmz-section-heading"><div><h3>Classificação dos pontos</h3><p>Escolha o tipo uma vez por grupo. CTO usa a capacidade informada para todos os pontos do grupo; RT usa a metragem; DIO usa a quantidade de portas.</p></div><button id="kmz-raw-preview" class="secondary-button" type="button">Ver pontos e linhas no mapa</button></div>
            <div class="kmz-rule-list">${cards}</div>`;
    }

    function step4() {
        const rows = state.analysis.folders.filter((folder) => folder.route_candidate).map((folder) => (
            `<tr><td>${escapeHtml(folder.path)}</td><td>${folder.points}</td><td>${folder.lines}</td><td>${Object.entries(folder.composition || {}).map(([name, count]) => `<span class="kmz-badge">${escapeHtml(name)} ${count}</span>`).join("")}</td><td><input class="kmz-checkbox" data-route="${escapeHtml(folder.path)}" type="checkbox" ${state.decisions.routes.includes(folder.path) ? "checked" : ""}></td></tr>`
        )).join("");
        const naming = state.decisions.naming;
        return `<h3>Rotas e nomenclatura</h3>
            <p>A raiz, CABOS e POP não viram rota. Somente pastas com “ROTA” são candidatas. Cabos fora da pasta da rota recebem a rota pela maioria das CTOs/caixas próximas.</p>
            <div class="kmz-bulk-actions">
                <button type="button" class="secondary-button" id="kmz-routes-select-all">Marcar todas</button>
                <button type="button" class="secondary-button" id="kmz-routes-select-none">Desmarcar todas</button>
                <button type="button" class="secondary-button" id="kmz-routes-select-with-lines">Marcar somente rotas com linhas</button>
            </div>
            <div class="kmz-table-wrap"><table class="kmz-table"><thead><tr><th>Rota</th><th>Pontos</th><th>Linhas</th><th>Composição</th><th>Criar</th></tr></thead><tbody>${rows || '<tr><td colspan="5">Nenhuma pasta ROTA detectada.</td></tr>'}</tbody></table></div>
            <div class="kmz-settings-grid">
                <label>Prefixo do projeto <input id="kmz-project-prefix" maxlength="24" value="${escapeHtml(naming.project_prefix)}" placeholder="Ex.: JDS"></label>
                <label class="kmz-check-field"><input id="kmz-preserve-names" type="checkbox" ${naming.preserve_source_names ? "checked" : ""}><span>Manter nome original dos equipamentos</span></label>
                ${numberControl({ label: "Distância máxima da RT ao cabo", attributes: 'id="kmz-reserve-distance"', value: state.decisions.reserve_max_distance_m, min: 1, max: 500, step: 1, suffix: "m" })}
            </div>
            <div class="kmz-code-example"><strong>Padrão:</strong> CAB-JDS-ROTA-05-001 · DROP-JDS-ROTA-05-001 · CTO-JDS-ROTA-05-001 · CEO/CDO-JDS-ROTA-05-001. O nome e a pasta originais ficam no lote.</div>`;
    }

    async function detectTopology() {
        const pending = unresolvedItems();
        if (pending.length) throw new Error(`Resolva antes de calcular as ligações:\n${pending.slice(0, 15).join("\n")}${pending.length > 15 ? `\n... e mais ${pending.length - 15}` : ""}`);
        setStatus("Calculando proximidade entre cabos, CTOs e caixas...");
        const data = await apiPost(`/api/map/projects/${projectId()}/import/topology/`);
        state.topologyJunctions = data.junctions;
        state.topologySummary = data.summary;
        state.topologyCalculated = true;
        data.junctions.forEach((junction) => {
            if (!state.decisions.junctions[junction.junction_id]) {
                state.decisions.junctions[junction.junction_id] = { action: junction.action };
            }
        });
        invalidatePreview();
        setStatus(`${data.junctions.length} relações entre cabos e equipamentos detectadas.`);
        render();
    }

    function step5() {
        const topology = state.decisions.topology;
        const defaults = state.decisions.topology_defaults;
        const rows = state.topologyJunctions.map((junction) => {
            const selected = state.decisions.junctions[junction.junction_id]?.action || junction.action;
            return `<tr>
                <td>${escapeHtml(junction.line_name)}</td>
                <td>${escapeHtml(junction.point_name)}<div class="kmz-samples">${escapeHtml(junction.point_type)}</div></td>
                <td>${formatMeters(junction.distance_m)} m</td>
                <td>${junction.is_endpoint ? '<span class="kmz-badge success">Ponta</span>' : '<span class="kmz-badge">Meio</span>'}</td>
                <td><select data-junction="${escapeHtml(junction.junction_id)}">${optionList(JUNCTION_ACTIONS, selected)}</select></td>
            </tr>`;
        }).join("");
        return `<h3>Ligações e cortes automáticos</h3>
            <p>O sistema projeta cada CTO/CEO/CDO sobre o cabo próximo. Você decide se conecta, corta, apenas passa ou cria uma derivação. Cortes e derivações geram novos segmentos com origem/destino.</p>
            <div class="kmz-settings-grid kmz-topology-settings">
                ${numberControl({ label: "Proximidade máxima", attributes: 'id="kmz-topology-distance"', value: topology.proximity_m, min: 1, max: 100, step: 1, suffix: "m" })}
                ${numberControl({ label: "Tolerância de ponta", attributes: 'id="kmz-endpoint-distance"', value: topology.endpoint_tolerance_m, min: 1, max: 100, step: 1, suffix: "m" })}
                <label>CTO no meio <select id="kmz-default-cto">${optionList(JUNCTION_ACTIONS, defaults.cto)}</select></label>
                <label>CEO/CDO no meio <select id="kmz-default-splice">${optionList(JUNCTION_ACTIONS, defaults.splice_box)}</select></label>
            </div>
            <button id="kmz-detect-topology" class="primary-button" type="button">${state.topologyJunctions.length ? "Recalcular ligações" : "Detectar ligações"}</button>
            ${state.topologySummary ? `<div class="kmz-summary-grid compact"><article><strong>${state.topologySummary.junctions}</strong><span>relações</span></article><article><strong>${state.topologySummary.cuts}</strong><span>cortes</span></article><article><strong>${state.topologySummary.branches}</strong><span>derivações</span></article><article><strong>${state.topologySummary.passes}</strong><span>passagens</span></article></div>` : ""}
            ${state.topologyCalculated && rows ? `<div class="kmz-bulk-actions kmz-junction-bulk">
                <strong>Aplicar para todos</strong>
                <label>CTO no meio <select id="kmz-bulk-cto">${optionList(JUNCTION_ACTIONS, defaults.cto)}</select></label>
                <label>CEO/CDO no meio <select id="kmz-bulk-splice">${optionList(JUNCTION_ACTIONS, defaults.splice_box)}</select></label>
                <button type="button" class="secondary-button" id="kmz-apply-all-junctions">Aplicar a todos</button>
            </div>` : ""}
            ${state.topologyCalculated ? (rows ? `<div class="kmz-table-wrap kmz-junction-table"><table class="kmz-table"><thead><tr><th>Cabo original</th><th>Equipamento</th><th>Distância</th><th>Posição</th><th>Ação</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="kmz-success">Nenhuma relação por proximidade foi encontrada; a topologia pode seguir sem cortes.</div>') : '<div class="kmz-warning">Calcule as ligações para revisar os cortes.</div>'}`;
    }


    function rawPreviewGeojson() {
        const features = [];
        state.analysis.lines.forEach((line) => {
            const rule = effectiveLineRule(line);
            const pending = !rule.action || rule.action === "review";
            features.push({
                type: "Feature",
                geometry: { type: "LineString", coordinates: line.coordinates },
                properties: {
                    kind: "raw_line",
                    name: line.name,
                    folder: line.folder,
                    action: rule.action || "review",
                    fiber_count: rule.fiber_count || null,
                    cable_type: rule.cable_type || null,
                    color: pending ? "#facc15" : (line.color?.hex || "#64748b"),
                },
            });
        });
        const pointColors = { cto: "#0ea5e9", splice_box: "#a855f7", technical_reserve: "#f59e0b", pop: "#22c55e", dio: "#14b8a6", pole: "#64748b", other: "#94a3b8", ignore: "#475569" };
        state.analysis.points.forEach((point) => {
            const rule = effectivePointRule(point);
            const pending = !rule.type || rule.type === "review";
            features.push({
                type: "Feature",
                geometry: { type: "Point", coordinates: point.coordinates },
                properties: {
                    kind: "raw_point",
                    name: point.name,
                    folder: point.folder,
                    target_type: rule.type || "review",
                    color: pending ? "#facc15" : (pointColors[rule.type] || "#94a3b8"),
                },
            });
        });
        return { type: "FeatureCollection", features };
    }

    function openRawPreview() {
        state.returnStep = state.step;
        drawPreview(rawPreviewGeojson());
        setStatus("Prévia bruta aberta. Itens amarelos ainda estão em Revisar.");
    }

    function previewPopup(properties) {
        if (properties.kind === "cable_segment") {
            return `<strong>${escapeHtml(properties.proposed_code)}</strong><br>${escapeHtml(properties.source_name)}<br>${properties.fiber_count} fibra(s) · ${escapeHtml(properties.cable_type)}<br>${escapeHtml(properties.origin || "Sem origem")} → ${escapeHtml(properties.destination || "Sem destino")}<br>${formatMeters(properties.length_m)} m`;
        }
        if (properties.kind === "junction") {
            return `<strong>${escapeHtml(properties.name)}</strong><br>Cabo: ${escapeHtml(properties.line_name)}<br>Ação: ${escapeHtml(properties.action)}<br>Distância: ${formatMeters(properties.distance_m)} m`;
        }
        if (properties.kind === "raw_line") {
            return `<strong>${escapeHtml(properties.name)}</strong><br>${escapeHtml(properties.folder || "Sem pasta")}<br>Ação: ${escapeHtml(properties.action)}${properties.fiber_count ? `<br>${properties.fiber_count} fibra(s) · ${escapeHtml(properties.cable_type || "")}` : ""}`;
        }
        if (properties.kind === "raw_point") {
            return `<strong>${escapeHtml(properties.name)}</strong><br>${escapeHtml(properties.folder || "Sem pasta")}<br>Tipo: ${escapeHtml(properties.target_type)}`;
        }
        return `<strong>${escapeHtml(properties.name)}</strong><br>${escapeHtml(properties.target_type)}<br>${escapeHtml(properties.route || "Sem rota")}`;
    }

    function drawPreview(geojson) {
        clearPreview();
        const map = window.networkMap?.map;
        if (!window.L || !map) throw new Error("A prévia não conseguiu acessar o mapa. Confirme window.networkMap = { map, loadStructure } no final de map-editor.js.");
        dialog.close();
        returnButton.hidden = false;
        map.invalidateSize();
        state.previewLayer = L.geoJSON(geojson, {
            style(feature) {
                return { color: feature.properties.color || "#22d3ee", weight: 4, opacity: 0.9, dashArray: feature.properties.kind === "junction" ? "4 4" : null };
            },
            pointToLayer(feature, latlng) {
                const isJunction = feature.properties.kind === "junction";
                return L.circleMarker(latlng, {
                    radius: isJunction ? 7 : 6,
                    color: "#ffffff",
                    weight: 1.5,
                    fillColor: feature.properties.color || "#f59e0b",
                    fillOpacity: 0.95,
                });
            },
            onEachFeature(feature, layer) {
                layer.bindPopup(previewPopup(feature.properties || {}));
            },
        }).addTo(map);
        window.setTimeout(() => {
            map.invalidateSize();
            try { map.fitBounds(state.previewLayer.getBounds(), { padding: [35, 35], maxZoom: 19 }); } catch (_error) { /* bounds inválidos */ }
        }, 80);
    }

    async function generatePreview() {
        const pending = unresolvedItems();
        if (pending.length) {
            goToPending();
            throw new Error(`Existem ${pending.length} itens pendentes. A tela foi aberta no primeiro grupo que precisa de ajuste.`);
        }
        if (!state.topologyCalculated) throw new Error("Calcule as ligações antes da prévia final.");
        setStatus("Gerando a prévia topológica sem gravar...");
        const data = await apiPost(`/api/map/projects/${projectId()}/import/preview/`);
        state.decisions.preview_token = data.preview_token;
        state.topologyJunctions = data.junctions;
        state.topologySummary = data.summary;
        setStatus("Prévia gerada. Clique nos cabos e caixas no mapa; depois volte ao assistente.");
        state.returnStep = 6;
        drawPreview(data.preview_geojson);
    }

    function step6() {
        const pending = unresolvedItems();
        const previewReady = Boolean(state.decisions.preview_token);
        return `<h3>Prévia topológica obrigatória</h3>
            ${pending.length ? `<div class="kmz-warning"><strong>${pending.length} pendências impedem a prévia.</strong><br>${pending.slice(0, 12).map(escapeHtml).join("<br>")}${pending.length > 12 ? `<br>... e mais ${pending.length - 12}` : ""}<br><button id="kmz-fix-pending" class="secondary-button" type="button">Ir para as pendências</button></div>` : '<div class="kmz-success">Classificações resolvidas.</div>'}
            ${!state.topologyCalculated ? '<div class="kmz-warning">Volte à etapa Ligações e execute a detecção.</div>' : ""}
            <button id="kmz-generate-preview" class="primary-button" type="button">Gerar e abrir prévia no mapa</button>
            ${previewReady ? '<div class="kmz-success">Prévia confirmada para as decisões atuais. Qualquer alteração invalida este token.</div>' : '<p>Nada será gravado nesta etapa. Caso exista alguma pendência, o botão levará você diretamente ao local que precisa de correção.</p>'}`;
    }

    async function loadBatches() {
        if (!projectId()) throw new Error("Selecione um projeto.");
        const response = await fetch(`/api/map/projects/${projectId()}/import/batches/`, { credentials: "same-origin", headers: { Accept: "application/json" } });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        state.batches = data.batches;
        render();
    }

    async function undoBatch(batchId) {
        if (!confirm(`Desfazer completamente o lote #${batchId}?`)) return;
        const response = await fetch(`/api/map/projects/${projectId()}/import/batches/${batchId}/undo/`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" },
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        if (window.networkMap?.loadStructure) await window.networkMap.loadStructure(true);
        await loadBatches();
        alert(`Lote #${batchId} desfeito.`);
    }

    async function repairBatchFibers(batchId) {
        if (!confirm(`Verificar e gerar tubos/fibras dos cabos do lote #${batchId}?\nCabos que já possuem fibras não serão alterados.`)) return;
        setStatus(`Reparando fibras do lote #${batchId}...`);
        const response = await fetch(`/api/map/projects/${projectId()}/import/batches/${batchId}/repair-fibers/`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" },
        });
        const data = await response.json().catch(() => ({ error: "Resposta inválida." }));
        if (!response.ok && response.status !== 207) throw new Error(data.error || `HTTP ${response.status}`);
        if (window.networkMap?.loadStructure) await window.networkMap.loadStructure(true);
        await loadBatches();
        const repair = data.repair || {};
        const message = [
            `Lote #${batchId} verificado.`,
            `${repair.cables_repaired || 0} cabo(s) reparado(s).`,
            `${repair.fibers_created || 0} fibra(s) criada(s).`,
            `${repair.already_ready || 0} cabo(s) já estavam prontos.`,
            ...(data.errors?.length ? ["Falhas:", ...data.errors.slice(0, 12)] : []),
        ].join("\n");
        setStatus(data.errors?.length ? `Reparo concluído com ${data.errors.length} aviso(s).` : "Tubos e fibras gerados com sucesso.", Boolean(data.errors?.length));
        alert(message);
    }

    async function checkLegacyCleanup() {
        const response = await fetch(`/api/map/projects/${projectId()}/import/cleanup-legacy/`, { credentials: "same-origin", headers: { Accept: "application/json" } });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        state.cleanup = data;
        render();
    }

    async function executeLegacyCleanup() {
        if (!state.cleanup) return;
        const typed = prompt(`Esta limpeza procura somente objetos dos importadores antigos.\nDigite exatamente: ${state.cleanup.confirmation}`);
        if (typed !== state.cleanup.confirmation) return;
        const response = await fetch(`/api/map/projects/${projectId()}/import/cleanup-legacy/`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ confirmation: typed, candidate_hash: state.cleanup.candidate_hash }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        state.cleanup = null;
        if (window.networkMap?.loadStructure) await window.networkMap.loadStructure(true);
        alert(`Limpeza concluída.\n${JSON.stringify(data.deleted, null, 2)}`);
        render();
    }

    function importSummaryHtml(summary) {
        const labels = {
            ctos: "CTOs", elements: "equipamentos", cables: "cabos", routes: "rotas",
            reserves: "reservas", fibers: "fibras", fiber_tubes: "tubos",
            cable_relations: "ligações", ignored_points: "pontos ignorados",
            cable_models_created: "modelos criados", cables_without_fibers: "cabos sem fibras",
        };
        const entries = Object.entries(summary || {}).filter(([, value]) => Number(value || 0) > 0);
        if (!entries.length) return '<span class="kmz-muted">Sem resumo</span>';
        return `<div class="kmz-summary-badges">${entries.map(([key, value]) => `<span class="kmz-badge ${key === "cables_without_fibers" ? "warning" : ""}"><strong>${escapeHtml(value)}</strong> ${escapeHtml(labels[key] || key.replaceAll("_", " "))}</span>`).join("")}</div>`;
    }

    function batchesHtml() {
        if (!state.batches.length) return '<p class="kmz-muted">Histórico ainda não carregado ou vazio.</p>';
        return `<div class="kmz-table-wrap"><table class="kmz-table"><thead><tr><th>Lote</th><th>Arquivo</th><th>Status</th><th>Resumo</th><th>Ação</th></tr></thead><tbody>${state.batches.map((batch) => `<tr><td>#${batch.id}<div class="kmz-samples">${escapeHtml(new Date(batch.created_at).toLocaleString("pt-BR"))}</div></td><td>${escapeHtml(batch.filename)}</td><td>${escapeHtml(batch.status_label)}</td><td>${importSummaryHtml(batch.summary)}</td><td>${batch.status === "imported" ? `<div class="kmz-batch-actions"><button class="secondary-button" data-repair-batch="${batch.id}" type="button">Gerar/reparar fibras</button><button class="danger-button" data-undo-batch="${batch.id}" type="button">Desfazer lote</button></div>` : "—"}</td></tr>`).join("")}</tbody></table></div>`;
    }

    function cleanupHtml() {
        if (!state.cleanup) return "";
        const total = Object.values(state.cleanup.candidates).reduce((sum, value) => sum + Number(value || 0), 0);
        return `<div class="kmz-warning"><strong>Objetos antigos candidatos à limpeza: ${total}</strong><br>${escapeHtml(JSON.stringify(state.cleanup.candidates))}<br><button id="kmz-run-cleanup" class="danger-button" type="button" ${total ? "" : "disabled"}>Executar limpeza segura</button></div>`;
    }

    function step7() {
        const pending = unresolvedItems();
        const ready = !pending.length && Boolean(state.decisions.preview_token);
        const completed = state.completedImport;
        return `<h3>Importação definitiva e histórico</h3>
            ${completed ? `<div class="kmz-success"><strong>Importação concluída no lote #${escapeHtml(completed.batch_id)}.</strong><br>${importSummaryHtml(completed.imported)}</div>` : (ready ? '<div class="kmz-success">Tudo pronto. A operação será atômica e registrada em um lote que pode ser desfeito.</div>' : `<div class="kmz-warning"><strong>Importação bloqueada.</strong><br>${pending.length ? `${pending.length} classificações pendentes.<br>` : ""}${state.decisions.preview_token ? "" : "Gere novamente a prévia final."}</div>`)}
            <div class="kmz-management"><button id="kmz-refresh-batches" class="secondary-button" type="button">Atualizar histórico</button><button id="kmz-check-cleanup-final" class="danger-button" type="button">Revisar limpeza do teste antigo</button></div>
            ${cleanupHtml()}
            ${batchesHtml()}`;
    }

    function render() {
        if (!state.analysis && state.step > 1) state.step = 1;
        const steps = [null, step1, step2, step3, step4, step5, step6, step7];
        content.innerHTML = steps[state.step]();
        executeButton.disabled = state.step === 7 && (Boolean(state.completedImport) || unresolvedItems().length > 0 || !state.decisions.preview_token);
        bindCurrentStep();
    }

    function setGroupLineValue(key, field, value) {
        state.decisions.line_groups[key][field] = value;
        invalidatePreview();
    }

    function ensureLineOverride(sourceId) {
        if (!state.decisions.line_items[sourceId]) {
            const line = state.analysis.lines.find((item) => item.source_id === sourceId);
            state.decisions.line_items[sourceId] = { ...lineGroupRule(line.group_key) };
        }
        return state.decisions.line_items[sourceId];
    }

    function ensurePointOverride(sourceId) {
        if (!state.decisions.point_items[sourceId]) {
            const point = state.analysis.points.find((item) => item.source_id === sourceId);
            state.decisions.point_items[sourceId] = { ...pointGroupRule(point.group_key) };
        }
        return state.decisions.point_items[sourceId];
    }

    function bindValue(selector, callback) {
        document.querySelectorAll(selector).forEach((element) => {
            element.addEventListener("change", () => callback(element));
        });
    }

    function bindNumberSteppers() {
        document.querySelectorAll(".kmz-number-control").forEach((control) => {
            const input = control.querySelector("input[type='number']");
            if (!input) return;
            control.querySelectorAll("[data-number-step]").forEach((button) => {
                button.addEventListener("click", () => {
                    const direction = Number(button.dataset.numberStep || 0);
                    const step = Number(input.step || 1);
                    const current = Number(input.value || input.min || 0);
                    const min = input.min === "" ? -Infinity : Number(input.min);
                    const max = input.max === "" ? Infinity : Number(input.max);
                    const precision = String(step).includes(".") ? String(step).split(".")[1].length : 0;
                    const next = Math.min(max, Math.max(min, current + direction * step));
                    input.value = next.toFixed(precision);
                    input.dispatchEvent(new Event("change", { bubbles: true }));
                });
            });
        });
    }

    function bindCurrentStep() {
        bindNumberSteppers();
        const fileInput = document.getElementById("kmz-file");
        const chooseFile = document.getElementById("kmz-choose-file");
        const dropzone = document.querySelector("[data-kmz-dropzone]");
        chooseFile?.addEventListener("click", () => fileInput?.click());
        fileInput?.addEventListener("change", (event) => {
            state.file = event.target.files[0] || null;
            state.analysis = null;
            state.decisions = freshDecisions();
            setStatus(state.file ? `${state.file.name} selecionado. Clique em Analisar arquivo.` : "");
            render();
        });
        ["dragenter", "dragover"].forEach((eventName) => dropzone?.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragging");
        }));
        ["dragleave", "drop"].forEach((eventName) => dropzone?.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragging");
        }));
        dropzone?.addEventListener("drop", (event) => {
            const file = event.dataTransfer?.files?.[0] || null;
            if (!file) return;
            const extension = file.name.toLowerCase().split(".").pop();
            if (!["kml", "kmz"].includes(extension)) {
                setStatus("Selecione um arquivo .kml ou .kmz.", true);
                return;
            }
            state.file = file;
            state.analysis = null;
            state.decisions = freshDecisions();
            setStatus(`${file.name} selecionado. Clique em Analisar arquivo.`);
            render();
        });
        document.getElementById("kmz-analyze")?.addEventListener("click", () => analyze().catch((error) => setStatus(error.message, true)));
        document.getElementById("kmz-raw-preview")?.addEventListener("click", () => {
            try { openRawPreview(); } catch (error) { setStatus(error.message, true); }
        });
        document.getElementById("kmz-load-batches")?.addEventListener("click", () => loadBatches().catch((error) => setStatus(error.message, true)));
        document.getElementById("kmz-check-cleanup")?.addEventListener("click", () => checkLegacyCleanup().catch((error) => setStatus(error.message, true)));

        bindValue("[data-line-group-action]", (element) => {
            state.decisions.line_groups[element.dataset.lineGroupAction].action = element.value;
            invalidateTopology();
            render();
        });
        bindValue("[data-line-group-cable-type]", (element) => setGroupLineValue(element.dataset.lineGroupCableType, "cable_type", element.value));
        bindValue("[data-line-group-fibers]", (element) => { setGroupLineValue(element.dataset.lineGroupFibers, "fiber_count", element.value); render(); });
        bindValue("[data-line-group-model]", (element) => setGroupLineValue(element.dataset.lineGroupModel, "cable_model_id", element.value));
        bindValue("[data-line-group-length]", (element) => setGroupLineValue(element.dataset.lineGroupLength, "length_m", element.value));

        bindValue("[data-line-item-action]", (element) => {
            const id = element.dataset.lineItemAction;
            if (element.value === "inherit") delete state.decisions.line_items[id];
            else ensureLineOverride(id).action = element.value;
            invalidateTopology();
            render();
        });
        bindValue("[data-line-item-cable-type]", (element) => { ensureLineOverride(element.dataset.lineItemCableType).cable_type = element.value; invalidatePreview(); });
        bindValue("[data-line-item-fibers]", (element) => { ensureLineOverride(element.dataset.lineItemFibers).fiber_count = element.value; invalidatePreview(); render(); });
        bindValue("[data-line-item-model]", (element) => { ensureLineOverride(element.dataset.lineItemModel).cable_model_id = element.value; invalidatePreview(); });
        bindValue("[data-line-item-length]", (element) => { ensureLineOverride(element.dataset.lineItemLength).length_m = element.value; invalidatePreview(); });

        bindValue("[data-point-group-type]", (element) => {
            const rule = state.decisions.point_groups[element.dataset.pointGroupType];
            applyPointTypeDefaults(rule, element.value);
            invalidateTopology();
            render();
        });
        bindValue("[data-point-group-capacity]", (element) => { state.decisions.point_groups[element.dataset.pointGroupCapacity].capacity = element.value; invalidatePreview(); });
        bindValue("[data-point-group-length]", (element) => { state.decisions.point_groups[element.dataset.pointGroupLength].length_m = element.value; invalidatePreview(); });
        bindValue("[data-point-group-subtype]", (element) => { state.decisions.point_groups[element.dataset.pointGroupSubtype].subtype = element.value; invalidatePreview(); });
        bindValue("[data-point-group-ports]", (element) => { state.decisions.point_groups[element.dataset.pointGroupPorts].port_capacity = element.value; invalidatePreview(); });

        bindValue("[data-point-item-type]", (element) => {
            const id = element.dataset.pointItemType;
            if (element.value === "inherit") delete state.decisions.point_items[id];
            else applyPointTypeDefaults(ensurePointOverride(id), element.value);
            invalidateTopology();
            render();
        });
        bindValue("[data-point-item-capacity]", (element) => { ensurePointOverride(element.dataset.pointItemCapacity).capacity = element.value; invalidatePreview(); });
        bindValue("[data-point-item-length]", (element) => { ensurePointOverride(element.dataset.pointItemLength).length_m = element.value; invalidatePreview(); });
        bindValue("[data-point-item-subtype]", (element) => { ensurePointOverride(element.dataset.pointItemSubtype).subtype = element.value; invalidatePreview(); });
        bindValue("[data-point-item-ports]", (element) => { ensurePointOverride(element.dataset.pointItemPorts).port_capacity = element.value; invalidatePreview(); });

        bindValue("[data-route]", (element) => {
            const path = element.dataset.route;
            state.decisions.routes = element.checked
                ? [...new Set([...state.decisions.routes, path])]
                : state.decisions.routes.filter((item) => item !== path);
            invalidatePreview();
        });
        const routeCandidates = () => (state.analysis?.folders || []).filter((folder) => folder.route_candidate);
        document.getElementById("kmz-routes-select-all")?.addEventListener("click", () => {
            state.decisions.routes = routeCandidates().map((folder) => folder.path);
            invalidatePreview();
            render();
        });
        document.getElementById("kmz-routes-select-none")?.addEventListener("click", () => {
            state.decisions.routes = [];
            invalidatePreview();
            render();
        });
        document.getElementById("kmz-routes-select-with-lines")?.addEventListener("click", () => {
            state.decisions.routes = routeCandidates().filter((folder) => folder.lines > 0).map((folder) => folder.path);
            invalidatePreview();
            render();
        });
        document.getElementById("kmz-project-prefix")?.addEventListener("change", (event) => { state.decisions.naming.project_prefix = event.target.value; invalidatePreview(); });
        document.getElementById("kmz-preserve-names")?.addEventListener("change", (event) => { state.decisions.naming.preserve_source_names = event.target.checked; invalidatePreview(); });
        document.getElementById("kmz-reserve-distance")?.addEventListener("change", (event) => { state.decisions.reserve_max_distance_m = event.target.value; invalidatePreview(); });

        document.getElementById("kmz-topology-distance")?.addEventListener("change", (event) => { state.decisions.topology.proximity_m = event.target.value; invalidateTopology(); render(); });
        document.getElementById("kmz-endpoint-distance")?.addEventListener("change", (event) => { state.decisions.topology.endpoint_tolerance_m = event.target.value; invalidateTopology(); render(); });
        document.getElementById("kmz-default-cto")?.addEventListener("change", (event) => { state.decisions.topology_defaults.cto = event.target.value; invalidateTopology(); render(); });
        document.getElementById("kmz-default-splice")?.addEventListener("change", (event) => { state.decisions.topology_defaults.splice_box = event.target.value; invalidateTopology(); render(); });
        document.getElementById("kmz-detect-topology")?.addEventListener("click", () => detectTopology().catch((error) => setStatus(error.message, true)));
        bindValue("[data-junction]", (element) => {
            state.decisions.junctions[element.dataset.junction] = { action: element.value };
            const row = state.topologyJunctions.find((item) => item.junction_id === element.dataset.junction);
            if (row) row.action = element.value;
            invalidatePreview();
        });
        document.getElementById("kmz-apply-all-junctions")?.addEventListener("click", () => {
            const ctoAction = document.getElementById("kmz-bulk-cto")?.value;
            const spliceAction = document.getElementById("kmz-bulk-splice")?.value;
            state.topologyJunctions.forEach((junction) => {
                const action = junction.point_type === "cto" ? ctoAction
                    : junction.point_type === "splice_box" ? spliceAction
                        : null;
                if (!action) return;
                state.decisions.junctions[junction.junction_id] = { action };
                junction.action = action;
            });
            invalidatePreview();
            setStatus("Regra global aplicada a todas as ligações detectadas.");
            render();
        });

        document.getElementById("kmz-fix-pending")?.addEventListener("click", goToPending);
        document.getElementById("kmz-generate-preview")?.addEventListener("click", () => generatePreview().catch((error) => {
            setStatus(error.message, true);
            content.scrollTo({ top: 0, behavior: "smooth" });
        }));
        document.getElementById("kmz-refresh-batches")?.addEventListener("click", () => loadBatches().catch((error) => setStatus(error.message, true)));
        document.getElementById("kmz-check-cleanup-final")?.addEventListener("click", () => checkLegacyCleanup().catch((error) => setStatus(error.message, true)));
        document.getElementById("kmz-run-cleanup")?.addEventListener("click", () => executeLegacyCleanup().catch((error) => setStatus(error.message, true)));
        document.querySelectorAll("[data-repair-batch]").forEach((button) => {
            button.addEventListener("click", () => repairBatchFibers(button.dataset.repairBatch).catch((error) => setStatus(error.message, true)));
        });
        document.querySelectorAll("[data-undo-batch]").forEach((button) => {
            button.addEventListener("click", () => undoBatch(button.dataset.undoBatch).catch((error) => setStatus(error.message, true)));
        });
    }

    async function executeImport() {
        const pending = unresolvedItems();
        if (pending.length) throw new Error(`Importação bloqueada por ${pending.length} pendências.`);
        if (!state.decisions.preview_token) throw new Error("Gere a prévia final antes de importar.");
        setStatus("Importando e criando o lote... Não feche esta tela.");
        const data = await apiPost(`/api/map/projects/${projectId()}/import/execute/`);
        clearPreview();
        if (window.networkMap?.loadStructure) await window.networkMap.loadStructure(true);
        state.completedImport = data;
        state.decisions.preview_token = "";
        await loadBatches();
        setStatus(`Importação concluída no lote #${data.batch_id}. Cabos e fibras foram recarregados no mapa.`);
        setStep(7);
        if (data.warnings?.length) {
            alert(`Importação concluída no lote #${data.batch_id}.\nAvisos:\n${data.warnings.join("\n")}`);
        }
    }

    openButton.onclick = () => {
        state.step = 1;
        state.file = null;
        state.analysis = null;
        state.topologyJunctions = [];
        state.topologyCalculated = false;
        state.cleanup = null;
        state.completedImport = null;
        state.decisions = freshDecisions();
        clearPreview();
        dialog.showModal();
        setStep(1);
    };
    dialog.querySelector(".dialog-close").onclick = () => {
        clearPreview();
        dialog.close();
    };
    document.getElementById("project-select")?.addEventListener("change", () => clearPreview());
    returnButton.onclick = () => {
        returnButton.hidden = true;
        dialog.showModal();
        setStep(state.returnStep || 6);
    };
    backButton.onclick = () => setStep(state.step - 1);
    nextButton.onclick = () => {
        if (state.step === 1 && !state.analysis) {
            setStatus("Analise um arquivo antes de continuar.", true);
            return;
        }
        if (state.step === 4 && unresolvedItems().length) {
            setStatus(`Ainda existem ${unresolvedItems().length} itens pendentes. Corrija os grupos antes de calcular as ligações.`, true);
            goToPending();
            return;
        }
        setStep(state.step + 1);
    };
    executeButton.onclick = () => executeImport().catch((error) => setStatus(error.message, true));
    document.querySelectorAll(".kmz-steps button").forEach((button) => {
        button.onclick = () => {
            const step = Number(button.dataset.step);
            if (step === 1 || state.analysis) setStep(step);
        };
    });

    render();
}());
