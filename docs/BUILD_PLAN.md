# Build plan — Ablaufwerk / Belegbrücke (v1, 31 Oct 2026)

Goal: "unpolished finished" = every part of the product works end to end on a
staging address, tested, with rough edges allowed. Business identity (registration,
Impressum, public prices, payments, domain) is the LAST wave and is done by the owner.

## Definition of "unpolished finished"
1. `make dev` starts the whole system offline on one machine; `make test` passes.
2. Website builds to static files: home, Belegbrücke page, E-Rechnung-Check page,
   10 guide pages, legal pages with `[[BUSINESS_ID_PENDING]]`, sitemap, robots.
3. Free checker: upload XML/PDF -> report from XSD, EN 16931, XRechnung (+ KoSIT in CI/Docker).
4. App: magic-link login, seller profile, upload CSV/XLSX, AI/heuristic mapping proposal,
   user correction, conversion to XRechnung CII (+ ZUGFeRD when Mustang is present),
   per-invoice validation report, download, 24 h deletion, monthly usage limit.
5. E-mail: double opt-in and login links through a mailer adapter (console now, Brevo later).
6. Content: 10 sourced guide texts, 12 Ada posts (scripts + rendered carousels),
   5-mail welcome sequence, 8 help articles — all drafts, nothing published.
7. Ops: Dockerfile for the app (incl. Java for KoSIT/Mustang), docker-compose,
   GitHub Actions CI (tests + KoSIT + official test suite), Cloudflare Workers Builds
   config for the site, backup and purge jobs, uptime check config, owner dashboard spec.
8. Independent review passed: security, privacy, legal-claims and end-to-end findings fixed or listed.

## Waves (each wave starts only when its inputs are done)
| Wave | Work | Runs | Inputs | Exit check |
| --- | --- | --- | --- | --- |
| 0 | Contracts, layout, CLAUDE.md, Makefile, CI skeleton | Orchestrator | — | contracts reviewed by critic agent |
| 1 | Engine · Mapping · Website · Content | 4 agents in parallel | contracts | each folder's tests pass; progress notes written |
| 2 | App · Ops | 2 agents in parallel | engine + mapping APIs | `make dev` runs; CI green |
| 3 | Integration: site <-> app, e2e test, staging deploy of the site | Orchestrator | waves 1–2 | e2e script passes |
| 4 | Independent review, then one fix round | Reviewer agent + owners | wave 3 | no open "high" findings |
| 5 | Business identity (owner): registration, Impressum, prices, Stripe, domain, server | Owner + orchestrator | wave 4 | legal pages filled, payment test passes |

## Agent briefs
### Engine (`engine/`)
- Package `engine` with: `build_cii(invoice: dict) -> bytes` (XRechnung 3.0 CII, totals computed with Decimal),
  `build_ubl(invoice) -> bytes` (XRechnung 3.0 UBL), `build_zugferd(invoice, visual_pdf: bytes|None) -> bytes`
  (EN16931 profile, PDF/A-3 via Mustang CLI when `MUSTANG_JAR` set; else raise `FeatureUnavailable`),
  `validate(file_bytes) -> Report` (XSD, CEN, XRechnung Schematron, KoSIT when `KOSIT_VALIDATOR_JAR` set),
  `render_pdf(invoice) -> bytes` (readable invoice PDF), German messages for the 40 most common rule IDs.
- Keep existing `generate.py`, `validate.py`, `sch2xslt.py` working; refactor into the package.
- Accept the invoice model from `contracts/invoice.schema.json` exactly; validate input against it first.
- Tests: both samples valid; every official CII test file from the KoSIT test suite that passed before still passes;
  10 negative tests (missing BT-10, wrong totals, bad IBAN, missing seller contact, exempt VAT without reason, etc.).
- Out of scope: UBL credit notes, non-EUR, allowances beyond document level.

### Mapping (`mapping/`)
- `read_table(file_bytes, filename) -> Table` for CSV (delimiter and encoding sniffing: `;`/`,`/tab, UTF-8/CP1252;
  German decimals "1.234,56", dates "31.10.2026") and XLSX (first sheet, header row detection).
- `propose(table, seller_profile, provider) -> Mapping` with per-field confidence and German reason;
  grouping mode detection (one row per invoice vs one row per line, grouped by invoice number).
- Providers: `heuristic` (synonym dictionary of German/English column names + value patterns, no network)
  and `anthropic` (sends headers + up to `AI_MAX_SAMPLE_ROWS` rows; strict JSON output; falls back to heuristic on error).
- `apply(table, mapping, seller_profile) -> list[invoice dict]` producing schema-valid invoices or per-row errors in German.
- Fixtures: 15 fictional exports covering real-world shapes (Lexware-like, sevdesk-like, Excel by hand, Access export,
  semicolon CP1252, one-row-per-line, missing VAT column with constant 19 %, mixed 7/19 %, credit note rows).
