# Bullseye Boss – Online-Server (PocketBase)

Die Online-Funktionen laufen auf `https://dart.anduuuuin.de` (PocketBase).

- `pb_migrations/` legt beim Start automatisch alle Tabellen an (scores, ghosts, duels, leagues, league_members, league_results, profiles, signals).
- `pb_hooks/aufraeumen.pb.js` löscht alle 10 Minuten Live-Duell-Nachrichten, die älter als 1 Stunde sind.

Auf dem Server liegen die Dateien unter `/opt/pb/dart/pb_migrations` und `/opt/pb/dart/pb_hooks`.
Nach einer Änderung: `systemctl restart pocketbase@dart`.
