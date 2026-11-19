---
name: divoom-times-gate-dashboard
description: Use when someone wants their Divoom Times Gate to show their own numbers (website traffic, Search Console / SEO stats, YouTube / Threads / X followers, Claude Code usage), asks to set up or change this dashboard, add an account or tile, change which tiles rotate on screens 4-5, or debug why the lamp is not updating.
---

# Divoom Times Gate dashboard

Five 128×128 tiles rendered by `dash.py` (Pillow) and pushed over the lamp's LAN API. A Cloudflare
Worker in `worker/` collects numbers on a cron; the Mac pulls `/latest` once every 5 minutes and
renders once a minute via launchd. Read [README.md](README.md) or [README.zh-TW.md](README.zh-TW.md)
for the architecture, and [docs/setup.md](docs/setup.md) and [docs/configuration.md](docs/configuration.md)
for the installation steps. Work from the cloned repository root; this guide
depends on the scripts and examples alongside it.

## Set up (in this order, confirm each step works before the next)

1. Check macOS and Python 3.9+. Create `.venv` with `python3 -m venv .venv`, then run
   `.venv/bin/python -m pip install pillow`, `.venv/bin/python -m unittest discover tests`,
   and `.venv/bin/python dash.py --demo`. Show `out/preview.png`. The demo needs no lamp,
   tokens or cloud account. On another OS, explain that fonts and scheduling need adaptation.
2. For lamp setup, obtain the IP and have the user enter LocalToken locally (never guess;
   a missing token returns `DeviceToken is err`). Create `~/.config/times-gate-dashboard/env`
   from `env.example` if absent, preserve existing settings, and set its permissions to 600.
   Set `PYTHON` to the absolute `.venv/bin/python` path, quoting paths with spaces.
3. Copy example account and scene files only if absent. Ask which accounts and tiles the user
   wants and keep account IDs consistent. Website metrics require the user's own JSON endpoint;
   there is no built-in GA4 or Search Console connector. Keep the collector URL empty for an
   initial local-only setup. Render with `.venv/bin/python dash.py` before pushing.
4. Run `./run.sh` for the lamp setup and check the screens before enabling `./install-launchd.sh`.
   Check `~/Library/Logs/times-gate-dashboard.log`; uninstall with `./install-launchd.sh uninstall`.
5. If the user chooses the collector, follow [Deploy the collector](docs/setup.md#2-deploy-the-collector-cloudflare-worker).
   Check Node >=22.12.0, use `npm ci`, run `npm test`, and configure the KV namespace.
   Replace placeholder accounts and remove unused sources before uploading. Have the user enter
   `PULL_TOKEN` and any JSON `auth_secret` values locally into the matching Worker secrets.
   After deployment, set `COLLECTOR_URL` and the matching `PULL_TOKEN` in the local env file
   **before** running `./lamp.sh push-config`. Expect `{"ok":true}`. Verify `/latest` after a
   successful cron; a successful bundle or deploy alone does not prove live collection works.
6. Report which of demo, lamp push, schedule, deployment and live collection were actually verified,
   and which remain untested. Keep demo-only setup local if that is all the user requested.

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
- Browser sources (Threads, X) cost Browser Run minutes: free plan is 10 min/day.
- Keep 1.5–4.5 s random gaps between scraping requests; only scrape the user's own accounts.
- Never write tokens into the repo; they live in the env file and Worker secrets.
