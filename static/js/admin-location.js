document.addEventListener("DOMContentLoaded", () => {
    const latitude = document.getElementById("id_latitude");
    const longitude = document.getElementById("id_longitude");
    if (!latitude || !longitude) return;

    const panel = document.createElement("div");
    panel.className = "af-location-panel";
    panel.innerHTML = `
        <strong>Localização rápida</strong>
        <div class="af-location-row">
            <input class="af-address-search" type="search" placeholder="Rua, número, cidade e estado">
            <button class="button af-search-location" type="button">Buscar endereço</button>
            <button class="button af-use-gps" type="button">Usar GPS deste aparelho</button>
        </div>
        <small>Você também pode preencher latitude e longitude. Se deixar vazio, DIO usa o CPD e CPD usa uma localização do projeto.</small>
        <output class="af-location-feedback"></output>
    `;
    const latitudeRow = latitude.closest(".form-row");
    latitudeRow?.parentNode.insertBefore(panel, latitudeRow);
    const feedback = panel.querySelector(".af-location-feedback");

    const applyCoordinates = (lat, lon, message) => {
        latitude.value = Number(lat).toFixed(7);
        longitude.value = Number(lon).toFixed(7);
        latitude.dispatchEvent(new Event("change", { bubbles: true }));
        longitude.dispatchEvent(new Event("change", { bubbles: true }));
        feedback.textContent = `${message}: ${latitude.value}, ${longitude.value}. Salve para atualizar o mapa.`;
        feedback.classList.remove("error");
    };

    panel.querySelector(".af-use-gps").addEventListener("click", () => {
        if (!navigator.geolocation) {
            feedback.textContent = "Este navegador não oferece localização por GPS.";
            feedback.classList.add("error");
            return;
        }
        feedback.textContent = "Obtendo localização...";
        navigator.geolocation.getCurrentPosition(
            ({ coords }) => applyCoordinates(coords.latitude, coords.longitude, "GPS localizado"),
            () => {
                feedback.textContent = "Não foi possível obter o GPS. Verifique a permissão do navegador.";
                feedback.classList.add("error");
            },
            { enableHighAccuracy: true, timeout: 12000 },
        );
    });

    panel.querySelector(".af-search-location").addEventListener("click", async () => {
        const query = panel.querySelector(".af-address-search").value.trim();
        if (!query) {
            feedback.textContent = "Digite o endereço completo.";
            feedback.classList.add("error");
            return;
        }
        feedback.textContent = "Buscando endereço...";
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=br&q=${encodeURIComponent(query)}`, {
                headers: { "Accept-Language": "pt-BR" },
            });
            const results = await response.json();
            if (!results.length) throw new Error("Endereço não encontrado.");
            applyCoordinates(results[0].lat, results[0].lon, results[0].display_name);
        } catch (error) {
            feedback.textContent = error.message || "Falha ao buscar o endereço.";
            feedback.classList.add("error");
        }
    });
});
