# Content agent – progress

## 2026-10-31 · Wave 1 content drafts (branch `agent/content`)

All texts are **drafts**. Nothing published, nothing sent, no accounts created.

### Files
- `content/guides/` – 5 guides (German, "Sie", 750–880 words, front matter per brief):
  `e-rechnungspflicht-2027-2028.md`, `pdf-ist-keine-e-rechnung.md`, `xrechnung-oder-zugferd.md`,
  `pflichtfelder-e-rechnung.md`, `e-rechnung-aus-excel-oder-alter-software.md`.
  Each ends with the brand.md scope line verbatim and a CTA to `/e-rechnung-pruefen`.
- `content/emails/` – `01-double-opt-in.md`, `02-magic-link.md`, `03-welcome-1-pruefbericht.md`,
  `04-welcome-2-belegbruecke.md`, shared `_footer.md` ([[BUSINESS_ID_PENDING]] + scope line), `README.md` (placeholders).
- `content/help/` – `dateien-hochladen.md`, `spaltenzuordnung-pruefen.md`, `fehlermeldungen-verstehen.md`
  (BR-DE-15, BR-CO-25, BR-CO-26, BR-CO-15 + row error codes), `ihre-daten.md` (retention per api.md, AI value shapes),
  `limits-kostenloser-plan.md` (3 valid invoices/month, no prices).
- `content/ada/posts/` – ig-001..ig-004 (`post.md` each; ig-001/002/004 carousels with `slides.json`,
  `slide-1..6.svg` + `.png`, 1080×1350; ig-003 reel script). `render_slides.py` renders all carousels.
- `content/ada/bio.md`, `content/ada/guidelines.md`.
- `content/requirements.txt` (cairosvg, Pillow – tooling only), `content/tests/test_content_files.py` (10 static checks).

### How to run
- Render slides: `pip install -r content/requirements.txt && python content/ada/posts/render_slides.py`
- Tests: `python -m pytest --import-mode=importlib -q content/tests` (not yet in `testpaths`, see request).

### Sources used (all opened 2026-10-31)
| Source | Used in |
| --- | --- |
| § 14 UStG – gesetze-im-internet.de/ustg_1980/__14.html | G1–G5, ig-001/002/003 |
| § 27 Abs. 38 UStG – gesetze-im-internet.de/ustg_1980/__27.html | G1, G2, G5, ig-002 |
| §§ 33, 34, 34a UStDV – gesetze-im-internet.de/ustdv_1980/ | G1, ig-002 |
| §§ 4, 5 ERechV – gesetze-im-internet.de/erechv/ | G3, G4 |
| BMF-Schreiben 15.10.2024 (PDF hosted by IHK) | G1, G2, G3, G5, ig-001/002 |
| IHK Köln on BMF-Schreiben 15.10.2025 | G1, G2, G4, G5 |
| IHK Hannover on second BMF letter (read, not cited) | background |
| IHK Lüneburg-Wolfsburg „E-Rechnung umsetzen“ | G1, G2, G5 |
| xeinkauf.de XRechnung + Versionen/Bundles (KoSIT) | G3, G5 |
| e-rechnung-bund.de: buyer reference FAQ; XRechnung 3.0.1 news | G3, G4, help, ig-003/004 |
| ferd-net.de ZUGFeRD; fnfe-mpe.org Factur-X | G2, G3 |
| Peppol BIS 3.0 rule BR-CO-25 | G4, help, ig-003 |
| KoSIT xrechnung-schematron + CEN EN16931 artefacts (pinned in `engine/rules/`) | G4, help, ig-004 |
| Bundesagentur für Arbeit: OZG-RE | G5 |
(G1 = Pflicht 2027/2028, G2 = PDF, G3 = XRechnung/ZUGFeRD, G4 = Pflichtfelder, G5 = drei Wege.) 17 distinct URLs.

### Unverified points ([prüfen] in the texts)
- G1: Randnummern refer to the BMF letter of 15.10.2024; the 15.10.2025 letter may renumber. bundesfinanzministerium.de
  blocks automated fetching (robots), so the BMF original was read only via the IHK-hosted 2024 PDF and IHK summaries of 2025.
- G2: individual format agreements (§ 14 Abs. 1 Satz 6 Nr. 2 UStG) – case by case.
- G3: Länder/Kommunen rules for B2G; ZUGFeRD availability in Belegbrücke v1 (engine spike).
- G4: using the customer number as BT-10 fallback – to agree with customers.
- G5: which federal bodies use OZG-RE.
- Help: confidence thresholds; behaviour at the free-plan limit; upload rate limits; BR-CO-26 for sellers with only a
  Steuernummer (rule text lists BT-29/30/31, not BT-32); privacy policy link and processors.
- E-mail 01: "no disclosure to third parties" sentence vs. Datenschutzerklärung.
- Ada: Meta AI label name; hashtag behaviour of "#KI-generiert"; Impressum duty for the Instagram profile.
- ig-004: rerun the demo with the final engine before posting.

### Open issues
- **BR-CO-25 missing from pinned CEN rules:** `engine/rules/cen/EN16931-CII-validation.xslt` contains no BR-CO-25 (checked by grep).
  Texts explain the rule from the Peppol BIS 3.0 page. Engine owner should confirm (request filed).
- `content/tests` not in `pyproject.toml` `testpaths` (request filed).
- E-mails need an unsubscribe endpoint and `{{ unsubscribe_url }}`; not in `contracts/api.md` (request filed).
- ig-003 reel: script only, no video produced.
- Fonts: slides rendered with Inter (IBM Plex Sans not installed in sandbox); re-render once Plex is available.
- `content/carousels/02-wen-trifft-2027/slide-1.svg` is superseded by `content/ada/posts/ig-002-wer-muss-ab-2027/`; left in place.
