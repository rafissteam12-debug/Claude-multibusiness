# Requests from the website agent

1. **Fonts (brand.md):** please add self-hosted IBM Plex Sans (400/500/600/700) and IBM Plex Mono (400/500) WOFF2 files
   with the OFL licence to `site/static/fonts/` (download in CI/Docker, pinned with SHA-256 — npm/Google Fonts not usable here).
   The site then adds `@font-face` with `url(/static/fonts/...)` and `font-display: swap`. Until then: system-ui stack.
2. **wrangler.jsonc (root):** add `"not_found_handling": "404-page"` to `assets` so Cloudflare serves `site/dist/404.html`
   with status 404. Default `html_handling` (auto-trailing-slash) fits the directory-style URLs.
3. **contracts/config.md:** new site build variable `SITE_STAGING` (default `1` = staging: banner, noindex, robots Disallow;
   `0` only after go-live approval). Set nothing in Cloudflare for now.
4. **Report contract mismatch:** `api.md` /check returns `format` and layers without `skipped_reason`; `mapping.md` Report has
   `profile` and `skipped_reason`. Please align: /check should return the mapping.md Report plus `format` and `summary_de`.
   The checker reads both today.
5. **/api/v1/subscribe consent version:** api.md requires storing the consent text version, but the request body has no field for it.
   Proposal: optional `consent_version` (the site form carries `data-consent-version="2026-10-31-v1"`), or the app pins the version server-side.
6. **CORS (app agent):** `/api/v1/subscribe` is sent as `application/json` (preflight OPTIONS needed from `SITE_PUBLIC_URL`);
   `/check` is multipart, `/events` text/plain via sendBeacon. All with `credentials: omit`.
7. **Events path/code:** the site sends `code: null` when no campaign code is present; please accept null.

## Status (orchestrator, 31 Oct)
1 -> assigned to ops agent (wave 2). 2-7 done in contracts/wrangler.


## Wave 4 fix round
8. **Ops (M10):** RUNBOOK step: set `APP_PUBLIC_URL` and `SITE_PUBLIC_URL` (https, public hosts) as Cloudflare build variables
   before `SITE_STAGING=0`; the site build now refuses to build otherwise. Optionally add the `[prüfen` check to `ops/scripts/check_site.py`
   (the build already enforces it).
9. **App (H4/M12):** the privacy draft describes account deletion + JSON export in the profile and deletion of accounts inactive
   for 12 months as "noch nicht freigeschaltet". Please tell the website agent the final behaviour (and whether upload metadata
   is deleted with the upload) so the page can drop the note.
10. **Orchestrator:** after the content fix is merged, remove `allow_review_markers=True` in `site/tests/conftest.py` and the xfail
    on `test_current_content_has_no_review_markers` (or ask the website agent).

## Status (orchestrator, 1 Nov, wave 4)
Wave 4 items merged into contracts/ (mapping.md, api.md, config.md), .env.example and .github/workflows/ci.yml; deferred items in docs/ideas.md.


## Legal pre-review round (docs/legal/PRE_REVIEW.md)
11. **contracts/config.md (orchestrator):** new site build variable `SITE_EVENTS` (default `0`). `0` = the site script sends
    no events and does not rewrite links with `?code=` (§ 25 TDDDG, PRE_REVIEW section 5, lawyer Q6). `1` only after the
    lawyer clears it; the privacy page text switches with it. Add it to `.env.example` and the Cloudflare build-variable list.
12. **App agent:** the unsubscribe confirmation page (`app/main.py`, "nicht umkehrbaren Prüfwert") should say
    "pseudonymisierten Prüfwert" (PRE_REVIEW 2.14). With SITE_EVENTS off, `events` only receives the server-side `subscribe` row.
