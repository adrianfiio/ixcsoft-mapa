{% load static %}
const CACHE_NAME = 'afservice-tech-shell-v0.1.0';
const STATIC_ASSETS = [
  '{% static "css/technician-app.css" %}?v=0.1.0',
  '{% static "js/technician-app.js" %}?v=0.1.0',
  '{% static "pwa/manifest.webmanifest" %}?v=0.1.0',
  '{% static "pwa/offline.html" %}',
  '{% static "pwa/icons/icon-192.png" %}',
  '{% static "pwa/icons/icon-512.png" %}',
  '{% static "pwa/icons/maskable-512.png" %}'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME && key.startsWith('afservice-tech-')).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Nunca cachear dados autenticados, API, mídia privada, login ou logout.
  if (url.origin === self.location.origin && (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/media/') ||
    url.pathname.startsWith('/login/') ||
    url.pathname.startsWith('/sair/') ||
    url.pathname === '/app/' ||
    url.pathname === '/app/sw.js'
  )) {
    if (request.mode === 'navigate') {
      event.respondWith(fetch(request).catch(() => caches.match('{% static "pwa/offline.html" %}')));
    }
    return;
  }

  // Recursos externos (Leaflet e tiles) ficam sob responsabilidade da rede e do cache HTTP normal.
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('{% get_static_prefix %}')) {
    event.respondWith(caches.match(request).then(hit => hit || fetch(request).then(response => {
      if (response.ok) caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
      return response;
    })));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('{% static "pwa/offline.html" %}')));
  }
});
