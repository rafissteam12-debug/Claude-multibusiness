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
   no e-mails, no social posts, no purchases, no account sign-ups. Local and staging only.
   Staging pages must send `X-Robots-Tag: noindex, nofollow` (site `_headers`), carry a
   visible "Testversion" banner, and are never linked from anywhere.
3. No secrets in the repository. Read keys only from environment variables listed in
   `contracts/config.md`. Never print them. `.env` is git-ignored.
4. No invented facts. No testimonials, customer counts, ratings, or claims of
   "rechtssicher"/"garantiert konform". Every legal or deadline statement in content
   carries a source URL. No tax or legal advice; scope line: we deliver a technical
   converter and a validation report; the customer confirms content and VAT.
5. Ada is always disclosed as AI-generated ("KI-generiert") in image, caption and bio.
6. Business identity is LAST. Impressum, address, registration, VAT number, prices
   on public pages: use the exact placeholder `[[BUSINESS_ID_PENDING]]`.
   No prices in any user-facing output (site, app, e-mails) until cleared; drafts in
   `content/` may contain them.
7. Customer invoice data follows the retention rules in `contracts/api.md` (raw upload
   deleted at conversion or after 24 h; outputs and error texts after 24 h). Never log
   invoice contents or AI prompts with values. Tests use only fictional fixtures
   (`engine/samples/`, `mapping/fixtures/`) with `.example`/`.invalid` addresses and
   documented test IBANs (e.g. DE89370400440532013000).
8. Only a file that is `valid` per the validity rule in `contracts/mapping.md` is offered
   as an e-invoice. A skipped check is shown as skipped, never as passed.

## Ownership — write only inside your folder
| Folder | Owner | Purpose |
| --- | --- | --- |
| `contracts/`, `docs/`, `CLAUDE.md`, root files (`Makefile`, `pyproject.toml`, root `requirements.txt`, `.env.example`, `.github/`) | Orchestrator only | Shared contracts, plan, aggregation |
| `engine/` | Engine agent | Invoice model -> XRechnung/ZUGFeRD, validation |
| `mapping/` | Mapping agent | CSV/XLSX -> invoice model (heuristics + AI) |
| `app/` | App agent | FastAPI service, DB, auth, jobs, app pages |
| `site/` | Website agent | Static site generator and pages, checker UI |
| `content/` | Content agent | Guide texts, Ada posts, e-mails, help texts |
| `ops/` | Ops agent | Docker, CI, Cloudflare config, monitoring |
Each agent works in its own git worktree/branch `agent/<name>` and never merges; the
orchestrator merges. Your folder's dependencies go in `<folder>/requirements.txt` (yours).
New environment variables, contract changes or edits in another folder: write them to
`docs/requests/<your-agent>.md` and continue with a stub. The orchestrator merges requests.
Brand names live in `contracts/brand.md`; code reads them from there (one place).

## Tech stack (fixed — do not substitute)
- Python 3.12+ everywhere. No Node build step (npm is not reachable in the build sandbox).
- engine: lxml, saxonche (XSLT), factur-x; KoSIT validator + Mustang (Java) run in CI/Docker.
- mapping: pandas is NOT allowed (weight); use csv + openpyxl. AI via `anthropic` SDK.
- app: FastAPI, Jinja2 templates, stdlib sqlite3, vanilla JS. No JS frameworks, no CDNs.
- site: Python build script (Jinja2 + markdown) -> `site/dist/`, deployed by Cloudflare
  Workers Builds (build: `pip install -r site/requirements.txt && python site/build.py`).
- Tests: pytest (importlib mode, see `pyproject.toml`). Each folder has `tests/`; test files are named
  `test_<folder>_<topic>.py`. Cross-folder tests carry `@pytest.mark.integration`. `make test` runs unit tests.
- Validation rule files are pinned in `engine/rules/` (see `VERSIONS.md`); never read rule files from outside the repo.

## Contracts (in `contracts/`)
- `invoice.schema.json` — the ONLY invoice model between mapping, engine and app.
- `seller_profile.schema.json` — the user's company data; always wins for seller fields.
- `mapping.md` + `types.py` — Table, Mapping, RowError, Report, frozen engine/mapping signatures, AI data rule.
- `api.md` — HTTP endpoints of the app.
- `config.md` — environment variables.
- `brand.md` — colours, fonts, voice, disclosure rules.
Do not change contracts yourself; request changes (see above).

## Definition of done for any task
Code runs, tests pass (`make test`), no rule above broken, a short entry added to
`docs/progress/<your-agent>.md`: what you built, how to run it, what is stubbed, open issues.
Commit with a clear message in English. Never force-push.
