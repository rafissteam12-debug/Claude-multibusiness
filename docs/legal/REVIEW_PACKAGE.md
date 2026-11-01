# Review package for the legal specialist — Belegbrücke (Ablaufwerk)

Status: handover draft, 1 Nov 2026. Prepared by an AI agent, **not a lawyer; not legal advice**. Nobody has been
contacted; nothing has been sent, signed or bought. The gap analysis behind this package is `docs/legal/PRE_REVIEW.md`.

## 1. One-page summary

**Who:** Ablaufwerk, a solo founder in Germany, not yet registered and not yet launched (business data:
`[[BUSINESS_ID_PENDING]]`). Everything runs on staging only.

**What:** *Belegbrücke* is a self-serve web tool for businesses. It turns an existing invoice export (CSV/XLSX) into German
e-invoices (XRechnung 3.0 CII; ZUGFeRD EN 16931 PDF/A-3) and validates every file (XSD, EN 16931, XRechnung rules, the KoSIT
validator). Only files that pass are offered as e-invoices. It also offers a free "E-Rechnung-Check" (upload an XML/PDF
e-invoice, get a validation report, no account), German guide pages, an e-mail newsletter with double opt-in, and
"Ada", an openly AI-generated illustrated presenter. Scope line on every page: *"Belegbrücke ist ein technisches Werkzeug.
Inhalt der Rechnung, Umsatzsteuer und Pflichten bestätigen Sie oder Ihre Steuerberatung. Keine Steuer- oder Rechtsberatung."*
Plans: free (3 valid invoices a month) and paid plans later; no prices published and no payment integration yet.

**Data in short:** login by e-mail magic link (no passwords); a company profile (seller data incl. IBAN, contact person);
uploaded exports with the customer's buyers' data — **raw file deleted at successful conversion or after 24 h; outputs and
error texts after 24 h**; saved column mappings (no cell values); hashed IPs for rate limits (2 days); anonymous event counts
(13 months); web-server logs 14 days, IPs truncated; no backups. AI column mapping (Anthropic) is **off by default**; when on,
it receives column names and value *shapes* ("31.10.2026" → "dd.dd.dddd"); real values only if the user switches a toggle on.

```
 Visitor's browser                                  Customer (business user)
   |  static pages (no cookies, no third-party assets)   |  magic-link login, cookies: bb_session (7 d),
   v                                                     |  bb_pre (1 h), bb_t_* (15 min / 1 h)
 [Cloudflare — website delivery, USA, DPF + SCC]         v
   |  beacon {event, path, campaign code}  ------>  [App server — EU VPS (provider TBD), Caddy + FastAPI + SQLite]
   |  checker upload (XML/PDF, discarded)  ------>     |  account, seller profile, mappings, usage counters
   |  newsletter sign-up (e-mail)          ------>     |  uploads + outputs in TEMP_DIR (max 24 h), purge hourly
                                                       |  logs 14 d, IP truncated, no backups
                                                       |
                       only if AI_PROVIDER=anthropic   |  column names + value shapes
                       (default: off)                  |  (+ real sample values only on user opt-in)
                                                       v
                                         [Anthropic Ireland Ltd. (contract) / Anthropic PBC — inference "global",
                                          storage "us"; DPA with SCC Module 2/3]
                                                       |
                       only if MAILER=brevo            |  recipient address + mail text (login link, opt-in,
                                                       v  welcome mails)
                                         [Brevo — e-mail sending (entity/seat from contract, unverified here)]
```

## 2. Documents to review

