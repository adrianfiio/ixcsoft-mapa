(function () {
    "use strict";

    const dialog = document.getElementById("container-dialog");
    const yamlForm = document.getElementById("container-device-type-form");
    const yamlPreview = document.getElementById("container-device-type-preview");
    const terminationForm = document.getElementById("container-fiber-termination-form");
    if (!dialog || !yamlForm || !terminationForm) return;

    let containerData = null;

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        return item ? decodeURIComponent(item.split("=")[1]) : "";
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    async function request(path, options = {}) {
        const response = await fetch(path, {
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrfToken(), Accept: "application/json", ...(options.headers || {}) },
            ...options,
        });
        const data = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        if (!response.ok) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
        return data;
    }

    function containerId() {
        return dialog.dataset.elementId || "";
    }

    function setMessage(message, error = false) {
        const target = document.getElementById("container-extension-message");
        if (!target) return;
        target.textContent = message || "";
        target.classList.toggle("error", error);
    }

    function showDevicePreview(preview) {
        const interfaces = preview.interfaces || [];
        const skipped = preview.skipped_interfaces || [];
        yamlPreview.hidden = false;
        yamlPreview.innerHTML = `
            <div class="device-type-preview-head">
                <div><strong>${escapeHtml(preview.manufacturer)} · ${escapeHtml(preview.model)}</strong><span>${escapeHtml(preview.slug)}</span></div>
                <span class="device-type-count">${interfaces.length} interface(s)</span>
            </div>
            <div class="device-type-port-list">
                ${interfaces.map((item) => `<span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.source_type)} → ${escapeHtml(item.port_type)}</small></span>`).join("")}
            </div>
            ${skipped.length ? `<details><summary>${skipped.length} interface(s) ignorada(s)</summary>${skipped.map((item) => `<p>${escapeHtml(item.name)} · ${escapeHtml(item.warning)}</p>`).join("")}</details>` : ""}`;
    }

    async function submitYaml(action) {
        const id = containerId();
        const file = yamlForm.elements.file.files[0];
        if (!id) throw new Error("Abra novamente a estrutura do rack/torre.");
        if (!file) throw new Error("Selecione um arquivo YAML.");
        const formData = new FormData(yamlForm);
        formData.set("action", action);
        setMessage(action === "preview" ? "Analisando device type..." : "Criando equipamento e interfaces...");
        const data = await request(`/api/map/elements/${id}/equipment/import-yaml/`, {
            method: "POST",
            body: formData,
        });
        showDevicePreview(data.preview);
        if (action === "import") {
            setMessage(`${data.created.name}: ${data.created.ports_created} porta(s) criada(s).`);
            yamlForm.reset();
            await window.networkMap?.manageContainer?.(id);
        } else {
            setMessage("YAML válido. Confira as interfaces e clique em Importar equipamento.");
        }
    }

    function opticalDestinationPorts(data) {
        const supported = new Set(["dio", "pon", "sfp_1g", "sfp_plus_10g"]);
        return (data.equipment || []).flatMap((equipment) =>
            (equipment.ports || [])
                .filter((port) => supported.has(port.type) && !port.fusion_used)
                .map((port) => ({ ...port, equipment_name: equipment.name }))
        );
    }

    function populateTermination(data) {
        containerData = data;
        const cableSelect = terminationForm.elements.cable_id;
        const fiberSelect = terminationForm.elements.cable_fiber_id;
        const portSelect = terminationForm.elements.destination_port_id;
        cableSelect.innerHTML = '<option value="">Selecione o cabo que chega à estrutura</option>'
            + (data.cables || []).map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${cable.fiber_count}F</option>`).join("");
        fiberSelect.innerHTML = '<option value="">Selecione primeiro o cabo</option>';
        const ports = opticalDestinationPorts(data);
        portSelect.innerHTML = '<option value="">Selecione a porta óptica de destino</option>'
            + ports.map((port) => `<option value="${port.id}">${escapeHtml(port.equipment_name)} · ${escapeHtml(port.label)}</option>`).join("");
        terminationForm.querySelector("button[type='submit']").disabled = !data.cables?.length || !ports.length;
    }

    function populateFibers(cableId) {
        const fiberSelect = terminationForm.elements.cable_fiber_id;
        const cable = (containerData?.cables || []).find((item) => String(item.id) === String(cableId));
        const fibers = (cable?.fibers || []).filter((fiber) => !fiber.used);
        fiberSelect.innerHTML = fibers.length
            ? '<option value="">Selecione a fibra</option>' + fibers.map((fiber) => `<option value="${fiber.id}">F${fiber.number} · ${escapeHtml(fiber.color_name)}</option>`).join("")
            : '<option value="">Cabo sem fibras livres/geradas</option>';
    }

    async function refreshExtensions() {
        const id = containerId();
        if (!id || !dialog.open) return;
        try {
            const data = await request(`/api/map/elements/${id}/equipment/`);
            populateTermination(data);
            drawInternalLinks(data);
        } catch (error) {
            setMessage(error.message, true);
        }
    }

    function drawInternalLinks(data) {
        const scroll = document.querySelector(".container-topology-scroll");
        const topology = document.getElementById("container-equipment-list");
        if (!scroll || !topology) return;
        scroll.querySelector(".container-link-overlay")?.remove();
        const links = (data.links || []).filter((link) => link.source_port_id && link.destination_port_id);
        if (!links.length) return;
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.classList.add("container-link-overlay");
        scroll.appendChild(svg);
        const redraw = () => {
            const box = scroll.getBoundingClientRect();
            const width = Math.max(scroll.scrollWidth, scroll.clientWidth);
            const height = Math.max(scroll.scrollHeight, scroll.clientHeight);
            svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
            svg.setAttribute("width", width);
            svg.setAttribute("height", height);
            svg.innerHTML = "";
            links.forEach((link) => {
                const source = topology.querySelector(`[data-port-id="${link.source_port_id}"]`);
                const destination = topology.querySelector(`[data-port-id="${link.destination_port_id}"]`);
                if (!source || !destination) return;
                const a = source.getBoundingClientRect();
                const b = destination.getBoundingClientRect();
                const x1 = a.left - box.left + scroll.scrollLeft + a.width / 2;
                const y1 = a.top - box.top + scroll.scrollTop + a.height / 2;
                const x2 = b.left - box.left + scroll.scrollLeft + b.width / 2;
                const y2 = b.top - box.top + scroll.scrollTop + b.height / 2;
                const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
                const middle = (x1 + x2) / 2;
                path.setAttribute("d", `M${x1},${y1} C${middle},${y1} ${middle},${y2} ${x2},${y2}`);
                path.setAttribute("class", `container-link-line ${link.link_type || "fiber"}`);
                svg.appendChild(path);
            });
        };
        requestAnimationFrame(redraw);
        window.setTimeout(redraw, 120);
    }

    yamlForm.querySelector("[data-device-type-preview]")?.addEventListener("click", () => {
        submitYaml("preview").catch((error) => setMessage(error.message, true));
    });
    yamlForm.addEventListener("submit", (event) => {
        event.preventDefault();
        submitYaml("import").catch((error) => setMessage(error.message, true));
    });
    terminationForm.elements.cable_id.addEventListener("change", (event) => populateFibers(event.target.value));
    terminationForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const id = containerId();
        const payload = Object.fromEntries(new FormData(terminationForm));
        try {
            setMessage("Criando terminação óptica...");
            await request(`/api/map/elements/${id}/equipment-links/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    cable_fiber_id: payload.cable_fiber_id,
                    destination_port_id: payload.destination_port_id,
                    link_type: "fiber",
                    loss_db: payload.loss_db || "0.1",
                }),
            });
            setMessage("Fibra terminada na porta selecionada.");
            await window.networkMap?.manageContainer?.(id);
        } catch (error) {
            setMessage(error.message, true);
        }
    });

    const observer = new MutationObserver(() => {
        if (dialog.open) window.setTimeout(refreshExtensions, 80);
    });
    observer.observe(dialog, { attributes: true, attributeFilter: ["open", "data-element-id"] });
    window.addEventListener("resize", () => {
        if (dialog.open) refreshExtensions();
    });
}());
