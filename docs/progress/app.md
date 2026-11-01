# App agent — progress

## 2026-11-01 — wave 2 (branch `agent/app`)

### What is built
- `app.main:app` (FastAPI, created lazily via `create_app()`), every endpoint of `contracts/api.md` plus `/healthz`.
  JSON errors `{"error":{"code","message_de"}}` everywhere under `/api/` (incl. 404/405/422).
- Security (api.md "Security rules"): non-GET app endpoints need `X-CSRF-Token` (session token) and same origin
  (`Origin` == APP_PUBLIC_URL origin, or `Sec-Fetch-Site: same-origin`; any other `Sec-Fetch-Site` is rejected).
  CORS only on `/check`, `/subscribe`, `/events` for SITE_PUBLIC_URL, OPTIONS preflight answered, no credentials;
  public POSTs from other origins get 403. Magic-link, opt-in and unsubscribe links: GET shows a button, POST consumes.
  Tokens: random 32 bytes, stored as HMAC-SHA256, single use (atomic), 15 min TTL (unsubscribe: 1 year).
  Rate limits (sqlite `rate_hits`, keys are salted hashes): check 20/h per IP, magic link 5/h per e-mail + 20/h per IP,
  subscribe 10/h per IP (3/h per e-mail, silent), events 600/h, uploads 60/h per user.
  Headers: CSP without inline scripts (`script-src 'self'`), X-Frame-Options DENY, Referrer-Policy no-referrer, nosniff,
  Permissions-Policy, COOP, HSTS on https, `X-Robots-Tag: noindex, nofollow` and the "Testversion – nicht öffentlich"
  banner whenever APP_ENV != prod; `Cache-Control: no-store` on non-static responses.
  Session cookie `bb_session` HttpOnly, SameSite=Lax, Secure on https/staging/prod; sessions in DB (hashed id, 7 days).
- Logging: a filter on uvicorn access/error logs removes client addresses, strips query strings on
  `/api/v1/auth/callback|confirm|unsubscribe` and redacts any `token=`. Errors log only exception class names.
- Storage: stdlib sqlite3 at DATABASE_PATH, numbered migrations in `app/migrations/` (`001_init.sql`), tables per brief.
  No raw IPs; mappings store column names/constants/transforms only.
- Jobs: thread pool (2 workers). read_table -> apply -> build_cii(profile) -> validate -> totals_warning; ZUGFeRD via
  build_zugferd (FeatureUnavailable -> format "unavailable", job continues). Only valid files get download URLs and
  only while the monthly limit allows (free 3 / start 30 / business 300; `plan` column only). Valid invoices over the
  limit are shown as valid with status `limit` and no download. Every invoice gets a readable PDF labelled
  "keine E-Rechnung". ZIP of all offered files (`zip_url`). Max 500 invoices per job.
- Retention: raw upload deleted when the job is done or after RETENTION_HOURS; files, job results and error texts
  after RETENTION_HOURS (status `expired`); also checked on read. Background timer (10 min, not in APP_ENV=test) and
  `python -m app.purge` for cron. Unconfirmed opt-ins removed after 7 days.
- Mailer: `console` (prints subject + link, keeps an outbox; refused in prod) and `brevo` (urllib, transactional API;
  not called in tests). Texts from `content/emails/` (Jinja + Markdown, footer kept with `[[BUSINESS_ID_PENDING]]`).
  Opt-in -> welcome 1 on confirmation, welcome 2 after 3 days (timer tick).
- Pages (Jinja2, vanilla JS in `app/static`, no CDNs, brand colours, 375 px): `/login`, token confirm pages, `/app`,
  `/app/profile` (BR-CO-26 explained), `/app/upload`, `/app/mapping/{id}` (dropdowns, constants, transforms in words,
  confidence colour + word, reason_de, "Vorschlag ohne KI", "Echte Beispielwerte an die KI senden" default off,
  BT-10 hint, save for reuse), `/app/jobs/{id}` (layers incl. skipped with reason), `/bestaetigt`, `/hilfe`,
  `/hilfe/{slug}` (renders `content/help/`). Scope line from brand.md on every page. No prices.

### How to run
```
python -m uvicorn app.main:app --port 8000      # offline with defaults; login link is printed to stdout
python -m pytest app/tests -q                   # 76 tests (18 marked integration: engine + mapping)
python -m app.purge                             # one retention run
```

