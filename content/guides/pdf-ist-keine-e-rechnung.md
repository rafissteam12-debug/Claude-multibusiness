---
title: "Warum ein PDF keine E-Rechnung ist"
description: "Ein PDF per E-Mail ist rechtlich eine „sonstige Rechnung“. Was eine E-Rechnung ausmacht, was hybride Formate sind und was das für Sie heißt."
slug: "pdf-ist-keine-e-rechnung"
sources:
  - title: "§ 14 UStG – Ausstellung von Rechnungen (gesetze-im-internet.de)"
    url: "https://www.gesetze-im-internet.de/ustg_1980/__14.html"
  - title: "§ 27 UStG – Übergangsvorschriften, Abs. 38 (gesetze-im-internet.de)"
    url: "https://www.gesetze-im-internet.de/ustg_1980/__27.html"
  - title: "BMF-Schreiben vom 15.10.2024 zur E-Rechnung (bereitgestellt von der IHK)"
    url: "https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf"
  - title: "IHK Köln: BMF-Schreiben zur E-Rechnung vom 15.10.2025"
    url: "https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012"
  - title: "FeRD: ZUGFeRD"
    url: "https://www.ferd-net.de/standards/zugferd"
  - title: "FNFE-MPE: Factur-X / ZUGFeRD (Profile)"
    url: "https://fnfe-mpe.org/factur-x/factur-x_en/"
  - title: "IHK Lüneburg-Wolfsburg: E-Rechnung umsetzen"
    url: "https://www.ihk.de/ihklw/online-magazin/unser-recht/e-rechnung-umsetzen-7175714"
last_checked: "2026-10-31"
---

# Warum ein PDF keine E-Rechnung ist

Viele Unternehmen verschicken ihre Rechnungen seit Jahren als PDF per E-Mail. Das fühlt sich elektronisch an. Für das Umsatzsteuergesetz ist es das aber nicht: Ein PDF ist eine **sonstige Rechnung**, keine **elektronische Rechnung**. Dieser Ratgeber erklärt den Unterschied und was er für Ihre Rechnungen bedeutet.

## Die Definition im Gesetz

§ 14 Abs. 1 UStG unterscheidet zwei Arten von Rechnungen:

- **Elektronische Rechnung:** eine Rechnung, „die in einem strukturierten elektronischen Format ausgestellt, übermittelt und empfangen wird und eine elektronische Verarbeitung ermöglicht“.
- **Sonstige Rechnung:** eine Rechnung, „die in einem anderen elektronischen Format oder auf Papier übermittelt wird“.

Außerdem muss das strukturierte Format der europäischen Norm EN 16931 entsprechen oder – wenn beide Seiten das vereinbaren – sich richtig und vollständig in ein solches Format übertragen lassen. (Quelle: [§ 14 Abs. 1 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html))

Das Schlüsselwort ist **strukturiert**. Ein PDF zeigt Text und Zahlen für Menschen an. Ein Programm kann daraus nicht verlässlich ablesen, welche Zahl der Nettobetrag ist und welche die Umsatzsteuer. Eine E-Rechnung dagegen ist ein Datensatz, in dem jedes Feld eine feste Bedeutung hat.

Das BMF-Schreiben vom 15.10.2024 sagt es ausdrücklich: Ein PDF ohne integrierte strukturierte Daten ist eine sonstige Rechnung (Rn. 7, [PDF bei der IHK](https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf)). Die IHK Köln fasst das neue BMF-Schreiben vom 15.10.2025 so zusammen: „Ein einfaches PDF-Dokument, das per E-Mail versendet wird, erfüllt diese Voraussetzung nicht mehr.“ (Quelle: [IHK Köln](https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012))

## Wie eine E-Rechnung aussieht

Eine E-Rechnung ist im Kern eine XML-Datei. Darin steht zum Beispiel nicht einfach „Rechnungsnummer: 2026-104“, sondern ein Element mit fester Bedeutung, das in der Norm einen Namen und eine Nummer hat – etwa „Invoice number“ (BT-1). Die Buchhaltungssoftware Ihres Kunden kann die Rechnung damit automatisch einlesen und prüfen.

