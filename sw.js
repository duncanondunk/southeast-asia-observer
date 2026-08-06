/**
 * Service Worker cleanup — 临时禁用缓存，清理旧版本
 * 原因：Vercel 主站在大陆访问不稳定，旧 SW 的缓存优先/网络优先策略
 * 导致部分用户浏览器长期滞留旧页面，出现导航、样式与最新代码不一致。
 * 本 SW 安装后立即删除全部缓存并注销自身，所有请求直接走网络。
 */
self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { return caches.delete(k); }));
    }).then(function () {
      return self.clients.claim();
    }).then(function () {
      return self.clients.matchAll({ type: 'window' }).then(function (clients) {
        clients.forEach(function (c) { c.navigate(c.url); });
      });
    })
  );
});

self.addEventListener('fetch', function () {
  // 不拦截任何请求：彻底放弃 SW 缓存，避免再困住用户
});
