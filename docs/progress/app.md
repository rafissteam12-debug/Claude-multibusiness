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
