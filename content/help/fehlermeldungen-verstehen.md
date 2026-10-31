---
title: "Fehlermeldungen verstehen"
slug: "fehlermeldungen-verstehen"
sources:
  - title: "KoSIT: XRechnung-Schematron (BR-DE-*)"
    url: "https://github.com/itplr-kosit/xrechnung-schematron"
  - title: "CEN/ConnectingEurope: EN 16931 Validierungsartefakte (BR-CO-*)"
    url: "https://github.com/ConnectingEurope/eInvoicing-EN16931"
  - title: "Peppol BIS Billing 3.0: BR-CO-25"
    url: "https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-25/"
  - title: "E-Rechnung Bund: What is a buyer reference?"
    url: "https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/"
last_checked: "2026-10-31"
---

# Fehlermeldungen verstehen

Belegbrücke prüft jede erzeugte Datei, bevor Sie sie herunterladen. Nur Dateien ohne Fehler werden als E-Rechnung angeboten. Diese Seite erklärt, was die Meldungen bedeuten.

## Zwei Arten von Meldungen

**Zeilenfehler** entstehen beim Lesen Ihrer Datei, bevor eine E-Rechnung gebaut wird. Sie nennen Zeile und Spalte:

| Code | Bedeutung |
| --- | --- |
| `missing_required` | Eine Pflichtangabe fehlt in dieser Zeile. |
| `bad_number` | Ein Betrag ist keine lesbare Zahl. |
| `bad_date` | Ein Datum ist nicht lesbar. |
| `unknown_unit` | Die Einheit ist unbekannt (z. B. „Kart.“). |
| `inconsistent_invoice` | Zeilen mit derselben Rechnungsnummer haben unterschiedliche Kopfdaten (z. B. zwei Kunden). |
| `negative_amount` | Negativer Betrag, der nicht als Gutschrift erkannt wurde. |
| `buyer_address_missing` | Die Anschrift des Kunden fehlt. |

**Prüffehler** entstehen bei der Validierung der fertigen Datei. Sie haben eine Regelkennung wie `BR-DE-15`.

## Prüfschichten

| Schicht | Prüft |
| --- | --- |
| XSD | technischen Aufbau der Datei |
| EN 16931 | Regeln der europäischen Norm (`BR-…`, `BR-CO-…`) |
| XRechnung | deutsche Zusatzregeln (`BR-DE-…`) |
| KoSIT | offizieller Validator der KoSIT |

Eine Schicht kann **übersprungen** sein, zum Beispiel wenn der KoSIT-Validator in einer Testumgebung nicht verfügbar ist. Übersprungen wird immer mit Grund angezeigt und zählt nie als bestanden.

## Die häufigsten Regeln, einfach erklärt

### BR-DE-15 – Käuferreferenz fehlt

Regeltext: „Das Element ‚Buyer reference‘ (BT-10) muss übermittelt werden.“

**Bedeutet:** In einer XRechnung muss das Feld Käuferreferenz gefüllt sein. Bei Bundesbehörden ist das die Leitweg-ID. (Quelle: [E-Rechnung Bund](https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/))

**So beheben Sie es:** Ordnen Sie in der Spaltenzuordnung eine Spalte mit der Käuferreferenz zu oder setzen Sie einen festen Wert. Die Leitweg-ID bekommen Sie von Ihrem Auftraggeber. Bei Geschäftskunden fragen Sie, was dort stehen soll (oft eine Bestellnummer).

### BR-CO-25 – Fälligkeit oder Zahlungsbedingungen fehlen

Regeltext (übersetzt): Ist der zu zahlende Betrag positiv, muss ein Fälligkeitsdatum (BT-9) oder ein Text zu den Zahlungsbedingungen (BT-20) vorhanden sein. (Quelle: [Peppol BIS 3.0](https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-25/))

**So beheben Sie es:** Hinterlegen Sie eine Standard-Zahlungsbedingung im Profil (z. B. „Zahlbar innerhalb von 14 Tagen ohne Abzug“) oder ordnen Sie eine Spalte „fällig am“ zu.

### BR-CO-26 – keine Kennung des Verkäufers

Regeltext (übersetzt): Damit der Käufer den Lieferanten automatisch erkennen kann, muss die Verkäuferkennung (BT-29), die Registernummer (BT-30) und/oder die USt-IdNr. (BT-31) vorhanden sein.

**So beheben Sie es:** Tragen Sie in Ihrem Profil Ihre USt-IdNr. oder Handelsregisternummer ein. Eine Steuernummer allein erfüllt diese Regel nicht. [prüfen: Umgang bei Unternehmen ohne USt-IdNr. und ohne Registereintrag mit Engine-Stand abgleichen]

### BR-CO-15 – Summen passen nicht

Regeltext (übersetzt): Rechnungsbetrag mit Umsatzsteuer (BT-112) = Rechnungsbetrag ohne Umsatzsteuer (BT-109) + Umsatzsteuerbetrag (BT-110).

**So beheben Sie es:** Meist ist es eine Rundungsdifferenz. Belegbrücke rechnet die Summen aus den Positionen neu. Weicht das Ergebnis von den Summen in Ihrem Export ab, sehen Sie beide Werte. Prüfen Sie, welcher stimmt, und korrigieren Sie gegebenenfalls Ihre Quelldaten.

## Weitere Regeln, die oft vorkommen

- **BR-DE-2, BR-DE-5, BR-DE-6, BR-DE-7** – Ansprechpartner des Verkäufers mit Name, Telefon und E-Mail fehlt. → Profil ergänzen.
- **BR-DE-1** – Zahlungsanweisungen fehlen (z. B. IBAN). → Bankverbindung im Profil ergänzen.
- **BR-DE-16** – weder USt-IdNr. noch Steuernummer angegeben. → Profil ergänzen.
- **BR-63** – elektronische Adresse des Käufers ohne Adressart. → Adressart zuordnen (meist „EM“ für E-Mail).

Die Regeltexte stammen aus den offiziellen Prüfdateien. (Quellen: [KoSIT](https://github.com/itplr-kosit/xrechnung-schematron), [EN 16931](https://github.com/ConnectingEurope/eInvoicing-EN16931))

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*
