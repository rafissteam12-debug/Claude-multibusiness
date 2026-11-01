# Website agent — progress

## 31 Oct 2026 — wave 1: static site + checker UI

**Built**
- `site/build.py`: Jinja2 templates (`site/templates/`) + guide markdown -> `site/dist/`. Needs jinja2, markdown, PyYAML (pure-Python fallback; for front matter).
- `site/config.py`: the one config. Brand names, colours, scope line parsed from `contracts/brand.md`;
  `APP_PUBLIC_URL` / `SITE_PUBLIC_URL` from env (defaults per `contracts/config.md`); `SITE_STAGING` (default ON; `0` turns it off).
- Pages: `/`, `/belegbruecke/`, `/e-rechnung-pruefen/`, `/ratgeber/` + one page per guide, `/impressum/`, `/datenschutz/`, `/agb/`, `/bestaetigt/`, `/404.html`.
  URLs use directory style (`/x/index.html`) so both Cloudflare assets and `http.server` serve them.
- Checker (`static/checker.js`): validates type/size (XML/PDF, 5 MB), POSTs multipart to `APP_PUBLIC_URL/api/v1/check`,
  renders per-layer pass / fail / "übersprungen – reason", errors with id, message_de, location; overall valid only if
  `valid === true` AND no layer has errors AND at least one layer ran. Mock mode: `?mock=1`, or automatically when the API is
  unreachable (clearly labelled "Beispielbericht … Ihre Datei wurde nicht geprüft"). Bundled `static/mock-report.json`.
- Sign-up box (checker + guide pages): unticked consent checkbox, POST JSON to `/api/v1/subscribe` with source `check`/`guide`.
- `static/site.js`: events via `navigator.sendBeacon` (text/plain JSON `{name,path,code}`) for page_view, link_click, check_run, subscribe;
  `?code=` (validated `[a-z0-9-]`, max 32) carried by rewriting internal and app links. No cookies, no Web Storage.
- Staging: banner "Testversion – nicht öffentlich", meta robots noindex, `_headers` with X-Robots-Tag + CSP and security headers,
  `robots.txt` Disallow: /. Sitemap, canonical, Open Graph always generated.
- Guides: from `content/guides/*.md`; if none, 2 samples from `site/fixtures/guides/` labelled "Beispieltext". Missing front matter keys,
  bad slug, empty sources fail the build loudly. Sources + "Zuletzt geprüft am …" under each guide.

**Run**
```
python site/build.py                      # -> site/dist
python -m http.server -d site/dist 8080   # http://localhost:8080 ; checker offline: /e-rechnung-pruefen/?mock=1
python -m pytest site/tests -q            # 35 tests; JS behaviour tests use node if installed, else skipped
```

**Stubbed / placeholders**
- Legal pages: `[[BUSINESS_ID_PENDING]]`, privacy text marked "Entwurf, juristische Prüfung ausstehend". Prices: placeholder only.
- Fonts: system-ui stack (IBM Plex requested). No og:image. No Ada visuals on the site yet.

**Open issues**
- Report shape differs between `contracts/api.md` (`format`, no `skipped_reason`) and `contracts/mapping.md` (`profile`, `skipped_reason`); checker accepts both (see requests).
- `/bestaetigt` exists on both site and app (api.md); the site version is a static thank-you page.
- Cloudflare does not serve `404.html` for unknown paths unless `not_found_handling` is set (see requests).
- Fixed-page sources (BMF FAQ, §§ 14, 27 UStG, DSGVO, § 5 DDG) were last checked 31 Oct 2026; re-check before go-live.


## Wave 4 fix round (REVIEW H2, M10, M12/H4 site part)

**Built**
- `site/build.py` fails (exit 1, message on stderr) if any rendered page contains `[prüfen` (case-insensitive):
  each hit names the rendered page and line plus the source file and line (guide markdown or template).
- With `SITE_STAGING=0` the build refuses an unset, localhost/loopback (`localhost`, `*.localhost`, `127.x`, `::1`, `0.0.0.0`)
  or non-https `APP_PUBLIC_URL` / `SITE_PUBLIC_URL`. Staging builds keep the localhost defaults.
- `static/checker.js`: no automatic mock fallback any more. App unreachable -> status
  "Der Prüfdienst ist gerade nicht erreichbar. Bitte später erneut versuchen.", report hidden. Mock only with `?mock=1` (labelled as before).
