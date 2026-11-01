# Ops agent – progress

## 2026-11-01 · Wave 2 (branch `agent/ops`)

### Built (all under `ops/`)
- `ops/pins.txt` – KoSIT validator 1.6.2 standalone jar, XRechnung config `v2026-08-31`
  (`xrechnung-3.0.2-validator-configuration-2026-08-31.zip`), Mustang CLI 2.26.0. SHA-256 = the `sha256:` digests
  GitHub shows next to each release asset (read 2026-10-31 via web tool, twice; not downloaded here).
  "Pin on first run": a hash of `-` prints `PIN-ON-FIRST-RUN <name> <sha>`; a set hash that differs fails.
- `ops/scripts/fetch_tools.py` – stdlib download + SHA-256 check + safe unzip; config always ends at
  `<dest>/kosit-config/scenarios.xml`; `--env-file $GITHUB_ENV` sets `KOSIT_VALIDATOR_JAR/KOSIT_CONFIG_DIR/MUSTANG_JAR`;
  `--strict` (Docker) refuses unpinned files.
- `ops/scripts/check_site.py` – no prices anywhere in `site/dist` (legal thresholds like "800.000 Euro" pass);
  staging mode: banner, meta noindex, `_headers` X-Robots-Tag, robots Disallow, `[[BUSINESS_ID_PENDING]]` on
  Impressum/Datenschutz/AGB. `--mode release` = go-live gate (fails today with 28 findings, as expected).
- `ops/scripts/validate_testsuite.py` + `suite_known_invalid.txt` – KoSIT batch over all CII files of the suite vs our
  3 layers; fails on any false "valid", on KoSIT rejecting a suite file, on new or stale known differences, and if the
  engine's own KoSIT layer does not run.
- `ops/scripts/check_mustang.py` – `build_zugferd` on `engine/samples/*.json` with real Mustang; on failure re-runs
  the engine's exact Mustang commands and prints the output (engine request 6).
- `ops/scripts/purge.sh` – hourly loop: `python -m app.purge` + safety net deleting TEMP_DIR files older than
  RETENTION_HOURS. No backups in v1: data lives 24 h, a backup would only keep it longer.
- `ops/ci/ci.yml` – jobs `test` (pytest not network, site build, site check, pins check), `validators`
  (tools, suite clone `v2026-08-31`, engine tests, suite comparison, Mustang), `docker` (image build, tools in image,
  /healthz smoke non-blocking, `caddy validate`, `compose config`), `network` (only if `ANTHROPIC_API_KEY` secret set).
  Actions pinned to exact tags (checkout v4.2.2, setup-python v5.3.0, upload-artifact v4.6.2).
