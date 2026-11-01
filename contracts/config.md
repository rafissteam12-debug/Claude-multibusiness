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
| `CONSENT_HMAC_KEYS` | app | unset (legacy only) | `keyid:base64key,...`, first = current key, ≥ 32 bytes; required in staging/prod; must differ from SESSION_SECRET; implicit `legacy-session` = SESSION_SECRET for records before the switch — after rotating SESSION_SECRET list `legacy-session:<old>`; keep old consent keys 3 years |
| `ONBOARDING_OPEN` | app | `0` | prod only: new accounts need `1` AND non-draft AGB/AVV ids; staging/dev/test always open |
| `AI_TRANSFER_CLEARED` | app | `0` | staging/prod: `AI_PROVIDER=anthropic` requires `1` (set only after the Chapter V review), else the app refuses to start |
| `MAILER` | app | `console` | `console` (prints) or `brevo` |
| `BREVO_API_KEY` | app | — | only when `MAILER=brevo` |
| `MAIL_FROM` | app | `ablaufwerkinfo@gmail.com` | |
| `AI_PROVIDER` | mapping | `heuristic` | `heuristic` (no network) or `anthropic` |
| `ANTHROPIC_API_KEY` | mapping | — | only when `AI_PROVIDER=anthropic` |
| `AI_MODEL` | mapping | `claude-sonnet-5-5` | override per environment |
| `MAPPING_AI_DEBUG` | mapping | `0` | `1` attaches the AI's raw target list (no cell values) for diagnosis; CI network tests only |
| `AI_MAX_SAMPLE_ROWS` | mapping | `5` | rows sent to the AI; headers + samples only |
| `KOSIT_VALIDATOR_JAR` | engine | unset | path; layer skipped with a visible notice if unset |
| `KOSIT_CONFIG_DIR` | engine | unset | directory of the pinned KoSIT XRechnung validator configuration; required with `KOSIT_VALIDATOR_JAR` |
| `KOSIT_MAX_PARALLEL` | engine | `2` | max. concurrent KoSIT JVMs per process (`-Xmx1g` each); size to server RAM |
| `XRECHNUNG_TESTSUITE_DIR` | engine tests | unset | checkout of the official XRechnung test suite; suite test skipped if unset |
| `ENGINE_REAL_TOOLS` | engine tests | unset | `1` runs the opt-in tests against real KoSIT/Mustang |
| `APP_DOMAIN` | ops (Caddy) | unset | app host name only (e.g. `app.<domain>`), read by `ops/Caddyfile`; never edit tracked files on the server |
| `MUSTANG_JAR` | engine | unset | path; ZUGFeRD PDF/A-3 disabled if unset |
| `EVENTS_ALLOWED` | app | `page_view,link_click,check_run,subscribe,upload,mapping_confirmed,conversion_done` | |
| `RETENTION_HOURS` | app | `24` | |
| `SITE_EVENTS` | site build | `0` | `0` = no usage beacon, no link rewriting (§ 25 TDDDG). `1` only after legal clearance |
| `SITE_STAGING` | site build | `1` | `1` = banner, noindex, robots Disallow. `0` only after go-live approval by the owner |

Rule: with only defaults set, `make dev` must run the whole system offline
(heuristic mapping, console mailer, KoSIT layer skipped with notice).
