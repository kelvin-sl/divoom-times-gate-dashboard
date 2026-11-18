---
name: divoom-times-gate-dashboard
description: Use when someone wants their Divoom Times Gate to show their own numbers (website traffic, Search Console / SEO stats, YouTube / Threads / X followers, Claude Code usage), asks to set up or change this dashboard, add an account or tile, change which tiles rotate on screens 4-5, or debug why the lamp is not updating.
---

# Divoom Times Gate dashboard

Five 128×128 tiles rendered by `dash.py` (Pillow) and pushed over the lamp's LAN API. A Cloudflare
Worker in `worker/` collects numbers on a cron; the Mac pulls `/latest` once every 5 minutes and
renders once a minute via launchd. Read `README.md` for the full architecture before changing it.

## Set up (in this order, confirm each step works before the next)

1. `pip install pillow && python3 dash.py --demo` → open `out/preview.png`; `python3 -m unittest discover tests`.
2. Ask the user for the lamp IP and LocalToken (never guess; a missing token returns `DeviceToken is err`).
   Write `~/.config/times-gate-dashboard/env` from `env.example`, `PYTHON` as an absolute path.
3. Ask which accounts to show: website stats endpoint (URL, which fields), YouTube channel ids,
   Threads / X handles. Confirm the list with the user before writing `config/accounts.json` and
   `config/scenes.json` (start from `examples/`).
4. `./run.sh` once, then `./install-launchd.sh`. Check `~/Library/Logs/times-gate-dashboard.log`.
5. Collector (optional): follow README "架收集器". Use `/probe?group=…` to test one account
   before relying on the cron. Then `./lamp.sh push-config`.

## Change things

- Tiles and rotation: `config/scenes.json` (`fixed` = screens 1-3, `pool` = random screens 4-5).
- Accounts: `config/accounts.json`, then `./lamp.sh push-config` (no redeploy).
- Switch now: `./lamp.sh next`, `./lamp.sh show <id> [<id>]`, `./lamp.sh auto on|off`.
- New tile type: add a `t_<name>(ctx, spec)` to `dash.py`, register it in `TILES`, add it to the
  pool in `examples/scenes.json` so `tests/test_dash.py` renders it.
- New source: add a function to `worker/src/sources.js`, a parser + test in `parse.js` /
  `test/parse.test.js`, and a key in `SOURCES` in `index.js`.

## Rules

- Keep the Mac side one-shot: no loops, no daemons. Push with `/usr/bin/curl` (launchd Python is
  blocked from the LAN on macOS).
- Browser sources (Threads, X) cost Browser Rendering minutes: free plan is 10 min/day.
- Keep 1.5–4.5 s random gaps between scraping requests; only scrape the user's own accounts.
- Never write tokens into the repo; they live in the env file and Worker secrets.