### Stubbed / not verified
- Brevo: request built and sent through an injectable opener; never called against the real API.
- AI provider: only the offline fallback path is exercised (no key).
- ZUGFeRD: always "unavailable" locally (no MUSTANG_JAR); the success path is untested here.
- Dev without SESSION_SECRET uses a random per-process secret (sessions end on restart).

### Open issues
- Rate limits use `request.client.host`; behind a proxy run uvicorn with `--proxy-headers` and trusted forwarders (ops).
- (wave 4) Account deletion / data export added — see below.
- Fonts: system-ui until IBM Plex is self-hosted (ops).

## 2026-11-01 — wave 4 fix round (review `docs/review/REVIEW.md`)

### Fixed
- **H1** `read_table`, `propose`, account deletion run via `run_in_threadpool`; `/check` validation via
  `anyio.to_thread` (limiter 4). Upload parsed once: columns, row count and per-column samples cached in the
  `uploads` row (`samples_json`, migration `002_retention.sql`) plus a 4-entry/15-min in-memory table cache
  (`app/tablecache.py`) for propose and the job. `TableReadError` -> **400** `unreadable_file` with its German text.
  Test: `/healthz` answers in < 1 s while a monkeypatched 2-s `read_table` runs.
- **H2** `MailTemplates(strict=True)` and `helptexts.load_articles(strict=True)` raise `UnverifiedContent` on `[prüfen`
  (also in included partials). The app loads strictly at startup in staging/prod (`main.content_strict`); dev/test log a
  warning. Unit tests on temp fixtures; integration test `test_real_content_rendered_by_app_has_no_markers` fails until
  the content fix is merged (only failure in the suite on this branch).
- **H3** `check.detect_format(data, kind, report)` labels from the profile / `guideline_id` (uses
  `engine.validation.describe_guideline`): XRechnung only for an XRechnung guideline ID, ZUGFeRD for other recognised
  CII/PDF, `unknown` otherwise. `enforce_known_profile` makes an unknown profile never valid; `summary_de` says
  "Gültig" only when `valid` is true. Jobs also treat profile `unknown` as invalid.
- **H4** `GET /api/v1/account/export` (JSON download: account, seller profile, mappings, usage; no cell values) and
  `DELETE /api/v1/account` (CSRF + same-origin): removes files on disk, uploads, files, jobs, mappings, usage, sessions,
  seller profile, login tokens, rate-limit buckets and the user; clears the cookie. Profile page: "Konto löschen" with a
  confirmation step (checkbox + second button). Purge deletes accounts without login for 12 months.
- **M1** One app-wide `BoundedSemaphore(2)` around every validate call (`app/validation.py`); conversions build all
  XMLs first and validate them in one `engine.validate_many` call. The engine's own KoSIT semaphore is *not* acquired
  from outside (it is taken inside validate/validate_many; nesting could deadlock).
- **M2** Token links: `GET ?token=` moves the token into an HttpOnly cookie limited to that path and 303-redirects to the
  path without query; the redirect carries `Referrer-Policy: no-referrer`. The confirm page has no token in URL or HTML
  and keeps `same-origin` (no-referrer on the page itself makes browsers send `Origin: null` on the POST, which our
  origin check rejects — comment and test `test_null_origin_is_rejected_but_policy_avoids_it` kept). POST accepts the
  token from the form field (tests/no-cookie) or the cookie.
- **M3** Mapping page lists propose `warnings` and its own "Kein Leistungsdatum gefunden" (link to § 14 UStG) and offers
  the checkbox "Leistungsdatum = Rechnungsdatum" (maps `/delivery_date` to the issue-date column with the same
  transforms). Job result: `notes_de` per invoice without delivery date/period, shown as a warning.
- **M4/M6** Convert button disabled while a required target is unmapped (`/number`, `/issue_date`, `/buyer/name`,
  `/lines/*/description|quantity|net_price`, `unmapped_required` from propose, `/buyer_reference` for XRechnung);
  inline "nicht zugeordnet – bitte Spalte wählen oder festen Wert eingeben" + summary. Constant select for
  `/lines/*/vat_category` (S/Z/E/AE/K/G/O in plain German); `/buyer_reference` constant as text. UI-only gate: the API
  still accepts such conversions (invoices then fail validation and are not offered).
- **M7** Raw upload deleted at job end only if ≥ 1 valid file was offered; otherwise kept (24 h rule still applies) and
  the job page offers "Zuordnung ändern" (`mapping_id`, `upload_available` in the job response).
