---
title: "XRechnung oder ZUGFeRD – Unterschiede und was Ihr Kunde braucht"
description: "XRechnung ist reines XML, ZUGFeRD ein PDF mit eingebetteten Daten. Beide können E-Rechnungen sein. So finden Sie das richtige Format für Ihren Kunden."
slug: "xrechnung-oder-zugferd"
sources:
  - title: "KoSIT / xeinkauf.de: XRechnung"
    url: "https://xeinkauf.de/xrechnung/"
  - title: "xeinkauf.de: XRechnung – Versionen und Bundles"
    url: "https://xeinkauf.de/xrechnung/versionen-und-bundles/"
  - title: "FeRD: ZUGFeRD"
    url: "https://www.ferd-net.de/standards/zugferd"
  - title: "FNFE-MPE: Factur-X / ZUGFeRD"
    url: "https://fnfe-mpe.org/factur-x/factur-x_en/"
  - title: "BMF-Schreiben vom 15.10.2024 zur E-Rechnung (bereitgestellt von der IHK)"
    url: "https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf"
  - title: "§ 4 E-Rechnungsverordnung (ERechV)"
    url: "https://www.gesetze-im-internet.de/erechv/__4.html"
  - title: "§ 5 E-Rechnungsverordnung (ERechV)"
    url: "https://www.gesetze-im-internet.de/erechv/__5.html"
  - title: "E-Rechnung Bund: What is a buyer reference?"
    url: "https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/"
  - title: "E-Rechnung Bund: New version XRechnung 3.0.1"
    url: "https://e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/"
last_checked: "2026-10-31"
---

# XRechnung oder ZUGFeRD – Unterschiede und was Ihr Kunde braucht

Wer sich mit der E-Rechnung beschäftigt, stößt schnell auf zwei Namen: **XRechnung** und **ZUGFeRD**. Beide setzen dieselbe europäische Norm um, die EN 16931. Sie unterscheiden sich vor allem darin, wie die Rechnung beim Empfänger ankommt – und wer welches Format verlangt.

## XRechnung: reines XML

