(function () {
    "use strict";

    const state = {
        projectId: "",
        routes: [],
        selected: new Set(),
        allRoutes: true,
        showReserves: true,
        showRouteLines: true,
        applying: false,
    };

    function normalize(value) {
        return String(value || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toUpperCase()
            .replace(/[^A-Z0-9]+/g, "-")
            .replace(/^-+|-+$/g, "");
    }

    function routeEntries(feature) {
        const p = feature?.properties || feature || {};
        const labels = [];
        if (Array.isArray(p.route_names)) labels.push(...p.route_names);
        if (p.route_name) labels.push(p.route_name);
        // Para o próprio objeto NetworkRoute, nome/código são a rota.
        if (!labels.length && (p.nome || p.name)) labels.push(p.nome || p.name);
        const unique = new Map();
        labels.forEach((label) => {
            const clean = String(label || "").trim();
            const key = normalize(clean);
            if (key && clean && !unique.has(key)) unique.set(key, { key, label: clean });
        });
        return [...unique.values()];
    }

    function routeLabel(feature) {
        return routeEntries(feature)[0]?.label || "";
    }

    function routeKey(feature) {
        return routeEntries(feature)[0]?.key || "";
    }

    function storageKey() {
        return `ixcsoft-map-route-filter:${state.projectId || "none"}`;
    }

    function save() {
        try {
            localStorage.setItem(storageKey(), JSON.stringify({
                allRoutes: state.allRoutes,
                selected: [...state.selected],
                showReserves: state.showReserves,
                showRouteLines: state.showRouteLines,
            }));
        } catch (_error) {}
    }

    function restore() {
        try {
            const raw = localStorage.getItem(storageKey());
            if (!raw) return;
            const saved = JSON.parse(raw);
            state.allRoutes = saved.allRoutes !== false;
            state.selected = new Set(Array.isArray(saved.selected) ? saved.selected.map(String) : []);
            state.showReserves = saved.showReserves !== false;
            state.showRouteLines = saved.showRouteLines !== false;
        } catch (_error) {}
    }

    function uniqueRoutes(routes, elements, cables) {
        const found = new Map();
        [...(routes || []), ...(elements || []), ...(cables || [])].forEach((feature) => {
            routeEntries(feature).forEach(({ key, label }) => {
                if (!found.has(key)) found.set(key, { key, label });
            });
        });
        return [...found.values()].sort((a, b) => a.label.localeCompare(b.label, "pt-BR", { numeric: true }));
    }

    function ensurePanel() {
        const sidebar = document.querySelector("#map-sidebar .sidebar-content");
        if (!sidebar || document.getElementById("route-filter-v092")) return;
        const sections = sidebar.querySelectorAll(":scope > .editor-section");
        const layerSection = [...sections].find((section) => section.textContent.includes("Camadas"));
        const section = document.createElement("section");
        section.id = "route-filter-v092";
        section.className = "editor-section route-filter-v092";
        section.innerHTML = `
            <div class="section-heading"><span>Filtro por rota</span><button type="button" data-route-filter-toggle aria-expanded="false">Abrir</button></div>
            <div class="route-filter-summary-v092">Todas as rotas visíveis</div>
            <div class="route-filter-body-v092" hidden>
                <div class="route-filter-actions-v092">
                    <button type="button" data-route-all>Todas</button>
                    <button type="button" data-route-none>Nenhuma</button>
                </div>
                <label class="route-filter-reserve-v092"><input type="checkbox" data-route-lines checked><span>Mostrar traçados de rota</span></label>
                <label class="route-filter-reserve-v092"><input type="checkbox" data-route-reserves checked><span>Mostrar reservas técnicas</span></label>
                <div class="route-filter-list-v092" data-route-list></div>
            </div>`;
        (layerSection || sections[0])?.insertAdjacentElement("afterend", section);
        section.querySelector("[data-route-filter-toggle]").onclick = (event) => {
            const body = section.querySelector(".route-filter-body-v092");
            body.hidden = !body.hidden;
            event.currentTarget.textContent = body.hidden ? "Abrir" : "Fechar";
            event.currentTarget.setAttribute("aria-expanded", String(!body.hidden));
        };
        section.querySelector("[data-route-all]").onclick = () => {
            state.allRoutes = true;
            state.selected.clear();
            applyAndReload();
        };
        section.querySelector("[data-route-none]").onclick = () => {
            state.allRoutes = false;
            state.selected.clear();
            applyAndReload();
        };
        section.querySelector("[data-route-lines]").onchange = (event) => {
            state.showRouteLines = event.currentTarget.checked;
            applyAndReload();
        };
        section.querySelector("[data-route-reserves]").onchange = (event) => {
            state.showReserves = event.currentTarget.checked;
            applyAndReload();
        };
    }

    function renderPanel() {
        ensurePanel();
        const section = document.getElementById("route-filter-v092");
        if (!section) return;
        const list = section.querySelector("[data-route-list]");
        const routeLines = section.querySelector("[data-route-lines]");
        const reserve = section.querySelector("[data-route-reserves]");
        const summary = section.querySelector(".route-filter-summary-v092");
        routeLines.checked = state.showRouteLines;
        reserve.checked = state.showReserves;
        list.innerHTML = state.routes.length
            ? state.routes.map((route) => `
                <label class="route-filter-item-v092">
                    <input type="checkbox" value="${route.key}" ${state.allRoutes || state.selected.has(route.key) ? "checked" : ""}>
                    <span>${escapeHtml(route.label)}</span>
                    <button type="button" data-only-route="${route.key}" title="Mostrar somente esta rota">Só</button>
                </label>`).join("")
            : '<p class="help-text">Nenhuma rota identificada neste projeto.</p>';
        list.querySelectorAll('input[type="checkbox"]').forEach((input) => {
            input.onchange = () => {
                if (state.allRoutes) {
                    state.selected = new Set(state.routes.map((item) => item.key));
                }
                state.allRoutes = false;
                if (input.checked) state.selected.add(input.value);
                else state.selected.delete(input.value);
                applyAndReload();
            };
        });
        list.querySelectorAll("[data-only-route]").forEach((button) => {
            button.onclick = () => {
                state.allRoutes = false;
                state.selected = new Set([button.dataset.onlyRoute]);
                applyAndReload();
            };
        });
        summary.textContent = state.allRoutes
            ? `Todas as rotas · reservas ${state.showReserves ? "ativas" : "ocultas"}`
            : state.selected.size
                ? `${state.selected.size} rota(s) visível(is) · reservas ${state.showReserves ? "ativas" : "ocultas"}`
                : "Nenhuma rota visível";
    }

    function escapeHtml(value) {
        const span = document.createElement("span");
        span.textContent = value == null ? "" : String(value);
        return span.innerHTML;
    }

    function applyAndReload() {
        save();
        renderPanel();
        if (state.applying) return;
        state.applying = true;
        Promise.resolve(window.networkMap?.loadStructure?.())
            .finally(() => { state.applying = false; });
    }

    function setData({ routes = [], elements = [], cables = [], projectId = "" } = {}) {
        const changedProject = String(projectId || "") !== state.projectId;
        state.projectId = String(projectId || "");
        if (changedProject) {
            state.allRoutes = true;
            state.selected.clear();
            state.showReserves = true;
            state.showRouteLines = true;
            restore();
        }
        state.routes = uniqueRoutes(routes, elements, cables);
        const valid = new Set(state.routes.map((item) => item.key));
        state.selected = new Set([...state.selected].filter((key) => valid.has(key)));
        renderPanel();
    }

    function visible(feature) {
        if (state.allRoutes) return true;
        const keys = routeEntries(feature).map((entry) => entry.key);
        return keys.some((key) => state.selected.has(key));
    }

    function isElementVisible(feature) {
        return visible(feature);
    }

    function isCableVisible(feature) {
        return visible(feature);
    }

    function isRouteVisible(feature) {
        return state.showRouteLines && visible(feature);
    }

    function areReservesVisible() {
        return state.showReserves;
    }

    function modernizeYamlPicker() {
        const form = document.getElementById("container-device-type-form");
        const input = form?.elements?.file;
        if (!form || !input || form.querySelector("[data-yaml-drop-v092]")) return;
        const originalLabel = input.closest("label");
        const drop = document.createElement("div");
        drop.className = "yaml-drop-v092";
        drop.dataset.yamlDropV092 = "true";
        drop.tabIndex = 0;
        drop.innerHTML = `
            <div class="yaml-drop-icon-v092">⇧</div>
            <div><strong>Selecionar YAML</strong><span data-yaml-name>Nenhum arquivo selecionado</span></div>
            <button type="button" data-yaml-select>Procurar arquivo</button>
            <button type="button" data-yaml-clear hidden>Limpar</button>`;
        input.classList.add("yaml-native-input-v092");
        originalLabel.insertAdjacentElement("afterend", drop);
        originalLabel.classList.add("yaml-original-label-v092");
        const name = drop.querySelector("[data-yaml-name]");
        const clear = drop.querySelector("[data-yaml-clear]");
        const sync = () => {
            const file = input.files?.[0];
            name.textContent = file ? `${file.name} · ${(file.size / 1024).toFixed(1)} KB` : "Nenhum arquivo selecionado";
            clear.hidden = !file;
            drop.classList.toggle("has-file", Boolean(file));
        };
        drop.querySelector("[data-yaml-select]").onclick = (event) => { event.stopPropagation(); input.click(); };
        clear.onclick = (event) => { event.stopPropagation(); input.value = ""; sync(); };
        drop.addEventListener("click", (event) => {
            if (!event.target.closest("button")) input.click();
        });
        input.addEventListener("change", sync);
        ["dragenter", "dragover"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
            event.preventDefault();
            drop.classList.add("dragging");
        }));
        ["dragleave", "drop"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
            event.preventDefault();
            drop.classList.remove("dragging");
        }));
        drop.addEventListener("drop", (event) => {
            const file = [...(event.dataTransfer?.files || [])].find((item) => /\.ya?ml$/i.test(item.name));
            if (!file) return;
            const transfer = new DataTransfer();
            transfer.items.add(file);
            input.files = transfer.files;
            input.dispatchEvent(new Event("change", { bubbles: true }));
        });
        drop.addEventListener("keydown", (event) => {
            if (["Enter", " "].includes(event.key)) {
                event.preventDefault();
                input.click();
            }
        });
        sync();
    }

    // IXCSOFT_MAP_MASTER_SUITE_V1: o formulário já existe no template; observar
    // todo o documento congelava projetos grandes por causa dos marcadores Leaflet.
    document.addEventListener("DOMContentLoaded", () => {
        ensurePanel();
        modernizeYamlPicker();
    });
    ensurePanel();
    modernizeYamlPicker();

    window.mapV092 = {
        setData,
        isElementVisible,
        isCableVisible,
        isRouteVisible,
        areReservesVisible,
    };
}());
