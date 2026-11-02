// Offline support for the installed app (https only). Pages and data: network first, then the last
// copy. Photos, images and fonts: the cached copy, refreshed in the background. The API is never cached.
const V = "elk-v3";
const SHELL = ["./", "index.html", "data/cuts.json", "data/field.json", "manifest.webmanifest", "img/elk.webp", "img/elk-mask.png", "img/keepawake.mp4", "img/icon-192.png"];

self.addEventListener("install", e => e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));

const networkFirst = async req => {
  const c = await caches.open(V);
  try { const res = await fetch(req); if (res.ok) c.put(req, res.clone()); return res }
  catch { return (await c.match(req, { ignoreSearch: true })) || (req.mode === "navigate" && c.match("index.html")) || Response.error() }
};
const cacheFirst = async (req, e) => {
  const c = await caches.open(V), hit = await c.match(req);
  const fresh = fetch(req).then(res => { if (res.ok || res.type === "opaque") c.put(req, res.clone()); return res }).catch(() => hit);
  if (hit) { e.waitUntil(fresh); return hit }
  return fresh;
};

self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.pathname.startsWith("/api/")) return;
  if (req.mode === "navigate" || /\.(json|csv|html|webmanifest)$/.test(url.pathname)) return e.respondWith(networkFirst(req));
  if (url.origin !== location.origin && !/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) return;
  e.respondWith(cacheFirst(req, e));
});