- **M8** Mapping table becomes stacked cards below 760 px. Checked with Playwright at 375 px: no horizontal scroll
  (scrollWidth 375), select 317 px wide, button disabled until BT-10 set (screenshot in the agent scratchpad only).
- **M9** Startup marks `queued`/`running` jobs failed ("Server neu gestartet – bitte erneut umwandeln"); purge expires
  them after 24 h; `too_many_jobs` only counts jobs from the last hour.
- **M12** Deleting an upload also clears `columns_json` ('[]'), `samples_json`, `size`; only `row_count` stays.
- **L1** Mapping PUT type checks -> 400 German message; the HTTP middleware catches unexpected exceptions, logs only
  the class name and answers 500 (JSON under /api, short HTML page otherwise).
- **L2** Job page: "bis 2. November, 01:37 Uhr" (Europe/Berlin, `expires_de`); codes shown small after the German text.
- **L4** Unsubscribe keeps a `consent_records` row: HMAC-SHA256(SESSION_SECRET, lowercased e-mail), consent version,
  request/confirm/unsubscribe times; purged 3 years after unsubscribe (period to be confirmed by the owner). Events
  purged after ~13 months (396 days).
- **L9** `PRAGMA secure_delete = ON` on every connection.
- **L7 (note, no code)** The free limit (3 valid invoices/month) is per account = per e-mail address; anyone can get more
  with new addresses, and deleting the account also resets the counter. Acceptable for staging; decide with payments
  (e.g. per seller VAT id/IBAN fingerprint).

### How to run
`python -m pytest -m "not network" app` — all app tests pass except the real-content `[prüfen` integration test until
content is merged. Whole suite on this branch: 400 passed, 2 skipped, 1 failed (that test).

### Open issues
- Changing SESSION_SECRET makes existing consent HMACs unverifiable (no lookup possible); keep the secret stable or add
  a dedicated key later (would need a config.md entry).
- Server-side gate for unmapped required fields is not enforced (UI only), to keep the API usable for scripted checks.

### Follow-up (owner decision: consent proof, 3 years, minimum data) — migration `003_consent_records.sql`
- `consent_records` now has three parts. **Consent evidence**: `email_hmac`, `consent_version`, `source` (from
  /subscribe), `requested_at`, `confirmed_at`, written when the double opt-in is confirmed. **Withdrawal evidence**:
  `unsubscribed_at`, `method='link'`, set on the open record at unsubscribe. **Suppression use**: a later /subscribe
  for an unsubscribed HMAC goes through the normal double opt-in only (no auto-reactivation, no import). Confirming it
  creates a NEW record, and the old withdrawal record stays. No plain e-mail, no IP, no user agent.
- Purge: 3 years after `unsubscribed_at`, or 3 years after `confirmed_at` when never unsubscribed and the subscribers
  row is gone.
- Confirm now only acts on a pending request (`confirmed_at IS NULL`). A second confirm of an already confirmed
  address sends no second welcome mail and writes no second record.
- **Known limitation:** the HMAC is keyed with SESSION_SECRET. If that secret is rotated, old records can no longer be
  matched to an address, so purge-by-subscription and suppression lookups stop working for those records. This needs a
  separate `CONSENT_HMAC_KEY` (request 13); not implemented.

### Legal pre-review items (docs/legal/PRE_REVIEW.md) — migration `004_terms_acceptance.sql`
- 2.13 / 7.7: every app page footer links Impressum, Datenschutz, AGB (absolute URLs on SITE_PUBLIC_URL). The login form
  has a line about the AGB, B2B-only use and the privacy notice.
- 8.1 / 9.10: the login confirm page asks for two required checkboxes: AGB accepted (version `agb-draft-1`) and "Ich
  nutze Belegbrücke ausschließlich für mein Unternehmen (B2B)". These are asked before the account exists, and again
  at the next login for accounts with another or no stored version. Without both boxes the token is not consumed and
  no user is created. `users.terms_version`, `terms_accepted_at` and `b2b_confirmed_at` are stored and included in the
  data export. Sessions that started before this change are not interrupted; the user is asked at the next login.
- 6.4: verbatim texts per version in `app/legal_texts/` (`consent-2026-10-31-v1.txt`: heading, intro, checkbox label,
  scope; `terms-agb-draft-1.txt`: the two acceptance labels). Each file is pinned by sha256 in `app/settings.py`, and
  the app refuses to start if one is missing or changed. Any wording change needs a new version. An integration test
  compares the site's subscribe label with the stored text.
