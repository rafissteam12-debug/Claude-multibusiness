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

## Wave 4 fix round (1 Nov)
7. **api.md — account endpoints (high, GDPR).** `GET /api/v1/account/export` -> JSON attachment
   `{export_created_at, product, account{email,plan,created_at,last_login_at}, seller_profile, mappings[{mapping_id,
   provider, model, mapping, columns, save_for_reuse, confirmed, created_at, updated_at}], usage[{month, valid_invoices}],
   note_de}` (no cell values). `DELETE /api/v1/account` (login, CSRF header, same-origin) -> `200 {"status":"deleted"}`;
   deletes user, sessions, seller profile, mappings, uploads + files on disk, jobs, generated files, usage, login tokens;
   clears the session cookie. Newsletter subscription is separate (own unsubscribe link).
8. **api.md — retention additions.** Raw upload deleted at a conversion that offered ≥ 1 valid file (otherwise kept until
   24 h); upload metadata (column names, samples, size) deleted with it, only the row count stays; accounts without
   login for 12 months deleted with all data; interrupted jobs marked `failed` at startup and expired after 24 h;
   events deleted after 13 months; on unsubscribe a consent proof (HMAC of the address with SESSION_SECRET, consent
   version, request/confirm/unsubscribe dates) is kept 3 years (owner to confirm the period). Privacy page (site/content)
   should state these.
9. **api.md — token links.** `GET ?token=` now answers `303` to the same path without query (token moved to an HttpOnly
   cookie scoped to that path, `Referrer-Policy: no-referrer` on the redirect); the confirm page shows the button; POST
   consumes (token from form field or cookie). Please update the "Magic-link and opt-in links" rule.
10. **api.md — errors.** Unreadable upload (`TableReadError`, incl. size/row/column/zip limits) -> `400 unreadable_file`
    (was 422). Malformed mapping PUT field types -> `400 invalid_mapping`; semantic mapping problems stay `422`.
    Unexpected errors -> `500 internal_error`.
11. **api.md — response extras.** `/conversions/{id}`: `mapping_id`, `upload_available`, `expires_de`, per invoice
    `notes_de` (e.g. missing delivery date) and `guideline_id`; `/check` may add `invalid_reason_de` when the profile is
    unknown.
12. **Content (H2).** App startup in staging/prod now fails on any `[prüfen` in `content/emails/*` (incl. `_footer.md`)
    or `content/help/*`.

## Status (orchestrator, 1 Nov, wave 4)
Wave 4 items merged into contracts/ (mapping.md, api.md, config.md), .env.example and .github/workflows/ci.yml; deferred items in docs/ideas.md.
13. **config.md — `CONSENT_HMAC_KEY` (medium, not implemented).** Consent records hash the e-mail with
    SESSION_SECRET. Rotating that secret breaks HMAC matching for all existing records. Please add a separate, stable
    `CONSENT_HMAC_KEY` (required outside dev; app falls back to SESSION_SECRET in dev). The app will switch once it
    is in config.md.
14. **api.md — consent records (owner decision 1 Nov).** Kept 3 years. Three parts: consent evidence (HMAC, version,
    source, requested/confirmed), withdrawal (unsubscribed_at, method `link`), suppression use (re-subscribe only via
    double opt-in, new record). Please replace "POST removes the address and its consent record" in the unsubscribe
    row, and update the privacy page.
15. **api.md (pre-review 6.7, orchestrator).** Line 14, unsubscribe row: replace "POST removes the address and its consent
    record" with "POST removes the address from the list and closes its consent record (kept 3 years, HMAC only)". Also
    remove "period to be confirmed by the owner" from the retention text (owner decided 3 years on 1 Nov). Add
    withdrawal method `reply` via `python -m app.admin unsubscribe`.
16. **api.md — login acceptance.** `POST /api/v1/auth/callback` needs form fields `accept_terms=1` and `b2b=1` when the
    address has no account, or when its stored AGB version differs from the current one (`agb-draft-1`). Without them
    it returns 400, the token is not consumed and no account is created. Please document this, and the users columns
    in the retention/export description.
