(function () {
    "use strict";

    const dialog = document.getElementById("container-dialog");
    const yamlForm = document.getElementById("container-device-type-form");
    const yamlPreview = document.getElementById("container-device-type-preview");
    const terminationForm = document.getElementById("container-fiber-termination-form");
    if (!dialog || !yamlForm || !terminationForm) return;

    let containerData = null;
    let lastYamlEquipmentTypeV07551 = "";

    function csrfToken() {
        const item = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
        if (item) return decodeURIComponent(item.split("=")[1]);
        return document.querySelector("[name='csrfmiddlewaretoken']")?.value
            || document.querySelector("meta[name='csrf-token']")?.content
            || "";
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    async function request(path, options = {}) {
        // ordem-v091-csrf
        const headers = {
            "X-CSRFToken": csrfToken(),
            Accept: "application/json",
            ...(options.headers || {}),
        };
        const response = await fetch(path, {
            credentials: "same-origin",
            ...options,
            headers,
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
        const modules = preview.module_bays || [];
        const powerPorts = preview.power_ports || [];
        const groups = new Map();
        interfaces.forEach((item) => {
            const key = item.group_name || item.description || "Interfaces";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(item);
        });
        yamlPreview.hidden = false;
        yamlPreview.innerHTML = `
            <div class="device-type-preview-head">
                <div><strong>${escapeHtml(preview.manufacturer)} · ${escapeHtml(preview.model)}</strong><span>${escapeHtml(preview.slug)}</span></div>
                <span class="device-type-count">${interfaces.length} porta(s) após expansão</span>
            </div>
            <div class="device-type-preview-meta-v07510">
                <span>${preview.u_height ? `${preview.u_height}U` : "Altura não informada"}</span>
                <span>${preview.is_full_depth ? "Profundidade completa" : "Profundidade parcial/não informada"}</span>
                <span>${modules.length} módulo(s)</span>
                <span>${powerPorts.length} alimentação(ões)</span>
            </div>
            ${preview.comments ? `<p>${escapeHtml(preview.comments)}</p>` : ""}
            <div class="device-type-port-groups-v07510">
                ${[...groups.entries()].map(([name, rows]) => `
                    <section><header><strong>${escapeHtml(name)}</strong><span>${rows.length}</span></header>
                    <div class="device-type-port-list">${rows.map((item) => `<span><b>${escapeHtml(item.name)}</b><small>${escapeHtml(item.source_type)} → ${escapeHtml(item.port_type)}</small></span>`).join("")}</div></section>`).join("")}
            </div>
            ${modules.length ? `<details open><summary>Módulos/slots</summary>${modules.map((item) => `<p>${escapeHtml(item.name)}</p>`).join("")}</details>` : ""}
            ${powerPorts.length ? `<details><summary>Alimentação</summary>${powerPorts.map((item) => `<p>${escapeHtml(item.name)} · ${escapeHtml(item.source_type)}</p>`).join("")}</details>` : ""}
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
        const legacyUrl = `/api/map/elements/${id}/equipment/import-yaml/`;
        const typedUrl = `/api/map/v07551/elements/${id}/equipment/import-yaml/`;
        const selectedType = String(yamlForm.elements.equipment_type?.value || "auto");
        const typedEquipmentTypesV078 = new Set(["switch", "router", "access_point", "ptp"]);
        const useTypedSwitch = typedEquipmentTypesV078.has(selectedType) || typedEquipmentTypesV078.has(lastYamlEquipmentTypeV07551);
        let data;
        try {
            data = await request(useTypedSwitch ? typedUrl : legacyUrl, { method: "POST", body: formData });
        } catch (error) {
            // YAML genérico equipment/equipments não pertence ao formato NetBox
            // legado. Em auto, tenta o importador tipado sem prejudicar OLT,
            // ONU, rádios e demais device types já suportados.
            if (action !== "preview" || selectedType !== "auto" || useTypedSwitch) throw error;
            data = await request(typedUrl, { method: "POST", body: formData });
        }
        lastYamlEquipmentTypeV07551 = String(
            data.preview?.equipment_type || data.preview?.suggested_equipment_type || selectedType
        );
        showDevicePreview(data.preview);
        if (action === "import") {
            setMessage(`${data.created.name}: ${data.created.ports_created} porta(s) criada(s).`);
            yamlForm.reset();
            lastYamlEquipmentTypeV07551 = "";
            await window.mapMasterSuite?.openContainerWorkspace?.(id);
        } else {
            setMessage("YAML válido. Confira as interfaces e clique em Importar equipamento.");
        }
    }

    function ensureDropTerminationFields() {
        if (terminationForm.querySelector("[data-drop-termination-v091]")) return;
        const wrapper = document.createElement("div");
        wrapper.className = "container-drop-termination-v091";
        wrapper.dataset.dropTerminationV091 = "true";
        wrapper.hidden = true;
        wrapper.innerHTML = `
            <label>Forma de entrada do DROP
                <select name="termination_method">
                    <option value="">Selecione</option>
                    <option value="pto">PTO + cordão até o transceiver</option>
                    <option value="direct_connector">Conector direto no transceiver</option>
                </select>
            </label>
            <p>Este campo aparece somente quando um cabo DROP será ligado diretamente em SFP/SFP+.</p>`;
        const submit = terminationForm.querySelector("button[type='submit']");
        const anchor = submit?.closest("footer") || submit;
        if (anchor?.parentNode) anchor.parentNode.insertBefore(wrapper, anchor);
        wrapper.querySelector("select")?.addEventListener("change", syncDropTerminationFields);
    }

    function selectedCable(cableId = terminationForm.elements.cable_id.value) {
        return (containerData?.cables || []).find((item) => String(item.id) === String(cableId));
    }

    function selectedDestinationPort(portId = terminationForm.elements.destination_port_id.value) {
        return (containerData?.equipment || []).flatMap((equipment) =>
            (equipment.ports || []).map((port) => ({ ...port, equipment_name: equipment.name }))
        ).find((port) => String(port.id) === String(portId));
    }

    function opticalDestinationPorts(data, cable) {
        const allowed = new Set(["dio"]);
        if (cable?.cable_type === "drop") {
            allowed.add("sfp_1g");
            allowed.add("sfp_plus_10g");
        }
        return (data.equipment || []).flatMap((equipment) =>
            (equipment.ports || [])
                .filter((port) => allowed.has(port.type) && !port.fusion_used)
                .map((port) => ({ ...port, equipment_name: equipment.name }))
        );
    }

    function syncDropTerminationFields() {
        ensureDropTerminationFields();
        const wrapper = terminationForm.querySelector("[data-drop-termination-v091]");
        const method = terminationForm.elements.termination_method;
        const cable = selectedCable();
        const port = selectedDestinationPort();
        const needsMethod = cable?.cable_type === "drop" && ["sfp_1g", "sfp_plus_10g"].includes(port?.type);
        if (wrapper) wrapper.hidden = !needsMethod;
        if (method) {
            method.required = needsMethod;
            if (!needsMethod) method.value = "";
        }
    }

    function populateDestinationPorts(cableId) {
        const portSelect = terminationForm.elements.destination_port_id;
        const cable = selectedCable(cableId);
        const ports = cable ? opticalDestinationPorts(containerData, cable) : [];
        portSelect.innerHTML = cable
            ? '<option value="">Selecione a porta óptica de destino</option>'
                + ports.map((port) => `<option value="${port.id}">${escapeHtml(port.equipment_name)} · ${escapeHtml(port.label)}</option>`).join("")
            : '<option value="">Selecione primeiro o cabo</option>';
        const submit = terminationForm.querySelector("button[type='submit']");
        if (submit) submit.disabled = !cable || !ports.length;
        syncDropTerminationFields();
    }

    function populateTermination(data) {
        containerData = data;
        ensureDropTerminationFields();
        const cableSelect = terminationForm.elements.cable_id;
        const fiberSelect = terminationForm.elements.cable_fiber_id;
        const portSelect = terminationForm.elements.destination_port_id;
        cableSelect.innerHTML = '<option value="">Selecione o cabo que chega à estrutura</option>'
            + (data.cables || []).map((cable) => `<option value="${cable.id}">${escapeHtml(cable.name)} · ${cable.fiber_count}F · ${escapeHtml(cable.cable_type_label || cable.cable_type || "")}</option>`).join("");
        fiberSelect.innerHTML = '<option value="">Selecione primeiro o cabo</option>';
        portSelect.innerHTML = '<option value="">Selecione primeiro o cabo</option>';
        terminationForm.querySelector("button[type='submit']").disabled = true;
        syncDropTerminationFields();
    }

    function populateFibers(cableId) {
        const fiberSelect = terminationForm.elements.cable_fiber_id;
        const cable = selectedCable(cableId);
        const fibers = cable?.fibers || [];
        fiberSelect.innerHTML = fibers.length
            ? '<option value="">Selecione a fibra</option>' + fibers.map((fiber) => `<option value="${fiber.id}" ${fiber.used ? "disabled" : ""}>F${fiber.number} · ${escapeHtml(fiber.color_name)}${fiber.used ? ` · EM USO${fiber.used_by ? ` — ${escapeHtml(fiber.used_by)}` : ""}` : " · livre"}</option>`).join("")
            : '<option value="">Cabo sem fibras geradas</option>';
        populateDestinationPorts(cableId);
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
    terminationForm.elements.destination_port_id.addEventListener("change", syncDropTerminationFields);
    terminationForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const id = containerId();
        const payload = Object.fromEntries(new FormData(terminationForm));
        try {
            const cable = selectedCable(payload.cable_id);
            const port = selectedDestinationPort(payload.destination_port_id);
            const needsMethod = cable?.cable_type === "drop" && ["sfp_1g", "sfp_plus_10g"].includes(port?.type);
            if (needsMethod && !payload.termination_method) {
                throw new Error("Escolha PTO ou conector direto para terminar o DROP em SFP/SFP+.");
            }
            setMessage("Criando terminação óptica...");
            await request(`/api/map/elements/${id}/equipment-links/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    cable_fiber_id: payload.cable_fiber_id,
                    destination_port_id: payload.destination_port_id,
                    link_type: "fiber",
                    termination_method: payload.termination_method || "",
                    loss_db: String(payload.loss_db || "0.1").replace(",", "."),
                }),
            });
            setMessage("Fibra terminada na porta selecionada.");
            await window.networkMap?.manageContainer?.(id);
        } catch (error) {
            setMessage(error.message, true);
        }
    });

    document.addEventListener("map:container-rendered", (event) => {
        if (!dialog.open || !event.detail?.data) return;
        populateTermination(event.detail.data);
        drawInternalLinks(event.detail.data);
    });
    window.addEventListener("resize", () => {
        if (dialog.open && containerData) drawInternalLinks(containerData);
    });
}());