- `templates/datenschutz.html` rebuilt from the data model (app/migrations/001_init.sql, app/jobs.py purge, app/main.py,
  mapping/ai.py, ops/Caddyfile): table of every data category with purpose and retention, processors (EU hosting planned,
  Cloudflare, Brevo, Anthropic; third-country location stated as a fact), rights Art. 15-21/7(3)/77, controller placeholder.
  Marked "Entwurf – wird vor Veröffentlichung geprüft". `content/legal/datenschutz-fakten.md` did not exist yet; facts taken from code.
- Tests: marker check and URL checks use temporary fixtures; DOM-simulated checker tests (node) for unreachable app and `?mock=1`;
  privacy page fact test.

**Known state**
- `python site/build.py` currently FAILS on 6 `[prüfen` markers in 5 `content/guides/*.md` (content agent removes them).
  The shared test fixture builds with `allow_review_markers=True`; `test_current_content_has_no_review_markers` is a
  non-strict xfail that turns green (XPASS) once content is merged — then drop the xfail and the flag in `conftest.py`.
  `make dev`/`make site` and CI's site build step fail until then.

**Open issues**
- Privacy page states account deletion, JSON export and deletion of inactive accounts after 12 months (REVIEW H4); these are
  NOT in the app code yet, so the page says "noch nicht freigeschaltet". Re-check against the app fix before go-live.
- Upload metadata (type, size, row count, column names) is described as kept until account deletion (current code); update if
  the app deletes it with the upload (REVIEW M12). Event counts have no purge today (stated on the page). Caddy log retention not defined.

**Update after merging main (wave 4 merged)**
- Content is free of `[prüfen`; `python site/build.py` passes. Test fixture now enforces the check (flag and xfail removed).
- Privacy draft updated to the merged app: account deletion + JSON export in the profile, inactive accounts deleted after
  12 months, upload metadata deleted with the upload, events purged after ~13 months, consent proof (HMAC) 3 years after
  unsubscribe, unconfirmed opt-ins 7 days. Verified in app/jobs.py, app/main.py, app/migrations/002_retention.sql and
  checked against content/legal/datenschutz-fakten.md. Still open (owner/legal): controller, legal bases, processor contracts,
  proxy log retention, consent-proof period.

**Legal pre-review round**
- Privacy draft: 14-day log retention as configured (rotated files; size-based limits stated honestly); Anthropic Ireland, Limited
  as EEA contract partner (verified on anthropic.com/legal/commercial-terms, 1 Nov 2026) with Anthropic PBC (USA) as further
  processor; HMAC called "pseudonymisiert" with all three consent-record retention cases; cookie table; Art. 21 box; Art. 22,
  Art. 13(2)(e) and withdrawal-effect sentences; Cloudflare/Anthropic retention and role split listed as open.
- `SITE_EVENTS` build variable (default off): `data-events` empty, `site.js` sends nothing and does not rewrite links.
- Impressum: every § 5 Abs. 1 DDG item (Nr. 1-8, verified on gesetze-im-internet.de) as `[[BUSINESS_ID_PENDING]]`.
- Still open: legal bases/legitimate interests (lawyer Q8), AVV role split (Q1), safeguards (Q3-5), Cloudflare cookie check (owner).

**AVV page:** `content/legal/avv-entwurf.md` rendered as `/avv/` (template `legal_doc.html`, draft banner, in sitemap like the other legal pages, linked from Datenschutz). Missing file fails the build.

## Remediation release (1 Nov 2026): AGB page, P1-8 privacy reconciliation
- `/agb/` now renders `content/legal/agb-entwurf.md` via `LEGAL_DOCS` + `legal_doc.html` (shows `Version agb-draft-2` and the
  front-matter status "Entwurf – nicht freigegeben ..."); missing file fails the build like `/avv/`. Old `site/templates/agb.html` removed.
- `site/templates/datenschutz.html` reconciled with `content/legal/datenschutz-fakten.md`: strict log retention stated as
  "Ausgelegt auf 14 Tage; wird mit der Servereinrichtung aktiviert" (only size-based rotation described as set today; no backups);
  AI mapping off by default, only after legal clearance in staging/prod, inference location default "global" (source link),
  workspace residency to be confirmed by the owner; Cloudflare Customer DPA "Version 6.4, gültig ab 3. April 2026 (laut Cloudflare-Seite,
  geprüft 1. Nov. 2026)"; unverified seats of Cloudflare/Brevo no longer asserted; AGB acceptance record (ist) added.
- Tests: `site/tests/test_site_privacy.py` (no active strict-retention claim while fakten says "geplant"; DPA string derived from
  fakten; AI wording; AGB page; AGB missing fails build). Run: `python -m pytest site/tests && python site/build.py`.
- Open: switch the log wording to "ist" once ops' retention is live on the server and fakten is updated; Anthropic workspace residency.
