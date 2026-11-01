# Requests from the ops agent (2026-11-01)

1. **App agent: `GET /healthz`** – 200 `{"status":"ok"}`, no auth, no DB writes, no CORS, cheap (used by the
   Docker HEALTHCHECK every 30 s and by compose `depends_on: service_healthy`). Until it exists the container is
   "unhealthy" and `purge`/`caddy` will not start. CI smoke step is non-blocking until then.
2. **App agent: `python -m app.purge`** – one retention run per `contracts/api.md` (raw uploads, generated files,
   job error texts, expired tokens older than `RETENTION_HOURS`; jobs -> `expired`), exit 0 on success, prints
   counts only. Called hourly by `ops/scripts/purge.sh`.
3. **App agent: logging** – uvicorn access log is off in the image (query strings carry tokens). App logs must not
   contain tokens, raw IPs, cell values, file names or AI prompts.
4. **Orchestrator: `pyproject.toml` testpaths** – add `"ops/tests"` (stdlib + pytest + PyYAML, offline).
5. **Orchestrator: copy** `ops/ci/ci.yml` -> `.github/workflows/ci.yml`. Optionally add secret `ANTHROPIC_API_KEY`.
6. **Engine agent: test-suite path** – `engine/tests/test_engine_kosit_suite.py` hard-codes
   `/home/claude/itplr-kosit/...`; please read `XRECHNUNG_TESTSUITE_DIR` (fallback to that path). CI symlinks the
   fixed path meanwhile. Also: an opt-in test that keeps `KOSIT_*`/`MUSTANG_JAR` when `ENGINE_REAL_TOOLS=1`.
7. **Engine agent: KoSIT config 2026-08-31** – engine rules are pinned to schematron v2.6.0 (2026-08-31); CI compares
   against the official config of the same date. If CI shows new differences, update `engine/rules/`.
8. **Orchestrator: `.env.example`** – add `KOSIT_CONFIG_DIR=` (in config.md, missing in `.env.example`).
9. **Orchestrator (later)** – pin actions by commit SHA (dependabot), pin base image digest from the CI log.

## Status (orchestrator, 1 Nov)
testpaths, ci.yml copy, KOSIT_CONFIG_DIR in .env.example: done. App requests forwarded to the app agent. Engine requests (XRECHNUNG_TESTSUITE_DIR, opt-in real-tools test): wave 4 fix round. SHA/digest pinning of actions + base image: wave 5.

## Wave 4 fix round (ops, 1 Nov)
10. **Orchestrator: `contracts/config.md` + `.env.example`** – add
    `APP_DOMAIN` | ops (Caddy) | unset | app host name only (e.g. `app.<domain>`, no scheme); read by `ops/Caddyfile`
    as `{$APP_DOMAIN}`; unset -> Caddy refuses to start (placeholder default). `.env.example`: `APP_DOMAIN=`.
    `ACME_EMAIL` is **not** needed: the Caddyfile sets no ACME account e-mail (Let's Encrypt does not require one).
11. **Orchestrator: `contracts/config.md` + `.env.example`** – add `KOSIT_MAX_PARALLEL` | engine | `2` | max.
    concurrent KoSIT JVMs (`-Xmx1g` each); same request as the engine agent's (review M1). `.env.example`:
    `KOSIT_MAX_PARALLEL=2`.
12. **Orchestrator: copy** `ops/ci/ci.yml` -> `.github/workflows/ci.yml` again (actions now pinned to commit SHAs,
    Caddy validate uses `-e APP_DOMAIN`, compose config uses `--env-file .env`). Note: the `test` job's
    `check_site.py --mode staging` step now fails on `[prüfen` in built HTML (H2 guard); it stays red until the
    content agent removes the 5 notes in `ratgeber/*`.
13. **Orchestrator (optional): Cloudflare build command** – consider appending
    `&& python ops/scripts/check_site.py` (mode follows `SITE_STAGING`) so a Cloudflare build with localhost URLs
    under `SITE_STAGING=0`, or with `[prüfen` notes, fails there too. Needs a CLAUDE.md change (fixed command).
14. **Wave 5: base image digest** – could not be resolved here (Docker Hub registry blocked by the proxy). Take it
    from the CI step "Base image digest" and set `ARG PYTHON_IMAGE=python:3.12-slim-trixie@sha256:...` in
    `ops/Dockerfile` (ops agent), same for `caddy:2.10-alpine` in compose/CI.

## Status (orchestrator, 1 Nov, wave 4)
Wave 4 items merged into contracts/ (mapping.md, api.md, config.md), .env.example and .github/workflows/ci.yml; deferred items in docs/ideas.md.

## Remediation P1-5 (ops, 1 Nov)
15. **Orchestrator: copy** `ops/ci/ci.yml` -> `.github/workflows/ci.yml` (new step "Log retention script on fixture").
16. **Orchestrator: `contracts/config.md` + `.env.example`** – add (implemented by the app agent in `app/settings.py`):
    - `CONSENT_HMAC_KEYS` | app | unset (dev/test: falls back to SESSION_SECRET) | required in staging/prod; secret;
      `keyid:base64key,...`, first entry signs new consent records, all entries match old ones; generate with
      `openssl rand -base64 32`; must differ from `SESSION_SECRET`; keep old keys listed when rotating.
      `.env.example`: `CONSENT_HMAC_KEYS=`.
    - `AI_TRANSFER_CLEARED` | app | `0` | `1` only after the owner clears the transfer to Anthropic; staging/prod
      refuse `AI_PROVIDER=anthropic` without it. `.env.example`: `AI_TRANSFER_CLEARED=0`.
    - `ONBOARDING_OPEN` | app | `0` | prod only: `1` allows new accounts (also needs final AGB/AVV).
      `.env.example`: `ONBOARDING_OPEN=0`.
17. **Owner (server setup)**: install `ops/host/journald-belegbruecke.conf` (RUNBOOK "Log retention: 14 days");
    until then container logs have no age limit.
18. **Later (ops)**: Caddy 2.11 `roll_at 00:00` would make the daily cut lossless inside Caddy; needs the image
    bump and a CI `caddy validate` run.
