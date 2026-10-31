---
title: "Was mit Ihren Daten passiert"
slug: "ihre-daten"
last_checked: "2026-10-31"
---

# Was mit Ihren Daten passiert

Rechnungsdaten sind vertraulich. Belegbrücke speichert so wenig wie möglich und so kurz wie möglich.

## Löschfristen

| Was | Wann gelöscht |
| --- | --- |
| **Hochgeladene Datei** (CSV/XLSX) | sobald die Umwandlung erfolgreich war – spätestens nach **24 Stunden** |
| **Erzeugte Dateien** (XRechnung, ZUGFeRD, Prüfbericht) | nach **24 Stunden** |
| **Fehlermeldungen eines Umwandlungsauftrags** (können Zellinhalte enthalten) | nach **24 Stunden** |
| **Gespeicherte Spaltenzuordnung** | bleibt, bis Sie sie löschen – sie enthält nur Spaltennamen, feste Werte und Umwandlungen, **keine Zellinhalte** |
| **Ihr Verkäuferprofil** | bleibt, solange Ihr Konto besteht |
| **Datei im kostenlosen E-Rechnung-Check** | direkt nach der Prüfung, sie wird nicht gespeichert |

**Laden Sie Ihre E-Rechnungen innerhalb von 24 Stunden herunter.** Danach ist der Download-Link nicht mehr gültig, und der Auftrag wird als „abgelaufen“ angezeigt. Die Aufbewahrung Ihrer Rechnungen ist Ihre Aufgabe; Belegbrücke ist kein Archiv.

## Was die KI sieht

Belegbrücke kann einen KI-Dienst nutzen, um die Spaltenzuordnung vorzuschlagen. Standardmäßig bekommt die KI **keine echten Werte**, sondern:

- Ihre **Spaltennamen** und
- die **Form** der Werte aus höchstens einigen Beispielzeilen. Buchstaben werden zu `X`/`x`, Ziffern zu `d`, Satzzeichen bleiben stehen.

Beispiele:

| Echter Wert | Was die KI sieht |
| --- | --- |
| `Müller GmbH` | `Xxxxxx XxxX` |
| `31.10.2026` | `dd.dd.dddd` |
| `1.234,56` | `d.ddd,dd` |

Nur wenn Sie die Einstellung **„Echte Beispielwerte senden“** einschalten, werden echte Werte aus den Beispielzeilen übermittelt. Das kann die Zuordnung bei ungewöhnlichen Spaltennamen verbessern. Die Einstellung ist standardmäßig aus.

Ist die KI nicht verfügbar, schlägt Belegbrücke die Zuordnung mit festen Regeln vor („Vorschlag ohne KI“). Dabei verlässt nichts den Server.

## Was wir nicht tun

- Wir schreiben keine Rechnungsinhalte in Protokolldateien.
- Wir protokollieren keine KI-Anfragen mit Werten.
- Wir speichern keine IP-Adressen im Klartext.
- Anmeldelinks werden nur als Hash gespeichert, nie im Klartext, gelten 15 Minuten und nur einmal.

## Wer Belegbrücke betreibt

[[BUSINESS_ID_PENDING]]

Details zur Verarbeitung, zu Dienstleistern und zu Ihren Rechten finden Sie in der Datenschutzerklärung. [prüfen: Link und Auftragsverarbeiter (Hosting, E-Mail, KI-Anbieter) nach Klärung der Geschäftsidentität ergänzen]

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*
