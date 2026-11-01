# Runbook: Belegbrücke app

Plain steps for running the app on a small EU VPS. **Nothing here may be done without the owner's
approval** (CLAUDE.md rule 2): no server is bought, no domain is pointed, nothing is deployed yet.
The static website is separate: Cloudflare Workers Builds builds it from the repo (`site/`, `wrangler.jsonc`).

## What runs where
| Piece | Where | Notes |
| --- | --- | --- |
| Website | Cloudflare (staging address) | `pip install -r site/requirements.txt && python site/build.py`, `npx wrangler deploy` |
| App | VPS, `ops/docker-compose.yml` | `app` (uvicorn :8000, not published), `purge` (hourly), `logretention` (daily), `caddy` (80/443, HTTPS) |
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
   Install the journald drop-in (14-day container/host log limit; not active before this step):
   `sudo install -m 0644 -D ops/host/journald-belegbruecke.conf /etc/systemd/journald.conf.d/belegbruecke.conf &&
   sudo systemctl restart systemd-journald` (after step 4, from the checkout; details in "Log retention: 14 days").
4. `git clone` the repository (read-only deploy key) to `/srv/ablaufwerk`, check out the release tag.
5. Create `/srv/ablaufwerk/.env` from `.env.example`, `chmod 600 .env`. Set at least:
   `APP_ENV=staging` (or `prod` at go-live), `APP_DOMAIN` (the app's host name only, e.g.
   `app.<domain>`, no `https://`), `APP_PUBLIC_URL` (`https://` + `APP_DOMAIN`), `SITE_PUBLIC_URL`,
   `SESSION_SECRET` (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`),
   `CONSENT_HMAC_KEYS` (see "Rotate secrets"; required in staging/prod),
   `MAILER`, `BREVO_API_KEY` (if `brevo`), `AI_PROVIDER`, `ANTHROPIC_API_KEY` (if `anthropic`).
   Off by default, leave them off until the owner clears them in writing: `AI_TRANSFER_CLEARED=0` (must be `1`
   for `AI_PROVIDER=anthropic` in staging/prod; international transfer to Anthropic not yet cleared,
   `docs/legal/LAUNCH_COMPLIANCE.md`), `ONBOARDING_OPEN=0` (in prod, new accounts only with `1` and final
   AGB/AVV versions).
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
  Consent proofs signed with a `CONSENT_HMAC_KEYS` key are not affected; for records from before dedicated keys,
  list the old secret as `legacy-session:...` first (see `CONSENT_HMAC_KEYS` below).
- `CONSENT_HMAC_KEYS` (keys for the consent-proof HMACs, kept 3 years): format `keyid:base64key,...`, the
  **first** entry signs new records, all listed keys are used to match old ones. New key:
  `openssl rand -base64 32`, with a new id (e.g. `c2027a:<value>`). It must never equal `SESSION_SECRET`
  (the app refuses to start). Rotate by putting the new entry **first and keeping every old entry listed**
  (`c2027a:<new>,c2026a:<old>`); removing an old key makes the records signed with it unmatchable. After a
  `SESSION_SECRET` rotation, list the old session secret as `legacy-session:<old SESSION_SECRET>` so records
  from before dedicated keys stay matchable. Leaked key: add a new first key at once; keep the leaked one only
  for matching. Format and checks are implemented by the app agent (`app/settings.py`).
- `ANTHROPIC_API_KEY` / `BREVO_API_KEY`: create the new key in the provider console, update `.env`,
  restart, check one mapping proposal / one mail, then revoke the old key. In CI: GitHub repo
  Settings -> Secrets -> `ANTHROPIC_API_KEY`.
- Never paste keys into tickets, chats, commit messages or logs. If one is committed by mistake: revoke
  it first, then clean up.

## Logs
- `dc logs app|purge|caddy|logretention` (container stdout via journald; 14-day limit only after the host
  drop-in is installed, see "Log retention: 14 days").
- Caddy access log: `dc exec caddy sh -c 'tail /var/log/caddy/access.log'` (volume `caddy_logs`).
- Caddy access log: IPs masked (/16, /32), `token` removed from query strings, `Referer` (can hold a token
  URL), cookies, authorization, CSRF, X-Forwarded-For and Set-Cookie headers deleted (test:
  `ops/tests/test_ops_scripts.py::test_caddy_log_filter_deletes_sensitive_headers`). uvicorn access logs are off (`--no-access-log`).
- **Never logged:** invoice contents (cell values, XML, PDFs), uploaded file names, AI prompts with values,
  magic-link / opt-in / unsubscribe tokens, session cookies, raw IP addresses, API keys, e-mail bodies.
  Error logs carry exception class names and counts, not values.
- Purge: `purge` service logs one line per run; "ERROR app.purge failed" means retention is at risk: fix the same day.

## Log retention: 14 days
Owner decision: web server and container logs are kept 14 days. Three kinds of enforcement:

**1. Enforced by code in this repo (tested: `ops/tests/test_ops_log_retention.py`, CI step "Log retention
script on fixture").** The `logretention` service runs `ops/scripts/log_retention.py` once at start and then
daily at 00:05 UTC on the `caddy_logs` volume:
- Daily rotation of `/var/log/caddy/access.log` by **copy-truncate**: if the file holds a line from before
  today (UTC), it is read and truncated to 0 bytes right after the read; the lines are filed by their own
  timestamp into `access-day-YYYY-MM-DD.log`. Caddy keeps writing to the same (now empty) file.
  Why not rename + `caddy reload`: Caddy 2.10 keeps log files open across reloads, so a renamed file would
  keep getting lines, and the reload would need the admin API reachable from another container. Caddy opens
  the file with `O_APPEND`, so after the truncate its next line starts at offset 0 (no hole). No line is filed
  twice (every byte read is removed by the truncate). Residual risk: a line written in the microseconds between
  the final read and the truncate is lost; the script first waits for 2 s without writes to keep that window
  out of traffic. (Caddy 2.11 has `roll_at` for lossless time-based rolling; switching the image is a separate
  change that needs the CI `caddy validate` step.)
- Every line older than 14 days is removed from every log file (day files, Caddy's size-rolled
  `access-<timestamp>.log[.gz]`, gzip kept), a file whose newest line is older is deleted, a file without
  readable timestamps goes by its mtime. Rewrites are atomic. With one run per day **no line is older than
  14 days + 1 day**. The active file never holds lines from before the last run.
- Only `access.log`, `access-day-*.log` and Caddy's rolled names are touched; other files, directories and
  symlinks never.
- Check on the server: `dc logs logretention` (one line per run, counts only; `ERROR` = fix the same day),
  `dc run --rm logretention python /opt/ops/log_retention.py --dir /var/log/caddy --verify` (exit 1 lists files
  with over-age lines, never their content).
- Caddy's own `roll_size 5MiB` / `roll_keep_for 336h` in the Caddyfile stay as a size backstop.

**2. Enforced by host configuration, installed by the owner at server setup (NOT active until then).**
Compose sends stdout/stderr of `app`, `purge`, `caddy` and `logretention` to the `journald` logging driver
(`json-file` and `local` rotate by size only and cannot be limited by age). The age limit lives on the host:
1. `sudo install -m 0644 -D ops/host/journald-belegbruecke.conf /etc/systemd/journald.conf.d/belegbruecke.conf`
2. `sudo systemctl restart systemd-journald`
3. Check: `systemd-analyze cat-config systemd/journald.conf | grep -E 'MaxRetentionSec|MaxFileSec'` shows
   `MaxRetentionSec=14day` and `MaxFileSec=1day`; `journalctl CONTAINER_TAG=ablaufwerk-app -n 5` shows lines.
journald deletes whole journal files whose newest entry is older than `MaxRetentionSec`; with `MaxFileSec=1day`
an entry outlives 14 days by about one day (journald.conf(5):
https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html). The drop-in applies to the whole
host journal, so SSH and system logs follow 14 days too. Until it is installed, the distribution default applies
(often no age limit). `dc logs` keeps working with journald; recreating a container no longer deletes its logs
(they stay in the journal until the age limit). Not testable in CI: the test only checks the file content and
that every compose service uses journald.

**3. Outside our control.** The app domain is DNS-only (grey cloud), so Cloudflare does not proxy app requests.
The website is served by Cloudflare Workers (static assets, `wrangler.jsonc` sets no observability/logging).
What Cloudflare itself logs and for how long is set by Cloudflare and the account plan, not by this repo; we make
no claim about it. Owner checks before go-live: https://developers.cloudflare.com/workers/observability/logs/
and https://www.cloudflare.com/privacypolicy/ (and the DPA, go-live checklist).

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
The site build reads `APP_PUBLIC_URL`, `SITE_PUBLIC_URL`, `SITE_STAGING` and `SITE_EVENTS` at build time. Without them it
uses the dev defaults (`http://localhost:...`): the CSP in `_headers` and the checker point at localhost and
the checker on the staging site cannot reach the app.
1. Cloudflare dashboard -> **Workers & Pages** -> the site project -> **Settings** -> **Build** ->
   **Variables** (build variables, not runtime variables or secrets). Exact labels may differ slightly
   between dashboard versions; look for the build-time variables of the Git build.
2. Add `APP_PUBLIC_URL` = `https://<APP_DOMAIN>`, `SITE_PUBLIC_URL` = the site's address,
   `SITE_STAGING` = `1`, `SITE_EVENTS` = `0` (`1` only after the lawyer clears the beacon, PRE_REVIEW
   section 5). Save, then retry the latest build (Deployments -> latest -> Retry build).
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
- [ ] Log retention: journald drop-in installed (`MaxRetentionSec=14day`, `MaxFileSec=1day` shown by
      `systemd-analyze cat-config systemd/journald.conf`), `dc logs logretention` shows daily `ok` lines,
      `--verify` passes; Cloudflare's own log retention checked in its docs/DPA.
- [ ] Mail sending (Brevo) tested with an own address only; sender domain SPF/DKIM set.
