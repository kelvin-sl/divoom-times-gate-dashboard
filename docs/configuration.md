# Configuration

**English** · [繁體中文](configuration.zh-TW.md) · [← Back to README](../README.md)

## `config/accounts.json`: what to collect

```json
{
  "youtube": [{ "id": "yt-me", "label": "Me", "channel": "UC…channel id" }],
  "threads": [{ "id": "threads-me", "label": "Me", "handle": "your.handle" }],
  "x":       [{ "id": "x-me", "label": "Me", "handle": "your_handle" }],
  "json":    [{ "id": "site", "url": "https://…", "auth_secret": "SITE_API_TOKEN",
                "fields": { "visits_7d": "traffic.visits", "weekly_visits": "traffic.weekly" } }]
}
```

- `id` is the name tiles use to refer to the account, and `label` is the short name shown on the tile. `theme` optionally picks a theme for that account.
- To find a YouTube channel id, search the channel page source for `channelId`, or use About → Share channel → Copy channel ID.
- A `json` account is read with GET from its `url`. If it has an `auth_secret`, the collector takes the value of the Worker secret with that name and sends it as `Authorization: Bearer …`. `fields` maps dotted paths in the response, such as `a.b.0`, to flat numbers. The next section shows how to set this up.

## Connecting website traffic and SEO

The GA4 and Search Console APIs both need OAuth or a service account, and those credentials don't belong in the lamp's collector. The cleaner setup is a **read-only JSON endpoint** of your own, which the collector reads every 15 minutes:

```
GA4 Data API ─────┐
                  ├─▶ your small service (pulls on a schedule, stores) ─▶ GET /api/summary (Bearer token) ─▶ collector
Search Console ───┘
```

The endpoint only has to return the numbers you want on the lamp. For example:

```json
{
  "through": "11/18",
  "traffic": { "visits": 4820, "visits_prev": 4100, "weekly": [2100, 2600, 2450, 3100, 3500, 3900, 4100, 4820] },
  "search":  { "impressions": 18400, "impressions_prev": 14900, "clicks": 512, "clicks_prev": 431,
               "weekly": [120, 180, 210, 260, 330, 390, 431, 512] }
}
```

Map those paths in `fields` in `accounts.json` (see `examples/accounts.json`). Then show them with `stats` tiles:

- **Website tile:** the main number is 7-day visits, the second is search impressions with a % change, and the bars are 8 weeks of visits.
- **Search tile:** the main number is 7-day search clicks, the second is impressions, and the bars are 8 weeks of clicks.

For a new site, these are the numbers worth checking every day:

- **Visits:** whether anyone is coming.
- **Search impressions:** whether Google has started to show you in results. These usually move weeks before clicks do.
- **Search clicks:** whether rankings are turning into traffic.

Search Console data runs about 2–3 days behind, so the tile shows a "through" date at the bottom.

If your analytics tool already has an API that takes a token (GET + Bearer), you can point `url` at it and pick fields with `fields`, with no separate service.

## `config/scenes.json`: what the five screens show

```json
{
  "theme": "night",
  "rotate": { "auto": true, "every_minutes": 5 },
  "fixed": [ screen 1, screen 2, screen 3 ],
  "pool":  [ { "id": "youtube", "tile": "big", "account": "yt-me" }, … ]
}
```

| `tile` | Shows | Parameters |
|---|---|---|
| `claude` | Clock, plus today's Claude Code sessions and output tokens | — |
| `big` | One account: followers (large), weekly change, handle | `account` |
| `rows` | 2–3 accounts on one platform; each row is label, followers, weekly change | `accounts` |
| `total` | Followers summed over several accounts, with per-platform subtotals | `accounts`, `title` |
| `stats` | A JSON account: main number, second number with % change, 8 bars | `account`, `main`, `second`, `bars`, `note` |
| `pending` | A tile not connected yet: dotted frame and a note | `title`, `pending` |

Every tile also takes `title` and `theme`. To change the text printed on tiles, use `labels`, for example `"labels": {"total": "followers", "collecting": "warming up"}`. The available keys are in `LABELS` in `dash.py`.

To control screens 4–5:

```sh
./lamp.sh list                   # the pool; ▶ marks the two on screen
./lamp.sh next                   # draw a new pair now
./lamp.sh show youtube x         # pin two tiles; with one id, screen 5 is random
./lamp.sh auto off               # stop redrawing automatically
```

## Themes

There are two built-in themes:

- `night` has thin rules and shows rising numbers in the accent colour.
- `poster` has condensed upper-case titles and a 2px rule, and puts rising numbers in an accent-coloured chip.

To use your own colours and logo, add `config/themes.json`. Any field you leave out comes from `night`:

```json
{ "mine": { "bg": "#101418", "ink": "#f2f2f2", "accent": "#ff7a00", "mark": "/abs/path/logo.png", "wordmark": "My Site" } }
```

Platform colours, such as YouTube red and Claude orange, are only used for main numbers, bars and logos. The theme sets the background and the colours for up and down.

## Files in this repository

| Path | Purpose |
|---|---|
| `dash.py` | Render and push (one file, only needs Pillow) |
| `run.sh` / `lamp.sh` / `install-launchd.sh` | One update pass / control screens 4–5 / install the schedule |
| `worker/` | Cloudflare collector (`parse.js` pure functions, `sources.js` per platform, `index.js` schedule and endpoints) |
| `examples/` | Made-up config and snapshot for `--demo` and the tests |
| `assets/logos/` | Platform logos, generated from SVG by `tools/build_logos.py` |
| `docs/preview.png` | README image, rebuilt by `tools/build_preview.py` after `dash.py --demo` |
| `SKILL.md` | Lets Claude Code or another AI assistant set this up for you |
