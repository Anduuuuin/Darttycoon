/// <reference path="../pb_data/types.d.ts" />
// Alle 10 Minuten: Echtzeit-Nachrichten löschen, die älter als 1 Stunde sind.
cronAdd("signals_aufraeumen", "*/10 * * * *", () => {
  $app.db().newQuery("DELETE FROM signals WHERE created < strftime('%Y-%m-%d %H:%M:%fZ', 'now', '-1 hour')").execute();
});
