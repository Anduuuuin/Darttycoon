/// <reference path="../pb_data/types.d.ts" />
// Legt alle Tabellen für die Online-Funktionen von Bullseye Boss an (einmalig, beim Start von PocketBase).
migrate((app) => {
  const open = { listRule: "", viewRule: "", createRule: "", updateRule: null, deleteRule: null };
  const T = (name) => ({ name, type: "text", max: 5000 });
  const N = (name) => ({ name, type: "number" });
  const J = (name) => ({ name, type: "json", maxSize: 2000000 });
  const created = { name: "created", type: "autodate", onCreate: true, onUpdate: false };
  const tables = [
    { name: "scores", fields: [T("game"), T("name"), T("club"), N("value"), T("day")],
      indexes: ["CREATE INDEX idx_scores_game_day ON scores (game, day)"] },
    { name: "ghosts", fields: [T("code"), T("name"), T("club"), J("data")],
      indexes: ["CREATE INDEX idx_ghosts_code ON ghosts (code)"] },
    { name: "duels", fields: [T("code"), T("challenger"), { name: "won", type: "bool" }, T("result")],
      indexes: ["CREATE INDEX idx_duels_code ON duels (code)"] },
    { name: "leagues", fields: [T("code"), T("name"), T("owner"), N("season")], updateRule: "",
      indexes: ["CREATE UNIQUE INDEX idx_leagues_code ON leagues (code)"] },
    { name: "league_members", fields: [T("league"), T("mk"), T("club"), T("manager"), J("team")],
      indexes: ["CREATE INDEX idx_lm_league ON league_members (league)"] },
    { name: "league_results", fields: [T("league"), N("season"), T("home"), T("away"), N("hw"), N("aw"), T("detail")],
      indexes: ["CREATE INDEX idx_lr_league ON league_results (league)"] },
    { name: "profiles", fields: [T("code"), T("name"), T("club"), J("stats"), T("updated_at")], updateRule: "",
      indexes: ["CREATE UNIQUE INDEX idx_profiles_code ON profiles (code)"] },
    // Echtzeit-Nachrichten (Live-Duell, Einladungen). Werden stündlich aufgeräumt.
    { name: "signals", fields: [T("topic"), T("event"), J("payload")],
      indexes: ["CREATE INDEX idx_signals_topic ON signals (topic)"] },
  ];
  for (const t of tables) {
    try { app.findCollectionByNameOrId(t.name); continue; } catch (e) {}
    const c = new Collection(Object.assign({ type: "base" }, open, {
      name: t.name,
      updateRule: t.updateRule === undefined ? null : t.updateRule,
      fields: t.fields.concat([created]),
      indexes: t.indexes,
    }));
    app.save(c);
  }
}, (app) => {
  for (const n of ["scores", "ghosts", "duels", "leagues", "league_members", "league_results", "profiles", "signals"]) {
    try { app.delete(app.findCollectionByNameOrId(n)); } catch (e) {}
  }
});
