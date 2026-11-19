# Troubleshooting

**English** · [繁體中文](troubleshooting.zh-TW.md) · [← Back to README](../README.md)

## Gotchas

- **Python started by launchd can't reach the lamp** (`No route to host`). macOS Local Network privacy blocks it, but the system `/usr/bin/curl` is not affected. That is why `dash.py` pushes images through curl rather than Python's HTTP.
- **The computer and the lamp may be on different subnets.** Wi-Fi and wired networks are often served by different routers, for example a modem and a mesh router that each hand out addresses. The lamp and the computer need addresses from the same router.
- **Cloudflare Browser Run's free plan allows 10 minutes a day.** Past that it returns 429 until the next UTC day. One pass over a few Threads and X accounts takes about 25 s, so those sources run only on the first cron of every second hour (even UTC hours). The runs in between reuse the last numbers. For more accounts or fresher numbers, change `browserDue` in `parse.js` or move to a paid plan.
- **Threads and X pages never go network-idle.** Wait for the word "followers" to appear on the page instead.
- **A manual `/collect` gets cut off early.** A run started by hand inside `waitUntil` stops after about 30 s, while cron runs get longer. To see a full pass, wait for the next cron run.
- **Threads "recent views" only shows when you are logged in.** Public pages show only the follower count, and this project does not use a logged-in session.
- **When a source fails,** the collector keeps the previous numbers and marks them with `stale_since`, so the lamp never goes blank.

## Scraping public pages

YouTube, Threads and X numbers are read from public pages rather than official APIs. A site redesign can break this, and a platform's terms may limit automated access. Decide for yourself, and use it only for your own accounts. Requests are spaced 1.5–4.5 s apart at random, and browser sources run only every two hours. If you prefer official APIs, use the YouTube Data API or the Threads API behind your own endpoint and connect it as a `json` account.
