# Requests from the app agent (2026-11-01)

1. **api.md — form field for CSRF (low).** No-JS forms (logout button, magic-link confirm page, login fallback) send the
   token as `csrf_token` form field (urlencoded bodies only); JSON/multipart requests use the `X-CSRF-Token` header.
   Pre-login endpoints (`/auth/magic-link`, `/auth/callback` POST) use a signed double-submit token bound to a
   `bb_pre` cookie, plus the origin check. Please document.
2. **api.md — `consent_version` optional (medium).** The site's subscribe form does not send `consent_version` yet;
   the app stores the current version (`2026-10-31-v1`) when it is missing and rejects unknown ones. Site: please send it.
3. **api.md — response extras (low).** `/conversions/{id}` also returns `job_id`, `profile`, `formats`, `created_at`,
   `expires_at`, `row_errors`, `formats_unavailable`, `summary`, and per invoice `layers`, `warnings`, `totals_warning`,
   `formats{kind:{status,message_de}}` (status `valid|invalid|unavailable|limit`), `counted`, `limit_reached`,
   `download_urls.pdf` (readable PDF, not an e-invoice). `/mappings/propose` accepts `send_real_values` and
   `ignore_saved` and returns `reused`. `/healthz` added (ops). Please add to the contract.
4. **Content — free-plan limit behaviour confirmed** (content request 7): all invoices are validated; valid ones are
   offered up to the limit; over the limit they show "gültig, Limit erreicht" without download and do not count.
5. **Ops — proxy headers.** Run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy>` so per-IP rate limits see the
   real client; the app hashes it and never stores or logs it.
6. **Unsubscribe token TTL.** api.md's 15 min TTL applies to login/opt-in links; unsubscribe links in mails live 1 year
   (single use). Please confirm.

## Status (orchestrator, 1 Nov)
1 csrf form field + bb_pre: in api.md. 2 consent_version optional in contract AND the site now sends it. 3 extra fields + /healthz: in api.md. 4 free-limit behaviour: content texts to be checked in the wave-4 review. 5 --proxy-headers: added to ops/Dockerfile (orchestrator edit). 6 unsubscribe tokens single use, 1 year: confirmed in api.md. Account deletion endpoint: wave 4 fix round (GDPR).
