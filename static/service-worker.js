// STS2决策器 Service Worker
const CACHE_NAME = 'sts2-advisor-v1';
const STATIC_CACHE = [
  '/',
  '/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

// 安装：缓存静态资源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_CACHE))
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 拦截请求：网络优先，失败回退缓存
self.addEventListener('fetch', event => {
  // 只缓存GET请求
  if (event.request.method !== 'GET') return;

  // API请求不缓存（实时数据）
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // 静态页面：网络优先，失败用缓存
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // 缓存成功的响应
        if (response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request).then(cached => cached || caches.match('/')))
  );
});