| # | Path | What it is |
| --- | --- | --- |
| 1 | `site/templates/datenschutz.html` | privacy policy draft (German) |
| 2 | `content/legal/datenschutz-fakten.md` | fact sheet: every data item, purpose, place, retention, as built |
| 3 | `site/templates/impressum.html` | Impressum skeleton (placeholders) |
| 4 | `site/templates/agb.html` | AGB skeleton (placeholders) — to be drafted |
| 5 | `site/templates/partials/subscribe.html` | newsletter form and consent text v1 (`2026-10-31-v1`) |
| 6 | `content/emails/01-double-opt-in.md` … `04-welcome-2-belegbruecke.md`, `_footer.md` | opt-in, login and welcome mails |
| 7 | `content/help/ihre-daten.md` | in-app help page "Was mit Ihren Daten passiert" |
| 8 | `contracts/api.md` (sections "Security rules", "Retention") | retention and security rules the code follows |
| 9 | `ops/RUNBOOK.md` (sections "Logs", "Log retention", "Retention and backups") | log handling and retention |
| 10 | `docs/legal/LAUNCH_COMPLIANCE.md` | owner decisions of 1 Nov 2026 |
| 11 | `docs/legal/PRE_REVIEW.md` | gap check with proposed fixes and file references |
| 12 | Provider terms (owner keeps dated PDFs): Anthropic Commercial Terms (Jun 17, 2025) + DPA (Feb 24, 2025); Cloudflare Customer DPA v6.4 (Apr 3, 2026); Brevo General Conditions of Use with DPA; FlexPost written confirmation on service of documents; hosting AVV (once chosen) | contracts |
| 13 | To be drafted (not yet existing): AVV for customers + TOMs annex; Art. 30 records | — |

## 3. Questions for the lawyer (19)

Each can be answered with yes/no plus a short reason or a wording.

1. **Roles.** For uploaded exports and generated invoices, is Ablaufwerk a processor of its customers (Art. 28 DSGVO)? For
   the free E-Rechnung-Check (no account, file discarded after the response), are we controller or processor, and on which
   legal basis?
2. **Customer AVV.** If yes to processor: may the AVV be concluded electronically together with the AGB at the first login?
   Please review or supply the AVV and the TOMs annex (draft to follow).
3. **AI default mode.** Are column names plus value *shapes* ("Xxxxxx XxxX", "dd.dd.dddd") personal data? If not, is the
   default AI mode outside Chapter V altogether?
4. **AI real-value mode.** The contracting party is Anthropic Ireland, Limited; processing "may run in any available
   geography", storage in the US; DPA with SCC Module 2/3. Is this sufficient for the opt-in "Echte Beispielwerte senden"?
   Do we need a transfer impact assessment, and is the user's toggle a valid customer instruction? Please give a privacy-policy
   wording.
5. **Cloudflare.** For website delivery, is reliance on Cloudflare's DPF certification (SCC fallback, DPA v6.4) enough, and how
   should the retention of Cloudflare's connection logs be described?
6. **§ 25 TDDDG — event beacon.** The site's script reads the page path and a `?code=` campaign value in the browser and sends
   them via `sendBeacon` (no cookie, no ID). Does this fall under § 25 Abs. 1? If yes, is it covered by Abs. 2 Nr. 2, or do we
   need consent (or should we switch to server-side counting)?
7. **App cookies.** Are `bb_session` (7 days), `bb_pre` (CSRF, 1 h) and the token cookies `bb_t_*` (15 min / 1 h) all
   "unbedingt erforderlich" under § 25 Abs. 2 Nr. 2, so that listing them in the privacy policy is enough (no banner)?
8. **Legal bases.** Please confirm or correct the table in `PRE_REVIEW.md` item 2.3 (6(1)(b) account and conversion;
   6(1)(f) rate limits, logs, event counting, site delivery; 6(1)(a) newsletter).
9. **Consent proof.** We keep an HMAC of the address, consent version, source and timestamps for 3 years after withdrawal
   (reasoning: Art. 7(1) DSGVO, § 195 BGB). Correct legal basis (6(1)(c) or (f))? Is 3 years proportionate? Must we call the
   HMAC "pseudonymised personal data" instead of "nicht umkehrbar"?
