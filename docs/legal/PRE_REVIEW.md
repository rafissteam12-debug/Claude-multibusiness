# Legal pre-review: GDPR and German-law gap check (Belegbrücke / Ablaufwerk)

Status: working paper, 1 Nov 2026. **Prepared by an AI agent, not a lawyer. This is not legal advice.** It is meant to
make the specialist review faster, not to replace it. Nothing here is public. Nothing was sent, signed or bought.

Scope: the current drafts on `main` (`site/templates/datenschutz.html`, `impressum.html`, `agb.html`,
`content/legal/datenschutz-fakten.md`, `content/emails/*`, `content/help/ihre-daten.md`) checked against the code
(`app/`, `site/static/`, `ops/`) and the owner decisions in `docs/legal/LAUNCH_COMPLIANCE.md`.

Status values: **ok** (the draft and the code match, nothing to add) · **gap** (missing or wrong; fix proposed) ·
**owner decision** (a business choice is needed first) · **lawyer question** (needs a legal opinion; the number points to
`docs/legal/REVIEW_PACKAGE.md`, "Questions").

## 0. Sources: what was verified, and how

Opened on 1 Nov 2026 with WebFetch. Quotes are short excerpts.

| Norm | Official URL | Verified? | What was checked |
| --- | --- | --- | --- |
| § 25 TDDDG | https://www.gesetze-im-internet.de/ttdsg/__25.html | yes | Abs. 1: storage/access only with consent; Abs. 2 Nr. 2: no consent if "unbedingt erforderlich, damit der Anbieter eines digitalen Dienstes einen vom Nutzer ausdrücklich gewünschten digitalen Dienst zur Verfügung stellen kann" |
| § 7 Abs. 2, 3 UWG | https://www.gesetze-im-internet.de/uwg_2004/__7.html | yes | Abs. 2 Nr. 2: e-mail advertising needs "vorherige ausdrückliche Einwilligung"; Abs. 3 Nr. 1–4: existing-customer exception incl. notice "bei Erhebung der Adresse und bei jeder Verwendung" |
| § 5 DDG | https://www.gesetze-im-internet.de/ddg/__5.html | yes | Abs. 1 Nr. 1–8 (name, address, legal form/representatives; fast electronic contact incl. e-mail; supervisory authority; register; regulated professions; USt-IdNr./W-IdNr.; liquidation; AV media) — "leicht erkennbar, unmittelbar erreichbar und ständig verfügbar" |
| § 38 Abs. 1 BDSG | https://www.gesetze-im-internet.de/bdsg_2018/__38.html | yes | DPO required "soweit sie in der Regel mindestens 20 Personen ständig … beschäftigen" (or DPIA-subject processing, etc.) |
| § 14 Abs. 1 BGB | https://www.gesetze-im-internet.de/bgb/__14.html | yes | definition "Unternehmer" |
| § 195 BGB | https://www.gesetze-im-internet.de/bgb/__195.html | yes | "Die regelmäßige Verjährungsfrist beträgt drei Jahre." |
| § 309 Nr. 7 BGB | https://www.gesetze-im-internet.de/bgb/__309.html | yes (headings) | "Haftungsausschluss bei Verletzung von Leben, Körper, Gesundheit und bei grobem Verschulden" |
| § 310 Abs. 1 BGB | https://www.gesetze-im-internet.de/bgb/__310.html | yes | §§ 305 Abs. 2/3, 308 Nr. 1, 2–9, 309 not applicable to AGB used toward an Unternehmer; § 307 still applies |
| § 312g Abs. 1 BGB | https://www.gesetze-im-internet.de/bgb/__312g.html | yes | Widerrufsrecht for consumers in Fernabsatzverträgen |
| § 36 VSBG | https://www.gesetze-im-internet.de/vsbg/__36.html | yes | Abs. 1 information duty for Unternehmer with website or AGB; Abs. 3 exemption from Nr. 1 for ≤ 10 employees on 31 Dec of the previous year |
| § 38 Abs. 1 ZPO | https://www.gesetze-im-internet.de/zpo/__38.html | yes | jurisdiction agreements only between "Kaufleute, juristische Personen des öffentlichen Rechts …" |
| § 14b Abs. 1 UStG | https://www.gesetze-im-internet.de/ustg_1980/__14b.html | yes | invoice copies kept "acht Jahre" (customer's duty) |
| § 34 Abs. 1 RVG | https://www.gesetze-im-internet.de/rvg/__34.html | yes | consumer client: first consultation "höchstens 190 Euro" (used in REVIEW_PACKAGE) |
| VO (EU) 2024/3228 | https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32024R3228 | yes | "Die Verordnung (EU) Nr. 524/2013 wird mit Wirkung vom 20. Juli 2025 aufgehoben." → no ODR-platform link needed |
| Durchführungsbeschluss (EU) 2023/1795 (EU-US DPF) | https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32023D1795 | partly (recital 7 only; operative Art. 1 not reached) | adequate protection for data sent to certified organisations |
| **DSGVO (VO (EU) 2016/679), all articles cited below** (Art. 5, 6, 7, 13, 15–22, 28, 30, 32–34, 44–46, 77) | https://eur-lex.europa.eu/eli/reg/2016/679/oj | **unverified** | EUR-Lex returned only the recitals (page text cut at about recital 81); a direct download was blocked by the sandbox proxy. Article contents below are from general knowledge and **must be checked by the reviewer** |
| Durchführungsbeschluss (EU) 2021/914 (SCC) | https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj | **unverified** (not opened; cited in the Anthropic DPA) | |
| § 18 Abs. 2 MStV | (state treaty, no gesetze-im-internet.de page) | **unverified** | |
| Art. 50 KI-VO (EU) 2024/1689 | https://eur-lex.europa.eu/eli/reg/2024/1689/oj | **unverified** (not opened) | optional, see question 19 |
| BGH V ZR 210/22 (Impressum address) | via e-recht24.de summary in LAUNCH_COMPLIANCE.md | **unverified** (original ruling not opened) | |

