# Divoom Times Gate Dashboard

[![test](https://github.com/kelvin-sl/divoom-times-gate-dashboard/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/kelvin-sl/divoom-times-gate-dashboard/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.9%2B-3776ab)
![cloudflare](https://img.shields.io/badge/collector-Cloudflare%20Workers-f38020)
![macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**English** · [繁體中文](README.zh-TW.md)

**Turn the five screens of a Divoom Times Gate into a desk dashboard for your own numbers.**

Website visits, search impressions and clicks, followers on your own accounts, and today's
Claude Code usage. A Cloudflare cron collects; your Mac renders once a minute and exits.

[Quick start](#quick-start) · [Why this dashboard?](#why-this-dashboard) ·
[Architecture](#architecture) · [Documentation](#documentation)

## See it in action

![Five Times Gate screens: website, followers, Claude Code, and two tiles drawn from the pool](docs/preview.png)

Rendered by `python3 dash.py --demo` from the made-up data in [`examples/`](examples/), at the
lamp's real 128×128 resolution. Screens 1–3 stay fixed. Every 5 minutes, screens 4–5 show two
tiles drawn at random from a pool, and the same pair never comes up twice in a row.

| Tile | What it shows | Where the numbers come from |
| :--- | :------------ | :-------------------------- |
| Website | 7-day visits, search impressions with % change, 8 weeks of bars | A read-only JSON endpoint you own |
| Followers | Total across your accounts, per-platform subtotals, weekly change | Public YouTube, Threads and X pages |
| Claude Code | Clock, today's sessions and output tokens | Local transcripts in `~/.claude`, never uploaded |
| Pool | Search clicks, YouTube, Threads, X, or a dotted frame for platforms not connected yet | Same as above |

## Why this dashboard?

- **Collection keeps running while your Mac sleeps.** A Cloudflare Worker collects every 15
  minutes and stores one snapshot a day, so "change from a week ago" always has data.
- **Nothing stays resident on your Mac.** launchd runs one pass a minute and exits: 0.2 s and
  47 MB with the Claude scan cached.
- **No API keys for followers.** YouTube is read from the channel page; Threads and X through
  a headless browser on the Cloudflare free plan.
- **Analytics credentials stay out of the collector.** Traffic and SEO come from a small JSON
  endpoint you control, so GA4 and Search Console credentials never reach the lamp.
- **The data is a file.** `data/latest.json` is the latest snapshot, ready for other tools.

### How it compares with other Times Gate projects

Summarised from each repo's GitHub description (2026-11-19):

| Project | What it does | How this repo differs |
| :------ | :----------- | :-------------------- |
| [averhaegen/hacs-divoom-times-gate-dev](https://github.com/averhaegen/hacs-divoom-times-gate-dev) | Home Assistant integration | Needs Home Assistant; this needs only Python and curl |
| [raishack/divoom-times-gate-controller](https://github.com/raishack/divoom-times-gate-controller) | Local controller: images, GIFs, widgets, playlists | General control; this one is about your numbers and growth |
| [shallow-seek-nothing/divoom-times-gate](https://github.com/shallow-seek-nothing/divoom-times-gate) | Five-panel PC dashboard (GPU / CPU / services / clock / weather) | Watches your computer; this watches your site and accounts |
| [johnpc/divoom-time-gate](https://github.com/johnpc/divoom-time-gate) | Home Assistant status on the Times Gate (TypeScript) | Same as above |
| [4ch1m/pixoo-rest](https://github.com/4ch1m/pixoo-rest) | REST API for the Divoom **Pixoo** | A different device |

## Architecture

```
 Cloudflare (always on)                      Your Mac (nothing stays running)
┌───────────────────────────────┐          ┌───────────────────────────────────────┐
│ Worker cron, every 15 min     │  GET     │ launchd runs run.sh every 60 s, exits │
│  YouTube   public channel page│ /latest  │  1. curl the snapshot → data/latest   │
│  Threads/X headless browser   │ ───────▶ │     (every 5 min; keeps the old file  │
│  JSON      your traffic / SEO │ Bearer   │      if the pull fails)               │
│            endpoint           │ token    │  2. dash.py reads data/ + ~/.claude   │
│ KV: latest, day:<date> (60 d) │          │     → five 128×128 tiles → the lamp   │
└───────────────────────────────┘          └──────────────────┬────────────────────┘
                                                              │ POST http://<lamp-ip>/post
                                                              ▼  (LAN, LocalToken)
                                                       Divoom Times Gate
```

Collection runs in the cloud because Threads and X need a browser and weekly changes need a
history. Rendering runs locally because the lamp only accepts LAN requests and your Claude
transcripts live on your computer. If you only want the clock and Claude usage, skip Cloudflare.

## Quick start

On macOS with Python 3.9+. No lamp, tokens or Cloudflare account are needed for the preview:

```sh
git clone https://github.com/kelvin-sl/divoom-times-gate-dashboard
cd divoom-times-gate-dashboard
python3 -m venv .venv
.venv/bin/python -m pip install pillow
.venv/bin/python -m unittest discover tests
.venv/bin/python dash.py --demo          # → out/preview.png
open out/preview.png
```

Then follow [Setup](docs/setup.md) to push to the lamp, schedule it with launchd and,
optionally, deploy the collector.

**Or let an AI assistant do it.** In Claude Code, Codex or another assistant with terminal access, paste:

```text
Help me set up this Divoom Times Gate dashboard on my Mac:
https://github.com/kelvin-sl/divoom-times-gate-dashboard

Clone the repository into a local project folder, then read README.md, SKILL.md and docs/.
First create a Python virtual environment, install Pillow, run the tests, and show
me the demo preview. This step needs no lamp or Cloudflare account.
Then guide me through the lamp setup, asking for missing settings. Have me enter
tokens locally, and preserve any existing configuration. Set up the optional
Cloudflare collector only if I choose to use it. Verify each completed step and
tell me what remains untested.
```

[SKILL.md](SKILL.md) is the setup guide the assistant follows.

## Documentation

| Guide | What you will find |
| :---- | :----------------- |
| [Setup](docs/setup.md) | Requirements, pushing to the lamp, launchd, deploying the Cloudflare collector |
| [Configuration](docs/configuration.md) | Accounts, connecting website traffic and SEO, tiles, the rotation pool, themes |
| [Times Gate local API](docs/times-gate-api.md) | The two commands this project uses and the `PicID` rule |
| [Troubleshooting](docs/troubleshooting.md) | launchd and Local Network, subnets, free-plan limits, scraping caveats |

## Scope and limits

- **macOS only for now.** Rendering uses macOS system fonts and scheduling uses launchd.
- **Bring your own analytics endpoint.** This repo does not include a GA4 or Search Console connector.
- **Public pages, not official APIs.** A redesign can break scraping, and platform terms may
  limit automated access. Use it for your own accounts; see [Troubleshooting](docs/troubleshooting.md#scraping-public-pages).

Background write-up: [Turning a Divoom Times Gate into a growth dashboard](https://kelvinwang.info/en/blog/divoom-times-gate-dashboard/?utm_source=github&utm_medium=readme&utm_campaign=divoom-times-gate-dashboard)
([中文版](https://kelvinwang.info/zh-hant/blog/divoom-times-gate-dashboard/?utm_source=github&utm_medium=readme&utm_campaign=divoom-times-gate-dashboard)).

## Verification and contributing

```sh
.venv/bin/python -m unittest discover tests      # renderer, rotation, empty/corrupt data
(cd worker && npm ci && npm test)                # collector parsing
```

| What | How | Result (2026-11-19) |
| :--- | :-- | :------------------ |
| Rendering | 10 Python tests, including a corrupt `latest.json` and Pillow without libraqm; run on macOS in CI | Pass |
| Rotation | Never repeats the previous pair; no redraw before the interval | Pass |
| Collector parsing | 6 Node tests: K/M suffixes, login walls, failures keep old data | Pass |
| Live YouTube read | `sources.youtube` against YouTube's own channel | Subscribers, views, videos |
| Live Threads / X read | Public pages rendered in local Chrome, parsed with the same `parse.js` | Follower counts |
| Worker bundle | `npx wrangler deploy --dry-run` | Builds (137 KB gzip) |
| Push to the lamp | `./lamp.sh show x threads` against a real lamp | All five screens `error_code: 0` |

[Issues](https://github.com/kelvin-sl/divoom-times-gate-dashboard/issues) and small fixes are
welcome. Include your macOS version, Python version and the command output. Add a test for
changed behavior. If this helps your desk, a GitHub star helps others find it.

## Security

- Lamp and collector tokens live in `~/.config/times-gate-dashboard/env` (mode 600) and in
  Worker secrets, never in the repository.
- The collector's endpoints require a Bearer token. The lamp is only reached over your LAN.
- Claude Code transcripts are read locally; only the rendered tiles leave your Mac, to the lamp.

## License

[MIT](LICENSE). Platform logos are from [Simple Icons](https://simpleicons.org/) 16.36.0 (CC0).
Divoom, Times Gate, YouTube, Threads, X and Claude are trademarks of their respective owners.
This project is not affiliated with any of them.