- `ops/Dockerfile` (+ `ops/Dockerfile.dockerignore`, used automatically by BuildKit) – python:3.12-slim-trixie,
  default-jre-headless, tools stage with `fetch_tools.py --strict`, non-root uid 10001, `/data` volume
  (`DATABASE_PATH=/data/app.db`, `TEMP_DIR=/data/tmp`), `APP_ENV=staging` default, healthcheck on `/healthz`,
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --no-server-header`.
- `ops/docker-compose.yml` – app (port not published, read-only rootfs, cap_drop ALL) + purge + caddy:2.10-alpine.
- `ops/Caddyfile` – `[[BUSINESS_ID_PENDING_DOMAIN]]`, auto HTTPS, 11 MiB body limit (10 MB file + multipart),
  HSTS/nosniff/DENY/CSP-if-missing/X-Robots-Tag, access log with masked IPs and `token` query removed.
- `ops/RUNBOOK.md`, `ops/tests/test_ops_scripts.py` (23 offline tests).

### Orchestrator: copy / wire
| From | To |
| --- | --- |
| `ops/ci/ci.yml` | `.github/workflows/ci.yml` (verbatim) |
| nothing else | Dockerfile, ignore file, compose, Caddyfile stay in `ops/` (`docker build -f ops/Dockerfile .`, `docker compose -f ops/docker-compose.yml`) |
Plus: add `"ops/tests"` to `testpaths` in `pyproject.toml` (see requests).

### Verified locally
- `python -m pytest ops/tests` 23 passed; whole repo `python -m pytest -m "not network"` passes.
- `python site/build.py` + `check_site.py` (staging OK; release mode lists the pending items).
- YAML of ci.yml and compose loads; `docker compose -f ops/docker-compose.yml config` OK; every path referenced
  by ci.yml/Dockerfile exists (test); `purge.sh --once` against a temp dir (safety net works; app.purge missing).
- fetch logic with mocked downloads (hash ok, mismatch, pin-on-first-run, strict, zip with/without top folder, zip-slip).

### Only in CI (first push)
- Real downloads and hash match; `docker build` (no Docker daemon in the sandbox); KoSIT CLI against the
  2026-08-31 config; suite comparison; Mustang flags (engine request 6); `caddy validate` of the Caddyfile syntax
  (log filter block written from Caddy docs memory); `/healthz` smoke (non-blocking until the app has it).

### Open issues
- Hashes come from GitHub's asset pages via a summarising web tool (consistent on two reads). If CI reports a
  mismatch, re-check the release page before anything else.
- Actions pinned to tags, not commit SHAs (SHA lookup blocked here).
- Engine `conftest.py` deletes `KOSIT_*`/`MUSTANG_JAR`, so "engine tests with tools" cannot exercise real tools;
  real-tool coverage is in `validate_testsuite.py` and `check_mustang.py`.
- Base image not pinned by digest yet (CI prints it).
- Website request 1 (self-hosted IBM Plex fonts) not done: deferred by orchestrator (ideas.md).

## 2026-11-01 · Fix after first real CI run (41255736670, commit 204d3d1)
- KoSIT and our 3 layers agreed on 41/41 suite files; 04.05a (BR-CL-10, BR-CL-21) and 02.01a-cvd (BR-CL-13) are
  invalid under the current code lists for BOTH. `suite_known_diffs.txt` replaced by `suite_known_invalid.txt`
  (file + exact rule ids). The script accepts a listed file only when KoSIT and we both reject it with exactly
  those ids; it still fails on any disagreement, any unlisted rejection, other rule ids, and stale entries.
- Open: if our layers report extra ids for those two files, CI prints both sets; then adjust the list or the engine.

## 2026-11-01 · Wave 4 fix round (review M2, M10, L3, L8, ops parts of M1/M9, pins)
- **M2** `ops/Caddyfile` log filter also deletes `request>headers>Referer` (Cookie, Authorization, CSRF,
  X-Forwarded-For, Set-Cookie already). Test parses the filter block: `test_caddy_log_filter_deletes_sensitive_headers`.
- **M10/H2** `ops/scripts/check_site.py`: default mode follows `SITE_STAGING` (`0` -> release); release mode fails
  on `localhost`/`127.0.0.1` in `_headers` or any page; both modes fail on `[prüfen` in built HTML. Current
  `site/dist` has 5 such pages, so the CI staging check is red until content fixes H2 (intended).
  Runbook: Cloudflare build-variable step (Workers & Pages -> project -> Settings -> Build -> Variables).
- **L3** Caddyfile site address `{$APP_DOMAIN:[[BUSINESS_ID_PENDING_DOMAIN]]}`; compose passes only `APP_DOMAIN`
  to caddy; all runbook commands use `docker compose --env-file .env -f ops/docker-compose.yml` (`dc`).
  No ACME e-mail used. Runbook: never edit tracked files on the server.
- **L8** App domain DNS-only (grey cloud) for v1, documented. Compose network `edge` (172.30.53.0/24), caddy fixed
  at .2, app `FORWARDED_ALLOW_IPS=172.30.53.2`; image CMD no longer passes `--forwarded-allow-ips *` (image default
  `127.0.0.1`). Not an `internal` network: the app needs outbound access (Anthropic, Brevo).
- **M9/M1** Runbook: deploy at quiet hours, restart marks running jobs failed; sizing notes with `KOSIT_MAX_PARALLEL`.
- **Pins** Actions pinned to commit SHAs (via `git ls-remote`; `gh api` was blocked); test enforces SHA + tag comment.
  Base image digest: still wave 5 (registry blocked here).
- Run: `python -m pytest -m "not network" ops`.
- Only in CI: `caddy validate` with `{$APP_DOMAIN}`; the negative step (no APP_DOMAIN must fail) is non-blocking
  until the first run confirms Caddy rejects the placeholder address; compose `ipv4_address`/ipam config.
- Requests 10-14 in `docs/requests/ops.md` (APP_DOMAIN, KOSIT_MAX_PARALLEL, ci.yml copy, optional Cloudflare
  build command check, base image digest).
