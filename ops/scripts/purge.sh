#!/bin/sh
# Hourly retention purge (contracts/api.md "Retention"), run by the `purge` service in ops/docker-compose.yml.
#
# 1. `python -m app.purge` (requested from the app agent, docs/requests/ops.md): deletes raw uploads,
#    generated files, job error texts and expired tokens older than RETENTION_HOURS in DB and TEMP_DIR.
#    It must print counts only, never file names, invoice values or tokens.
# 2. Safety net: any file in TEMP_DIR older than RETENTION_HOURS is deleted even if the app CLI fails.
#    (DB rows with error texts can only be purged by step 1; its failure is logged loudly.)
#
# Backups: none in v1 on purpose. Customer data lives at most 24 h; a backup would only keep it longer.
# Lost DB = users log in again via magic link and re-upload. Revisit when accounts/plans hold paid state.
set -u

INTERVAL="${PURGE_INTERVAL_SECONDS:-3600}"
HOURS="${RETENTION_HOURS:-24}"
TMP="${TEMP_DIR:-/data/tmp}"

run_once() {
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if python -m app.purge; then
    echo "$ts purge: app.purge ok"
  else
    echo "$ts purge: ERROR app.purge failed (exit $?) - DB error texts may outlive retention" >&2
  fi
  if [ -d "$TMP" ]; then
    n="$(find "$TMP" -type f -mmin +"$((HOURS * 60))" -print -delete 2>/dev/null | wc -l)"
    find "$TMP" -mindepth 1 -type d -empty -mmin +"$((HOURS * 60))" -delete 2>/dev/null
    echo "$ts purge: safety net removed $n file(s) older than ${HOURS} h"
  fi
}

if [ "${1:-}" = "--once" ]; then
  run_once
  exit 0
fi
while :; do
  run_once
  sleep "$INTERVAL"
done
