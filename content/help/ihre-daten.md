---
title: "Was mit Ihren Daten passiert"
slug: "ihre-daten"
last_checked: "2026-11-01"
---

# Was mit Ihren Daten passiert

Rechnungsdaten sind vertraulich. Belegbrücke speichert so wenig wie möglich und so kurz wie möglich.

## Löschfristen

| Was | Wann gelöscht |
| --- | --- |
| **Hochgeladene Datei** (CSV/XLSX) | sobald die Umwandlung erfolgreich war – spätestens nach **24 Stunden** |
| **Erzeugte Dateien** (XRechnung, ZUGFeRD, lesbares PDF) | nach **24 Stunden** |
| **Fehlermeldungen eines Umwandlungsauftrags** (können Zellinhalte enthalten) | nach **24 Stunden** |
| **Gespeicherte Spaltenzuordnung** | bleibt, solange Ihr Konto besteht – sie enthält Spaltennamen, Umwandlungen und die festen Werte, die Sie selbst eintragen, **keine Zellinhalte** aus Ihrer Datei |
| **Ihr Unternehmensprofil** (auch IBAN und Steuerangaben) | bleibt, solange Ihr Konto besteht |
| **Datei im kostenlosen E-Rechnung-Check** | direkt nach der Prüfung, sie wird nicht gespeichert |

**Laden Sie Ihre E-Rechnungen innerhalb von 24 Stunden herunter.** Danach ist der Download-Link nicht mehr gültig, und der Auftrag wird als „abgelaufen“ angezeigt. Die Aufbewahrung Ihrer Rechnungen ist Ihre Aufgabe; Belegbrücke ist kein Archiv.

## Was die KI sieht

Belegbrücke kann einen KI-Dienst nutzen, um die Spaltenzuordnung vorzuschlagen. Standardmäßig bekommt die KI **keine echten Werte**, sondern:

- Ihre **Spaltennamen** und
- die **Form** der Werte aus bis zu fünf Beispielzeilen. Buchstaben werden zu `X`/`x`, Ziffern zu `d`, Satzzeichen bleiben stehen.

Beispiele:

| Echter Wert | Was die KI sieht |
| --- | --- |
| `Müller GmbH` | `Xxxxxx XxxX` |
| `31.10.2026` | `dd.dd.dddd` |
| `1.234,56` | `d.ddd,dd` |

Nur wenn Sie die Einstellung **„Echte Beispielwerte an die KI senden“** einschalten, werden echte Werte aus den Beispielzeilen übermittelt. Das kann die Zuordnung bei ungewöhnlichen Spaltennamen verbessern. Die Einstellung ist standardmäßig aus.

Ist die KI eingerichtet, nutzt Belegbrücke den Dienst von Anthropic. Anthropic kann Anfragen laut seiner Dokumentation in beliebigen Regionen verarbeiten, auch außerhalb der EU. (Quelle: [Anthropic, Data residency](https://platform.claude.com/docs/en/manage-claude/data-residency))

Ist die KI nicht verfügbar, schlägt Belegbrücke die Zuordnung mit festen Regeln vor („Vorschlag ohne KI“). Dabei verlässt nichts den Server.

## Was wir nicht tun

- Wir schreiben keine Rechnungsinhalte in Protokolldateien.
- Wir protokollieren keine KI-Anfragen mit Werten.
- Wir speichern keine IP-Adressen im Klartext.
- Anmeldelinks werden nur als Hash gespeichert, nie im Klartext, gelten 15 Minuten und nur einmal.

## Konto löschen und Daten herunterladen

- **Konto löschen:** Auf der Seite **Profil** finden Sie den Knopf **„Konto löschen“**. Nach Ihrer Bestätigung werden sofort gelöscht: Ihr Konto mit E-Mail-Adresse, Ihre Anmeldungen, Ihr Unternehmensprofil, Ihre gespeicherten Zuordnungen, hochgeladene Dateien, erzeugte Dateien, Ihre Umwandlungsaufträge und die Nutzungszählung. Das lässt sich nicht rückgängig machen. Laden Sie vorher herunter, was Sie noch brauchen.
- **Daten herunterladen:** Ebenfalls auf der Seite **Profil**: **„Daten herunterladen (JSON)“** lädt Ihre Kontodaten, Ihr Unternehmensprofil, Ihre gespeicherten Zuordnungen und Ihre Nutzungszählung als JSON-Datei herunter. Hochgeladene und erzeugte Dateien sind nicht enthalten.
- **Inaktive Konten:** Haben Sie sich **12 Monate** lang nicht angemeldet, wird Ihr Konto mit allen oben genannten Daten gelöscht.

Eine Anmeldung für E-Mail-Hinweise ist davon getrennt. Von diesen E-Mails melden Sie sich über den Abmeldelink in jeder E-Mail ab. Nach einer Abmeldung bewahren wir drei Jahre lang einen Nachweis Ihrer früheren Einwilligung und der Abmeldung auf – ohne Ihre E-Mail-Adresse im Klartext, nur einen Prüfwert (HMAC), die Version des Einwilligungstextes und die Daten.

## Wer Belegbrücke betreibt

[[BUSINESS_ID_PENDING]]

Details zur Verarbeitung, zu Dienstleistern und zu Ihren Rechten finden Sie in den Datenschutzhinweisen auf unserer Website (Link „Datenschutz“ unten auf jeder Seite).

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*