Provider documents opened on 1 Nov 2026 (facts, not law):

- Anthropic Commercial Terms, https://www.anthropic.com/legal/commercial-terms: Section C: "Data submitted through the Services
  will be processed in accordance with the Anthropic Data Processing Addendum"; effective Jun 17, 2025; **contracting entity
  for EEA customers: Anthropic Ireland, Limited** (Anthropic PBC for customers elsewhere).
- Anthropic DPA, https://www.anthropic.com/legal/data-processing-addendum: effective Feb 24, 2025; "Customer is the controller and
  Anthropic is Customer's processor"; EU SCC Module 2 and/or 3 (Decision 2021/914), Irish law and courts; the DPF is **not**
  mentioned; subprocessors at https://www.anthropic.com/subprocessors (15-day objection right); deletion within 30 days
  after the end of the agreement.
- Cloudflare Customer DPA, https://www.cloudflare.com/cloudflare-customer-dpa/: **Version 6.4, effective April 3, 2026**;
  SCC Module 2 (customer = controller) / Module 3 (customer = processor); clause 6.4: Cloudflare complies with the DPF, and
  if that lapses, transfers fall back to the SCCs.
- Brevo: https://help.brevo.com/hc/en-us/articles/15403782599570 says only that the DPA is at the end of the General Conditions
  of Use. Brevo's terms page and Anthropic's retention article (privacy.claude.com) **could not be opened** (permission request
  timed out) → Brevo entity/seat/hosting and Anthropic API retention period are **unverified**.

## 1. Top gaps (short list)

1. **No AVV for customers.** Customers upload invoice exports that hold their buyers' personal data, so Ablaufwerk is most
   likely their processor (Art. 28). No AVV template exists, and the unused design draft `site/offer-page.dc.html:139` already
   promises one. (Items 2.1, 3.4.)
2. **Legal bases, controller and DSE contact are still placeholders** (`datenschutz.html:13-14, 82, 85, 88`). Proposed table in 2.3.
3. **The privacy page is out of date in three places:** log retention ("eine Frist in Tagen ist noch nicht festgelegt",
   `datenschutz.html:62`, also `:9`), the Anthropic party (`:80` names "Anthropic, PBC (USA)", but the Commercial Terms name
   Anthropic Ireland, Limited for EEA customers), and the HMAC described as "nicht umkehrbar" (`:37, :73`) although it is
   pseudonymous personal data while the key exists.
4. **§ 25 TDDDG: the site's event beacon** (`site/static/site.js:26-31, 101`) runs script in the visitor's browser that reads
   the path and the `?code=` value and sends them. Whether this counts as "Zugriff" and whether it is "unbedingt erforderlich"
   is open. The page says "keine Cookies" (true), but that is not the whole § 25 test. (Item 5.)