XRechnung ist der deutsche Standard für elektronische Rechnungen an öffentliche Auftraggeber. Er baut auf der EN 16931 auf und wird von der Koordinierungsstelle für IT-Standards (KoSIT) im Auftrag des IT-Planungsrats betrieben. Eine XRechnung kann in zwei Syntaxen erstellt werden: **UBL** und **UN/CEFACT CII**. (Quelle: [xeinkauf.de](https://xeinkauf.de/xrechnung/))

Aktuell ist die Version **3.0** (Bundle 3.0.2). Laut KoSIT gab es im Sommer 2026 kein normatives Release; XRechnung 3.0 bleibt daher mindestens bis zum 31.07.2027 in Kraft. Eine Vorversion von XRechnung 4.0 wurde im September 2026 veröffentlicht. (Quelle: [xeinkauf.de](https://xeinkauf.de/xrechnung/), [Versionen und Bundles](https://xeinkauf.de/xrechnung/versionen-und-bundles/))

Eine XRechnung ist **nur** eine XML-Datei. Es gibt kein mitgeliefertes Rechnungsbild. Der Empfänger braucht eine Software oder einen Viewer, um sie lesbar anzuzeigen.

XRechnung ergänzt die Norm um deutsche Regeln. Einige Felder, die in der EN 16931 optional sind, werden Pflicht. Beispiele:

- **Käuferreferenz (BT-10):** Bei Rechnungen an Bundesbehörden steht hier die **Leitweg-ID**; sie ist Pflichtbestandteil jeder XRechnung. (Quelle: [E-Rechnung Bund](https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/))
- **Elektronische Adressen von Verkäufer und Käufer (BT-34, BT-49):** seit Version 3.0 verpflichtend. (Quelle: [E-Rechnung Bund](https://e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/))
- **Kontaktdaten des Verkäufers** (Name, Telefon, E-Mail) und **Zahlungsangaben**.

## ZUGFeRD: PDF mit eingebetteten Daten

ZUGFeRD ist ein **hybrides** Format: Ein PDF/A-3-Dokument enthält zusätzlich die strukturierten Rechnungsdaten als XML. Seit ZUGFeRD 2.0 wird dafür die Syntax CII verwendet. (Quelle: [FeRD](https://www.ferd-net.de/standards/zugferd)) Technisch ist ZUGFeRD identisch mit dem französischen **Factur-X**. (Quelle: [FNFE-MPE](https://fnfe-mpe.org/factur-x/factur-x_en/))

Der Vorteil: Menschen öffnen die Datei wie jedes PDF. Programme lesen die eingebettete XML. Für die Umsatzsteuer gilt aber der XML-Teil als führend (BMF-Schreiben 15.10.2024, Rn. 31, [PDF](https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf)).

ZUGFeRD hat mehrere **Profile** mit unterschiedlichem Umfang, unter anderem MINIMUM, BASIC WL, BASIC, EN16931 und EXTENDED. (Quelle: [FNFE-MPE](https://fnfe-mpe.org/factur-x/factur-x_en/)) Die Profile **MINIMUM** und **BASIC-WL** genügen nicht für eine E-Rechnung im Sinne des UStG (BMF-Schreiben 15.10.2024, Rn. 25 und 30).

## Der Vergleich

| | XRechnung | ZUGFeRD (ab Profil BASIC) |
| --- | --- | --- |
| Was Sie verschicken | XML-Datei | PDF/A-3 mit eingebetteter XML |
| Für Menschen lesbar ohne Software | nein | ja |
| Grundlage | EN 16931 + deutsche Zusatzregeln | EN 16931 (je nach Profil) |
| Typischer Einsatz | Rechnungen an öffentliche Auftraggeber, zunehmend B2B | B2B, besonders wenn der Empfänger noch manuell bucht |
| Im B2B als E-Rechnung nach UStG | ja | ja, außer MINIMUM und BASIC-WL |

(Quellen: [xeinkauf.de](https://xeinkauf.de/xrechnung/), [FeRD](https://www.ferd-net.de/standards/zugferd), BMF-Schreiben 15.10.2024, Rn. 25, 30, 31)

## Was Ihr Kunde braucht

**Öffentliche Auftraggeber des Bundes:** Die E-Rechnungsverordnung sieht grundsätzlich den Standard XRechnung in der jeweils aktuellen Fassung vor; ein anderer Standard ist möglich, wenn er der europäischen Norm entspricht. (Quelle: [§ 4 ERechV](https://www.gesetze-im-internet.de/erechv/__4.html)) Zusätzlich verlangt § 5 ERechV unter anderem eine **Leitweg-Identifikationsnummer**, Bankverbindung, Zahlungsbedingungen und eine E-Mail-Adresse des Rechnungsstellers. (Quelle: [§ 5 ERechV](https://www.gesetze-im-internet.de/erechv/__5.html)) Bundesländer und Kommunen haben eigene Regeln. [prüfen: Landesregelungen im Einzelfall]

**Geschäftskunden (B2B):** Das Gesetz schreibt kein bestimmtes Format vor, solange es der EN 16931 entspricht. Format und Übermittlungsweg vereinbaren Sie mit Ihrem Kunden (BMF-Schreiben 15.10.2024, Rn. 36). In der Praxis heißt das: **Fragen Sie nach.** Manche Kunden bevorzugen XRechnung, weil ihre Software sie direkt verarbeitet. Andere möchten ZUGFeRD, weil sie die Rechnung auch ansehen wollen.

**Private Endkunden:** Für Rechnungen an Privatpersonen gilt die E-Rechnungspflicht nicht (BMF-Schreiben 15.10.2024, Rn. 1, 8, 19).

## Drei Fragen an Ihren Kunden

1. **Welches Format?** XRechnung (UBL oder CII) oder ZUGFeRD – und welches Profil?
2. **Welche Käuferreferenz?** Behörden geben eine Leitweg-ID vor. Manche Unternehmen erwarten eine Bestellnummer oder Kostenstelle im Feld BT-10.
3. **Welcher Weg?** E-Mail, Upload in ein Portal oder Peppol?

Die Antworten gehören in Ihre Kundenstammdaten. Dann muss niemand bei jeder Rechnung neu fragen.

## Was Belegbrücke erzeugt

Belegbrücke erzeugt XRechnung 3.0 in der Syntax CII. ZUGFeRD im Profil EN 16931 ist geplant; ob es in der ersten Version verfügbar ist, steht noch nicht fest. [prüfen: Status ZUGFeRD vor Veröffentlichung mit Engine-Stand abgleichen] Jede Datei wird vor dem Download validiert. Nur gültige Dateien werden als E-Rechnung angeboten.

---

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*

Sie haben eine XRechnung oder ZUGFeRD-Datei bekommen oder selbst erstellt? Prüfen Sie sie kostenlos mit dem [E-Rechnung-Check](/e-rechnung-pruefen).