- Tests: heuristic maps >= 80 % of required fields correctly on the fixtures; `apply` output validates in the engine.

### App (`app/`)
- FastAPI per `contracts/api.md`; sqlite3 schema with migrations; magic-link auth; seller profile;
  uploads in `TEMP_DIR`; background jobs in-process (thread pool) with a jobs table; purge job (24 h);
  plan limits; events table; rate limits by IP hash; security headers; CSRF on form posts.
- Pages (Jinja2, vanilla JS, 375 px-ready): login, dashboard, upload, mapping review (table with dropdowns,
  confidence colours, "use for future uploads"), job result (per invoice valid/invalid with German messages, downloads), profile.
- Mailer adapter: `console` and `brevo` (transactional + double opt-in list).
- Tests: API tests for every endpoint; e2e test: login -> upload fixture -> propose -> confirm -> convert -> download valid XML.

### Website (`site/`)
- `site/build.py` renders `site/templates/` + `content/guides/*.md` -> `site/dist/`. Pages: `/`, `/belegbruecke`,
  `/e-rechnung-pruefen` (checker UI calling `APP_PUBLIC_URL/api/v1/check`, with a mock mode for offline),
  `/ratgeber/` + one page per guide, `/impressum`, `/datenschutz`, `/agb` (placeholders), `/bestaetigt`, 404.
- Self-hosted fonts, no third-party requests, no cookies; events beacon to `/api/v1/events`.
- SEO: titles, meta descriptions, canonical, Open Graph, sitemap.xml, robots.txt, JSON-LD (Organization placeholder, Article).
- Uses the offer page design (`site/offer-page.dc.html`) as visual reference; brand per `contracts/brand.md`.
- Tests: build succeeds; every internal link resolves; no external URLs except cited sources; lighthouse-style checks
  scripted where possible (HTML validity, alt texts, heading order).

### Content (`content/`)
- `content/guides/*.md` — 10 guides with front matter (title, description, slug, sources, last_checked):
  Pflicht 2027/2028, PDF ist keine E-Rechnung, XRechnung vs ZUGFeRD, Pflichtfelder, Käuferreferenz/Leitweg-ID,
  Ausnahmen (Kleinbetrag, Kleinunternehmer), E-Rechnung aus Excel/alter Software, Prüfen und Validieren,
  häufige Fehler, Empfang seit 2025. Every legal statement sourced (official/IHK/BMF preferred), checked date.
- `content/ada/posts/` — 12 posts (scripts, captions, alt text, CTA, tracked code `ig-NNN`), carousels rendered to PNG from SVG templates.
- `content/emails/` — welcome sequence (5 mails) + double opt-in + login mail texts.
- `content/help/` — 8 help articles for the app (upload formats, mapping, errors, deletion, limits).
- No prices, no testimonials, no invented numbers. Use `[[BUSINESS_ID_PENDING]]` where the business is named legally.

### Ops (`ops/`)
- Dockerfile (python:3.12-slim + JRE, downloads KoSIT validator + XRechnung config + Mustang at build with pinned
  versions and SHA-256), docker-compose (app + volume), `ops/ci/ci.yml` copied to `.github/workflows/` by orchestrator
  (tests, KoSIT run over the official test suite, site build), `wrangler.jsonc` for site assets, purge + backup cron,
  Uptime Kuma monitor list, `ops/RUNBOOK.md` (deploy, rollback, restore, rotate secrets).
- No real deploy of the app; staging server comes in wave 5 after owner approval.

### Reviewer (wave 4, independent; did not build anything)
- Checks: rules in CLAUDE.md, OWASP top 10 basics, privacy (retention, logs, AI data), every legal claim has a source,
  accessibility basics, e2e run, contract adherence. Output `docs/review/REVIEW.md` with findings rated high/medium/low.

## Failure handling (decided in advance)
| If | Then |
| --- | --- |
| A package or download is blocked in the agent sandbox | Do the step in GitHub Actions or Docker build (full internet); never vendor random copies |
| KoSIT/Mustang unavailable locally | Layer skipped with a visible notice locally; CI must run it; release blocked if CI cannot |
| Two agents need the same file | Neither edits it; request via `docs/requests/`; orchestrator decides |
| A contract is wrong | Stop, request a change; orchestrator updates contract + all callers in one commit |
| Heuristic mapping < 80 % on fixtures | Add synonyms/patterns first; AI provider is an add-on, not a crutch |
| AI provider fails or no key | Fall back to heuristic silently, show "Vorschlag ohne KI" in UI |
| Tests fail at a wave exit | Wave does not close; owner of the folder fixes; orchestrator re-runs |
| An agent session ends mid-task | Work is committed in small steps; next agent resumes from `docs/progress/` |
| Scope creep (features not in this plan) | Write to `docs/ideas.md`; do not build |