10. **Retention periods.** Are these acceptable as stated: inactive accounts deleted after 12 months; job metadata without
    contents kept while the account exists; event counts 13 months; logs 14 days; hashed IPs 2 days?
11. **Newsletter.** Do consent text v1 (`subscribe.html:12`) and the double opt-in flow (button page, 15-minute link, mail
    `01-double-opt-in.md`) meet § 7 Abs. 2 Nr. 2 UWG and Art. 7 DSGVO? Does the "source" (e.g. an Instagram campaign code) need
    mention in the consent text?
12. **§ 7 Abs. 3 UWG.** May we send product news to account holders who did not subscribe? If yes, what notice wording is needed
    at the login form and in each mail?
13. **Impressum address.** FlexPost has confirmed that documents can be served at its address. Is that a sufficient
    "ladungsfähige Anschrift" for a sole trader, or is the home or a business address required? What written evidence should
    we keep?
14. **Impressum content.** Is a second contact channel besides e-mail needed? Do the guide pages and Ada posts require a
    "Verantwortlich nach § 18 Abs. 2 MStV" entry, and must the Impressum be linked from our social-media profiles?
15. **B2B-only.** Is an AGB clause "nur für Unternehmer (§ 14 BGB)" plus a required checkbox at the first login enough to
    exclude consumer law (Widerrufsrecht, cancellation button, digital-product rules, gross prices, § 36 VSBG)? What applies
    if a consumer signs up for the free plan anyway?
16. **Liability and "valid".** How far can B2B AGB limit liability for wrong validation results or for invoices that a
    recipient rejects (under § 307 BGB with § 310 Abs. 1)? Does showing "gültig" create a quality guarantee? Is a separate,
    lower liability for the free plan possible?
17. **Customer duties.** Is it enough to say in the AGB that we delete files after 24 h, that we are not an archive, and that
    the customer must keep invoices (§ 14b UStG) and inform its buyers? Is any other clause needed for the buyers' data?
18. **Organisation.** Please confirm: no data protection officer needed (§ 38 BDSG, solo); Art. 30 records needed as
    controller and as processor; no DPIA needed; any formal requirements for a breach procedure.
19. **AI transparency (optional).** Beyond the existing "KI-generiert" disclosure for Ada and the label "Vorschlag" on AI
    mappings, are there obligations under Art. 50 KI-VO (Regulation (EU) 2024/1689) that apply to us? (Text and application date not verified
    in this pre-review.)

## 4. Already decided by the owner (1 Nov 2026, from `LAUNCH_COMPLIANCE.md`)

- Consent evidence: kept 3 years, minimum data (HMAC, version, source, timestamps; withdrawal date and method; no IP, no user
  agent, no plain address); re-subscription only through a new double opt-in. Built.
- Web-server and container logs: 14 days (configured; a strict age limit on the host is still to be set up).
- Providers accepted: Anthropic (DPA via Commercial Terms Section C), Cloudflare (Customer DPA in the Self-Serve Subscription
  Agreement), Brevo in principle (takes effect with the account; account creation needs separate approval).
- Impressum address: FlexPost confirmed service of documents; keep it in writing; lawyer to confirm.
- AI: off by default; launch option (a) AI off or (b) shapes only to be chosen after the review; real-value opt-in stays off
  until then (recommended in the plan).
- App hosting in the EU; no backups by design; nothing goes public before the owner's written go-live approval.
- Open owner decisions: B2B-only (recommended in `PRE_REVIEW.md` 8.1), § 7 Abs. 3 UWG use, host choice, legal form.

## 5. How to get the review (web research, 1 Nov 2026)

**Research only — no recommendation of a specific firm. No provider was contacted, no account created, no form submitted.**
Prices are as publicly stated on the date checked and may change; they are not offers.

