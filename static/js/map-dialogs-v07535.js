(function (global) {
    "use strict";

    const ROOT_ID = "map-dialog-v07535";
    let active = null;

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value == null ? "" : String(value);
        return node.innerHTML;
    }

    function ensureDialog() {
        let dialog = document.getElementById(ROOT_ID);
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = ROOT_ID;
        dialog.className = "map-dialog-v07535";
        dialog.setAttribute("aria-labelledby", `${ROOT_ID}-title`);
        dialog.innerHTML = `
            <form method="dialog" class="map-dialog-card-v07535" novalidate>
                <header>
                    <span class="map-dialog-icon-v07535" data-dialog-icon aria-hidden="true">i</span>
                    <div>
                        <h2 id="${ROOT_ID}-title" data-dialog-title>Mensagem</h2>
                        <p data-dialog-message></p>
                    </div>
                    <button type="button" class="map-dialog-close-v07535" data-dialog-cancel aria-label="Fechar">×</button>
                </header>
                <div class="map-dialog-fields-v07535" data-dialog-fields></div>
                <p class="map-dialog-error-v07535" data-dialog-error hidden></p>
                <footer>
                    <button type="button" data-dialog-cancel>Cancelar</button>
                    <button type="submit" class="map-dialog-primary-v07535" data-dialog-confirm>Confirmar</button>
                </footer>
            </form>`;
        document.body.appendChild(dialog);
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            finish(null);
        });
        dialog.querySelectorAll("[data-dialog-cancel]").forEach((button) => {
            button.addEventListener("click", () => finish(null));
        });
        dialog.querySelector("form").addEventListener("submit", (event) => {
            event.preventDefault();
            submit();
        });
        return dialog;
    }

    function finish(value) {
        if (!active) return;
        const { dialog, resolve } = active;
        active = null;
        dialog.classList.remove("is-danger-v07535", "is-alert-v07535");
        if (dialog.open) dialog.close();
        resolve(value);
    }

    function fieldMarkup(field, index) {
        const id = `${ROOT_ID}-field-${index}`;
        const required = field.required === false ? "" : " required";
        const disabled = field.disabled ? " disabled" : "";
        const description = field.description
            ? `<small>${escapeHtml(field.description)}</small>`
            : "";
        const label = `<span>${escapeHtml(field.label || "Valor")}</span>`;
        if (Array.isArray(field.options)) {
            const options = field.options.map((option) => {
                const item = typeof option === "object" ? option : { value: option, label: option };
                return `<option value="${escapeHtml(item.value)}" ${String(item.value) === String(field.value ?? "") ? "selected" : ""}>${escapeHtml(item.label)}</option>`;
            }).join("");
            return `<label for="${id}">${label}<select id="${id}" name="${escapeHtml(field.name || `field_${index}`)}"${required}${disabled}>${options}</select>${description}</label>`;
        }
        if (field.multiline) {
            return `<label for="${id}">${label}<textarea id="${id}" name="${escapeHtml(field.name || `field_${index}`)}" rows="${Number(field.rows || 4)}" maxlength="${Number(field.maxLength || 2000)}" placeholder="${escapeHtml(field.placeholder || "")}"${required}${disabled}>${escapeHtml(field.value || "")}</textarea>${description}</label>`;
        }
        const type = field.type || "text";
        const min = field.min !== undefined ? ` min="${escapeHtml(field.min)}"` : "";
        const max = field.max !== undefined ? ` max="${escapeHtml(field.max)}"` : "";
        const step = field.step !== undefined ? ` step="${escapeHtml(field.step)}"` : "";
        const maxLength = field.maxLength ? ` maxlength="${Number(field.maxLength)}"` : "";
        return `<label for="${id}">${label}<input id="${id}" name="${escapeHtml(field.name || `field_${index}`)}" type="${escapeHtml(type)}" value="${escapeHtml(field.value ?? "")}" placeholder="${escapeHtml(field.placeholder || "")}"${min}${max}${step}${maxLength}${required}${disabled}>${description}</label>`;
    }

    function normalizeFields(options) {
        if (Array.isArray(options.fields)) return options.fields;
        if (options.kind === "prompt") {
            return [{
                name: "value",
                label: options.label || "Valor",
                value: options.value || "",
                placeholder: options.placeholder || "",
                multiline: Boolean(options.multiline),
                rows: options.rows,
                type: options.type || "text",
                min: options.min,
                max: options.max,
                step: options.step,
                maxLength: options.maxLength,
                options: options.options,
                required: options.required !== false,
                description: options.description,
            }];
        }
        return [];
    }

    function open(options = {}) {
        const dialog = ensureDialog();
        if (active) finish(null);
        const fields = normalizeFields(options);
        const form = dialog.querySelector("form");
        const title = dialog.querySelector("[data-dialog-title]");
        const message = dialog.querySelector("[data-dialog-message]");
        const icon = dialog.querySelector("[data-dialog-icon]");
        const fieldsRoot = dialog.querySelector("[data-dialog-fields]");
        const error = dialog.querySelector("[data-dialog-error]");
        const cancel = dialog.querySelector("footer [data-dialog-cancel]");
        const confirm = dialog.querySelector("[data-dialog-confirm]");

        title.textContent = options.title || "Confirmação";
        message.textContent = options.message || "";
        message.hidden = !options.message;
        icon.textContent = options.icon || (options.danger ? "!" : options.kind === "alert" ? "i" : "✓");
        fieldsRoot.innerHTML = fields.map(fieldMarkup).join("");
        fieldsRoot.hidden = fields.length === 0;
        error.hidden = true;
        error.textContent = "";
        cancel.textContent = options.cancelLabel || "Cancelar";
        cancel.hidden = options.kind === "alert";
        confirm.textContent = options.confirmLabel || (options.kind === "alert" ? "Entendi" : "Confirmar");
        confirm.disabled = false;
        dialog.classList.toggle("is-danger-v07535", Boolean(options.danger));
        dialog.classList.toggle("is-alert-v07535", options.kind === "alert");
        form.dataset.dialogMode = options.kind || "confirm";

        return new Promise((resolve) => {
            active = { dialog, resolve, options, fields };
            dialog.showModal();
            global.requestAnimationFrame(() => {
                const first = fieldsRoot.querySelector("input:not(:disabled), textarea:not(:disabled), select:not(:disabled)");
                (first || confirm).focus();
                if (first && "select" in first && typeof first.select === "function" && first.tagName === "INPUT") first.select();
            });
        });
    }

    async function submit() {
        if (!active) return;
        const { dialog, options, fields } = active;
        const form = dialog.querySelector("form");
        const error = dialog.querySelector("[data-dialog-error]");
        const confirm = dialog.querySelector("[data-dialog-confirm]");
        if (!form.reportValidity()) return;

        const data = {};
        fields.forEach((field, index) => {
            const name = field.name || `field_${index}`;
            const node = form.elements.namedItem(name);
            data[name] = node?.value ?? "";
        });
        let value = options.kind === "prompt" ? data.value : fields.length ? data : true;
        if (typeof options.validate === "function") {
            try {
                const result = await options.validate(value, data);
                if (typeof result === "string" && result) {
                    error.textContent = result;
                    error.hidden = false;
                    return;
                }
                if (result === false) return;
                if (result !== undefined && result !== true) value = result;
            } catch (validationError) {
                error.textContent = validationError.message || "Não foi possível validar os dados.";
                error.hidden = false;
                return;
            }
        }
        confirm.disabled = true;
        finish(value);
    }

    const api = {
        alert(options) {
            return open({ ...(typeof options === "string" ? { message: options } : options), kind: "alert" });
        },
        confirm(options) {
            return open({ ...(typeof options === "string" ? { message: options } : options), kind: "confirm" });
        },
        prompt(options) {
            return open({ ...(typeof options === "string" ? { label: options } : options), kind: "prompt" });
        },
        form(options) {
            return open({ ...options, kind: "form" });
        },
        close() {
            finish(null);
        },
        version: "0.75.35",
    };

    global.IXCMapDialog = Object.freeze(api);
})(window);
