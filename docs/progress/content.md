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

### Unverified points (historical, wave 3; all resolved in wave 4 fix round, see below)
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


## Wave 4 fix round (1 Nov 2026) — review H2, H4/M12, H5, L5

All `[prüfen …]` notes are gone from content/. New test `test_no_unverified_notes_in_shipped_content`
(`content/tests/test_content_files.py`) fails if `[prüfen`/`[pruefen` appears in guides, emails, help, ada or legal.
Run: `python -m pytest -m "not network" content` (whole suite: 330 passed).

| Where | Old | New | Source (opened 1 Nov 2026) |
| --- | --- | --- | --- |
| G1 e-rechnungspflicht | "Randnummern können sich verschoben haben [prüfen]" | 2025 letter amends/extends the 2024 letter in single Rn.; new ones get letters (Rn. 6a, 35a); our Rn. refer to 15.10.2024 | kpmg.com/de/de/home/themen/2025/10/bmf-ust-e-rechnung-neu.html (added to sources); cross-checked with a copy of the 2025 letter (steuerschroeder.de PDF: "wird in folgenden Randnummern … geändert bzw. ergänzt") |
| G2 pdf-ist-keine | "§ 14 Abs. 1 Satz 6 Nr. 2 … strenge Voraussetzungen [prüfen]" | quotes the condition ("richtige und vollständige Extraktion …"), Einzelfall -> Steuerberatung | gesetze-im-internet.de/ustg_1980/__14.html |
| G3 xrechnung-oder-zugferd | "Länder und Kommunen haben eigene Regeln [prüfen]" | ERechV title: "öffentliches Auftragswesen des Bundes"; ask Länder/Kommunen for their rules | gesetze-im-internet.de/erechv/ (added) |
| G3 | "ZUGFeRD geplant, Status offen [prüfen]" | ZUGFeRD EN 16931 offered only after PDF/A-3 + XML check; without the tool the app says so and delivers XRechnung only | engine/zugferd.py, app/jobs.py |
| G3, G4, ig-003 (L5) | "seit (XRechnung) 3.0" | "seit XRechnung 3.0.1 (gilt seit 1. Februar 2024)" | e-rechnung-bund.de/en/new-version-xrechnung-standard-3-0-1-available/ |
| G4 pflichtfelder | customer number "pragmatische Lösung [prüfen]" | "stimmen Sie mit ihm ab … z. B. Ihre Kundennummer bei ihm" (no claim) | – |
| G5 excel | "unter anderem die BA … [prüfen: welche Bundeseinrichtungen]" | only the BA named; "über ein solches Eingangsportal erreicht Ihre Rechnung die Behörde" | arbeitsagentur.de/ueber-uns/e-rechnung-rechnungsstellung-ueber-ozg-re |
| Mail 01 opt-in | "Keine Weitergabe an Dritte zu Werbezwecken [prüfen]" | "nur für diese E-Mails, nicht verkauft; Versand über einen E-Mail-Dienstleister, der die Adresse in unserem Auftrag verarbeitet"; consent version now `2026-10-31-v1` | app/settings.py, contracts/api.md |
| Help limits | "Hochladen … nicht begrenzt [prüfen]"; limit behaviour [prüfen] | not counted, technical limits table (60 uploads/h, 3 parallel jobs, 500 invoices/file); over the limit: "Gültig, aber Ihr Monatslimit ist erreicht", not offered, not counted | app/main.py, app/jobs.py, app/settings.py, app request 4 |
| Help spaltenzuordnung | thresholds [prüfen]; "0 bis 100 %" | hoch ≥ 80 %, mittel 50–<80 %, niedrig < 50 %; UI shows levels | app/main.py (mapping page) |
| Help ihre-daten | processors/link [prüfen] | "Datenschutz" link on the website; new section Konto löschen / Daten exportieren / 12 months inactivity (H4, as planned); mapping kept while the account exists (no separate delete); checkbox label as in UI | app templates, review H4 |
| Help fehlermeldungen (H5) | "nur USt-IdNr./HRB [prüfen]" | BT-29/30/31, one suffices; Steuernummer is BT-32; "Verkäuferkennung (BT-29)", e.g. the Steuernummer used as identifier; agree with customer; USt-IdNr. question -> Steuerberatung. Used the UI label "Verkäuferkennung" (no hyphen) | BR-CO-26 text in engine/rules/cen/EN16931-CII-validation.xslt |
| Ada bio | Impressum duty [prüfen] | § 5 Abs. 1 DDG quoted; owner decides | gesetze-im-internet.de/ddg/__5.html |
| Ada guidelines | hashtag ends at hyphen [prüfen] | claim removed (no official source found) | – |
| ig-003 | Meta label name [prüfen] | Instagram help: toggle "Label as made with AI" | help.instagram.com/761121959519495 |
| ig-004 | rerun demo [prüfen] | rerun 1 Nov 2026 on c987f2f: before 0 errors, after 1 × BR-DE-15, KoSIT skipped | engine/generate.py + validate.py |