5. **The app has no link to Impressum, Datenschutz or AGB, and no point of acceptance:** the app footer
   (`app/templates/base.html:38-46`) and the login page (`app/templates/login.html:8-14`) have neither; an account is created at
   the first magic-link click (`app/main.py:570-575`) with no AGB acceptance, no B2B confirmation and no privacy notice.
   (Items 7, 8.)

Further gaps: no consumer exclusion (B2B-only) anywhere (item 8); consent text v1 not stored verbatim with its version
(item 6.4); "unsubscribe by replying" is promised but no process exists (item 6.5); `contracts/api.md:14` says the unsubscribe
removes the consent record (code keeps it); no Art. 30 records and no breach procedure (item 10); the Cloudflare DPA copy is
recorded as v6.3, the current version is v6.4 (item 4.2).

## 2. Art. 13 DSGVO checklist (privacy page `site/templates/datenschutz.html`)

Article contents: unverified, see section 0.

| # | Art. 13 item | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 2.1 | Controller identity and contact (13(1)(a)) and, **new**, the role split controller/processor | gap + owner decision + lawyer Q1 | `datenschutz.html:13-14` placeholders; invoice data is described as if Ablaufwerk were the controller (`:58-60`) | After the business ID: name, address and e-mail. Add a paragraph: "For invoice data that you upload, we process on your behalf (Auftragsverarbeitung); your AVV with us applies; you are responsible for informing your customers" — subject to Q1. |
| 2.2 | DPO contact (13(1)(b)) | ok (not required, to confirm) | solo founder; § 38 Abs. 1 BDSG threshold of 20 persons (verified) | State "Ein Datenschutzbeauftragter ist nicht benannt" or leave out; reviewer to confirm that no DPIA-subject processing triggers § 38 Abs. 1 S. 2 (Q18). |
| 2.3 | Purposes **and legal basis per processing** (13(1)(c)) | gap → lawyer Q8 | `datenschutz.html:88` placeholder; `datenschutz-fakten.md:140` open | Proposal to check (not a conclusion): account, profile, uploads, conversion, export, magic link → Art. 6(1)(b); free checker → Q1 (6(1)(b) or (f)); rate limiting, hashed IPs, Caddy logs, Cloudflare delivery, `events` counting → 6(1)(f); newsletter → 6(1)(a) with § 7 Abs. 2 Nr. 2 UWG; consent proof after withdrawal → 6(1)(c) with Art. 7(1) or 6(1)(f) (Q9); AI mapping → part of 6(1)(b) or customer instruction (Q4). Add the legal basis as a column in the overview table (`:17-39`). |
| 2.4 | Legitimate interests named (13(1)(d)) | gap | none on the page | Name each interest next to every 6(1)(f) line: abuse protection / security (rate limits, logs), delivery of the site (Cloudflare), anonymous usage counting (events), defence against claims (consent proof). |
| 2.5 | Recipients / processors (13(1)(e)) | gap (partly ok) | `datenschutz.html:77-81` lists hosting (placeholder), Cloudflare, Brevo, Anthropic | Hosting provider name after the choice; **correct Anthropic** to "Anthropic Ireland, Limited (Irland) als Vertragspartner; Verarbeitung auch durch Anthropic PBC (USA) und weitere Unterauftragsverarbeiter" (wording per Q4); Brevo's entity/seat from the contract (unverified here); say that Brevo also sends **login links**, not only newsletter mail (`:79` does say this — ok). |
| 2.6 | Third-country transfer and safeguards (13(1)(f)) | gap → lawyer Q3–Q5 | `datenschutz.html:82` placeholder | Cloudflare: DPF certification + SCC fallback (DPA v6.4 cl. 6.2/6.4). Anthropic: SCC Module 2/3 under 2021/914 (DPA, no DPF mentioned). State "Kopie der Garantien: auf Anfrage an [contact]". Default AI mode may not be a personal-data transfer at all (Q3). |
| 2.7 | Retention per category (13(2)(a)) | mostly ok; 3 gaps | table `datenschutz.html:17-39` matches the code (`app/jobs.py:301-349`); gaps: (a) logs `:62` say no day limit, but the owner decided 14 days (`LAUNCH_COMPLIANCE.md:48-54`, `ops/RUNBOOK.md:89-117`); (b) Cloudflare "beim Dienstleister" (`:22`) gives no period or criterion; (c) consent proof `:37` says only "3 Jahre nach der Abmeldung", but the code also keeps a record during the subscription and deletes it 3 years after confirmation when the subscription is gone without an unsubscribe (`app/jobs.py:339-349`) | (a) Replace `:62` with: "Webserver- und Container-Protokolle: 14 Tage; bei sehr wenig Verkehr kann die größenbasierte Rotation einzelne Zeilen länger halten, bis die strenge Altersgrenze auf dem Server eingerichtet ist" — or, better, finish the journald/logrotate setup first and then state only "14 Tage". Remove "Aufbewahrungsdauer der Webserver-Protokolle" from the open list at `:9`. (b) Take Cloudflare's period from its documentation, or the criterion. (c) Describe all three cases. Also add: Anthropic retention (unverified here) and Brevo retention. |
| 2.8 | Rights Art. 15–21 (13(2)(b)) | gap (small) | `datenschutz.html:85` lists all; contact placeholder; **Art. 21 objection right is not shown separately** | Add its own highlighted box "Widerspruchsrecht (Art. 21)" for all 6(1)(f) processing (Art. 21(4) requires it to be shown clearly and separately from other information — unverified, see section 0). Name the contact address. |
| 2.9 | Right to withdraw consent (13(2)(c), Art. 7(3)) | ok | `datenschutz.html:73, 85`; link in every mail (`03:51`, `04:35`); code `app/main.py:487-512` | Add "Der Widerruf berührt nicht die Rechtmäßigkeit der bis dahin erfolgten Verarbeitung." |
| 2.10 | Complaint to a supervisory authority (13(2)(d), Art. 77) | ok, improvement | `datenschutz.html:85` | Name the authority of the founder's Land once the seat is known (optional but common). |
| 2.11 | Whether provision is required / consequences (13(2)(e)) | gap | not on the page | Add: "Für Konto und Umwandlung ist die E-Mail-Adresse erforderlich; ohne sie ist keine Anmeldung möglich. Angaben im Firmenprofil sind nötig, damit eine gültige E-Rechnung entsteht. Die Anmeldung zu E-Mail-Hinweisen ist freiwillig." |
| 2.12 | Automated decision-making (13(2)(f), Art. 22) | gap (wording only) | not on the page; the validator decides "valid/invalid" about a **file**, not about a person | Add: "Eine automatisierte Entscheidungsfindung im Sinne von Art. 22 DSGVO findet nicht statt. Die Prüfung bewertet Dateien, keine Personen." |
| 2.13 | Information at the point of collection (app) | gap | `app/templates/login.html:8-14` (no link); `app/templates/base.html:38-46` (footer without Datenschutz/Impressum) | Add footer links in the app (absolute URLs to the site pages) and a line under the login form: "Mit der Anmeldung gelten die AGB; Informationen zum Datenschutz: [Link]." |
| 2.14 | HMAC wording | gap | `datenschutz.html:37, 73`; `ihre-daten.md:58`; HMAC keyed with `SESSION_SECRET` (`app/security.py:31-33`) | Replace "nicht umkehrbarer Prüfwert" with "pseudonymisierter Prüfwert (HMAC). Wir können damit nur prüfen, ob eine bestimmte Adresse eingewilligt hatte" — it stays personal data (Q9). |
| 2.15 | Free checker | ok (Q1 for basis) | `datenschutz.html:51`, `pruefen.html:17`; code discards the file | none, apart from the legal basis. |

