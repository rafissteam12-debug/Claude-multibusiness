# Runbook: Belegbrücke app

Plain steps for running the app on a small EU VPS. **Nothing here may be done without the owner's
approval** (CLAUDE.md rule 2): no server is bought, no domain is pointed, nothing is deployed yet.
The static website is separate: Cloudflare Workers Builds builds it from the repo (`site/`, `wrangler.jsonc`).

## What runs where
| Piece | Where | Notes |
| --- | --- | --- |
| Website | Cloudflare (staging address) | `pip install -r site/requirements.txt && python site/build.py`, `npx wrangler deploy` |
| App | VPS, `ops/docker-compose.yml` | `app` (uvicorn :8000, not published), `purge` (hourly), `caddy` (80/443, HTTPS) |
| Data | Docker volume `appdata` -> `/data` | `app.db` (SQLite) and `tmp/` (uploads, outputs) |
| Validators | inside the image, `/opt/tools` | KoSIT 1.6.2, XRechnung config 2026-08-31, Mustang 2.26.0, pinned in `ops/pins.txt` |

## First deploy (later, owner approval needed)
1. Owner buys the VPS (EU region, e.g. 2 vCPU / 4 GB RAM, Debian or Ubuntu LTS) and the domain.
2. On the server: create a non-root user with SSH key login, disable password login, enable the
   firewall (allow 22, 80, 443 only), enable automatic security updates.
3. Install Docker Engine and the compose plugin from Docker's official apt repository.
4. `git clone` the repository (read-only deploy key) to `/srv/ablaufwerk`, check out the release tag.
5. Create `/srv/ablaufwerk/.env` from `.env.example`, `chmod 600 .env`. Set at least:
   `APP_ENV=staging` (or `prod` at go-live), `APP_PUBLIC_URL`, `SITE_PUBLIC_URL`,
   `SESSION_SECRET` (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`),
   `MAILER`, `BREVO_API_KEY` (if `brevo`), `AI_PROVIDER`, `ANTHROPIC_API_KEY` (if `anthropic`).
   Do not set `KOSIT_*`, `MUSTANG_JAR`, `DATABASE_PATH`, `TEMP_DIR` there; the image sets them.
6. Replace `[[BUSINESS_ID_PENDING_DOMAIN]]` in `ops/Caddyfile` with the real app domain
   (DNS A/AAAA record must already point at the server; Caddy then gets the certificate itself).
7. `docker compose -f ops/docker-compose.yml up -d --build`
8. Check: `docker compose -f ops/docker-compose.yml ps` (app "healthy"), `curl -I https://<domain>/healthz`,
   one check with a fictional sample (`engine/samples/`) on the checker; the KoSIT layer must show as run.
9. Note the image ID and git tag in the deploy log (a text file on the server is enough).

## Update and rollback
- Update: `git fetch --tags && git checkout <new tag>`, then `docker compose -f ops/docker-compose.yml up -d --build`.
  Before that, keep the old image: `docker tag ablaufwerk-app:local ablaufwerk-app:previous`.
- Rollback: `docker tag ablaufwerk-app:previous ablaufwerk-app:local && git checkout <old tag> &&
  docker compose -f ops/docker-compose.yml up -d --no-build`.
- Database changes must be backward compatible for one release (the app agent owns migrations).
  The DB holds no long-lived customer data (24 h), so in the worst case delete the volume and start empty.

## Rotate secrets
- `SESSION_SECRET`: generate a new value, put it in `.env`, `docker compose ... up -d`. All users are
  logged out; magic links issued before the change stop working. Do this at once if the value may have leaked.
- `ANTHROPIC_API_KEY` / `BREVO_API_KEY`: create the new key in the provider console, update `.env`,
  restart, check one mapping proposal / one mail, then revoke the old key. In CI: GitHub repo
  Settings -> Secrets -> `ANTHROPIC_API_KEY`.
- Never paste keys into tickets, chats, commit messages or logs. If one is committed by mistake: revoke
  it first, then clean up.

## Logs
- `docker compose -f ops/docker-compose.yml logs app|purge|caddy` (json-file, 5 x 10 MB per service, rotated).
- Caddy access log: IPs masked (/16, /32), `token` removed from query strings, cookies, authorization,
  CSRF and Set-Cookie headers deleted. uvicorn access logs are off (`--no-access-log`).
- **Never logged:** invoice contents (cell values, XML, PDFs), uploaded file names, AI prompts with values,
  magic-link / opt-in / unsubscribe tokens, session cookies, raw IP addresses, API keys, e-mail bodies.
  Error logs carry exception class names and counts, not values.
- Purge: `purge` service logs one line per run; "ERROR app.purge failed" means retention is at risk: fix the same day.

## Retention and backups
- Hourly `ops/scripts/purge.sh`: `python -m app.purge` (DB rows + files per `contracts/api.md`) and a
  safety net that deletes any file in `TEMP_DIR` older than `RETENTION_HOURS` (24).
- No backups in v1: customer data lives at most 24 h, a backup would only keep it longer.

## KoSIT configuration or tool update
1. New release of the XRechnung validator configuration (or KoSIT validator / Mustang): read its notes.
2. Update URL and hash in `ops/pins.txt` together (hash = the `sha256:` digest GitHub shows next to the
   asset; or set `-`, push to a branch, copy the `PIN-ON-FIRST-RUN` line from the CI log and pin it).
3. Ask the engine agent to re-copy the matching rule files into `engine/rules/` and update `VERSIONS.md`,
   and to bump the test-suite tag in `ops/ci/ci.yml` (`--branch v...`) to the matching suite release.
4. CI job `validators` must be green (suite comparison, no false "valid"); update
   `ops/scripts/suite_known_invalid.txt` (files both KoSIT and we reject, with rule ids) only with a reason. Then rebuild and deploy as above.
5. If CI cannot run KoSIT, do not release (BUILD_PLAN "Failure handling").

## Staging vs. production
| | Staging | Production |
| --- | --- | --- |
| Website `SITE_STAGING` | `1`: "Testversion" banner, noindex, `robots.txt` Disallow | `0`, only after owner approval |
| App `APP_ENV` | `staging` | `prod` |
| Validity | KoSIT must run (both) | KoSIT must run |
| App `X-Robots-Tag` | `noindex, nofollow` | `noindex, nofollow` (the app is never indexed) |
| Links | never linked from anywhere | linked from the website |

## Go-live checklist (owner signs off each line)
- [ ] Business identity done: no `[[BUSINESS_ID_PENDING]]` / `[[BUSINESS_ID_PENDING_DOMAIN]]` left
      (`python ops/scripts/check_site.py --mode release` passes; Caddyfile has the real domain).
- [ ] Prices cleared by the owner before any appear on site, app or e-mails.
- [ ] Impressum, Datenschutzerklärung and AGB reviewed by a lawyer; processors (hosting, Cloudflare,
      Anthropic, Brevo) listed with DPAs signed.
- [ ] `SITE_STAGING=0` in Cloudflare, `APP_ENV=prod` on the server, `SESSION_SECRET` freshly generated.
- [ ] CI green on the release commit, including the `validators` job (KoSIT suite + Mustang).
- [ ] `/healthz` healthy; one end-to-end run with fictional data; KoSIT layer shown as run.
- [ ] Purge verified: a test upload is gone after `RETENTION_HOURS` (or run `purge.sh --once` with a short value).
- [ ] Logs checked: no tokens, IPs or invoice values in `docker compose logs`.
- [ ] Mail sending (Brevo) tested with an own address only; sender domain SPF/DKIM set.
