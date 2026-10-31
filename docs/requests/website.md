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
