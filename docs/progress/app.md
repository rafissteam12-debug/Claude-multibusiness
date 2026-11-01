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
- No account deletion / data export endpoint yet.
- Fonts: system-ui until IBM Plex is self-hosted (ops).
