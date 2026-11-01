# Remediation release — 1 Nov 2026 (external audit P0/P1)

Base: `9eb2720` (main before remediation). Not legal advice. Nothing deployed, purchased, signed or sent.

## Corrections
| ID | Correction | Files |
| --- | --- | --- |
| P0-1 | Dedicated consent keyring `CONSENT_HMAC_KEYS` (`keyid:base64key,…`, first signs). Records store `key_id`; matching tries every listed key. Existing records migrated as `legacy-session` (= SESSION_SECRET) so they stay verifiable. Staging/prod refuse to start without the keyring, if the current key equals SESSION_SECRET, or if `legacy-session` is the signing key. Rotation: prepend new key, keep old ones 3 years; before rotating SESSION_SECRET list `legacy-session:<old>`. | `app/security.py`, `app/consent.py`, `app/settings.py`, `app/main.py`, `app/migrations/005_consent_key_id.sql` |
| P0-2 | `purge_consent_records()`: the audit's crash could not be reproduced on main (the `email` read is on `SELECT email FROM subscribers`, a real column). Real latent flaw fixed: active-subscriber matching used one key, so a key change could delete proofs of active subscribers. Rewritten on the keyring; records under a key no longer configured are kept and reported in a warning instead of deleted. | `app/jobs.py` |
| P0-3 | AGB not treated as final: full substantive B2B draft `agb-draft-2` ("Entwurf – nicht freigegeben", liability marked for lawyer); versioned acceptance kept (`agb-draft-1` acceptances preserved, users re-asked). Commercial onboarding gate: in prod new accounts are refused unless `ONBOARDING_OPEN=1` AND AGB/AVV ids are not drafts. | `content/legal/agb-entwurf.md`, `app/legal_texts/terms-agb-draft-2.txt`, `app/settings.py`, `app/main.py`, `site/build.py`, `site/templates/legal_doc.html` (old `agb.html` removed) |
| P0-4 | Customer AVV acceptance recorded: version `avv-draft-1` + timestamp per account, verbatim checkbox text hash-pinned, uploads blocked (403 `avv_required`) until accepted, re-asked on version change, included in the data export. | `app/migrations/006_avv_acceptance.sql`, `app/legal_texts/avv-avv-draft-1.txt`, `app/main.py`, `app/templates/upload.html`, `content/legal/avv-entwurf.md`, `contracts/api.md` |
| P1-5 | Strict 14-day log retention by behaviour: `log_retention.py` cuts the Caddy log daily (copy-truncate; Caddy 2.10 keeps files open across reload) and deletes every line older than 14 days; `--verify` mode; runs daily in a `logretention` service with no network and no secrets. All containers log to journald; host config `MaxRetentionSec=14day`, `MaxFileSec=1day` shipped. Token/cookie/Referer log filters unchanged. | `ops/scripts/log_retention.py`, `ops/docker-compose.yml`, `ops/host/journald-belegbruecke.conf`, `ops/Caddyfile`, `ops/Dockerfile`, `ops/RUNBOOK.md`, `ops/ci/ci.yml`, `.github/workflows/ci.yml` |
| P1-6 | Cloudflare DPA: Cloudflare's page shows **Version 6.4, effective 3 April 2026** (checked 1 Nov 2026). The PDF text was not retrievable here (marked unverified). All references reconciled; "v6.3" remains only as a historical note in PRE_REVIEW. | `content/legal/datenschutz-fakten.md`, `site/templates/datenschutz.html`, `docs/legal/LAUNCH_COMPLIANCE.md` |
| P1-7 | AI: default stays `heuristic` (no network). Staging/prod refuse to start with `AI_PROVIDER=anthropic` unless `AI_TRANSFER_CLEARED=1`. The code sets no `inference_geo`, so Anthropic's default "global" applies; workspace data residency must be read by the owner in the Anthropic Console (not visible from here). | `app/settings.py`, `content/legal/datenschutz-fakten.md`, `site/templates/datenschutz.html` |
| P1-8 | Privacy page states only what is configured: logs "Ausgelegt auf 14 Tage; wird mit der Servereinrichtung aktiviert"; AI off by default / only after clearance; unverified provider locations removed; AGB acceptance record added. Regression tests pin these phrases and the DPA version against the facts sheet. | `site/templates/datenschutz.html`, `content/legal/datenschutz-fakten.md` |
| — | Contracts and env: `CONSENT_HMAC_KEYS`, `ONBOARDING_OPEN`, `AI_TRANSFER_CLEARED`, AVV endpoint, onboarding gate, `agb-draft-2`. | `contracts/config.md`, `contracts/api.md`, `.env.example` |

Migrations: only new files (005, 006) added; applied migrations unchanged; existing consent records, AGB acceptances
and accounts preserved (tested).

## New regression tests (+35 net, 529 total)
- `app/tests/test_app_remediation.py` (31): SESSION_SECRET rotation keeps matching; consent-key rotation with old key
  kept; legacy migration; startup refusals (no keyring, key = SESSION_SECRET, legacy as signer, AI without clearance);
  purge: active > 3 y kept, unsubscribed > 3 y deleted, unsubscribed < 3 y kept, never-unsubscribed and gone > 3 y
  deleted, old-key record of active subscriber kept, unknown-key record kept with warning; onboarding gate in prod;
  AVV required/accepted/version change/export; AGB re-acceptance; integration test that app checkbox texts equal the
  content blocks.
- `ops/tests/test_ops_log_retention.py` (25): injected clock, lines at 13/14/15/30 days, day boundaries, idempotence,
  never deletes non-log files, active file keeps only ≤ 14-day lines, `--verify`, compose uses journald everywhere,
  journald conf values; CI step runs the script on a fixture directory.
- `site/tests/test_site_privacy.py` (5): no claim of active strict retention, DPA version equals facts sheet, AI
  wording, AGB page renders the draft, build fails without the AGB file.
- `content/tests/test_content_files.py` (+): AGB/AVV version ids, draft markers, checkbox blocks present.

## Results
- Local: `python -m pytest -m "not network"` → 529 passed, 2 skipped (real-tool tests), 1 deselected (network).
- CI: green on the final remediation commit (all 4 jobs; healthz now blocking, with a refusal check without the consent key). Informational step "Go-live readiness" fails by design until the business-ID stage.

## Not verifiable here / host-level
- journald driver and host retention: inactive until `ops/host/journald-belegbruecke.conf` is installed at server
  setup; until then container logs have no age limit (no server exists yet).
- Copy-truncate cut: a line written in the microseconds of the cut can be lost (never duplicated). Lossless option:
  Caddy 2.11 `roll_at` (needs image bump).
- Cloudflare's own log retention and the DPA 6.4 PDF text (pages blocked here).
- Anthropic workspace data-residency setting (owner's Console).
- Unverified legal references in the AGB draft: § 312i BGB, § 354a HGB, DSGVO article texts (EUR-Lex not loadable).
