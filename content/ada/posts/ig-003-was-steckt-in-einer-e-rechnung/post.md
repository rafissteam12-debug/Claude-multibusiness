# ig-003 · Was steckt in einer E-Rechnung?

- **Status:** Entwurf, nicht veröffentlicht
- **Format:** Reel, ca. 40 Sekunden, 9:16 (1080×1920)
- **Tracking-Code:** `ig-003` (Bio-Link-Ziel: `/e-rechnung-pruefen?ref=ig-003`; Anmeldungen mit `source: "ig-003"`)
- **CTA:** Link in der Bio
- **Offenlegung:**
  - „KI-generiert“-Badge oben links in **jeder** Szene (Stil wie Carousel-Badge).
  - Ada erscheint nur als die bestehende Illustration (`content/ada/ada-avatar-plain.svg`), animiert höchstens mit einfachen Bewegungen (Einblenden, leichtes Wippen). Keine fotorealistische Darstellung.
  - Wird eine synthetische Stimme verwendet: beim Hochladen Instagrams KI-Kennzeichnung einschalten (Hilfebereich, englische Fassung: „Label as made with AI“; Quelle: https://help.instagram.com/761121959519495) und in der Caption nennen. Ohne Stimme: nur Bildschirmtext plus lizenzfreie Musik.
- **Visuals:** Hintergrund Off-White `#F7F5F0`, Text Teal `#0F4C5C`, eine Akzentfarbe Orange `#B4410B` nur für die gerade erklärte Feldnummer. Feldnummern in Mono-Schrift.

## Hook (0–3 s)

Bildschirmtext groß: **„Was steht eigentlich in einer E-Rechnung?“**
Darunter klein: „Spoiler: nicht nur, was du im PDF siehst.“

## Skript

| Zeit | Bild | Bildschirmtext | Sprechtext (optional, Ada) |
| --- | --- | --- | --- |
| 0–3 s | Ada-Illustration links, Text rechts | Was steht eigentlich in einer E-Rechnung? | Was steht eigentlich in einer E-Rechnung? |
| 3–8 s | XML-Ausschnitt scrollt langsam, unscharf | Eine Datei. Jedes Feld hat eine Nummer. | Eine E-Rechnung ist eine Datei, in der jedes Feld eine feste Nummer hat. |
| 8–13 s | Feldkarte 1 | **BT-1** Rechnungsnummer · **BT-2** Rechnungsdatum | Rechnungsnummer und Datum – wie immer. |
| 13–19 s | Feldkarte 2 | **BT-31 / BT-32** USt-IdNr. oder Steuernummer · Name, Anschrift, Ansprechpartner | Deine Steuernummer oder USt-IdNr. muss als Datenfeld drin sein, nicht nur im Briefkopf. |
| 19–25 s | Feldkarte 3 (Akzent) | **BT-10** Käuferreferenz – in jeder XRechnung Pflicht. Bei Behörden: Leitweg-ID. | Neu für viele: die Käuferreferenz. In der XRechnung ist sie Pflicht. Bei Behörden steht dort die Leitweg-ID. |
| 25–30 s | Feldkarte 4 | **BT-49** elektronische Adresse des Kunden · seit XRechnung 3.0.1 Pflicht | Und die elektronische Adresse deines Kunden. |
| 30–35 s | Feldkarte 5 | Positionen · Summen netto, Steuer, brutto · Zahlungsbedingungen | Dazu Positionen, Summen und Zahlungsbedingungen. Die Summen müssen auf den Cent aufgehen. |
| 35–40 s | Ada + CTA-Karte | Fehlt was in deiner Rechnung? Kostenloser E-Rechnung-Check – Link in der Bio | Ob in deiner Rechnung etwas fehlt, zeigt dir der kostenlose Check. Link in der Bio. |

Fußzeile in jeder Szene: „Ada · Ablaufwerk – Keine Steuer- oder Rechtsberatung.“

## Caption

```
Was steht in einer E-Rechnung? Mehr, als viele alte Rechnungsprogramme exportieren.

Neben Rechnungsnummer, Datum und Beträgen braucht eine XRechnung zum Beispiel:
– die Käuferreferenz (BT-10), bei Behörden die Leitweg-ID
– die elektronische Adresse deines Kunden (BT-49)
– deine USt-IdNr. oder Steuernummer als Datenfeld
– Zahlungsbedingungen oder ein Fälligkeitsdatum

Was in deiner Datei fehlt, zeigt der kostenlose E-Rechnung-Check. Link in der Bio.

Quellen:
§ 14 Abs. 4 UStG: gesetze-im-internet.de/ustg_1980/__14.html
Käuferreferenz: e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/
XRechnung 3.0.1 (BT-34/BT-49): e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/
Regeltexte: github.com/itplr-kosit/xrechnung-schematron

#KI-generiert: Ada ist eine KI-generierte Figur von Ablaufwerk. [Bei synthetischer Stimme ergänzen: „Stimme KI-generiert.“] Keine Steuer- oder Rechtsberatung.

#ERechnung #XRechnung #Buchhaltung #Selbstständig
```

## Alt-Text / Untertitel

Reels haben keinen Alt-Text-Dialog wie Carousels; die Untertitel (= Bildschirmtext + Sprechtext oben) werden als Untertitel-Spur eingebrannt oder als automatische Untertitel geprüft.
Kurzbeschreibung für Barrierefreiheit (in Caption-Ende oder als Accessibility-Text, falls verfügbar): „Kurzvideo mit der KI-generierten, illustrierten Figur Ada. Erklärt die Felder einer E-Rechnung: Rechnungsnummer, Datum, Steuernummer, Käuferreferenz BT-10, elektronische Adresse BT-49, Positionen, Summen und Zahlungsbedingungen.“

## Quellen je Aussage

| Aussage | Quelle |
| --- | --- |
| Pflichtangaben einer Rechnung (Nummer, Datum, Steuernummer/USt-IdNr., Beträge) | https://www.gesetze-im-internet.de/ustg_1980/__14.html |
| BT-10 Pflicht in XRechnung (BR-DE-15) | https://github.com/itplr-kosit/xrechnung-schematron |
| BT-10 = Leitweg-ID bei Bundesbehörden | https://e-rechnung-bund.de/en/faq/what-is-a-buyer-reference/ |
| BT-34/BT-49 seit XRechnung 3.0.1 Pflicht | https://e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/ |
| Summen: BR-CO-15 | https://github.com/ConnectingEurope/eInvoicing-EN16931 |
| Zahlungsbedingungen oder Fälligkeitsdatum: BR-CO-25 | https://docs.peppol.eu/poacc/billing/3.0/rules/ubl-tc434/BR-CO-25/ |
| Alle Pflichtangaben im strukturierten Teil | https://www.ihk.de/koeln/hauptnavigation/recht-steuern/steuern/bmf-schreiben-zur-e-rechnung-vom-15-10-2025-6774012 |

## Produktion (offen)

Kein Video gerendert. Benötigt: Feldkarten im Carousel-Stil (Renderer `render_slides.py` kann auf 1080×1920 erweitert werden), Schnitt, ggf. Stimme. Siehe `docs/progress/content.md`.
