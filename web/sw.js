// Работа без интернета: оболочка приложения из кэша, тиражи — сначала из сети.
const SHELL = "lotto-shell-v2";
const FILES = ["./", "index.html", "lotto.js", "i18n.js", "manifest.webmanifest", "icon-180.png", "icon-192.png"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== SHELL && k !== "lotto-data").map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  // Всё своё — сначала из сети (чтобы обновления приходили сразу), без сети — из кэша.
  e.respondWith(fetch(e.request).then((r) => {
    const copy = r.clone();
    caches.open(url.pathname.endsWith("data.json") ? "lotto-data" : SHELL)
      .then((c) => c.put(e.request.url.split("?")[0], copy));
    return r;
  }).catch(() => caches.match(e.request.url.split("?")[0])));
});
