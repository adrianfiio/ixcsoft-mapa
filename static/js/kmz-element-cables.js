(function () {
    "use strict";
    const dialog = document.getElementById("kmz-element-cables-dialog");
    if (!dialog) return;
    const title = document.getElementById("kmz-element-cables-title");
    const subtitle = document.getElementById("kmz-element-cables-subtitle");
    const content = document.getElementById("kmz-element-cables-content");

    function esc(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function row(item, label) {
        return `<tr>
            <td><strong>${esc(item.code || item.name)}</strong><div class="kmz-samples">${esc(item.name)}</div></td>
            <td>${esc(label || item.action_label || item.relation)}</td>
            <td>${item.fiber_count} fibra${Number(item.fiber_count) === 1 ? "" : "s"}</td>
            <td>${esc(item.route_name || "Sem rota")}</td>
        </tr>`;
    }

    function section(name, items, label) {
        return `<section class="kmz-connection-section">
            <h3>${esc(name)} <span class="kmz-badge">${items.length}</span></h3>
            ${items.length ? `<div class="kmz-table-wrap"><table class="kmz-table"><thead><tr><th>Cabo</th><th>Relação</th><th>Capacidade</th><th>Rota</th></tr></thead><tbody>${items.map((item) => row(item, label)).join("")}</tbody></table></div>` : '<p class="kmz-muted">Nenhum cabo nesta categoria.</p>'}
        </section>`;
    }

    async function open(elementId) {
        content.innerHTML = '<p>Carregando ligações...</p>';
        dialog.showModal();
        const response = await fetch(`/api/map/elements/${elementId}/cable-topology/`, {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        });
        const data = await response.json().catch(() => ({ error: "Resposta inválida." }));
        if (!response.ok) {
            content.innerHTML = `<div class="kmz-warning">${esc(data.error || `HTTP ${response.status}`)}</div>`;
            return;
        }
        title.textContent = `Cabos · ${data.element.name}`;
        subtitle.textContent = `${data.element.code || "Sem código"} · ${data.element.subtype || data.element.type}`;
        content.innerHTML = [
            section("Cabo de entrada", data.connections.incoming, "Entrada"),
            section("Cabo de saída", data.connections.outgoing, "Saída"),
            section("Passagens, cortes e derivações", data.connections.passages),
        ].join("");
    }

    dialog.querySelector(".dialog-close").onclick = () => dialog.close();
    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-show-element-cables]");
        if (button) open(button.dataset.showElementCables);
    });
    window.kmzElementCables = { open };
}());
