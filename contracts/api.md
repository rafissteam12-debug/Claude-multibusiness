# App API contract v1

Base: the app (FastAPI) serves both JSON endpoints under `/api/v1` and its own HTML pages.
The static website (Cloudflare) calls only the public endpoints marked PUBLIC, via
`APP_PUBLIC_URL`. All responses JSON, UTF-8. Errors: `{"error": {"code": "...", "message_de": "..."}}`.
Rate limits are per IP hash (never store raw IPs).

## Public — free checker (no login)
| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/api/v1/check` PUBLIC | multipart `file` (XML or PDF, max 5 MB) | the Report from `mapping.md` (valid, profile, layers with skipped_reason, totals_warning) PLUS `"format": "XRechnung-CII"\|"XRechnung-UBL"\|"ZUGFeRD"\|"unknown"` and `"summary_de": str`. File discarded after the call. Rate limit 20/hour. |
| POST | `/api/v1/subscribe` PUBLIC | `{"email", "consent": true, "consent_version"?: "2026-10-31-v1" (optional; if absent the server stores its current version; unknown versions are rejected), "source": "check"|"guide"|"ig-..."}` (JSON; preflight OPTIONS must be answered) | `202`; starts double opt-in; server stores the consent version it knows, rejects unknown versions |
| GET | `/api/v1/confirm?token=` PUBLIC | — | shows a confirm button; POST same path consumes the token, then redirects to `/bestaetigt` |
| GET/POST | `/api/v1/unsubscribe?token=` PUBLIC | — | GET shows a confirm button, POST removes the address and its consent record; every marketing mail carries this link |
| POST | `/api/v1/events` PUBLIC | `{"name","path","code": str\|null}` as text/plain (sendBeacon) | `204`; whitelist of event names in `config.md` |

## App — needs login (magic link, no passwords)
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/magic-link` | `{"email"}` -> sends login link (mailer adapter) |
| GET | `/api/v1/auth/callback?token=` | sets session cookie (HttpOnly, Secure, SameSite=Lax), redirects `/app` |
| POST | `/api/v1/auth/logout` | clears session |
| POST | `/api/v1/uploads` | multipart CSV/XLSX (max 10 MB) -> `{"upload_id","columns":[...],"sample_rows":[...],"row_count"}`; raw file in temp dir, deleted after 24 h |
| POST | `/api/v1/mappings/propose` | `{"upload_id"}` (the user's single seller profile is used) -> `{"mapping_id","fields":[{"target":"<schema path>","source_column"|"constant","confidence":0-1,"reason_de"}],"grouping":{"invoice_number_column","mode":"row_per_invoice"|"row_per_line"}}` |
| PUT | `/api/v1/mappings/{id}` | user-corrected mapping; saved for reuse |
| POST | `/api/v1/conversions` | `{"upload_id","mapping_id","formats":["xrechnung-cii","zugferd"], "profile":"xrechnung"|"zugferd"}` -> `{"job_id"}` |
| GET | `/api/v1/conversions/{job_id}` | `{"status":"queued"|"running"|"done"|"failed","invoices":[{"number","valid","errors":[...],"download_urls":{...}}]}` |
| GET | `/api/v1/files/{file_id}` | download; 404 after 24 h |
| GET/PUT | `/api/v1/seller-profile` | the user's own company data (seller block of the schema) |
| GET | `/api/v1/usage` | invoices converted this month vs plan limit |
| GET | `/api/v1/account/export` | JSON attachment: account (email, plan, created_at, last_login_at), seller profile, mappings (no cell values), usage per month |
| DELETE | `/api/v1/account` | deletes user, sessions, seller profile, mappings, uploads + files, jobs, usage, login tokens; clears the session -> `{"status":"deleted"}`. Newsletter subscription is separate. |
| GET | `/healthz` | `{"status":"ok"}`, no auth, used by the Docker healthcheck |

Extra response fields the app may add (clients must ignore unknown keys): conversion details per invoice, `reused: bool` on mapping proposals when a saved mapping matched.

## Plans (enforced in app, prices NOT shown publicly until business ID is done)
`free`: 3 valid invoices per calendar month. `start`: 30. `business`: 300. Payment
integration is out of scope until Stage "Business ID"; the app has a `plan` column only.

## Pages served by the app
`/app` (dashboard), `/app/upload`, `/app/mapping/{id}`, `/app/jobs/{id}`, `/app/profile`,
`/login`, `/bestaetigt`. All German. Vanilla JS. Must work at 375 px width.

## Security rules (v1, mandatory)
- Every non-GET request under `/api/v1` (except PUBLIC ones) requires header `X-CSRF-Token` (or a `csrf_token`
  form field for no-JS forms) matching the session's token, AND an `Origin`/`Sec-Fetch-Site` check (same-origin only).
  Before login, the token is bound to the short-lived `bb_pre` cookie.
- CORS: PUBLIC endpoints allow origin `SITE_PUBLIC_URL` only, no credentials, and answer OPTIONS preflight (JSON on /subscribe). App endpoints: no CORS.
- `/api/v1/events` accepts `text/plain` bodies (sendBeacon) containing JSON.
- Magic-link, opt-in and unsubscribe links: `GET ?token=` answers `303` to the same path without the query (token moved to
  an HttpOnly cookie scoped to that path, `Referrer-Policy: no-referrer` on the redirect); the confirm page shows a button; a `POST` consumes the token
  (mail scanners must not burn tokens or fake consent). Tokens single-use, stored hashed, 15 min TTL for login and opt-in (unsubscribe links: single use, 1 year),
  never written to logs. Magic-link requests rate-limited per e-mail (5/hour) and per IP hash.
- Double opt-in stores: e-mail, consent text version, timestamp of request and confirmation.
- Consent text v1 (2026-10-31-v1) covers: the welcome mails and occasional notes on e-invoice rule changes and Belegbrücke. No other mail types without a new consent version.
- XML parsing of untrusted files: `resolve_entities=False, no_network=True, huge_tree=False`; size limits enforced before parsing.
- `/files/{id}` checks ownership; conversions add `zip_url` for all files of a job; after 24 h job status becomes `expired`.
- Retention: raw upload deleted at successful conversion or after 24 h, whichever comes first; generated files and
  job error messages (may contain cell values) deleted after 24 h; mappings kept (no cell values).
  "Successful" = at least one valid file offered; otherwise the raw upload stays until 24 h so the mapping can be corrected.
  Upload metadata (column names, samples, size) is deleted with the upload; only the row count stays.
  Accounts without login for 12 months are deleted with all data. Jobs interrupted by a restart are marked `failed`
  at startup and expire after 24 h. Events are deleted after 13 months. On unsubscribe a consent proof (HMAC of the
  address keyed with SESSION_SECRET, consent version, request/confirm/unsubscribe dates) is kept 3 years (period to be confirmed by the owner).
- Errors: unreadable upload incl. size/row/column/zip limits -> `400 unreadable_file`; malformed mapping PUT -> `400 invalid_mapping`;
  semantic mapping problems -> `422`; unexpected -> `500 internal_error` (log the exception class name only).
- Content guard: in staging/prod the app refuses to start if any mail or help text contains `[prüfen`.
