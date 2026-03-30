const CACHE_NAME = 'shiftmanager-v1';

const SHELL_ASSETS = [
    '/',
    '/static/css/app.css',
    '/static/js/auth.js',
    '/static/js/api.js',
    '/static/js/app.js',
    '/static/js/pages/login.js',
    '/static/js/pages/dashboard.js',
    '/static/js/pages/profile.js',
    '/static/js/pages/availability.js',
    '/static/js/pages/qualifications.js',
    '/static/js/pages/documents.js',
    '/static/js/pages/documentazione.js',
    '/static/js/pages/my_offers.js',
    '/static/js/pages/my_calendar.js',
    '/static/js/pages/my_history.js',
    '/static/js/pages/available_shifts.js',
    '/static/js/pages/notifications.js',
    '/static/js/pages/messages.js',
    '/static/js/pages/calendar.js',
    '/static/js/pages/doctors.js',
    '/static/js/pages/institutions.js',
    '/static/js/pages/offers.js',
    '/static/js/pages/admin_documents.js',
    '/static/js/pages/analytics.js',
    '/static/manifest.json',
    '/static/icons/icon.svg',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(SHELL_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            ))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API calls and auth: network only, never cache private data
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // Navigation requests (HTML): network-first, fallback to cached shell
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match('/'))
        );
        return;
    }

    // Static assets: cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request)
                .then(cached => cached || fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                }))
        );
        return;
    }

    // Everything else: network only
    event.respondWith(fetch(event.request));
});
