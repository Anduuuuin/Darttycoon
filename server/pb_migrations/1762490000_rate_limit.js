/// <reference path="../pb_data/types.d.ts" />
// Schutz vor Missbrauch: begrenzt, wie viele Anfragen eine IP-Adresse pro Minute schicken darf.
// Großzügig gewählt, weil sich im Mobilfunk viele Spieler eine IP-Adresse teilen können.
migrate((app) => {
  const s = app.settings();
  // Caddy steht davor: echte Spieler-IP aus dem Header X-Forwarded-For lesen (sonst wären alle Spieler "eine" IP)
  s.trustedProxy.headers = ["X-Forwarded-For"];
  s.trustedProxy.useLeftmostIP = false;
  s.rateLimits.enabled = true;
  s.rateLimits.rules = [
    { label: "/api/",           maxRequests: 600, duration: 60, audience: "" }, // alles zusammen: 600 pro Minute
    { label: "*:create",        maxRequests: 60,  duration: 60, audience: "" }, // neue Einträge (Ergebnisse, Ligen …): 60 pro Minute
    { label: "signals:create",  maxRequests: 400, duration: 60, audience: "" }, // Live-Duell-Nachrichten: 400 pro Minute
    { label: "*:auth",          maxRequests: 10,  duration: 60, audience: "" }, // Admin-Login: 10 Versuche pro Minute
  ];
  app.save(s);
}, (app) => {
  const s = app.settings();
  s.rateLimits.enabled = false;
  app.save(s);
});
