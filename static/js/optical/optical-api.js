(function (global) {
    "use strict";

    const namespace = global.IXCOptical = global.IXCOptical || {};

    function csrfToken() {
        const cookie = document.cookie
            .split("; ")
            .find((item) => item.startsWith("csrftoken="));
        if (cookie) return decodeURIComponent(cookie.split("=")[1]);
        return document.querySelector("#map-csrf-token input[name=csrfmiddlewaretoken]")?.value || "";
    }

    async function request(url, options = {}) {
        const headers = { Accept: "application/json", ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        const method = String(options.method || "GET").toUpperCase();
        if (method !== "GET" && method !== "HEAD") headers["X-CSRFToken"] = csrfToken();
        const response = await fetch(url, { credentials: "same-origin", ...options, method, headers });
        if (response.status === 204) return null;
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const details = data.detail || data.error || data.errors;
            const message = Array.isArray(details)
                ? details.join(" ")
                : typeof details === "object" && details
                    ? Object.values(details).flat().join(" ")
                    : details;
            throw new Error(message || `Erro HTTP ${response.status}`);
        }
        return data;
    }

    function json(method, body, signal) {
        return { method, signal, body: body === undefined ? undefined : JSON.stringify(body) };
    }

    async function loadWorkspace(elementId, signal) {
        const elementResponse = await request(`/api/map/elements/${elementId}/`, { signal });
        const element = elementResponse.element;
        if (!element || !["cto", "splice_box"].includes(element.element_type)) {
            throw new Error("Este elemento não é uma caixa óptica editável.");
        }
        const optional = (promise, fallback) => promise.catch((error) => {
            if (error.name === "AbortError") throw error;
            return { ...fallback, unavailable_reason: error.message };
        });
        const requests = [
            request(`/api/map/elements/${elementId}/splices/`, { signal }),
            request(`/api/map/elements/${elementId}/layout/`, { signal }),
            optional(request(`/api/map/elements/${elementId}/fusion-cables/?radius_m=5`, { signal }), { cables: [] }),
        ];
        if (element.element_type === "cto") {
            requests.push(optional(
                request(`/api/map/master/ctos/${elementId}/splitter-ports/`, { signal }),
                { splitters: [], unavailable: true },
            ));
        }
        const [optical, layout, cableState, servicePorts = null] = await Promise.all(requests);
        return {
            element,
            optical,
            layout: layout.layout || {},
            cableState,
            servicePorts: servicePorts?.unavailable ? null : servicePorts,
        };
    }

    const api = {
        request,
        loadWorkspace,
        saveLayout(elementId, layout, signal) {
            return request(`/api/map/elements/${elementId}/layout/`, json("PATCH", { layout }, signal));
        },
        createSplice(elementId, payload, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "splice",
                ...payload,
            }, signal));
        },
        deleteSplice(elementId, spliceId, signal) {
            return request(`/api/map/elements/${elementId}/splices/${spliceId}/`, { method: "DELETE", signal });
        },
        connectSplitterInput(elementId, splitterId, fiberId, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "splitter_input",
                splitter_id: splitterId,
                fiber_id: fiberId,
            }, signal));
        },
        connectSplitterOutput(elementId, portId, fiberId, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "splitter_output",
                port_id: portId,
                fiber_id: fiberId,
            }, signal));
        },
        connectSplitterCascade(elementId, splitterId, sourcePortId, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "splitter_cascade",
                splitter_id: splitterId,
                source_port_id: sourcePortId,
            }, signal));
        },
        clearSplitterInput(elementId, splitterId, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "clear_splitter_input",
                splitter_id: splitterId,
            }, signal));
        },
        clearSplitterOutput(elementId, portId, signal) {
            return request(`/api/map/elements/${elementId}/splices/`, json("POST", {
                connection_type: "clear_splitter_output",
                port_id: portId,
            }, signal));
        },
        createInternalGroup(elementId, signal) {
            return request(`/api/map/elements/${elementId}/trays/`, json("POST", {
                number: 1,
                name: "Estrutura interna",
                capacity: 288,
            }, signal));
        },
        createSplitter(elementId, internalGroupId, ratio, signal) {
            return request(`/api/map/elements/${elementId}/splitters/`, json("POST", {
                tray_id: internalGroupId,
                ratio,
            }, signal));
        },
        updateSplitter(elementId, splitterId, ratio, signal) {
            return request(`/api/map/elements/${elementId}/splitters/${splitterId}/`, json("PATCH", { ratio }, signal));
        },
        deleteSplitter(elementId, splitterId, signal) {
            return request(`/api/map/elements/${elementId}/splitters/${splitterId}/`, { method: "DELETE", signal });
        },
        includeCable(elementId, cableId, signal) {
            return request(`/api/map/elements/${elementId}/fusion-cables/${cableId}/`, json("POST", {
                action: "pass",
                max_distance_m: 5,
            }, signal));
        },
        excludeCable(elementId, cableId, signal) {
            return request(`/api/map/elements/${elementId}/fusion-cables/${cableId}/`, { method: "DELETE", signal });
        },
        cutCable(elementId, cableId, signal) {
            return request(`/api/map/elements/${elementId}/cables/${cableId}/cut/`, json("POST", {}, signal));
        },
        updateServicePort(elementId, payload, signal) {
            return request(`/api/map/master/ctos/${elementId}/splitter-ports/`, json("PATCH", payload, signal));
        },
    };

    namespace.api = Object.freeze(api);
})(window);
