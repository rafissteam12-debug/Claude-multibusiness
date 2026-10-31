# App API contract v1

Base: the app (FastAPI) serves both JSON endpoints under `/api/v1` and its own HTML pages.
The static website (Cloudflare) calls only the public endpoints marked PUBLIC, via
`APP_PUBLIC_URL`. All responses JSON, UTF-8. Errors: `{"error": {"code": "...", "message_de": "..."}}`.
Rate limits are per IP hash (never store raw IPs).

## Public — free checker (no login)
| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/api/v1/check` PUBLIC | multipart `file` (XML or PDF, max 5 MB) | `{"valid": bool, "format": "XRechnung-CII"|"XRechnung-UBL"|"ZUGFeRD"|"unknown", "layers": [{"name","ran","errors":[{"id","message_de","location"}],"warnings":[...]}], "summary_de": str}` — file discarded after the call. Rate limit 20/hour. |
| POST | `/api/v1/subscribe` PUBLIC | `{"email", "consent": true, "source": "check"|"guide"|"ig-..."}` | `202`; starts double opt-in via mailer adapter |
| GET | `/api/v1/confirm?token=` PUBLIC | — | redirects to `/bestaetigt` |
| POST | `/api/v1/events` PUBLIC | `{"name","path","code"}` | `204`; whitelist of event names in `config.md` |

## App — needs login (magic link, no passwords)
| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/magic-link` | `{"email"}` -> sends login link (mailer adapter) |
| GET | `/api/v1/auth/callback?token=` | sets session cookie (HttpOnly, Secure, SameSite=Lax), redirects `/app` |
| POST | `/api/v1/auth/logout` | clears session |
| POST | `/api/v1/uploads` | multipart CSV/XLSX (max 10 MB) -> `{"upload_id","columns":[...],"sample_rows":[...],"row_count"}`; raw file in temp dir, deleted after 24 h |
| POST | `/api/v1/mappings/propose` | `{"upload_id","seller_profile_id"}` -> `{"mapping_id","fields":[{"target":"<schema path>","source_column"|"constant","confidence":0-1,"reason_de"}],"grouping":{"invoice_number_column","mode":"row_per_invoice"|"row_per_line"}}` |
| PUT | `/api/v1/mappings/{id}` | user-corrected mapping; saved for reuse |
| POST | `/api/v1/conversions` | `{"upload_id","mapping_id","formats":["xrechnung-cii","zugferd"]}` -> `{"job_id"}` |
| GET | `/api/v1/conversions/{job_id}` | `{"status":"queued"|"running"|"done"|"failed","invoices":[{"number","valid","errors":[...],"download_urls":{...}}]}` |
| GET | `/api/v1/files/{file_id}` | download; 404 after 24 h |
| GET/PUT | `/api/v1/seller-profile` | the user's own company data (seller block of the schema) |
| GET | `/api/v1/usage` | invoices converted this month vs plan limit |

## Plans (enforced in app, prices NOT shown publicly until business ID is done)
`free`: 3 valid invoices per calendar month. `start`: 30. `business`: 300. Payment
integration is out of scope until Stage "Business ID"; the app has a `plan` column only.

## Pages served by the app
`/app` (dashboard), `/app/upload`, `/app/mapping/{id}`, `/app/jobs/{id}`, `/app/profile`,
`/login`, `/bestaetigt`. All German. Vanilla JS. Must work at 375 px width.