## 3. Art. 28 DSGVO — processor agreements

| # | Relationship | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 3.1 | Ablaufwerk → **Anthropic** | owner decision taken; lawyer Q4 | `LAUNCH_COMPLIANCE.md:29`; DPA incorporated by Commercial Terms Section C (verified) | Keep dated PDFs of Commercial Terms (Jun 17, 2025) and DPA (Feb 24, 2025). Record that the party is **Anthropic Ireland, Limited**. Check the subprocessor list and subscribe to change notices. |
| 3.2 | Ablaufwerk → **Cloudflare** | owner decision taken | `LAUNCH_COMPLIANCE.md:30` says "v6.3"; the live DPA is **v6.4, effective April 3, 2026** | Store the v6.4 PDF dated 1 Nov 2026; correct the record. |
| 3.3 | Ablaufwerk → **Brevo**, **hosting** | open (account / provider not chosen) | `LAUNCH_COMPLIANCE.md:31-32`; `datenschutz-fakten.md:129, 132` | Accept the Brevo DPA when the account is created (separate approval); choose an EU host and sign its AVV; record entity, seat, subprocessors. |
| 3.4 | **Customer → Ablaufwerk** (Ablaufwerk as processor) | **gap**, lawyer Q1–Q2 | no AVV anywhere (repository search for "AVV/Auftragsverarbeitung"); `site/offer-page.dc.html:139` promises "schließen einen Auftragsverarbeitungsvertrag ab" (design draft, not built into `site/dist`) | Draft an AVV (Art. 28(3) content: subject, duration = account term + 24 h, data types, categories of data subjects (buyers, contact persons), instructions, confidentiality, TOMs annex, subprocessor list (hosting, Anthropic; Brevo only for account mail), support with rights, deletion/return (built: 24 h, account delete, JSON export), audits). Conclude it electronically together with the AGB. Write a TOMs annex from what is built (`ops/RUNBOOK.md`, `contracts/api.md` security rules). |
| 3.5 | Sub-processor approval for customers | gap | — | General written authorisation with a notice period for changes (mirror Anthropic's 15-day objection right). |

## 4. Chapter V — third-country transfers

| # | Flow | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 4.1 | Anthropic (AI mapping) | lawyer Q3, Q4; owner decision on launch option | Inference "global", storage "us" only (`LAUNCH_COMPLIANCE.md:34-42`, source platform.claude.com, not re-opened here); default payload = column names + value shapes (`mapping/ai.py:94`, `ihre-daten.md:24-39`); real values only with the toggle (`app/templates/upload.html:14-15`, `mapping.html:109`) | Owner options (a)/(b)/(c) in `LAUNCH_COMPLIANCE.md:40-41` stay valid. Suggested for review: launch with (a) AI off or (b) shapes only, real-value toggle hidden until Q4 is answered; document a short transfer impact assessment (TIA) if real values are ever sent. |
| 4.2 | Cloudflare (website delivery) | ok in substance, record to fix | DPA v6.4 cl. 6.4 (DPF) + SCC fallback; app DNS-only, so app traffic does not pass Cloudflare (`ops/RUNBOOK.md:35-40`) | Name the DPF + SCC basis on the privacy page; confirm the DPF listing of Cloudflare, Inc. (the DPF list page could not be read here — unverified). |
| 4.3 | Brevo | unverified | Brevo terms not opened | Check Brevo's hosting and subprocessors (for example US mail-delivery providers) from the contract; add safeguards if any. |
| 4.4 | Hosting | ok if EU | `ops/RUNBOOK.md:32` (EU VPS planned) | Choose an EU provider whose AVV excludes non-EU subprocessors, or document them. |

## 5. § 25 TDDDG — every storage or access on the user's device (verified text, section 0)

Repository search for `set_cookie`, `Set-Cookie`, `localStorage`, `sessionStorage`, `document.cookie`, `indexedDB`
(excluding tests): only the app sets cookies; no Web Storage anywhere (`site/static/site.js:2`, `app/static/*`).

| Storage / access | Where set | Attributes | Purpose | Status (proposal) |
| --- | --- | --- | --- | --- |
| `bb_session` | `app/security.py:13`, `app/main.py:324-325, 578` | HttpOnly, Secure (prod), SameSite=Lax, path `/`, 7 days (`app/settings.py:30`) | keeps the user logged in | strictly necessary (Abs. 2 Nr. 2) — to confirm, Q7 |
| `bb_pre` | `app/security.py:14`, `app/main.py:441, 931` | same, 1 h | CSRF protection before login | strictly necessary (security of the requested service) — Q7 |
| `bb_t_login`, `bb_t_optin`, `bb_t_unsubscribe` | `app/main.py:414-415, 428-429` | HttpOnly, Lax, scoped to the token path; 15 min (login/opt-in), 1 h (unsubscribe) | moves the token out of the URL | strictly necessary — Q7 |
| Site event beacon (`navigator.sendBeacon`) | `site/static/site.js:26-31, 56, 86, 101` | sends `{name, path, code}` on page view, app-link click and sign-up; no cookie, no ID | usage counting | **lawyer question Q6**: script reads `location.pathname` / query in the browser. Probably not "unbedingt erforderlich" for the requested service. Options: (1) move counting to the server (count `/api/v1/check` and `/subscribe` hits server-side, which the app already does for `subscribe`, `app/main.py:409-410`) and drop `page_view`/`link_click`; (2) keep it and ask for consent; (3) keep it if Q6 says it is outside § 25. |
| Link rewriting `?code=` | `site/static/site.js:38-52` | changes link URLs in the page, stores nothing | carry campaign code | include in Q6 |
| Cloudflare cookies on the site (e.g. bot or challenge cookies) | not in our code | — | — | **owner check**: open the staging site with browser dev tools, list cookies; if Cloudflare sets any, describe them or switch the feature off. The privacy page claims "keine Cookies" (`datenschutz.html:43`). |
| Google Fonts in `site/offer-page.dc.html:10-11` | design reference only; not in `site/dist` | — | — | ok as long as it is never published; if the page is ever built, self-host the fonts (CLAUDE.md: no CDNs). |

Privacy-page text for the app cookies (`datenschutz.html:56`) matches the code — ok. Add cookie names and lifetimes as a small table.

## 6. Newsletter — § 7 Abs. 2 Nr. 2, Abs. 3 UWG and Art. 7 DSGVO

| # | Point | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 6.1 | Prior, express consent; checkbox not pre-ticked | ok | `site/templates/partials/subscribe.html:11-12`; server rejects without `consent: true` (`app/main.py:383-384`) | — |
| 6.2 | Double opt-in; scanners cannot confirm | ok | `content/emails/01-double-opt-in.md`; GET shows a button, POST confirms (`contracts/api.md:13`, `app/main.py:465-479`) | Lawyer Q11: 15-minute confirmation window (`01:2, 14`) is short but not a legal issue; confirm the DOI mail contains no advertising (it describes the subscription only). |
| 6.3 | Proof (Art. 7(1)) | ok, owner decision taken; Q9 | `app/migrations/003_consent_records.sql`; 3 years (§ 195 BGB verified) | The HMAC key is `SESSION_SECRET` (`app/security.py:31-33`); `ops/RUNBOOK.md:69-71` tells the owner to rotate it at once if leaked, which would make all proofs unmatchable. Implement the requested `CONSENT_HMAC_KEY` before launch (already requested, `LAUNCH_COMPLIANCE.md:23-24`). |
| 6.4 | Proof of **what** was consented to | gap | version string only: `app/settings.py:22`, form `subscribe.html:5`; the label text lives only in a template that can change | Store the verbatim v1 text (checkbox label + scope sentence) in a versioned file (for example `contracts/consent/2026-10-31-v1.txt`, orchestrator) and add a test that the form label equals it; bump the version on every wording change. |
| 6.5 | Withdrawal as easy as consent | gap (small) | link in each mail (ok). `01-double-opt-in.md:25` also promises "einfach auf eine E-Mail antworten und ‚abmelden' schreiben" — no process, and `consent_records.method` knows only `'link'` (`app/main.py:500-504`) | Either remove the reply promise, or document a manual process (owner deletes via an admin command that writes `method='reply'`) with a deadline. |
| 6.6 | Unsubscribe link in **every** advertising mail | ok | `03:51`, `04:35`; `contracts/api.md:14` | — |
| 6.7 | Contract text inconsistent with code | gap (orchestrator) | `contracts/api.md:14` "removes the address and its consent record"; `:65` "period to be confirmed by the owner" (decided 1 Nov) | Update the contract: removes the address, closes the consent record (kept 3 years). |
| 6.8 | § 7 Abs. 3 UWG for account holders | owner decision → Q12 | account e-mails get only transactional mail today (`02-magic-link.md`) | If product news to account holders without newsletter consent is wanted: notice at collection (login page) and in every mail, plus an opt-out. Otherwise: state "Konto-E-Mail-Adressen erhalten keine Werbung". |
| 6.9 | Sender identity / valid reply address (§ 7 Abs. 2 Nr. 3 UWG) | open until business ID | `_footer.md:4` placeholder | Fill with the Impressum data. |

## 7. § 5 DDG — Impressum (`site/templates/impressum.html`)

| # | Item (§ 5 Abs. 1) | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 7.1 | Nr. 1 name, **ladungsfähige Anschrift**, legal form, representatives | owner decision taken + lawyer Q13 | `impressum.html:7` placeholders; FlexPost: owner obtained a confirmation that documents can be served there (`LAUNCH_COMPLIANCE.md:56-65`) | Keep the confirmation in writing (contract clause or e-mail, dated). Lawyer to confirm it meets the standard (BGH V ZR 210/22 via eRecht24 — unverified). Fallback: home address or a business address where service is possible. |
| 7.2 | Nr. 2 fast electronic contact incl. e-mail | gap (small) | `impressum.html:9` only e-mail | Add a second direct channel (contact form or phone); Q14. |
| 7.3 | Nr. 3 supervisory authority | ok (none expected) | — | Confirm no permit is needed for the business. |
| 7.4 | Nr. 4 register | ok as placeholder | `impressum.html:11` | Fill if registered; remove the line for an Einzelunternehmen without an entry. |
| 7.5 | Nr. 6 USt-IdNr. / W-IdNr. | ok as placeholder | `impressum.html:11` | Fill "where one exists". |
| 7.6 | "Verantwortlich für den Inhalt" | lawyer Q14 | `impressum.html:13` | This heading usually refers to § 18 Abs. 2 MStV (journalistic-editorial content; unverified). Guides and Ada posts may qualify; name the person and the norm, or remove. |
| 7.7 | "leicht erkennbar, unmittelbar erreichbar, ständig verfügbar" | gap for the app | site footer ok (`site/templates/base.html:51-53`); app footer has no link (`app/templates/base.html:38-46`) | Link Impressum, Datenschutz, AGB from every app page; also on the social profiles where Ada posts appear (later, before publishing). |
| 7.8 | ODR-platform link | ok — not needed | VO 524/2013 repealed from 20 July 2025 (verified) | Do not add the old ODR link. |
| 7.9 | Staging | ok | "Testversion" banner, `X-Robots-Tag: noindex, nofollow` (`site/dist/_headers`), never linked | — |

## 8. Consumers — B2C possible? (document B2B-only)

| # | Point | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 8.1 | Who can sign up | **gap** | anyone with an e-mail address gets a free account (`app/main.py:570-575`); no B2B statement in AGB (`agb.html` placeholders), login (`login.html`) or site | Owner decision: B2B-only (the product serves the B2B e-invoice obligation). Then: AGB clause "Angebot ausschließlich für Unternehmer i. S. d. § 14 BGB"; a required checkbox at the first login "Ich nutze Belegbrücke für mein Unternehmen (§ 14 BGB) und akzeptiere die AGB" (store version + timestamp, like consent records); the same statement on the site near the call to action. Q15. |
| 8.2 | Consequences if B2C stays possible | lawyer Q15 | — | Widerrufsrecht (§ 312g BGB verified) and its information, a cancellation button for paid plans, digital-product rules, prices incl. VAT, § 36 VSBG statement (exemption for ≤ 10 employees covers only Nr. 1, verified). Even the free plan might be a consumer contract when personal data is provided — Q15. |
| 8.3 | Prices | ok (rule 6) | no prices in user-facing output; plan limits only (`04-welcome-2-belegbruecke.md:26`, `contracts/api.md:37-39`) | Keep until cleared. With B2B-only, net prices are possible (lawyer to confirm). |

## 9. AGB basics for a SaaS converter (`site/templates/agb.html` is a placeholder)

| # | Clause | Status | Evidence | Proposed content (for the lawyer to draft or check) |
| --- | --- | --- | --- | --- |
| 9.1 | Scope / B2B only | gap | `agb.html:7` | see 8.1. |
| 9.2 | Service description + **scope line** | partly ok | `agb.html:9` uses the brand scope line ("technisches Werkzeug … Keine Steuer- oder Rechtsberatung", `contracts/brand.md:15-16`) | Add: what "gültig" means (passed XSD, EN 16931, XRechnung Schematron and KoSIT with the pinned configuration, `engine/rules/VERSIONS.md`); skipped checks are shown as skipped; no promise that a recipient accepts the file; the customer checks content and VAT. No words like "rechtssicher" or "garantiert" (rule 4). Q16. |
| 9.3 | Customer duties | gap | 24 h retention (`contracts/api.md:59-65`), "kein Archiv" (`ihre-daten.md:22`) | Customer downloads within 24 h and archives invoices itself (§ 14b UStG: 8 years, verified — customer's duty); customer has the right to upload the data (buyers' personal data) and informs its buyers; correct seller profile. Q17. |
| 9.4 | Availability, changes, free plan limits | gap | plan limits `contracts/api.md:37-39` | No availability guarantee on the free plan; maintenance windows; the right to change features with notice. |
| 9.5 | Liability | gap → Q16 | — | In B2B, § 309 Nr. 7 does not apply directly, but § 307 does (§ 310 Abs. 1, verified). Usual structure (to check): unlimited for intent, gross negligence, injury to life/body/health, guarantees, ProdHaftG; for slight negligence only for essential obligations ("Kardinalpflichten"), limited to foreseeable, typical damage; possibly a cap tied to the fees; free plan treated separately. |
| 9.6 | Data protection / AVV | gap | see 3.4 | AVV as an annex accepted with the AGB. |
| 9.7 | AI feature | gap | AI mapping is a proposal the user confirms (`app/templates/mapping.html`) | State that mapping proposals (rules or AI) are suggestions; the user confirms them; the AI provider and the real-value toggle. |
| 9.8 | Term, termination, deletion | gap | account delete (`contracts/api.md:32`), 12-month inactivity deletion (`app/jobs.py:317-319`) | Mention both; export before deletion. |
| 9.9 | Law, venue | gap | — | German law; a jurisdiction clause only works toward Kaufleute etc. (§ 38 Abs. 1 ZPO, verified). |
| 9.10 | Incorporation / acceptance | gap | no acceptance step (`login.html`) | see 8.1; store AGB version + timestamp per user. |

## 10. Other duties found along the way

| # | Point | Status | Evidence | Proposed fix |
| --- | --- | --- | --- | --- |
| 10.1 | Records of processing (Art. 30, as controller and as processor) | gap | none in the repo | `datenschutz-fakten.md` is a good base; turn it into a record (one row per processing: purpose, categories, recipients, transfers, retention, TOMs). Q18 (whether the < 250-employee exemption applies — likely not, the processing is regular; unverified). |
| 10.2 | Data breach procedure (Art. 33/34) | gap | `ops/RUNBOOK.md` has no breach section | Add a short runbook section: detect, contain, assess, notify the authority within 72 h if required, inform customers as their processor "without undue delay", log every incident. |
| 10.3 | TOMs (Art. 32) | ok in substance, not documented | `contracts/api.md:44-58` security rules; `PRAGMA secure_delete`, hashed tokens, IP truncation, no backups (`ops/RUNBOOK.md:78-125`) | Write them up as the AVV annex (3.4). |
| 10.4 | Data minimisation / logs | ok | no invoice values, prompts or tokens in logs (`ops/RUNBOOK.md:84-86`); IP masking in Caddy | Finish the strict 14-day host setting before launch (`LAUNCH_COMPLIANCE.md:52-54`). |
| 10.5 | Ada disclosure | ok per brand rules (rule 5) | `contracts/brand.md:14` | Optional Q19 on AI Act transparency duties (unverified). |
| 10.6 | `ihre-daten.md` help page | ok, small fix | `content/help/ihre-daten.md:41` (Anthropic) and `:58` (HMAC wording) | Align with 2.5 and 2.14 (content agent). |

## 11. Who changes what (ownership per CLAUDE.md; nothing changed by this review)

- Website agent: `datenschutz.html` (2.3–2.14), `impressum.html` (7.x), `agb.html` (after the lawyer).
- App agent: footer links and login acceptance step (2.13, 7.7, 8.1, 9.10); unsubscribe-by-reply method (6.5); `CONSENT_HMAC_KEY` (6.3).
- Content agent: `01-double-opt-in.md:25` (6.5), `ihre-daten.md` (10.6), `_footer.md` after the business ID.
- Orchestrator: `contracts/api.md:14, :65` (6.7), consent text archive (6.4), `LAUNCH_COMPLIANCE.md:30` v6.3 → v6.4 (3.2), AVV and TOMs drafts (3.4), Art. 30 record (10.1).
- Ops agent: breach section in `ops/RUNBOOK.md` (10.2); strict log retention on the host (10.4).
- Owner: B2B-only decision (8.1), § 7 Abs. 3 UWG (6.8), Cloudflare cookie check (section 5), AI launch option (4.1), host choice, Brevo account (with approval).
