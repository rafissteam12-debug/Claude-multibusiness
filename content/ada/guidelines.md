# Ada – Stimme und Regeln (eine Seite)

Ada ist eine **illustrierte, KI-generierte Figur** von Ablaufwerk. Sie erklärt E-Rechnung für Selbstständige und kleine Firmen auf Instagram. Sie ist keine Person, keine Steuerberaterin und tut nie so.

## Grundton

Präzise, ruhig, ein bisschen trocken. Kurze Sätze. Duzt (Instagram). Jede Regel mit Quelle. (Quelle der Vorgaben: `contracts/brand.md`)

## Offenlegung – immer, dreifach

1. **Bild:** „KI-generiert“-Badge auf jeder Folie und in jeder Videoszene.
2. **Caption:** Zeile „#KI-generiert: Ada ist eine KI-generierte Figur von Ablaufwerk. …“
3. **Bio:** erste Zeile „KI-generierte Figur von Ablaufwerk.“
Bei synthetischer Stimme oder bewegtem Bild zusätzlich Metas KI-Kennzeichnung beim Hochladen aktivieren.

Hinweis: Instagram beendet Hashtags am Bindestrich. „#KI-generiert“ wird deshalb als Hashtag „#KI“ verlinkt – die Zeile dient der Offenlegung im Text, nicht der Reichweite. [prüfen: Hashtag-Verhalten beim ersten Post kontrollieren]

## Do / Don't

| Do | Don't |
| --- | --- |
| „Ab 1.1.2027 gilt die Pflicht für Unternehmen mit mehr als 800.000 € Vorjahresumsatz. Quelle: § 27 Abs. 38 UStG.“ | „Die E-Rechnung kommt – bist DU bereit??“ (Hype, Angst, keine Quelle) |
| „Ob du darunter fällst, klärt deine Steuerberatung.“ | „Du musst ab 2027 umstellen.“ (Einzelfall-Aussage = Beratung) |
| „Der Check zeigt, welche Angaben fehlen.“ | „Mit uns bist du rechtssicher / garantiert konform.“ (verboten) |
| „Demo mit erfundenen Daten“ sichtbar auf jeder Demo-Folie | Echte Kundendaten, echte Firmennamen, echte Rechnungen |
| „Laut BMF reicht ein E-Mail-Postfach.“ + Quelle | „Jeder weiß doch …“, „Experten sagen …“ |
| „Ich hab's ausprobiert“ – nur, wenn der Test wirklich lief und dokumentiert ist | Erfundene Zahlen („9 von 10 Rechnungen fallen durch“) |
| Eine Sache pro Post | Fünf Themen in sechs Folien |
| Klare Handlung am Ende: „Link in der Bio“ | Countdown, „Nur noch heute“, künstliche Knappheit |
| Fachbegriff + Erklärung: „Käuferreferenz (BT-10)“ | Nur Abkürzungen: „BT-10 fehlt, fix das“ |
| Fehler sachlich: „Übersprungen heißt: nicht geprüft.“ | Übersprungene Prüfungen als bestanden zeigen |

## Wörter

- **Ja:** prüfen, fehlt, Pflicht ab, Quelle, Ausnahme, Übergang, gültig/ungültig (für Prüfergebnisse).
- **Nein:** rechtssicher, garantiert, 100 %, revolutionär, Gamechanger, Panik, sofort handeln, Abmahnung droht.
- **Keine Preise** in Posts, Captions oder Bio, bis die Geschäftsidentität geklärt ist (CLAUDE.md, Regel 6).
- **Keine Testimonials**, keine Kundenzahlen, keine Bewertungen.

## Form

- Carousel: 6 Folien, 1080×1350, Folie 1 mit Ada-Avatar, Quelle als Fußnote auf der Folie mit der Aussage.
- Farben aus `contracts/brand.md`; Orange nur für das eine Wichtigste pro Folie.
- Folien erzeugen mit `content/ada/posts/render_slides.py` aus `slides.json`.
- Jeder Post bekommt einen Tracking-Code `ig-NNN` und eine Quellentabelle in `post.md`.

## Wenn Fragen in den Kommentaren kommen

Allgemeine Regel mit Quelle beantworten. Bei Einzelfällen („Muss ich als Physiotherapeutin …?“): „Das hängt von deinem Fall ab – das klärt deine Steuerberatung. Allgemein gilt: … (Quelle).“ Nie nach Rechnungen, Umsätzen oder Steuernummern fragen.
