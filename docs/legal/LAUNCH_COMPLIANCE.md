# Launch compliance plan (wave 5) — owner decisions of 1 Nov 2026

Status: working plan for the owner. Not legal advice. Nothing here is public. Every item ends with a check by a
lawyer or data-protection service before go-live (`SITE_STAGING=0`).

## Order of execution (agreed)
1. Confirm consent-evidence policy (3 years) — **decided**, documented below.
2. Map all data flows, obtain the provider DPAs (Art. 28 DSGVO).
3. Verify Anthropic's actual API configuration and international transfers (Chapter V DSGVO).
4. Confirm Cloudflare and server log retention — **14 days decided**, configured in `ops/`.
5. Verify the Impressum address legally (FlexPost question, see below).
6. Business registration and legal disclosures (Impressum, prices incl. VAT, payment, refunds, AGB).
7. Specialist review of privacy policy, Impressum, AGB, DPAs, transfers, newsletter consent — then go-live approval.

## 1. Consent evidence (decided: 3 years, minimum data)
| Part | Kept | Not kept |
| --- | --- | --- |
| Consent evidence | HMAC of the address, consent text version, source/form, requested and confirmed timestamps | plain address after unsubscribe, IP, user agent |
| Withdrawal evidence | unsubscribe timestamp, method ("link") | — |
| Suppression | re-subscription only through a new double opt-in, creating a new record; never automatic reactivation or import | — |
Reasoning to have confirmed: proof of consent (Art. 7 Abs. 1 DSGVO); regular limitation period 3 years (§ 195 BGB).
The limitation period does not justify keeping other data that long; everything else follows the shorter periods
in `content/legal/datenschutz-fakten.md`. Technical note: the HMAC key is `SESSION_SECRET` today; a separate
`CONSENT_HMAC_KEY` is requested so rotating the session secret does not break matching.

## 2. Providers and data flows
| Provider | Role | What must be documented | Status |
| --- | --- | --- | --- |
| Anthropic | AI column mapping (only when `AI_PROVIDER=anthropic`) | data sent (headers + value shapes by default; real values only on user opt-in), storage, subprocessors, transfers | DPA/commercial terms: obtain; transfer basis: check |
| Cloudflare | static website, DNS, security; IPs and technical logs | CDN/DNS/security logs, retention, DPA | DPA: accept |
| Brevo | transactional mails (opt-in, login), later newsletter | opt-in records, delivery, unsubscribe | DPA (in Brevo's General Conditions of Use): accept before any mail goes via Brevo |
| Server host | app, database, temporary files | location (EU), access logs, backups (none by design), retention | choose provider, sign AVV |

### Anthropic — verified facts (1 Nov 2026)
- Inference default `"global"`: "may run in any available geography"; the only alternative is `"us"`. No EU option.
- Storage at rest follows the workspace geo; currently `"us"` is the only workspace geo.
- So an EU server does **not** make AI processing EU-only.
- Mitigations already built: AI is off by default (heuristic mapping, no network); when on, only column names and
  value shapes ("dd.dd.dddd", "Xxxxx") are sent unless the user switches on real sample values.
- Options for launch: (a) launch with AI mapping off; (b) AI on with shapes only, transfer basis documented after
  review; (c) real-value opt-in stays off until the review is done. Recommended: (a) or (b) — owner decides after review.
Source: https://platform.claude.com/docs/en/manage-claude/data-residency

### Brevo
DPA is part of Brevo's General Conditions of Use (DPA section at the end). Source:
https://help.brevo.com/hc/en-us/articles/15403782599570

## 4. Log retention (decided: 14 days)
Configured, not only promised: Caddy access log rolls with `roll_keep_for 336h`; container logs limited by size/count
(see `ops/RUNBOOK.md`, "Log retention"). Cloudflare's own log retention is set by Cloudflare and must be described
from its documentation. The privacy page states only what is configured.
Gap to close at server setup: rotation is size-based, so on a quiet server lines can be older than 14 days. Make it
strict on the host: journald `MaxRetentionSec=14day` and a daily time-based rotation of the Caddy log volume
(e.g. logrotate `daily`, `rotate 14`, `maxage 14`) — see `ops/RUNBOOK.md`.

## 5. Impressum address — FlexPost warning
A pure mail-forwarding address or a mere letterbox is not a "ladungsfähige Anschrift"; the address must be a real
place where the business can actually be found and served (eRecht24 summary of BGH V ZR 210/22; for natural persons
usually the residence). Before using FlexPost: ask the provider in writing whether the address allows service of
documents at that location (e.g. staffed premises, power of attorney to receive), and have the lawyer confirm.
If not: home address, or a real business address (co-working with service possible).
Source: https://www.e-recht24.de/news/abmahnung/10313-neues-urteil-ein-postfach-im-impressum-reicht-nicht-aus.html

## 6. Business identity (launch requirement)
Registration (Gewerbeanmeldung / legal form) · Impressum (full name, legal form, serviceable address, contact,
USt-IdNr. if any) · prices incl. VAT information · payment provider, invoicing, refunds/withdrawal information · domain
in the business's name · EU hosting. All replace `[[BUSINESS_ID_PENDING]]`.

## 7. Specialist review — scope to request
GDPR privacy policy (Art. 13/14) · DPAs (Art. 28) · international transfers (Chapter V) · cookies/tracking (the site
sets no cookies; app uses only necessary cookies — to confirm) · newsletter consent and withdrawal · Impressum and
consumer information · AGB · the scope line ("technisches Werkzeug, keine Steuer- oder Rechtsberatung").
Materials to hand over: `content/legal/datenschutz-fakten.md`, `site/templates/datenschutz.html`, this file,
`contracts/api.md` (retention), `ops/RUNBOOK.md` (logs).
