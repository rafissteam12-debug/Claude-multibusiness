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

All compose commands run from `/srv/ablaufwerk` (the repository root) as
`docker compose --env-file .env -f ops/docker-compose.yml ...`; below shortened to `dc ...`
(`alias dc='docker compose --env-file .env -f ops/docker-compose.yml'`). `--env-file .env` lets compose
pass `APP_DOMAIN` to Caddy; the app container reads the whole `.env` itself.

**Never edit tracked files on the server** (`ops/Caddyfile`, compose file, ...). Everything that differs per
server goes into `.env`. `git status` must be clean, otherwise the next `git checkout <tag>` fails.

## Sizing notes
- 2 vCPU / 4 GB RAM is enough for v1. Every KoSIT validation starts a Java process with `-Xmx1g`
  (`JAVA_TOOL_OPTIONS` in the image).
- `KOSIT_MAX_PARALLEL` (default `2`; requested for `contracts/config.md`, implemented by the engine agent)
  caps how many KoSIT processes run at the same time. Keep `KOSIT_MAX_PARALLEL x 1 GB` plus about 1 GB for the
  app below the RAM of the server: 2 on 4 GB, 4 only on 8 GB or more. Set it in `.env` if you change it.
- Container `/tmp` is a 512 MB tmpfs (counts against RAM); uploads and outputs live on the `appdata` volume.

## First deploy (later, owner approval needed)
1. Owner buys the VPS (EU region, e.g. 2 vCPU / 4 GB RAM, Debian or Ubuntu LTS) and the domain.
2. On the server: create a non-root user with SSH key login, disable password login, enable the
   firewall (allow 22, 80, 443 only), enable automatic security updates.
   DNS for the app domain (Cloudflare, Websites -> domain -> DNS -> Records): A/AAAA record to the server,
   proxy status **DNS only (grey cloud)**. Decision for v1: DNS-only. Caddy then sees the real client
   addresses (rate limits per IP work) and gets its certificate itself. If the record is ever switched to
   "Proxied" (orange cloud), every request comes from Cloudflare addresses: first configure
   `trusted_proxies` for Cloudflare's ranges in the Caddyfile (a tracked change via the repo, not on the
   server), otherwise all users share one rate limit.
