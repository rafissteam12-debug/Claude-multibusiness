# Ablaufwerk — rules for every agent working in this repository

Read this file and `docs/BUILD_PLAN.md` before you change anything. They override
your own defaults. If something here blocks you, stop and report; do not work around it.

## What we are building
Belegbrücke: a self-serve web tool that turns a business's existing invoice export
(CSV/XLSX) into valid German e-invoices (XRechnung 3.0 CII; ZUGFeRD EN16931 PDF/A-3),
with AI proposing the column mapping and every file validated before download.
Plus: a free "E-Rechnung-Check" validator page, German guide pages, and content for
"Ada", an openly AI-generated illustrated presenter. Brand: Ablaufwerk.

## Hard rules (never break)
1. Separate venture. Nothing from BestBroker4U: no code, accounts, data, links, names.
2. Nothing goes public and nothing is sent. No deploy to production, no publishing,
   no e-mails, no social posts, no purchases, no account sign-ups. Staging and local only.
3. No secrets in the repository. Read keys only from environment variables listed in
   `contracts/config.md`. Never print them. `.env` is git-ignored.
4. No invented facts. No testimonials, customer counts, ratings, or claims of
   "rechtssicher"/"garantiert konform". Every legal or deadline statement in content
   carries a source URL. No tax or legal advice; scope line: we deliver a technical
   converter and a validation report; the customer confirms content and VAT.
5. Ada is always disclosed as AI-generated ("KI-generiert") in image, caption and bio.
6. Business identity is LAST. Impressum, address, registration, VAT number, prices
   on public pages: use the exact placeholder `[[BUSINESS_ID_PENDING]]`.
   Prices may appear only in `content/` drafts, never in `site/` output, until cleared.
7. Customer invoice data: process in memory or a temp dir, delete after the job;
   generated files kept max 24 h; never log invoice contents; never put them in tests
   (tests use the fictional fixtures in `engine/samples/` and `mapping/fixtures/`).
8. A file that fails validation is never offered as a valid e-invoice.

## Ownership — write only inside your folder
| Folder | Owner | Purpose |
| --- | --- | --- |
| `contracts/`, `docs/`, `CLAUDE.md`, root files | Orchestrator only | Shared contracts and plan |
| `engine/` | Engine agent | Invoice model -> XRechnung/ZUGFeRD, validation |
| `mapping/` | Mapping agent | CSV/XLSX -> invoice model (heuristics + AI) |
| `app/` | App agent | FastAPI service, DB, auth, jobs, app pages |
| `site/` | Website agent | Static site generator and pages, checker UI |
| `content/` | Content agent | Guide texts, Ada posts, e-mails, help texts |
| `ops/` | Ops agent | Docker, CI, Cloudflare config, monitoring |
Need a change in another folder or a contract? Write it to `docs/requests/<your-agent>.md`
and continue with a stub. The orchestrator merges requests.

## Tech stack (fixed — do not substitute)
- Python 3.12+ everywhere. No Node build step (npm is not reachable in the build sandbox).
- engine: lxml, saxonche (XSLT), factur-x; KoSIT validator + Mustang (Java) run in CI/Docker.
- mapping: pandas is NOT allowed (weight); use csv + openpyxl. AI via `anthropic` SDK.
- app: FastAPI, Jinja2 templates, stdlib sqlite3, vanilla JS. No JS frameworks, no CDNs.
- site: Python build script (Jinja2 + markdown) -> `site/dist/`, deployed by Cloudflare
  Workers Builds (build: `pip install -r site/requirements.txt && python site/build.py`).
- Tests: pytest. Each folder has `tests/`. `make test` runs all.

## Contracts (in `contracts/`)
- `invoice.schema.json` — the ONLY data model between mapping, engine and app.
- `api.md` — HTTP endpoints of the app.
- `config.md` — environment variables.
- `brand.md` — colours, fonts, voice, disclosure rules.
Do not change contracts yourself; request changes (see above).

## Definition of done for any task
Code runs, tests pass (`make test`), no rule above broken, a short entry added to
`docs/progress/<your-agent>.md`: what you built, how to run it, what is stubbed, open issues.
Commit with a clear message in English. Never force-push.
