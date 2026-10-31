---
title: "Welche Dateien kann ich hochladen?"
slug: "dateien-hochladen"
last_checked: "2026-10-31"
---

# Welche Dateien kann ich hochladen?

Belegbrücke liest den **Rechnungsexport** Ihres bisherigen Programms oder Ihre Excel-Liste und macht daraus E-Rechnungen.

## Erlaubte Formate

| Format | Hinweise |
| --- | --- |
| **CSV** (`.csv`) | Trennzeichen Semikolon `;`, Komma `,` oder Tabulator. Zeichensatz UTF-8 oder Windows-1252 (typisch für ältere deutsche Programme). Belegbrücke erkennt beides automatisch. |
| **Excel** (`.xlsx`) | Es wird das **erste Tabellenblatt** gelesen. Die Kopfzeile wird automatisch gesucht, auch wenn darüber ein Titel steht. |

- Maximale Dateigröße: **10 MB**.
- Nicht unterstützt: das alte Excel-Format `.xls`, `.ods`, PDF-Rechnungen, Bilder, ZIP-Dateien. Speichern Sie eine `.xls`-Datei in Excel bitte als `.xlsx` oder CSV.

## Wie die Tabelle aussehen sollte

- **Eine Kopfzeile** mit Spaltennamen, zum Beispiel `Rechnungsnr.`, `Datum`, `Kunde`, `Netto`, `USt-Satz`.
- Darunter die Daten. Leere Zeilen und Summenzeilen am Ende stören meist nicht, besser ist ein Export ohne sie.
- Deutsche Zahlen (`1.234,56`) und Datumsangaben (`31.10.2026`) sind in Ordnung.

Zwei Aufbauten werden erkannt:

1. **Eine Zeile pro Rechnung** – jede Rechnung hat eine Zeile mit Gesamtbetrag.
2. **Eine Zeile pro Rechnungsposition** – mehrere Zeilen mit derselben Rechnungsnummer gehören zu einer Rechnung.

Belegbrücke schlägt den Aufbau vor; Sie können ihn in der Spaltenzuordnung ändern.

## Was nicht in der Datei stehen muss

Ihre **eigenen Unternehmensdaten** (Name, Anschrift, Steuernummer oder USt-IdNr., Bankverbindung, Ansprechpartner) kommen aus Ihrem Verkäuferprofil, nicht aus der Datei. Legen Sie das Profil einmal unter **Profil** an.

## Was in der Datei stehen sollte

Mindestens: Rechnungsnummer, Rechnungsdatum, Name und Anschrift des Kunden, Leistung, Betrag und Steuersatz. Für XRechnung zusätzlich die **Käuferreferenz** (z. B. Leitweg-ID) und die **elektronische Adresse** des Kunden – wenn diese fehlen, können Sie in der Zuordnung einen festen Wert setzen.

## Datenschutz

Die hochgeladene Datei wird nach der Umwandlung gelöscht, spätestens nach 24 Stunden. Details: „Was mit Ihren Daten passiert“.

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*
