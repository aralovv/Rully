'use strict';

const CACHE_NAME = 'rully-shell-v9';
const STATIC_ASSETS = [
  '/',
  '/static/css/rully.css?v=9.0.0',
  '/static/js/icons.js?v=9.0.0',
  '/static/js/translations.js?v=9.0.0',
  '/static/js/cheatsheet_data.js?v=9.0.0',
  '/static/js/core/state.js?v=9.0.0',
  '/static/js/core/theme.js?v=9.0.0',
  '/static/js/core/hud.js?v=9.0.0',
  '/static/js/core/api.js?v=9.0.0',
  '/static/js/views/reference.js?v=9.0.0',
  '/static/js/views/home.js?v=9.0.0',
  '/static/js/views/prepare.js?v=9.0.0',
  '/static/js/views/quiz.js?v=9.0.0',
  '/static/js/views/amaliy.js?v=9.0.0',
  '/static/js/views/ai.js?v=9.0.0',
  '/static/js/views/profile.js?v=9.0.0',
  '/static/js/app.js?v=9.0.0',
  '/static/images/rully-avatar-128.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(STATIC_ASSETS).catch(function () { return null; });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME; }).map(function (k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (event) {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Never cache authenticated user/admin/payment/session/AI endpoints
  const isPublicRefApi =
    url.pathname.startsWith('/api/reference/') ||
    url.pathname === '/api/public/overview' ||
    url.pathname === '/api/subscription/plans';

  if (url.pathname.startsWith('/api/') && !isPublicRefApi) return;

  if (url.pathname.startsWith('/static/') || url.pathname === '/' || url.pathname === '/index.html' || isPublicRefApi) {
    event.respondWith(
      caches.open(CACHE_NAME).then(function (cache) {
        return cache.match(req).then(function (cached) {
          const networkFetch = fetch(req).then(function (resp) {
            if (resp && resp.ok && resp.type === 'basic') {
              cache.put(req, resp.clone());
            }
            return resp;
          }).catch(function () {
            return cached;
          });
          return cached || networkFetch;
        });
      })
    );
  }
});
