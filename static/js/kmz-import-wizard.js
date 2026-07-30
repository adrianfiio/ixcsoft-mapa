(function () {
    "use strict";

    const dialog = document.getElementById("kmz-import-dialog");
    const form = document.getElementById("kmz-import-form");
    const fileInput = document.getElementById("import-file");
    const openButton = document.getElementById("import-button");
    const closeButton = dialog?.querySelector(".dialog-close");
    const content = document.getElementById("kmz-import-content");
    const status = document.getElementById("kmz-import-status");

    if (!dialog || !form || !fileInput || !openButton || !content || !status) return;

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function meters(value) {
        return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(Number(value || 0));
    }

    function render(data) {
        const summary = data.summary;
        const colorRows = data.line_color_groups.map((group, index) => `
            <tr>
                <td><span class="kmz-color-chip" style="--kmz-color:${escapeHtml(group.hex || "#64748b")}"></span>${escapeHtml(group.hex || "Sem cor")}</td>
                <td>${group.count}</td>
                <td>${meters(group.total_length_m)} m</td>
                <td>
                    <select name="color_${index}_fiber_count">
                        <option value="">Perguntar / revisar</option>
                        ${data.supported_fiber_counts.map((count) => `<option value="${count}">${count} fibras</option>`).join("")}
                    </select>
                </td>
            </tr>`).join("");

        const folderRows = data.folders
            .filter((folder) => folder.lines || folder.points)
            .map((folder, index) => `
                <tr>
                    <td>${escapeHtml(folder.path)}</td>
                    <td>${folder.points}</td>
                    <td>${folder.lines}</td>
                    <td><input type="checkbox" name="route_${index}" ${folder.route_candidate ? "checked" : ""}></td>
                </tr>`).join("");

        const groupRows = data.point_groups.map((group, index) => `
            <tr>
                <td>${escapeHtml(group.key)}</td>
                <td>${group.count}</td>
                <td>${escapeHtml(group.samples.join(", "))}</td>
                <td>
                    <select name="point_group_${index}">
                        <option value="">Revisar</option>
                        <option value="cto" ${group.key === "alias_cto" || group.key === "numeric_name" ? "selected" : ""}>CTO</option>
                        <option value="splice_box" ${["alias_ceo", "alias_cdo", "alias_emenda"].includes(group.key) ? "selected" : ""}>Caixa de emenda</option>
                        <option value="technical_reserve" ${group.key === "alias_rt" ? "selected" : ""}>Reserva técnica</option>
                        <option value="pole">Poste</option>
                        <option value="pop">POP/CPD</option>
                        <option value="ignore">Ignorar</option>
                    </select>
                </td>
            </tr>`).join("");

        content.innerHTML = `
            <section class="kmz-summary-grid">
                <article><strong>${summary.placemarks}</strong><span>objetos</span></article>
                <article><strong>${summary.points}</strong><span>pontos</span></article>
                <article><strong>${summary.lines}</strong><span>linhas</span></article>
                <article><strong>${meters(summary.total_line_length_m)} m</strong><span>metragem calculada</span></article>
            </section>
            ${data.warnings.length ? `<div class="kmz-warning">${data.warnings.map(escapeHtml).join("<br>")}</div>` : ""}
            <details open><summary>1. Cores dos cabos</summary>
                <p>Defina a quantidade de fibras por cor. O backend já converte a cor KML AABBGGRR para hexadecimal web.</p>
                <div class="kmz-table-wrap"><table><thead><tr><th>Cor</th><th>Trechos</th><th>Metragem</th><th>Fibras</th></tr></thead><tbody>${colorRows}</tbody></table></div>
            </details>
            <details><summary>2. Pastas candidatas a rota</summary>
                <div class="kmz-table-wrap"><table><thead><tr><th>Pasta</th><th>Pontos</th><th>Linhas</th><th>Criar rota</th></tr></thead><tbody>${folderRows}</tbody></table></div>
            </details>
            <details><summary>3. Grupos de pontos</summary>
                <p>CDO e CEO são sugeridos como caixa de emenda. RT é sugerido como reserva técnica. Nomes numéricos são sugeridos como CTO com baixa confiança.</p>
                <div class="kmz-table-wrap"><table><thead><tr><th>Regra</th><th>Qtd.</th><th>Amostras</th><th>Importar como</th></tr></thead><tbody>${groupRows}</tbody></table></div>
            </details>
            <div class="kmz-next-note">
                Esta primeira entrega analisa e organiza as decisões sem gravar no banco.
                A etapa seguinte transformará as escolhas em NetworkRoute, FiberCable, NetworkElement/CTO e CableReserve.
            </div>`;
    }

    async function analyze(file) {
        const projectSelect = document.getElementById("project-select");
        if (!projectSelect?.value) throw new Error("Selecione um projeto antes de importar.");
        const body = new FormData();
        body.append("file", file);
        status.textContent = `Analisando ${file.name}...`;
        const csrf = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="))?.split("=")[1] || "";
        const response = await fetch(`/api/map/projects/${projectSelect.value}/import/analyze/`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": decodeURIComponent(csrf), Accept: "application/json" },
            body,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.detail || `Erro HTTP ${response.status}`);
        render(data.analysis);
        status.textContent = `Análise concluída: ${data.analysis.summary.points} pontos e ${data.analysis.summary.lines} linhas.`;
    }

    openButton.onclick = () => {
        form.reset();
        content.innerHTML = '<p class="help-text">Selecione um KML ou KMZ para iniciar a análise sem gravar dados.</p>';
        status.textContent = "";
        dialog.showModal();
    };
    closeButton.onclick = () => dialog.close();
    form.onsubmit = async (event) => {
        event.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;
        try {
            await analyze(file);
        } catch (error) {
            status.textContent = error.message;
            status.classList.add("error");
        }
    };
})();