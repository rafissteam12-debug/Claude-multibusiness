---
title: "So prüfen Sie die Spaltenzuordnung"
slug: "spaltenzuordnung-pruefen"
last_checked: "2026-11-01"
---

# So prüfen Sie die Spaltenzuordnung

Nach dem Hochladen schlägt Belegbrücke vor, welche Spalte Ihrer Datei zu welchem Feld der E-Rechnung gehört. Dieser Vorschlag ist ein **Vorschlag**. Sie prüfen und bestätigen ihn.

## Was Sie sehen

Für jedes Feld der E-Rechnung zeigt die Seite:

- **Feld** – zum Beispiel „Rechnungsnummer“ oder „Nettopreis je Einheit“.
- **Quelle** – die Spalte aus Ihrer Datei oder ein **fester Wert** (zum Beispiel „EM“ für E-Mail als Adressart).
- **Konfidenz** – wie sicher sich Belegbrücke ist: hoch, mittel oder niedrig.
- **Begründung** – warum diese Spalte gewählt wurde, zum Beispiel „Spaltenname enthält ‚Rechnung‘ und ‚Nr‘“.
- **Umwandlung** – falls nötig, etwa „deutsche Dezimalzahl“ oder „Datum TT.MM.JJJJ“.

## Konfidenz richtig lesen

| Konfidenz | Bedeutung | Was Sie tun |
| --- | --- | --- |
| hoch (ab 80 %) | Spaltenname und Werte passen eindeutig | kurz ansehen |
| mittel (50 bis unter 80 %) | plausibel, aber nicht eindeutig | Beispielwerte prüfen |
| niedrig (unter 50 %) oder leer | unsicher oder nichts gefunden | selbst zuordnen |

Auch eine hohe Konfidenz heißt nicht, dass der Vorschlag stimmt. Ein häufiger Fall: zwei Spalten „Betrag“ und „Betrag netto“. Schauen Sie bei allen Beträgen in die Beispielwerte.

Steht oben „Vorschlag ohne KI“, kam der Vorschlag nur aus festen Regeln (Spaltennamen und Wertmuster). Das ist normal, wenn die KI-Funktion nicht verfügbar ist.

## Korrigieren

1. Klicken Sie beim Feld auf die Quelle.
2. Wählen Sie die richtige Spalte – oder **Fester Wert**, wenn die Angabe für alle Rechnungen gleich ist (zum Beispiel ein Steuersatz von 19 %, wenn Ihre Datei keine Steuerspalte hat).
3. Prüfen Sie die Vorschau der ersten Zeilen.

Besonders genau hinsehen sollten Sie bei:

- **Netto oder brutto?** Enthält die Spalte Bruttopreise, wählen Sie die Umwandlung „brutto zu netto“.
- **Steuersatz** – 19, 7 oder 0 %. Bei 0 % brauchen Sie eine Steuerkategorie und einen Befreiungsgrund. Welche das ist, klärt Ihre Steuerberatung.
- **Einheit** – „Stk“, „Std“, „Pauschal“ werden in Codes der Norm übersetzt.
- **Gutschriften** – negative Beträge werden als Gutschrift erkannt.
- **Aufbau** – eine Zeile pro Rechnung oder eine Zeile pro Position, gruppiert nach Rechnungsnummer.

Ihre eigenen Unternehmensdaten (Verkäufer) werden nie aus der Datei zugeordnet. Sie kommen immer aus Ihrem Profil.

## Speichern

Klicken Sie auf **Zuordnung speichern**. Beim nächsten Export mit denselben Spaltennamen wird die Zuordnung wiederverwendet.

Gespeichert werden nur Spaltennamen, feste Werte und Umwandlungen – **keine Inhalte aus Ihren Zellen**.

## Danach

Starten Sie die Umwandlung. Zeilen, die sich nicht umwandeln lassen, erscheinen mit Zeilennummer und Grund, zum Beispiel „Zeile 14: Datum nicht lesbar“.

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*
