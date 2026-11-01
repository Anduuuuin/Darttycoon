# Bullseye Boss: Weg in den Google Play Store

## Einmalig einrichten
1. GitHub: Repo → Settings → Secrets and variables → Actions → New repository secret
   - `KEYSTORE_PASSPHRASE` = das Passwort für den Upload-Schlüssel (steht im Chat, sicher aufbewahren)
   - später: `ADMOB_APP_ID` = deine echte AdMob-App-ID (bis dahin werden Test-Anzeigen genutzt)
2. Datenschutz-Seite: `https://anduuuuin.github.io/darttycoon/privacy.html` (vorher Name, Adresse und E-Mail in `privacy.html` eintragen)

## App bauen
Repo → Actions → „Android-App bauen“ → Run workflow. Nach ein paar Minuten gibt es unter „Artifacts“ die Datei `BullseyeBoss.aab`.

## Google Play Console
1. Entwickler-Konto anlegen (einmalig 25 $).
2. App erstellen, Name „Bullseye Boss“, Sprache Deutsch, Spiel, kostenlos.
3. Testing → Geschlossener Test → neuen Release mit der `.aab` anlegen, Tester-Liste (mind. 12 E-Mail-Adressen) hinzufügen, Test-Link an die Tester schicken.
4. 14 Tage warten (Tester müssen dabei bleiben). Danach „Produktionszugriff beantragen“.
5. Store-Eintrag ausfüllen: Beschreibung, Screenshots, Icon 512×512, Feature-Grafik 1024×500, Datenschutz-Link, Datensicherheit (Werbung + Online-Daten angeben), Inhaltsbewertung, Werbung = „Ja“.
6. Bei „App-Signatur durch Google Play“ zustimmen (Standard).

## Werbung scharf schalten
AdMob-Konto anlegen, App „Bullseye Boss“ hinzufügen, Rewarded-Anzeigenblock erstellen. Dann die App-ID als Secret `ADMOB_APP_ID` eintragen und die Anzeigenblock-ID in `index.html` (`EN.unit`) ersetzen.
