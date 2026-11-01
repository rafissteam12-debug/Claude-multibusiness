---
title: "Pflichtfelder der E-Rechnung, die in alten Rechnungsprogrammen oft fehlen"
description: "Käuferreferenz (BT-10), elektronische Adresse, Steuernummer oder USt-IdNr., Zahlungsbedingungen: Diese Angaben fehlen oft. So füllen Sie sie."
slug: "pflichtfelder-e-rechnung"
sources:
  - title: "§ 14 UStG – Ausstellung von Rechnungen, Abs. 4 (gesetze-im-internet.de)"
    url: "https://www.gesetze-im-internet.de/ustg_1980/__14.html"
  - title: "KoSIT: XRechnung-Schematron (Geschäftsregeln BR-DE-*)"
    url: "https://github.com/itplr-kosit/xrechnung-schematron"
  - title: "CEN/ConnectingEurope: EN 16931 Validierungsartefakte (Geschäftsregeln BR-*)"
    url: "https://github.com/ConnectingEurope/eInvoicing-EN16931"
  - title: "Peppol BIS Billing 3.0: Regel BR-CO-25"
    url: "https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-25/"
  - title: "E-Rechnung Bund: What is a buyer reference?"
    url: "https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/"
  - title: "E-Rechnung Bund: New version XRechnung 3.0.1"
    url: "https://e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/"
  - title: "§ 5 E-Rechnungsverordnung (ERechV)"
    url: "https://www.gesetze-im-internet.de/erechv/__5.html"
  - title: "IHK Köln: BMF-Schreiben zur E-Rechnung vom 15.10.2025"
    url: "https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012"
last_checked: "2026-11-01"
---

# Pflichtfelder der E-Rechnung, die in alten Rechnungsprogrammen oft fehlen

Eine Rechnung, die als PDF völlig in Ordnung ist, kann als E-Rechnung durchfallen. Der Grund: Eine E-Rechnung wird nicht von einem Menschen gelesen, sondern von einer Software gegen feste Regeln geprüft. Fehlt ein Feld, das der Standard verlangt, meldet die Prüfung einen Fehler – auch wenn die Angabe „irgendwo“ auf dem PDF steht.

