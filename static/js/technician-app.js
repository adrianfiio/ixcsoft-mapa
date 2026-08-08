(() => {
  'use strict';

  const body = document.body;
  const endpoints = {
    projects: body.dataset.projectsUrl,
    elements: body.dataset.elementsUrl,
    cables: body.dataset.cablesUrl,
    routes: body.dataset.routesUrl,
    login: body.dataset.loginUrl || '/login/',
    sw: body.dataset.serviceWorkerUrl || '/app/sw.js',
  };

  const state = {
    map: null,
    projectId: null,
    elements: [],
    cables: [],
    routes: [],
    markers: [],
    cableLayers: [],
    routeLayers: [],
    selected: null,
    userLatLng: null,
    userMarker: null,
    accuracyCircle: null,
    deferredInstallPrompt: null,
    // MAP_V085_TECH_APP_LAYERS: sem "client" -- info demais pro campo.
    // "infrastructure" fica sem checkbox própria (CEO/CDO, postes etc.
    // continuam visíveis, só não tem toggle dedicado).
    layers: { cto: true, rack: true, tower: true, pop: true, infrastructure: true, cables: true, routes: true },
  };

  const el = (id) => document.getElementById(id);
  const statusPill = el('status-pill');
  const detailsSheet = el('details-sheet');
  const searchPanel = el('search-panel');
  const searchInput = el('search-input');
  const searchResults = el('search-results');
  const projectSelect = el('project-select');

  function text(value, fallback = '—') {
    if (value === null || value === undefined || value === '') return fallback;
    return String(value);
  }

  function setStatus(message) { statusPill.textContent = message; }

  async function fetchJson(url) {
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
      cache: 'no-store',
    });
    if (response.status === 401 || response.status === 302) {
      window.location.assign(`${endpoints.login}?next=${encodeURIComponent('/app/')}`);
      throw new Error('Sessão expirada.');
    }
    if (!response.ok) throw new Error(`HTTP ${response.status} ao carregar ${url}`);
    return response.json();
  }

  function extractRows(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.features)) return payload.features;
    if (Array.isArray(payload?.results)) return payload.results;
    if (Array.isArray(payload?.data)) return payload.data;
    return [];
  }

  function isClientLike(type) {
    return type.includes('client') || type.includes('cliente') || type.includes('customer');
  }

  function normalizeElement(raw) {
    const props = raw?.properties ? { ...raw.properties } : { ...raw };
    const geometry = raw?.geometry || props.geometry;
    const coords = geometry?.type === 'Point' ? geometry.coordinates : null;
    const lat = Number(props.latitude ?? props.lat ?? (coords ? coords[1] : NaN));
    const lng = Number(props.longitude ?? props.lng ?? props.lon ?? (coords ? coords[0] : NaN));
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    const type = String(props.element_type ?? props.type ?? props.subtype ?? 'infrastructure').toLowerCase();
    // MAP_V085_TECH_APP_LAYERS: cliente nem entra no estado -- não é só
    // uma camada desmarcada, é descartado antes de renderizar/buscar.
    if (isClientLike(type)) return null;
    return { ...props, id: props.id ?? raw.id, lat, lng, _type: type, _raw: raw };
  }

  function categoryFor(item) {
    const type = item._type;
    if (type.includes('cto')) return 'cto';
    if (type.includes('rack')) return 'rack';
    if (type.includes('tower') || type.includes('torre')) return 'tower';
    if (type.includes('pop') || type.includes('cpd')) return 'pop';
    return 'infrastructure';
  }

  function markerLabel(item, category) {
    if (category === 'cto') return 'CTO';
    if (category === 'rack') return 'RACK';
    if (category === 'tower') return 'TORRE';
    if (category === 'pop') return 'POP';
    const type = item._type.replaceAll('_', ' ').slice(0, 4).toUpperCase();
    return type || '•';
  }

  function makeMarkerIcon(item) {
    const category = categoryFor(item);
    return L.divIcon({
      className: '',
      html: `<div class="tech-marker ${category}">${markerLabel(item, category)}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
  }

  function itemTitle(item) {
    return text(item.name ?? item.title ?? item.label ?? item.username ?? item.login ?? `#${item.id}`);
  }

  function addElementMarker(item) {
    const category = categoryFor(item);
    if (!state.layers[category]) return;
    const marker = L.marker([item.lat, item.lng], { icon: makeMarkerIcon(item), keyboard: true });
    marker.on('click', () => openDetails(item, marker));
    marker.addTo(state.map);
    marker.__techCategory = category;
    marker.__techItem = item;
    state.markers.push(marker);
  }

  function parseCoordinates(candidate) {
    if (!candidate) return [];
    let value = candidate;
    if (typeof value === 'string') {
      try { value = JSON.parse(value); } catch (_) { return []; }
    }
    if (!Array.isArray(value)) return [];
    return value.map(point => {
      if (Array.isArray(point) && point.length >= 2) {
        const a = Number(point[0]); const b = Number(point[1]);
        if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
        return Math.abs(a) <= 90 && Math.abs(b) <= 180 ? [a, b] : [b, a];
      }
      const lat = Number(point?.lat ?? point?.latitude);
      const lng = Number(point?.lng ?? point?.lon ?? point?.longitude);
      return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null;
    }).filter(Boolean);
  }

  function normalizeCable(raw) {
    const props = raw?.properties ? { ...raw.properties } : { ...raw };
    const geometry = raw?.geometry || props.geometry;
    let coords = [];
    if (geometry?.type === 'LineString' && Array.isArray(geometry.coordinates)) {
      coords = geometry.coordinates.map(([lng, lat]) => [Number(lat), Number(lng)]).filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng));
    }
    if (!coords.length) {
      coords = parseCoordinates(props.coordinates ?? props.path ?? props.route ?? props.points ?? props.path_coordinates);
    }
    if (coords.length < 2) return null;
    return { ...props, id: props.id ?? raw.id, _coords: coords };
  }

  function addCable(cable) {
    if (!state.layers.cables) return;
    const color = cable.color || cable.project_color || '#38a8e8';
    const layer = L.polyline(cable._coords, { color, weight: 3, opacity: .82, interactive: true });
    layer.bindTooltip(text(cable.name ?? cable.label ?? `Cabo #${cable.id}`));
    layer.addTo(state.map);
    state.cableLayers.push(layer);
  }

  function normalizeRoute(raw) {
    const props = raw?.properties ? { ...raw.properties } : { ...raw };
    const geometry = raw?.geometry || props.geometry;
    if (geometry?.type !== 'MultiLineString' || !Array.isArray(geometry.coordinates)) return null;
    const segments = geometry.coordinates
      .map(line => line.map(([lng, lat]) => [Number(lat), Number(lng)]).filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng)))
      .filter(segment => segment.length >= 2);
    if (!segments.length) return null;
    return { ...props, id: props.id ?? raw.id, _segments: segments };
  }

  function addRoute(route) {
    if (!state.layers.routes) return;
    const layer = L.polyline(route._segments, { color: '#ffb84d', weight: 3, opacity: .75, dashArray: '8 6', interactive: true });
    layer.bindTooltip(text(route.nome ?? route.name ?? `Rota #${route.id}`));
    layer.addTo(state.map);
    state.routeLayers.push(layer);
  }

  function renderNetwork() {
    state.markers.forEach(m => m.remove());
    state.cableLayers.forEach(l => l.remove());
    state.routeLayers.forEach(l => l.remove());
    state.markers = [];
    state.cableLayers = [];
    state.routeLayers = [];
    state.elements.forEach(addElementMarker);
    state.cables.forEach(addCable);
    state.routes.forEach(addRoute);
    setStatus(`${state.elements.length} elementos • ${state.cables.length} cabos • ${state.routes.length} rotas`);
  }

  async function loadProjects() {
    const payload = await fetchJson(endpoints.projects);
    // MAP_V085_TECH_APP_PROJECTS_SHAPE: /api/map/projects/ sempre devolveu
    // {success, projects: [...]} -- não bate com nenhum dos formatos que
    // extractRows reconhece (.features/.results/.data/array puro), então
    // o seletor de projeto nunca populava, desde a primeira versão do app.
    const projects = Array.isArray(payload?.data?.projects)
      ? payload.data.projects
      : Array.isArray(payload?.projects)
        ? payload.projects
        : extractRows(payload);
    projectSelect.innerHTML = '';
    if (!projects.length) {
      projectSelect.append(new Option('Nenhum projeto disponível', ''));
      setStatus('Nenhum projeto de rede disponível');
      return;
    }
    projects.filter(p => p.is_active !== false).forEach(project => {
      projectSelect.append(new Option(text(project.name, `Projeto #${project.id}`), String(project.id)));
    });
    const saved = localStorage.getItem('afservice.tech.project');
    const chosen = projects.find(p => String(p.id) === saved && p.is_active !== false) || projects.find(p => p.is_active !== false);
    if (chosen) {
      projectSelect.value = String(chosen.id);
      await loadProject(chosen.id);
    }
  }

  async function loadProject(projectId) {
    if (!projectId) return;
    state.projectId = String(projectId);
    localStorage.setItem('afservice.tech.project', state.projectId);
    setStatus('Atualizando mapa...');
    try {
      const [elementsPayload, cablesPayload, routesPayload] = await Promise.all([
        fetchJson(`${endpoints.elements}?project_id=${encodeURIComponent(projectId)}`),
        fetchJson(`${endpoints.cables}?project_id=${encodeURIComponent(projectId)}`).catch(err => {
          console.warn('Camada de cabos indisponível:', err);
          return [];
        }),
        fetchJson(`${endpoints.routes}?project_id=${encodeURIComponent(projectId)}`).catch(err => {
          console.warn('Camada de rotas indisponível:', err);
          return [];
        }),
      ]);
      state.elements = extractRows(elementsPayload).map(normalizeElement).filter(Boolean);
      state.cables = extractRows(cablesPayload).map(normalizeCable).filter(Boolean);
      state.routes = extractRows(routesPayload).map(normalizeRoute).filter(Boolean);
      renderNetwork();
      fitNetwork(false);
    } catch (error) {
      console.error(error);
      setStatus('Falha ao carregar o projeto');
    }
  }

  function fitNetwork(force = true) {
    const points = state.elements.map(i => [i.lat, i.lng]);
    if (state.userLatLng) points.push([state.userLatLng.lat, state.userLatLng.lng]);
    if (!points.length) return;
    const bounds = L.latLngBounds(points);
    if (bounds.isValid() && (force || !state.map.__initialFitDone)) {
      state.map.fitBounds(bounds.pad(.08), { maxZoom: 17, animate: true });
      state.map.__initialFitDone = true;
    }
  }

  function detailPairs(item) {
    const category = categoryFor(item);
    const common = [
      ['Tipo', item._type.replaceAll('_', ' ').toUpperCase()],
      ['Status', item.status ?? item.operational_status],
      ['ID', item.id],
    ];
    if (category === 'cto') {
      return common.concat([
        ['Capacidade', item.capacity], ['Modelo', item.model], ['Splitters', item.splitters],
        ['Portas', item.ports], ['Ocupadas', item.occupied_ports ?? item.used_ports], ['Livres', item.free_ports],
      ]);
    }
    return common.concat([
      ['Modelo', item.model], ['Endereço', item.address], ['Descrição', item.description],
    ]);
  }

  function openDetails(item, marker) {
    state.selected = { item, marker };
    el('detail-type').textContent = categoryFor(item);
    el('detail-title').textContent = itemTitle(item);
    const grid = el('detail-grid');
    grid.replaceChildren();
    detailPairs(item).filter(([, value]) => value !== null && value !== undefined && value !== '').forEach(([label, value]) => {
      const box = document.createElement('div'); box.className = 'detail-item';
      const key = document.createElement('span'); key.textContent = label;
      const val = document.createElement('strong'); val.textContent = text(value);
      box.append(key, val); grid.append(box);
    });
    if (state.userLatLng) {
      const distance = state.map.distance(state.userLatLng, L.latLng(item.lat, item.lng));
      const box = document.createElement('div'); box.className = 'detail-item';
      const key = document.createElement('span'); key.textContent = 'Distância';
      const val = document.createElement('strong'); val.textContent = distance < 1000 ? `${Math.round(distance)} m` : `${(distance / 1000).toFixed(2)} km`;
      box.append(key, val); grid.append(box);
    }
    detailsSheet.classList.add('open');
    detailsSheet.setAttribute('aria-hidden', 'false');
  }

  function closeDetails() {
    detailsSheet.classList.remove('open'); detailsSheet.setAttribute('aria-hidden', 'true'); state.selected = null;
  }

  function renderSearch(query) {
    const q = query.trim().toLocaleLowerCase('pt-BR');
    searchResults.replaceChildren();
    if (!q) return;
    const results = state.elements.filter(item => {
      const haystack = [itemTitle(item), item.id, item._type, item.address, item.ixc_id, item.login, item.cto_name].map(text).join(' ').toLocaleLowerCase('pt-BR');
      return haystack.includes(q);
    }).slice(0, 40);
    results.forEach(item => {
      const button = document.createElement('button'); button.className = 'search-result'; button.type = 'button'; button.setAttribute('role', 'option');
      const main = document.createElement('span'); main.textContent = itemTitle(item);
      const meta = document.createElement('small'); meta.textContent = `${categoryFor(item).toUpperCase()} • #${text(item.id)}`;
      button.append(main, meta);
      button.addEventListener('click', () => {
        state.map.flyTo([item.lat, item.lng], Math.max(state.map.getZoom(), 18));
        const marker = state.markers.find(m => m.__techItem?.id === item.id);
        openDetails(item, marker);
        searchPanel.hidden = true;
      });
      searchResults.append(button);
    });
    if (!results.length) {
      const empty = document.createElement('div'); empty.className = 'search-result'; empty.textContent = 'Nenhum resultado.'; searchResults.append(empty);
    }
  }

  function locateUser() {
    if (!navigator.geolocation) { setStatus('GPS não disponível neste navegador'); return; }
    setStatus('Obtendo localização...');
    navigator.geolocation.getCurrentPosition(position => {
      const latlng = L.latLng(position.coords.latitude, position.coords.longitude);
      state.userLatLng = latlng;
      if (state.userMarker) state.userMarker.remove();
      if (state.accuracyCircle) state.accuracyCircle.remove();
      state.userMarker = L.marker(latlng, {
        icon: L.divIcon({ className: '', html: '<div class="user-location"></div>', iconSize: [18,18], iconAnchor:[9,9] }),
        zIndexOffset: 1000,
      }).addTo(state.map).bindTooltip('Sua localização');
      state.accuracyCircle = L.circle(latlng, { radius: Math.max(position.coords.accuracy || 0, 5), weight:1, fillOpacity:.06 }).addTo(state.map);
      state.map.flyTo(latlng, Math.max(state.map.getZoom(), 17));
      setStatus(`GPS ativo • precisão aproximada ${Math.round(position.coords.accuracy || 0)} m`);
      if (state.selected) openDetails(state.selected.item, state.selected.marker);
    }, error => {
      console.warn(error);
      const messages = { 1:'Permissão de localização negada', 2:'Localização indisponível', 3:'Tempo limite do GPS excedido' };
      setStatus(messages[error.code] || 'Não foi possível obter a localização');
    }, { enableHighAccuracy:true, timeout:12000, maximumAge:15000 });
  }

  function openDrawer() {
    el('side-drawer').classList.add('open'); el('side-drawer').setAttribute('aria-hidden','false'); el('drawer-backdrop').hidden = false; el('menu-button').setAttribute('aria-expanded','true');
  }
  function closeDrawer() {
    el('side-drawer').classList.remove('open'); el('side-drawer').setAttribute('aria-hidden','true'); el('drawer-backdrop').hidden = true; el('menu-button').setAttribute('aria-expanded','false');
  }

  function initMap() {
    state.map = L.map('tech-map', { zoomControl:false, attributionControl:true, preferCanvas:true }).setView([-14.235, -51.9253], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 20,
      attribution: '&copy; OpenStreetMap contributors',
      crossOrigin: true,
    }).addTo(state.map);
    L.control.zoom({ position:'bottomleft' }).addTo(state.map);
  }

  function setupEvents() {
    el('menu-button').addEventListener('click', openDrawer);
    el('drawer-close').addEventListener('click', closeDrawer);
    el('drawer-backdrop').addEventListener('click', closeDrawer);
    el('search-button').addEventListener('click', () => { searchPanel.hidden = !searchPanel.hidden; if (!searchPanel.hidden) searchInput.focus(); });
    el('search-close').addEventListener('click', () => { searchPanel.hidden = true; searchInput.value=''; searchResults.replaceChildren(); });
    searchInput.addEventListener('input', () => renderSearch(searchInput.value));
    projectSelect.addEventListener('change', () => loadProject(projectSelect.value));
    el('reload-button').addEventListener('click', () => { closeDrawer(); loadProject(state.projectId); });
    el('gps-button').addEventListener('click', locateUser);
    el('fit-button').addEventListener('click', () => fitNetwork(true));
    el('details-close').addEventListener('click', closeDetails);
    el('center-button').addEventListener('click', () => { if (state.selected) state.map.flyTo([state.selected.item.lat, state.selected.item.lng], 19); });
    el('route-button').addEventListener('click', () => {
      if (!state.selected) return;
      const { lat, lng } = state.selected.item;
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${lat},${lng}`)}`, '_blank', 'noopener,noreferrer');
    });
    document.querySelectorAll('[data-layer]').forEach(input => input.addEventListener('change', () => { state.layers[input.dataset.layer] = input.checked; renderNetwork(); }));
    window.addEventListener('online', () => { el('connection-banner').hidden = true; setStatus('Conexão restabelecida'); if (state.projectId) loadProject(state.projectId); });
    window.addEventListener('offline', () => { el('connection-banner').hidden = false; setStatus('Sem conexão'); });
  }

  function setupPwa() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => navigator.serviceWorker.register(endpoints.sw, { scope:'/app/' }).catch(err => console.warn('Service worker:', err)));
    }
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault(); state.deferredInstallPrompt = event; el('install-button').hidden = false;
    });
    el('install-button').addEventListener('click', async () => {
      if (!state.deferredInstallPrompt) return;
      state.deferredInstallPrompt.prompt();
      await state.deferredInstallPrompt.userChoice;
      state.deferredInstallPrompt = null; el('install-button').hidden = true;
    });
    const isiOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    if (isiOS && !standalone) el('ios-install-help').hidden = false;
  }

  async function boot() {
    initMap(); setupEvents(); setupPwa();
    el('connection-banner').hidden = navigator.onLine;
    try { await loadProjects(); }
    catch (error) { console.error(error); setStatus('Não foi possível carregar os projetos'); }
  }

  boot();
})();
