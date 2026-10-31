# Configuration contract

All configuration comes from environment variables. `.env.example` lists them with
dummy values. Real values live only in the server's environment / CI secrets.

| Variable | Used by | Default (dev) | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | app | `dev` | `dev` / `test` / `staging` / `prod` |
| `APP_PUBLIC_URL` | app, site build | `http://localhost:8000` | |
| `SITE_PUBLIC_URL` | app, site build | `http://localhost:8080` | |
| `DATABASE_PATH` | app | `./var/app.db` | SQLite file |
| `TEMP_DIR` | app | `./var/tmp` | uploads and generated files, purged after 24 h |
| `SESSION_SECRET` | app | random in dev | required outside dev |
| `MAILER` | app | `console` | `console` (prints) or `brevo` |
| `BREVO_API_KEY` | app | — | only when `MAILER=brevo` |
| `MAIL_FROM` | app | `ablaufwerkinfo@gmail.com` | |
| `AI_PROVIDER` | mapping | `heuristic` | `heuristic` (no network) or `anthropic` |
| `ANTHROPIC_API_KEY` | mapping | — | only when `AI_PROVIDER=anthropic` |
| `AI_MODEL` | mapping | set by orchestrator | keep configurable |
| `AI_MAX_SAMPLE_ROWS` | mapping | `5` | rows sent to the AI; headers + samples only |
| `KOSIT_VALIDATOR_JAR` | engine | unset | path; layer skipped with a visible notice if unset |
| `KOSIT_CONFIG_DIR` | engine | unset | directory of the pinned KoSIT XRechnung validator configuration; required with `KOSIT_VALIDATOR_JAR` |
| `MUSTANG_JAR` | engine | unset | path; ZUGFeRD PDF/A-3 disabled if unset |
| `EVENTS_ALLOWED` | app | `page_view,link_click,check_run,subscribe,upload,mapping_confirmed,conversion_done` | |
| `RETENTION_HOURS` | app | `24` | |
| `SITE_STAGING` | site build | `1` | `1` = banner, noindex, robots Disallow. `0` only after go-live approval by the owner |

Rule: with only defaults set, `make dev` must run the whole system offline
(heuristic mapping, console mailer, KoSIT layer skipped with notice).