Die Regeln haben Kennungen wie **BR-DE-15** oder **BR-CO-25**. „BR“ steht für Business Rule. Regeln mit „DE“ kommen aus dem deutschen Standard XRechnung, die anderen aus der europäischen Norm EN 16931. Die Felder selbst haben Nummern wie **BT-10** (Business Term). Die Regeltexte unten stammen aus den offiziellen Prüfdateien. (Quellen: [KoSIT XRechnung-Schematron](https://github.com/itplr-kosit/xrechnung-schematron), [EN 16931 Validierungsartefakte](https://github.com/ConnectingEurope/eInvoicing-EN16931))

## Die Grundlage: Pflichtangaben nach § 14 Abs. 4 UStG

Die umsatzsteuerlichen Pflichtangaben haben sich mit der E-Rechnung nicht geändert. Dazu gehören unter anderem vollständiger Name und Anschrift von Leistendem und Empfänger, Steuernummer oder USt-IdNr. des Leistenden, Ausstellungsdatum, fortlaufende Rechnungsnummer, Menge und Art der Leistung, Leistungsdatum, Entgelt nach Steuersätzen sowie Steuersatz und Steuerbetrag. (Quelle: [§ 14 Abs. 4 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html))

Neu ist: Nach dem BMF-Schreiben vom 15.10.2025 müssen alle Pflichtangaben im **strukturierten Datensatz** stehen – nicht nur im PDF-Bild. (Quelle: [IHK Köln](https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012))

Die folgenden vier Angaben fehlen in Exporten älterer Programme besonders oft.

## 1. Käuferreferenz (BT-10)

**Regel BR-DE-15:** „Das Element ‚Buyer reference‘ (BT-10) muss übermittelt werden.“

In einer XRechnung ist die Käuferreferenz Pflicht. Bei Rechnungen an Bundesbehörden steht hier die **Leitweg-ID**, über die die Rechnung beim richtigen Empfänger ankommt. (Quelle: [E-Rechnung Bund](https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/); [§ 5 ERechV](https://www.gesetze-im-internet.de/erechv/__5.html))

**Warum sie fehlt:** Ältere Programme kennen kein solches Feld. Bei Geschäftskunden gab es nie einen Grund, eines anzulegen.

**Was Sie tun können:**
- Bei Behörden: Die Leitweg-ID gibt Ihnen der Auftraggeber. Erfinden Sie keine.
- Bei Unternehmen: Fragen Sie, was dort stehen soll – oft eine Bestellnummer, ein Ansprechpartner oder eine Kostenstelle.
- Macht Ihr Kunde keine Vorgabe, stimmen Sie mit ihm ab, welcher Wert dort stehen soll – zum Beispiel Ihre Kundennummer bei ihm.
- Hinweis: BR-DE-15 ist eine Regel des deutschen Standards XRechnung. Für ZUGFeRD im Profil EN 16931 wird sie nicht geprüft – Ihr Kunde kann die Angabe trotzdem verlangen.

## 2. Elektronische Adresse von Verkäufer und Käufer (BT-34, BT-49)

Seit XRechnung 3.0.1 (gilt seit 1. Februar 2024) sind die elektronischen Adressen von Verkäufer (BT-34) und Käufer (BT-49) Pflicht. Für E-Mail-Adressen wird das Schema „EM“ angegeben, für eine Leitweg-ID „0204“. (Quelle: [E-Rechnung Bund](https://e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/))

**Regeln BR-62 / BR-63:** Die elektronische Adresse des Verkäufers bzw. Käufers muss eine Schema-Kennung haben.

**Warum sie fehlt:** In vielen Kundenstammdaten steht nur eine Postanschrift oder eine allgemeine Kontakt-E-Mail.

**Was Sie tun können:** Fragen Sie Ihre Kunden nach der Adresse, an die E-Rechnungen gehen sollen, und hinterlegen Sie sie getrennt von der Ansprechpartner-E-Mail.

Verwandt sind die deutschen Kontaktregeln **BR-DE-2, BR-DE-5, BR-DE-6, BR-DE-7**: Eine XRechnung muss einen Ansprechpartner des Verkäufers mit Name, Telefonnummer und E-Mail-Adresse enthalten.

## 3. Steuernummer oder USt-IdNr. des Verkäufers

**Regel BR-CO-26:** Damit der Käufer den Lieferanten automatisch erkennen kann, muss mindestens eine Kennung des Verkäufers vorhanden sein: Verkäuferkennung (BT-29), Registernummer (BT-30) und/oder USt-IdNr. (BT-31).

**Regel BR-DE-16:** Werden bestimmte Steuerkategorien verwendet (zum Beispiel S für den Regelsteuersatz), muss mindestens die USt-IdNr. (BT-31) oder die Steuernummer (BT-32) übermittelt werden.

**Warum sie fehlt:** Auf dem PDF steht die Steuernummer oft im Fußbereich als Teil des Briefpapiers. Im Datenexport des Programms ist sie dann gar nicht enthalten.

**Was Sie tun können:** Hinterlegen Sie Steuernummer und – falls vorhanden – USt-IdNr. einmal in Ihren Unternehmensdaten. In Belegbrücke gehören sie ins Verkäuferprofil und werden in jede Rechnung übernommen.

## 4. Zahlungsbedingungen und Zahlungsangaben

**Regel BR-CO-25:** Ist der fällige Betrag positiv, muss entweder ein Fälligkeitsdatum (BT-9) oder ein Text zu den Zahlungsbedingungen (BT-20) angegeben sein. (Quelle: [Peppol BIS Billing 3.0, BR-CO-25](https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-25/))

**Regel BR-DE-1:** Eine XRechnung muss Zahlungsanweisungen (BG-16) enthalten, zum Beispiel die Zahlungsart Überweisung mit IBAN.

**Warum sie fehlen:** „Zahlbar innerhalb von 14 Tagen“ steht oft als fester Text auf der Vorlage, nicht als Datenfeld. Die Bankverbindung steht im Briefkopf.

**Was Sie tun können:** Legen Sie Ihre Standard-Zahlungsbedingung und Bankverbindung als feste Werte an. Abweichungen pro Kunde (zum Beispiel 30 Tage) gehören in die Kundendaten.

## Ein Rechenfehler, der oft auffällt

**Regel BR-CO-15:** Rechnungsbetrag mit Umsatzsteuer (BT-112) = Rechnungsbetrag ohne Umsatzsteuer (BT-109) + Umsatzsteuerbetrag (BT-110).

Das klingt selbstverständlich. In Exporten entstehen aber Rundungsdifferenzen, etwa wenn die Steuer pro Position gerundet und dann addiert wird. Eine Abweichung von einem Cent reicht für einen Fehler. Belegbrücke berechnet die Summen deshalb aus den Positionen neu und zeigt Abweichungen zu Ihren Exportwerten an.

## Checkliste für Ihre Stammdaten

- [ ] Steuernummer und/oder USt-IdNr. Ihres Unternehmens
- [ ] Ansprechpartner mit Telefon und E-Mail
- [ ] Ihre elektronische Adresse für E-Rechnungen
- [ ] Bankverbindung und Standard-Zahlungsbedingung
- [ ] Pro Kunde: elektronische Adresse, Käuferreferenz/Leitweg-ID, gewünschtes Format

---

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*

Welche dieser Felder fehlen in Ihren Rechnungen? Der kostenlose [E-Rechnung-Check](/e-rechnung-pruefen) zeigt es Ihnen für eine einzelne XML- oder ZUGFeRD-Datei – mit Regelkennung und Erklärung.