17. **Site/content — pages linked from the app.** The app links `SITE_PUBLIC_URL/impressum/`, `/datenschutz/`, `/agb/`
    (all exist) and `/avv/` ("Auftragsverarbeitungsvertrag (Entwurf)", does not exist yet). The AGB page should
    carry version id `agb-draft-1`; a new AGB wording needs a new id. Tell the app, which then adds
    `app/legal_texts/terms-<id>.txt` and its hash, and asks every user once more.
18. **Site — consent label.** The subscribe checkbox label must stay word-for-word equal to
    `app/legal_texts/consent-2026-10-31-v1.txt`. Any change needs a new consent version, and the app must be told
    (integration test `test_site_checkbox_label_matches_stored_text`).
19. **Content (pre-review 6.5).** The opt-in mail promises unsubscribing by reply. This is now supported by the
    owner's command `python -m app.admin unsubscribe` (method `reply`). The deadline wording ("am selben Tag") is the
    owner's to confirm.

## Remediation release (app, 1 Nov)
20. **config.md — `CONSENT_HMAC_KEYS`** (replaces request 13 `CONSENT_HMAC_KEY`). Comma-separated `keyid:base64key`,
    first = current signing key, keys >= 32 bytes. Required in staging/prod; must differ from SESSION_SECRET; the
    first entry must not be `legacy-session`. Implicit `legacy-session` = SESSION_SECRET (records before the switch);
    after a SESSION_SECRET rotation list `legacy-session:<old SESSION_SECRET>` (raw value) to keep those records
    matchable. Dev/test default: none (legacy-session only).
21. **config.md — `ONBOARDING_OPEN`** `0`/`1`, default `0`. APP_ENV=prod only: new accounts need `1` AND non-draft AGB
    and AVV ids. Staging/dev/test always open.
22. **config.md — `AI_TRANSFER_CLEARED`** `0`/`1`, default `0`. Staging/prod: `AI_PROVIDER=anthropic` needs `1`
    (set only after the Chapter V review), else the app refuses to start. No `inference_geo` is set (Anthropic default
    "global").
23. **api.md — AVV acceptance.** `POST /api/v1/account/avv` (session + CSRF): JSON `{"accept": true,
    "avv_version": "avv-draft-1"}` -> 200 `{avv_version, avv_accepted_at}`; form `accept_avv=1` -> 303 /app/upload;
    400 `avv_required` without the tick, 409 `avv_version_changed` for a stale version. `POST /api/v1/uploads` -> 403
    `avv_required` (+ `avv_version`) until the current AVV version is accepted; asked again when it changes. Export
    `account` gains `avv_version`, `avv_accepted_at`. Current AGB id is now `agb-draft-2` (request 16).
24. **api.md — onboarding gate.** In prod with onboarding closed, `GET/POST /api/v1/auth/callback` for an address
    without an account returns a 403 page; the token is not consumed and no account is created.
25. **ops/RUNBOOK.md — key rotation.** Generate with `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`.
    Consent key: prepend the new `id:key`, keep old ones for 3 years. SESSION_SECRET rotation: first add
    `legacy-session:<old SESSION_SECRET>` to CONSENT_HMAC_KEYS, then rotate.
26. **content — checkbox texts.** Please add "Checkbox-Text agb-draft-2" to `content/legal/agb-entwurf.md` and
    "Checkbox-Text avv-draft-1" to `content/legal/avv-entwurf.md` (lines the user ticks; AVV label should contain the
    word "Auftragsverarbeitungsvertrag", AGB label 1 "Allgemeinen Geschäftsbedingungen", AGB label 2 the B2B
    statement). The app currently ships placeholders (TODO: replace `app/legal_texts/terms-agb-draft-2.txt`,
    `avv-avv-draft-1.txt` and their hashes in `app/settings.py`).
27. **site — `/avv/` page** carrying version id `avv-draft-1` (linked from the upload page).
