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
