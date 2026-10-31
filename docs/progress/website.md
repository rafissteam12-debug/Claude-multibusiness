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
