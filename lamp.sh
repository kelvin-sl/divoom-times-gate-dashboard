#!/bin/sh
# Change what screens 4-5 show, then update the lamp right away.
#   ./lamp.sh list               pool tiles; ▶ marks the two on screen
#   ./lamp.sh next               draw a new random pair now
#   ./lamp.sh show <id> [<id>]   put pool tile(s) on screens 4-5 (one id: screen 5 is random)
#   ./lamp.sh auto on|off        redraw automatically every rotate.every_minutes
#   ./lamp.sh push-config        upload config/accounts.json to the collector (no redeploy)
set -eu
cd "$(dirname "$0")"
ENV_FILE=${DASH_ENV:-$HOME/.config/times-gate-dashboard/env}
set -a; . "$ENV_FILE"; set +a
mkdir -p data
cmd=${1:-list}
if [ "$cmd" = push-config ]; then
  /usr/bin/curl -sSf -X PUT -H "Authorization: Bearer $PULL_TOKEN" -H 'Content-Type: application/json' \
    --data-binary @config/accounts.json "$COLLECTOR_URL/config"; echo
  exit 0
fi
[ $# -gt 0 ] && shift
rc=0; "${PYTHON:-python3}" - "$cmd" "$@" <<'PY' || rc=$?
import json, sys, time
cmd, args = sys.argv[1], sys.argv[2:]
sys.path.insert(0, ".")
from dash import draw
ids = [t["id"] for t in json.load(open("config/scenes.json")).get("pool", [])]
try: st = json.load(open("data/state.json"))
except Exception: st = {}
cur = st.get("picks") or []
if cmd == "list":
    for i in ids: print(("▶ " if i in cur else "  ") + i)
    print("auto:", "on" if st.get("auto", True) else "off"); sys.exit(3)  # 3 = done, don't push
if cmd == "next": st["picks"] = draw(ids, cur)
elif cmd == "show":
    bad = [a for a in args if a not in ids]
    if bad or not args: sys.exit(f"unknown tile {bad or '(none)'}; pool: {' '.join(ids)}")
    st["picks"] = args[:2] if len(args) > 1 else draw(ids, cur, first=args[0])
elif cmd == "auto" and args[:1] in (["on"], ["off"]): st["auto"] = args[0] == "on"
else: sys.exit(f"unknown command: {cmd} {' '.join(args)}")
st["since"] = time.time()
json.dump(st, open("data/state.json", "w"))
print("screens 4-5:", " + ".join(st.get("picks") or cur), "| auto", "on" if st.get("auto", True) else "off")
PY
[ $rc -eq 3 ] && exit 0
[ $rc -ne 0 ] && exit $rc
exec ./run.sh
