/**
 * Service Worker for Southeast Asia Watch
 * 策略：
 *  - 安装时预缓存核心资源（HTML/CSS/JS/图标/manifest）
 *  - 导航请求：网络优先，失败回退缓存首页
 *  - 文章数据（.json/.md）：网络优先 + 缓存兜底
 *  - 同源静态资源：stale-while-revalidate
 *  - 跨域资源（Google Fonts / jsDelivr CDN）：cache-first
 * 更新部署时只需改 CACHE 版本号即可触发刷新。
 */
const CACHE = 'sea-watch-v1';
const CORE = [
  './',
  './index.html',
  './article.html',
  './tags.html',
  './about.html',
  './css/style.css',
  './js/app.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(CORE).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // 跨域资源（CDN / 字体）：cache-first，离线也能用
  if (url.origin !== self.location.origin) {
    if (req.mode === 'navigate') return; // 跨域导航不拦截
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        }).catch(() => cached);
      })
    );
    return;
  }

  // 页面导航：网络优先，失败回退已缓存页面
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req).then((c) => c || caches.match('./index.html')))
    );
    return;
  }

  // 文章数据：网络优先 + 缓存兜底（保证内容可更新又能离线读）
  if (url.pathname.endsWith('.json') || url.pathname.endsWith('.md')) {
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // 其他同源静态资源：stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