- 6.5: `python -m app.admin unsubscribe <e-mail>` handles a reply "abmelden": it closes the consent record with
  `method='reply'` and deletes the subscription. It prints no address. Shared logic is in `app/consent.py`.
- 2.14: the unsubscribe page now says "pseudonymisierter Prüfwert (HMAC)" instead of "nicht umkehrbar".
- Profile page links "Auftragsverarbeitungsvertrag (Entwurf)" to `SITE_PUBLIC_URL/avv/`. The page itself is
  content/site's job (request 17).

## 2026-11-01 — remediation release (P0-1 … P0-4, P1-7)

### What changed
- **P0-1 consent keyring.** `CONSENT_HMAC_KEYS="keyid:base64key,..."` (first = current signing key, keys >= 32 bytes,
  ids `[A-Za-z0-9._-]`). Implicit last entry `legacy-session` = current SESSION_SECRET, unless listed explicitly as
  `legacy-session:<old SESSION_SECRET>` (raw value, not base64). Migration `005_consent_key_id.sql` adds
  `consent_records.key_id` (default `legacy-session`, so every existing record stays verifiable). New records store the
  current key id. Withdrawal (link, reply/admin) and the purge active-set match by (key_id, hmac) under every key.
  Re-subscribe performs no HMAC lookup (it only creates a new record at confirmation, current key). Staging/prod refuse
  to start without CONSENT_HMAC_KEYS, with `legacy-session` first, or when the current key equals SESSION_SECRET.
  **Rotation procedure:** consent key: prepend the new key and keep the old one listed until all its records are
  purged (3 years). SESSION_SECRET: once a dedicated key exists, rotating it does not affect new records; records with
  `legacy-session` stay matchable only while the OLD secret is listed as `legacy-session:<old>` (RUNBOOK request).
- **P0-2 purge.** Audit claim checked: in the old code `r["email"]` was read from `SELECT email FROM subscribers`
  (column exists), not from the `email_hmac` query, so it was not a crash. Rewritten for the keyring; records under a
  key id that is no longer configured are kept (cannot tell if still subscribed) and counted in a warning (no data).
- **P0-3 terms.** Current id `agb-draft-2` (`app/legal_texts/terms-agb-draft-2.txt`, pinned); `agb-draft-1` stays
  pinned for existing acceptances, those users are asked again. Checkbox labels on the login page are now rendered
  from the stored text verbatim. `ONBOARDING_OPEN` (0/1, default 0): in APP_ENV=prod a new account is refused (403
  page, token not consumed, no user row) unless ONBOARDING_OPEN=1 AND neither TERMS_VERSION starts with `agb-draft`
  nor AVV_VERSION with `avv-draft`. Existing accounts log in normally; staging/dev/test unaffected.
- **P0-4 AVV.** `avv-draft-1` (`app/legal_texts/avv-avv-draft-1.txt`, pinned). Migration `006_avv_acceptance.sql`
  adds `users.avv_version`, `users.avv_accepted_at`. `POST /api/v1/account/avv` (session + CSRF; JSON
  `{"accept": true, "avv_version"?}` or the upload-page form) records it; stale version -> 409. `POST /api/v1/uploads`
  returns 403 `avv_required` (German message, `avv_version`) until the current version is accepted; the upload page
  shows the checkbox instead of the upload form. Included in the account export.
- **P1-7 AI guard.** Staging/prod refuse `AI_PROVIDER=anthropic` without `AI_TRANSFER_CLEARED=1`. Default stays
  `heuristic`; no `inference_geo` is set anywhere (Anthropic default `"global"`, LAUNCH_COMPLIANCE.md section 2).

### Tests
`app/tests/test_app_remediation.py` (31 cases): key rotation (session secret, consent key), legacy migration,
startup refusals, five purge cases + unknown key, terms/labels/gate, AVV flow, AI guard. Test helper `login()` now
accepts the AVV by default (`avv=False` to skip).

### Open
- Checkbox texts `agb-draft-2` / `avv-draft-1` are now the verbatim content blocks (content/legal/agb-entwurf.md,
  avv-entwurf.md; integration test `test_app_checkbox_texts_equal_content_blocks`). AVV label links
  "Vertrag über die Auftragsverarbeitung" to SITE_PUBLIC_URL/avv/, AGB label links to /agb/.
- In prod, a magic link is still sent to a new address while onboarding is closed (refused at the callback; keeps
  the response identical so no account enumeration).