3. Install Docker Engine and the compose plugin from Docker's official apt repository.
4. `git clone` the repository (read-only deploy key) to `/srv/ablaufwerk`, check out the release tag.
5. Create `/srv/ablaufwerk/.env` from `.env.example`, `chmod 600 .env`. Set at least:
   `APP_ENV=staging` (or `prod` at go-live), `APP_DOMAIN` (the app's host name only, e.g.
   `app.<domain>`, no `https://`), `APP_PUBLIC_URL` (`https://` + `APP_DOMAIN`), `SITE_PUBLIC_URL`,
   `SESSION_SECRET` (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`),
   `MAILER`, `BREVO_API_KEY` (if `brevo`), `AI_PROVIDER`, `ANTHROPIC_API_KEY` (if `anthropic`).
   Do not set `KOSIT_*`, `MUSTANG_JAR`, `DATABASE_PATH`, `TEMP_DIR` there; the image sets them.
6. Do not edit `ops/Caddyfile`: it reads the domain from `APP_DOMAIN` in `.env`. Without it Caddy falls back
   to `[[BUSINESS_ID_PENDING_DOMAIN]]` and refuses to start. The DNS record (step 2) must already point at
   the server; Caddy then gets the certificate itself. No ACME e-mail is needed.
7. `dc up -d --build`
8. Check: `dc ps` (app "healthy"), `curl -I https://<domain>/healthz`,
   one check with a fictional sample (`engine/samples/`) on the checker; the KoSIT layer must show as run.
9. Note the image ID and git tag in the deploy log (a text file on the server is enough).

## Update and rollback
- Deploy at quiet hours (e.g. late evening or early morning, German time). Restarting the app marks all
  conversion jobs that are still queued or running as failed ("Server neu gestartet, bitte erneut
  umwandeln"; implemented by the app agent, review M9); those users have to start the conversion again.
  Optional: look at the job list first and wait until nothing is running.
- Update: `git status` (must be clean), keep the old image: `docker tag ablaufwerk-app:local ablaufwerk-app:previous`,
  then `git fetch --tags && git checkout <new tag> && dc up -d --build`.
- Rollback: `docker tag ablaufwerk-app:previous ablaufwerk-app:local && git checkout <old tag> &&
  dc up -d --no-build`.
- Database changes must be backward compatible for one release (the app agent owns migrations).
  The DB holds no long-lived customer data (24 h), so in the worst case delete the volume and start empty.

## Rotate secrets
- `SESSION_SECRET`: generate a new value, put it in `.env`, `dc up -d`. All users are
  logged out; magic links issued before the change stop working. Do this at once if the value may have leaked.
- `ANTHROPIC_API_KEY` / `BREVO_API_KEY`: create the new key in the provider console, update `.env`,
  restart, check one mapping proposal / one mail, then revoke the old key. In CI: GitHub repo
  Settings -> Secrets -> `ANTHROPIC_API_KEY`.
- Never paste keys into tickets, chats, commit messages or logs. If one is committed by mistake: revoke
  it first, then clean up.

## Logs
- `dc logs app|purge|caddy` (container stdout, json-file, 3 x 5 MB per container, rotated).
- Caddy access log: `dc exec caddy sh -c 'tail /var/log/caddy/access.log'` (volume `caddy_logs`).
- Caddy access log: IPs masked (/16, /32), `token` removed from query strings, `Referer` (can hold a token
  URL), cookies, authorization, CSRF, X-Forwarded-For and Set-Cookie headers deleted (test:
  `ops/tests/test_ops_scripts.py::test_caddy_log_filter_deletes_sensitive_headers`). uvicorn access logs are off (`--no-access-log`).
- **Never logged:** invoice contents (cell values, XML, PDFs), uploaded file names, AI prompts with values,
  magic-link / opt-in / unsubscribe tokens, session cookies, raw IP addresses, API keys, e-mail bodies.
  Error logs carry exception class names and counts, not values.
- Purge: `purge` service logs one line per run; "ERROR app.purge failed" means retention is at risk: fix the same day.

## Log retention: 14 days
Owner decision: web server and container logs are kept 14 days. What is configured, per location:

| Log | Where | How it is limited |
| --- | --- | --- |
| Caddy access log | volume `caddy_logs`, `/var/log/caddy/access.log` in the caddy container | Caddyfile `roll_size 5MiB`, `roll_keep 60`, `roll_keep_for 336h`: rolled (gzipped) files older than 14 days are deleted. |
| Caddy stdout (start-up, certificates, errors) | Docker json-file of the caddy container | compose `logging`: `max-size 5m`, `max-file 3` (15 MB) |
| App stdout/stderr (uvicorn access log off) | Docker json-file of the app container | same, 15 MB |
| Purge job output (one line per hourly run) | Docker json-file of the purge container | same, 15 MB (about 1 KB per day: see note) |

Honest limits of this setup:
- Caddy rolls by **size**, and old files are deleted when a roll happens. The active `access.log` is
  never cut by age: in a very quiet period (less than 5 MB of access lines in 14 days, roughly fewer than
  10 000 requests) it can hold lines older than 14 days until it reaches 5 MB. Rolled files older than 14 days
  are removed at the next roll.
- Docker json-file also rotates by **size only**. 15 MB per container holds well under 14 days for the app
  and caddy at normal traffic, but in quiet periods lines can be older. The purge container writes so little
  that its log can hold months; it contains counts only, no personal data.
- `dc up` that recreates a container (every update) deletes that container's json-file logs entirely.
- For a strict 14-day age limit, use journald on the host instead: in `/etc/systemd/journald.conf` set
  `MaxRetentionSec=14day` (and e.g. `SystemMaxUse=500M`), `systemctl restart systemd-journald`, then switch
  the compose `x-logging` anchor to `driver: journald` (no options needed) in a tracked change. journald
  deletes whole journal files, so entries can outlive the limit by up to one file's span; also set
  `MaxFileSec=1day` for a near-exact bound. The Caddy access file stays size-rolled either way; for a hard
  bound there, a daily host cron can run
  `dc exec caddy find /var/log/caddy -name 'access-*.log.gz' -mtime +14 -delete` (does not touch the active file).
- Docker daemon defaults (`/etc/docker/daemon.json` `log-driver`/`log-opts`) apply only to containers
  without their own `logging`; ours set it explicitly, so no daemon change is needed.
- Host logs (SSH, system) are outside this app: set the same journald values if they should follow 14 days too.

**No backups exist, by design** (also not of logs or of the database): nothing is copied anywhere, so no
copy can outlive these limits.

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

## Website: Cloudflare Workers Builds variables
The site build reads `APP_PUBLIC_URL`, `SITE_PUBLIC_URL` and `SITE_STAGING` at build time. Without them it
uses the dev defaults (`http://localhost:...`): the CSP in `_headers` and the checker point at localhost and
the checker on the staging site cannot reach the app.
1. Cloudflare dashboard -> **Workers & Pages** -> the site project -> **Settings** -> **Build** ->
   **Variables** (build variables, not runtime variables or secrets). Exact labels may differ slightly
   between dashboard versions; look for the build-time variables of the Git build.
2. Add `APP_PUBLIC_URL` = `https://<APP_DOMAIN>`, `SITE_PUBLIC_URL` = the site's address,
   `SITE_STAGING` = `1`. Save, then retry the latest build (Deployments -> latest -> Retry build).
3. Check the built site: `_headers` contains the app origin in `connect-src`, the "Testversion" banner is
   shown, `robots.txt` says `Disallow: /`. Locally the same build can be checked with
   `APP_PUBLIC_URL=... SITE_PUBLIC_URL=... python site/build.py && python ops/scripts/check_site.py`.
4. `SITE_STAGING=0` only after the owner's written go-live approval (go-live checklist below). Before
   that, run `SITE_STAGING=0 APP_PUBLIC_URL=... SITE_PUBLIC_URL=... python site/build.py && SITE_STAGING=0
   python ops/scripts/check_site.py`: release mode fails on any `localhost` reference in `_headers` or pages,
   on the business-ID placeholder and on the staging banner. Both modes fail on unverified `[prüfen` notes.

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
      (`python ops/scripts/check_site.py --mode release` passes, including no `localhost` and no `[prüfen`;
      `APP_DOMAIN` set in the server's `.env`).
- [ ] Prices cleared by the owner before any appear on site, app or e-mails.
- [ ] Impressum, Datenschutzerklärung and AGB reviewed by a lawyer; processors (hosting, Cloudflare,
      Anthropic, Brevo) listed with DPAs signed.
- [ ] `SITE_STAGING=0` in the Cloudflare build variables (with real `APP_PUBLIC_URL`/`SITE_PUBLIC_URL`),
      `APP_ENV=prod` on the server, `SESSION_SECRET` freshly generated.
- [ ] App domain DNS-only (grey cloud) in Cloudflare, or Caddy `trusted_proxies` configured.
- [ ] CI green on the release commit, including the `validators` job (KoSIT suite + Mustang).
- [ ] `/healthz` healthy; one end-to-end run with fictional data; KoSIT layer shown as run.
- [ ] Purge verified: a test upload is gone after `RETENTION_HOURS` (or run `purge.sh --once` with a short value).
- [ ] Logs checked: no tokens, IPs or invoice values in `dc logs`.
- [ ] Mail sending (Brevo) tested with an own address only; sender domain SPF/DKIM set.
