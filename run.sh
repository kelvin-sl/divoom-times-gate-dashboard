#!/bin/sh
# One update pass, then exit. launchd runs this every minute; nothing stays running.
#   1. pull the collector's snapshot into data/latest.json (skipped if COLLECTOR_URL is unset;
#      a failed pull keeps the previous file, so the lamp still updates)
#   2. dash.py renders five tiles and pushes them to the lamp
set -eu
cd "$(dirname "$0")"
ENV_FILE=${DASH_ENV:-$HOME/.config/times-gate-dashboard/env}
set -a; . "$ENV_FILE"; set +a
mkdir -p data
if [ -n "${COLLECTOR_URL:-}" ]; then
  # Only fetch the snapshot every 5 minutes; the clock tile still redraws every minute.
  if [ ! -f data/latest.json ] || [ -n "$(find data/latest.json -mmin +4)" ]; then
    if /usr/bin/curl -sSf -m 30 -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/latest" -o data/latest.json.tmp; then
      mv data/latest.json.tmp data/latest.json
    else
      rm -f data/latest.json.tmp
      echo "pull failed; keeping previous data/latest.json" >&2
    fi
  fi
fi
exec "${PYTHON:-python3}" dash.py --push "$DIVOOM_IP"
