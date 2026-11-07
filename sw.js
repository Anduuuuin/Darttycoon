// Bullseye Boss Service Worker v3: Spiel zuerst online laden, offline aus dem Zwischenspeicher.
// Online-Datenbank (eigener Server) wird NIE zwischengespeichert.
const CACHE='dt-cache-v5';
const CORE=['./','./index.html','./manifest.json','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==location.origin){
    return; // alles andere (z. B. Online-Server) geht direkt ins Netz
  }
  e.respondWith(fetch(req,{cache:'no-store'}).then(res=>{if(res.ok){const cp=res.clone();caches.open(CACHE).then(c=>c.put(req,cp))}return res}).catch(()=>caches.match(req).then(r=>r||caches.match('./index.html'))));
});
