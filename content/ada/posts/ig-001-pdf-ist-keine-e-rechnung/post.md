# ig-001 · PDF ist keine E-Rechnung

- **Status:** Entwurf, nicht veröffentlicht
- **Format:** Carousel, 6 Folien (1080×1350), `slide-1.png` … `slide-6.png`
- **Tracking-Code:** `ig-001` (Bio-Link-Ziel: `/e-rechnung-pruefen?ref=ig-001`; Anmeldungen mit `source: "ig-001"`)
- **CTA:** Link in der Bio
- **Offenlegung:** „KI-generiert“-Badge auf jeder Folie, Ada-Avatar auf Folie 1, Fußzeile „KI-generierte Figur“ ab Folie 2, Offenlegungszeile in der Caption

## Hook

„Dein PDF ist keine E-Rechnung. Auch wenn es per E-Mail kommt.“

## Folientexte

1. **E-RECHNUNG** – Dein PDF ist keine E-Rechnung. / Auch wenn es per E-Mail kommt. Warum – in 6 Folien, mit Quellen. / Wischen →
2. **DAS GESETZ** – Entscheidend ist: strukturiert. / § 14 UStG: Eine E-Rechnung wird „in einem strukturierten elektronischen Format ausgestellt, übermittelt und empfangen“ und ermöglicht eine elektronische Verarbeitung. / Ein PDF oder Papier nennt das Gesetz „sonstige Rechnung“. – Quelle: § 14 Abs. 1 UStG
3. **DER UNTERSCHIED** – PDF ist für Menschen. E-Rechnung für Software. / Im PDF: „Rechnungsnr.: 2026-104“ / In der E-Rechnung (XML): `<ram:ID>2026-104</ram:ID>` / Jedes Feld hat eine feste Bedeutung. Kein Programm muss raten, welche Zahl die Umsatzsteuer ist.
4. **UND ZUGFeRD?** – Sieht aus wie ein PDF. Enthält eine XML. / Für die Umsatzsteuer zählt der XML-Teil. / Weichen Bild und Daten ab, gelten die Daten. / Die Profile MINIMUM und BASIC-WL reichen nicht. – Quelle: BMF-Schreiben 15.10.2024, Rn. 25, 30, 31
5. **ACHTUNG** – Von außen siehst du es nicht. / Ein ZUGFeRD-PDF und ein normales PDF sehen im Viewer gleich aus. / Erst eine Prüfung zeigt, ob strukturierte Daten drin sind – und ob sie den Regeln entsprechen.
6. **SELBST PRÜFEN** – Prüf deine Datei. / Kostenloser E-Rechnung-Check: XML- oder ZUGFeRD-Datei hochladen, Prüfbericht lesen. Die Datei wird danach gelöscht. / Link in der Bio

## Caption

```
Dein PDF ist keine E-Rechnung – auch nicht, wenn es per E-Mail kommt.

Das Umsatzsteuergesetz verlangt für eine E-Rechnung ein strukturiertes Format, das Software lesen kann. Ein PDF ist für Menschen gemacht. ZUGFeRD sieht aus wie ein PDF, trägt aber die Rechnungsdaten als XML in sich – und die zählen.

Ob deine Datei strukturierte Daten enthält, siehst du von außen nicht. Der kostenlose E-Rechnung-Check zeigt es dir. Link in der Bio.

Quellen:
§ 14 UStG: gesetze-im-internet.de/ustg_1980/__14.html
BMF-Schreiben 15.10.2024 (PDF bei der IHK): ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf

#KI-generiert: Ada ist eine KI-generierte Figur von Ablaufwerk. Keine Steuer- oder Rechtsberatung.

#ERechnung #ZUGFeRD #XRechnung #Selbstständig #Buchhaltung
```

## Alt-Texte

Je Folie im Feld `alt` in `slides.json` (auch als `aria-label` in den SVGs). Zusammenfassung für den Post:
„Carousel mit 6 Folien der KI-generierten Figur Ada: Ein PDF ist keine E-Rechnung. Laut § 14 UStG braucht eine E-Rechnung ein strukturiertes Format. ZUGFeRD ist ein PDF mit eingebetteter XML. Von außen sieht man den Unterschied nicht; ein kostenloser Check zeigt ihn.“

## Quellen je Aussage

| Aussage | Quelle |
| --- | --- |
| Definition E-Rechnung / sonstige Rechnung | https://www.gesetze-im-internet.de/ustg_1980/__14.html |
| PDF ohne strukturierte Daten = sonstige Rechnung | BMF-Schreiben 15.10.2024, Rn. 7 – https://www.ihk.de/blueprint/servlet/resource/blob/6287096/b75ea97a08683f14991b4315c44fee1c/bmf-schreiben-15-10-2024-e-rechnung-data.pdf |
| ZUGFeRD = PDF/A-3 mit XML | https://www.ferd-net.de/standards/zugferd |
| XML-Teil führend; MINIMUM/BASIC-WL reichen nicht | BMF-Schreiben 15.10.2024, Rn. 25, 30, 31 (Link oben) |
| Check löscht Datei nach Prüfung | `contracts/api.md` (POST /api/v1/check: „file discarded after the call“) |

## Neu rendern

`python content/ada/posts/render_slides.py ig-001-pdf-ist-keine-e-rechnung`