New: `content/legal/datenschutz-fakten.md` — factual checklist (not a legal text) of all data categories from
`app/migrations/001_init.sql`, jobs/purge, security, mailer, mapping/ai.py, Caddyfile; marks "ist" vs. "geplant" (H4, M2, M7, M12, L4, L9).
Controller = `[[BUSINESS_ID_PENDING]]`. For the website agent's privacy page.

### Notes for the owner (instead of [prüfen] in texts)
- Instagram profile: decide how the Anbieterkennzeichnung (§ 5 DDG) is shown before creating the account.
- Check at the first post whether "#KI-generiert" is linked as a hashtag (irrelevant for disclosure) and the German name of the AI label toggle.
- Rerun ig-004 before posting.
- Brevo: conclude the DPA before `MAILER=brevo` — the opt-in mail says the provider processes "in unserem Auftrag".
- Seat/contracting entity of Anthropic, Brevo, Cloudflare and hoster: take from the contracts. Their legal pages
  (anthropic.com/legal/privacy, brevo.com/legal/termsofuse) could not be opened from the sandbox (permission prompt timed out); the checklist
  states "USA" for Anthropic and Cloudflare as known fact, flagged for verification.
- Help "ihre-daten" describes account deletion/export and the 12-month rule as planned (H4); keep in sync with the app fix.
- If M7 lands (keep the raw upload when no valid file was produced), help/legal texts already say "nach erfolgreicher Umwandlung, spätestens 24 h".
- The site build and the mail/help loaders should also fail on `[prüfen` (H2; site and app owners).

## Legal pre-review follow-up (1 Nov 2026)
- New `content/legal/avv-entwurf.md`: Art. 28 AVV draft (Ablaufwerk as processor for uploaded invoice data) with TOMs annex
  (only measures found in app/ops) and sub-processor list (host, Anthropic only with AI enabled, Brevo/Cloudflare without invoice data).
  Marked "Entwurf – vor Verwendung anwaltlich prüfen"; DSGVO article references unverified (EUR-Lex text cut before the articles).
- PRE_REVIEW 6.5: removed "reply 'abmelden'" from mail 01 and "reply to this e-mail" (no support process) from mail 04.
- PRE_REVIEW 10.6/2.14/2.5: help "ihre-daten" — HMAC is a "pseudonymisierter Prüfwert"; Anthropic Ireland as contracting entity, PBC (USA).
- datenschutz-fakten: Anthropic/Cloudflare/Brevo DPA facts and owner acceptance, three consent-proof deletion cases, HMAC key note,
  Cloudflare retention open, new open items (legal bases, roles, Art. 30 record, breach process).

## Remediation release (1 Nov 2026)
- **P0-3** `content/legal/agb-entwurf.md`: full B2B AGB draft, version `agb-draft-2` (scope/B2B-only § 14 BGB, formation,
  services + verbatim scope line, plans with `[[BUSINESS_ID_PENDING]]` prices, meaning of "gültig", customer duties,
  AVV/retention as in `contracts/api.md`, AI mapping, no SLA, liability (marked "Formulierung anwaltlich prüfen"),
  term/termination, deletion/export, versioned changes, law/jurisdiction placeholders). Norms checked on
  gesetze-im-internet.de: §§ 14, 276 Abs. 3, 307, 309 Nr. 7, 310 Abs. 1 BGB, § 14 ProdHaftG, § 14b UStG.
  Unverified and marked: § 312i BGB, § 354a HGB, DSGVO articles.
- **P0-4** `content/legal/avv-entwurf.md`: version `avv-draft-1`, section "Annahme und Nachweis" (checkbox, version id +
  timestamp + account, in export). Checkbox texts in fenced blocks "Checkbox-Text agb-draft-2" / "Checkbox-Text avv-draft-1".
- **P1-6** Cloudflare DPA: page shows "Version 6.4, effective April 3, 2026" (opened 1 Nov 2026); previous "Version (2025-06-20)".
  PDF not reachable (permission timeout) – PDF content unverified.
- **P1-7/8** datenschutz-fakten: AI off by default, `AI_TRANSFER_CLEARED` guard planned; `inference_geo` not set in code
  → workspace default (`global` unless changed); workspace residency = owner task in Console; strict log rotation "geplant".
- Tests: `python -m pytest -m "not network" content` (3 new tests). Open: AVV acceptance and AI guard are "geplant" until the
  app/ops branches are merged; update to "ist" then.
