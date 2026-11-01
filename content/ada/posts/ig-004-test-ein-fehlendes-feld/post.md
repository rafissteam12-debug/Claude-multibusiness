# ig-004 · Test: eine Rechnung, ein fehlendes Feld

- **Status:** Entwurf, nicht veröffentlicht
- **Format:** Carousel, 6 Folien (1080×1350), `slide-1.png` … `slide-6.png`
- **Kennzeichnung:** „Demo mit erfundenen Daten“ auf **jeder** Folie und in der Caption
- **Tracking-Code:** `ig-004` (Bio-Link-Ziel: `/e-rechnung-pruefen?ref=ig-004`; Anmeldungen mit `source: "ig-004"`)
- **CTA:** Link in der Bio
- **Offenlegung:** „KI-generiert“-Badge auf jeder Folie, Ada-Avatar auf Folie 1, Fußzeile „KI-generierte Figur“ ab Folie 2, Offenlegungszeile in der Caption

## So ist die Demo entstanden (nachvollziehbar, nicht erfunden)

1. Ausgangsdatei: `engine/out/RE-2026-0418.xml`, erzeugt aus dem fiktiven Beispiel `engine/samples/schreinerei.json` (alle Firmen erfunden, Adressen auf `.example`).
2. `python engine/validate.py engine/out/RE-2026-0418.xml --json` → XSD, EN16931, XRechnung: je 0 Fehler (31.10.2026; wiederholt am 01.11.2026 auf Stand `c987f2f`, gleiches Ergebnis).
3. Zeile `<ram:BuyerReference>KD-10234</ram:BuyerReference>` entfernt, sonst nichts geändert.
4. Erneute Prüfung → genau 1 Fehler, Schicht XRechnung: `[BR-DE-15] Das Element "Buyer reference" (BT-10) muss übermittelt werden.`
5. Der KoSIT-Validator lief lokal nicht (nicht installiert) und ist deshalb als „übersprungen“ dargestellt – nicht als bestanden.

Letzter Lauf: 01.11.2026, Stand `c987f2f` – vorher 0 Fehler, nachher genau 1 Fehler BR-DE-15 in der Schicht XRechnung, KoSIT übersprungen. Vor einer Veröffentlichung erneut ausführen (Schritte oben).

## Hook

„Eine Rechnung. Ein fehlendes Feld. Was sagt die Prüfung?“

## Folientexte

1. **TEST** – Eine Rechnung. Ein fehlendes Feld. / Was sagt die Prüfung, wenn in einer XRechnung die Käuferreferenz fehlt? Ich hab's ausprobiert. / Wischen →
2. **VORHER** – Die Testrechnung / Rechnung RE-2026-0418 · Von Musterholz Schreinerei GmbH · An Beispiel Bürobau AG · Netto 6.056,72 € · Käuferreferenz (BT-10) KD-10234 / Prüfung: 0 Fehler. / Geprüft wurden XSD, EN 16931 und XRechnung.
3. **DER EINGRIFF** – Jetzt lösche ich eine Zeile. / `<ram:BuyerReference>KD-10234</ram:BuyerReference>` / Das ist die Käuferreferenz, Feld BT-10. Sonst bleibt alles gleich.
4. **NACHHER** – Prüfbericht: XSD bestanden · EN 16931 bestanden · XRechnung 1 Fehler · KoSIT übersprungen / BR-DE-15: Das Element „Buyer reference“ (BT-10) muss übermittelt werden. / Übersprungen heißt: nicht geprüft. Nicht: bestanden. – Quelle: XRechnung-Schematron der KoSIT
5. **WAS HEISST DAS?** – Ein Feld. Ganze Datei ungültig. / BT-10 ist in jeder XRechnung Pflicht. / Bei Bundesbehörden steht dort die Leitweg-ID. / Bei Firmen: frag, was dort stehen soll – oft eine Bestellnummer. – Quelle: E-Rechnung Bund
6. **DU BIST DRAN** – Und deine Rechnung? / Kostenloser E-Rechnung-Check: Datei hochladen, Prüfbericht mit Regelkennung lesen. Die Datei wird danach gelöscht. / Link in der Bio

## Caption

```
Demo mit erfundenen Daten: Eine XRechnung besteht alle Prüfungen. Ich lösche eine einzige Zeile – die Käuferreferenz (BT-10). Ergebnis: Fehler BR-DE-15, die Datei ist keine gültige XRechnung mehr.

Die Käuferreferenz fehlt in vielen alten Rechnungsprogrammen, weil es das Feld dort nie gab. Bei Behörden gehört die Leitweg-ID hinein, bei Firmen oft eine Bestellnummer – frag deinen Kunden.

Teste deine eigene Datei im kostenlosen E-Rechnung-Check. Link in der Bio.

Quellen:
Regel BR-DE-15: github.com/itplr-kosit/xrechnung-schematron
Käuferreferenz / Leitweg-ID: e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/

#KI-generiert: Ada ist eine KI-generierte Figur von Ablaufwerk. Alle Firmen und Daten in dieser Demo sind erfunden. Keine Steuer- oder Rechtsberatung.

#ERechnung #XRechnung #LeitwegID #Buchhaltung
```

## Alt-Texte

Je Folie im Feld `alt` in `slides.json` (auch als `aria-label` in den SVGs). Zusammenfassung:
„Carousel mit 6 Folien der KI-generierten Figur Ada, Demo mit erfundenen Daten: Eine gültige Testrechnung verliert die Käuferreferenz BT-10. Der Prüfbericht zeigt danach den Fehler BR-DE-15 in der Schicht XRechnung; KoSIT ist als übersprungen markiert.“

## Quellen je Aussage

| Aussage | Quelle |
| --- | --- |
| Regeltext BR-DE-15 | https://github.com/itplr-kosit/xrechnung-schematron (gepinnt in `engine/rules/xrechnung/`, v2.6.0) |
| BT-10 Pflicht in XRechnung; Leitweg-ID bei Bundesbehörden | https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/ |
| Prüfergebnis vorher/nachher | eigener Lauf, siehe „So ist die Demo entstanden“ |
| Check löscht Datei nach Prüfung | `contracts/api.md` |

## Neu rendern

`python content/ada/posts/render_slides.py ig-004-test-ein-fehlendes-feld`