| Kind of provider | What it typically covers | Publicly stated price (as found) | Source (checked 1 Nov 2026) |
| --- | --- | --- | --- |
| **Lawyer, e.g. Fachanwalt für IT-Recht** (individual mandate) | Review of all documents in section 2, answers to section 3, drafting AGB/AVV; liability for the advice | For a **consumer** client the statutory fee for a first consultation is capped at 190 € (§ 34 Abs. 1 S. 3 RVG); a business client usually agrees an hourly or fixed fee. Example of a published fixed fee: SaaS-AGB drafting 389 € net, optional 60-minute consultation +199 € (one firm's page); review of existing AGB "on request" | https://www.gesetze-im-internet.de/rvg/__34.html ; https://anwalt-kg.de/allgemeine-geschaeftsbedingungen/saas-unternehmens-agb/ |
| **External data protection officer service** | Ongoing: records of processing, AVV/TOMs, TIAs, website/cookie check, breach contact; formal DPO appointment (not required for us, see Q18) | "ab 149 € / Monat", net, 24-month term (one provider); "ab 99,00 Euro pro Monat" (Händlerbund "Datenschutz Pro"; the page also shows 99,90 €, net/gross not stated) | https://gesellschaft-datenschutz.de/externer-datenschutzbeauftragter/ ; https://www.haendlerbund.de/de/leistungen/rechtssicherheit/agb-service/datenschutzgrundverordnung/datenschutzbeauftragter |
| **Flat-rate legal-text service: IT-Recht Kanzlei** | SaaS B2B AGB, privacy policy, Impressum, AVV template (must be adapted), update service | 19,90 € per month (page shows "1990 … monatlich", read as 19,90 €), net, cancellable monthly | https://www.it-recht-kanzlei.de/Service/saas-b2b-agb.php |
| **Flat-rate legal-text service: Händlerbund membership** | Legal texts (AGB, privacy, Impressum) for one shop or website; higher tiers with legal advice and help with warning letters | Website & Content Creator from 4,90 €/month; Starter from 9,90 €/month; Business from 57,90 €/month (12 months, "unbegrenzte Rechtsberatung"); all net | https://www.haendlerbund.de/de/leistungen/mitgliedschaft |
| **Self-service generators: eRecht24 Premium** | Generators for Impressum, privacy policy, AVV; AGB generator from "Business"; lawyer time only in higher tiers | Basic 15 €/month, Business 40 €/month, Enterprise 90 €/month (incl. 1 lawyer hour a year), Ultimate 800 €/month — shown as monthly rate with annual payment, net/gross not stated; a consultation hour is valued at 350 € on the advice page | https://www.e-recht24.de/premium ; https://www.e-recht24.de/mitglieder/uebersicht-rechtsberatungspakete/ |
| **IHK first consultation for founders** | Free orientation talk with a lawyer; not a document review | Example IHK Pfalz: "kostenfreie Rechtsanwalt-Sprechtage", for founders and companies in their first 3 years, once, seat in the Pfalz. Other IHKs have similar offers; check the IHK of the founder's seat | https://www.ihk.de/pfalz/innovation-umwelt-und-existenzgruendung/unternehmensgruendung/beratungsangebote-der-starterzentren/rechtsanwalt-sprechtag-1278880 |

Notes from the research, as facts:
- Generators and flat-rate texts are built for typical websites and shops. They do not by themselves answer the
  product-specific questions in section 3 (processor role, AI transfers, the event beacon, the liability for "valid"). Several
  of the packages above include some lawyer time; what that time covers is stated differently on each page.
- An IHK talk is free but short; it can help to choose the kind of provider, not replace the review.
- Lawyer fees for business clients are not capped by statute; ask for a written fee agreement (fixed fee or hourly rate and
  an estimate) before the mandate.

What the owner can do next (no step taken by this agent): send section 2 and section 3 of this package to the chosen
provider; ask for a fixed-fee quote for "review of privacy policy, Impressum, AGB and AVV for a B2B SaaS, plus answers to 19
questions".