Öffnet man so eine Datei im Editor, sieht sie für Menschen unhandlich aus. Das ist normal. Zum Lesen gibt es Visualisierungen; die IHK Lüneburg-Wolfsburg weist zum Beispiel auf ein kostenloses Visualisierungstool der Finanzverwaltung im ElsterPortal hin. (Quelle: [IHKLW](https://www.ihk.de/ihklw/online-magazin/unser-recht/e-rechnung-umsetzen-7175714))

## Und ZUGFeRD? Das ist doch ein PDF.

Ja – und nein. ZUGFeRD ist ein **hybrides** Format: ein PDF/A-3-Dokument, in das strukturierte Rechnungsdaten im XML-Format eingebettet sind. (Quelle: [FeRD](https://www.ferd-net.de/standards/zugferd)) Für Menschen sieht es aus wie ein normales PDF, für Programme steckt der Datensatz darin.

Für die Umsatzsteuer zählt bei hybriden Formaten der **XML-Teil**. Weichen Bild und Daten voneinander ab, gehen die strukturierten Daten vor (BMF-Schreiben 15.10.2024, Rn. 31). Nach dem neuen BMF-Schreiben müssen alle Pflichtangaben im strukturierten Datensatz enthalten sein. (Quelle: [IHK Köln](https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012))

Nicht jede ZUGFeRD-Datei reicht: XRechnung und ZUGFeRD ab Version 2.0.1 erfüllen die Anforderungen grundsätzlich, **ausgenommen die Profile MINIMUM und BASIC-WL** (BMF-Schreiben 15.10.2024, Rn. 25 und 30). Diese beiden Profile enthalten nicht alle Angaben der Norm. (Profilbeschreibungen: [FNFE-MPE zu Factur-X/ZUGFeRD](https://fnfe-mpe.org/factur-x/factur-x_en/))

Daraus folgt eine praktische Regel: **Man sieht einer Rechnung im PDF-Viewer nicht an, ob sie eine E-Rechnung ist.** Ein ZUGFeRD-PDF und ein gewöhnliches PDF sehen gleich aus. Erst ein Blick in die eingebetteten Daten oder eine Validierung zeigt den Unterschied.

## Warum der Unterschied wichtig ist

**Für Rechnungsaussteller:** Wer zur E-Rechnung verpflichtet ist und trotzdem nur ein PDF schickt, stellt keine Rechnung im geforderten Format aus. Ab wann das für Sie gilt, hängt von den Übergangsregeln ab: Für Leistungen in 2025 und 2026 sind PDF-Rechnungen mit Zustimmung des Empfängers noch erlaubt, für 2027 nur noch bei einem Vorjahresumsatz von höchstens 800.000 Euro. (Quelle: [§ 27 Abs. 38 UStG](https://www.gesetze-im-internet.de/ustg_1980/__27.html)) Details im Ratgeber „E-Rechnungspflicht 2027/2028“.

**Für Rechnungsempfänger:** Nach der Zusammenfassung der IHK Köln liegt bei einem Formatfehler keine E-Rechnung vor, sondern eine sonstige Rechnung – mit möglichen Folgen für den Vorsteuerabzug. (Quelle: [IHK Köln](https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012)) Was das in Ihrem Fall bedeutet, klärt Ihre Steuerberatung. Sicher ist: Ihre Kunden werden zunehmend nach einer E-Rechnung fragen.

## Häufige Missverständnisse

**„Unser PDF ist doch digital signiert.“** Eine Signatur ändert nichts daran, dass die Daten unstrukturiert sind.

**„Wir hängen eine Excel-Datei an.“** Eine Tabelle ist strukturiert, aber sie entspricht nicht der EN 16931 und ist nicht als E-Rechnung vereinbart. Ob eine individuelle Vereinbarung möglich ist, regelt § 14 Abs. 1 Satz 6 Nr. 2 UStG mit strengen Voraussetzungen. [prüfen: Einzelfall mit Steuerberatung klären]

**„Das PDF hat einen QR-Code.“** Ein QR-Code für die Überweisung ist praktisch, macht aber aus dem PDF keine E-Rechnung.

**„Wir scannen eingehende Papierrechnungen ein.“** Das ist Archivierung. Aus dem Scan wird keine E-Rechnung.

## Wie Sie herausfinden, was Sie verschicken

1. Nehmen Sie eine aktuelle Rechnung aus Ihrem System.
2. Ist es nur ein PDF, ist es keine E-Rechnung. Ist es eine XML-Datei oder ein PDF mit eingebetteter XML, lohnt sich eine Prüfung.
3. Lassen Sie die Datei validieren. Ein Prüfbericht zeigt, welche Regeln der Norm und – für XRechnung – der deutschen Vorgaben eingehalten sind und welche nicht.

---

*Belegbrücke ist ein technisches Werkzeug. Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung.*

Sie möchten wissen, ob eine Datei eine gültige E-Rechnung ist? Laden Sie sie in den kostenlosen [E-Rechnung-Check](/e-rechnung-pruefen). Die Datei wird nach der Prüfung gelöscht.
