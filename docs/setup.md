# Setup

**English** · [繁體中文](setup.zh-TW.md) · [← Back to README](../README.md)

## Requirements

First create the virtual environment and check the demo, as in the [README quick start](../README.md#quick-start).

- A Divoom Times Gate on the same LAN and subnet as your computer, for example both on `192.168.1.x`.
- The lamp's IP and its **LocalToken**. Without the token, the lamp answers `DeviceToken is err`.
- macOS and Python 3.9+. Install Pillow in a virtual environment, as in the [README quick start](../README.md#quick-start). The renderer uses macOS system fonts, including PingFang for CJK text; the schedule uses launchd. Other operating systems need font and scheduler changes.
- For the optional collector: a Cloudflare account and Node **22.12.0 or newer**, as required by the Wrangler version in `worker/package-lock.json`. See [Gotchas](troubleshooting.md#gotchas) for free-plan limits.

## 1. Push to the lamp

```sh
mkdir -p ~/.config/times-gate-dashboard
cp -n env.example ~/.config/times-gate-dashboard/env
chmod 600 ~/.config/times-gate-dashboard/env
cp -n examples/scenes.json examples/accounts.json config/
.venv/bin/python -c 'import sys; print(sys.executable)'
```

The copy commands preserve existing files. Edit `~/.config/times-gate-dashboard/env`:
set `DIVOOM_IP` and `DIVOOM_TOKEN` to your lamp's values, and set `PYTHON` to the full path
printed above, quoted if it contains spaces. Leave `COLLECTOR_URL` and `PULL_TOKEN` empty
for this first local update. launchd does not read your shell profile or activate a virtual environment.

```sh
./run.sh
```

Check the five screens on the lamp. The clock and local Claude usage should appear;
tiles without collected data show placeholders. Once this works, enable the schedule:

```sh
./install-launchd.sh
```

It runs every minute and logs to `~/Library/Logs/times-gate-dashboard.log`.
To remove the schedule, run `./install-launchd.sh uninstall`.

## 2. Deploy the collector (Cloudflare Worker)

Skip this section if you only want local Claude usage and the clock. Otherwise, finish step 2 first.
Edit `config/accounts.json`: replace example accounts with your own and remove sources you will not use.
Website metrics need your own JSON endpoint; see [Connecting website traffic and SEO](configuration.md#connecting-website-traffic-and-seo).
Keep account IDs consistent with `config/scenes.json`.

From the repository root:

```sh
cd worker
node --version                             # must be >= 22.12.0
npm ci
npm test
cp -n wrangler.example.jsonc wrangler.jsonc
npx wrangler login
npx wrangler kv namespace create KV
```

Put the returned namespace ID into `kv_namespaces[0].id` in `worker/wrangler.jsonc`.
For an existing installation, keep its namespace ID and skip namespace creation.
Then, still in `worker/`:

```sh
openssl rand -hex 24                        # make a token
npx wrangler secret put PULL_TOKEN          # paste that token when prompted
```

Save the same token as `PULL_TOKEN` in `~/.config/times-gate-dashboard/env`.
For each JSON account with `auth_secret`, also create the matching Worker secret, for example
`npx wrangler secret put SITE_API_TOKEN`, and enter that endpoint's token.

```sh
npx wrangler deploy                         # prints https://times-gate-collector.<you>.workers.dev
cd ..
```

**Before uploading configuration**, put the deployed URL (without a trailing slash) in
`COLLECTOR_URL` in the env file and check that `PULL_TOKEN` matches the Worker secret.

```sh
./lamp.sh push-config                       # upload config/accounts.json to KV
```

Expect `{"ok":true}`. After the next successful cron run (scheduled every 15 minutes),
`/latest` contains a snapshot and the Mac picks it up on its next pull.
Threads and X normally refresh every two hours (see [Gotchas](troubleshooting.md#gotchas)).
To change accounts later, edit `config/accounts.json` and run `./lamp.sh push-config`; you don't need to redeploy.

These commands trigger a run by hand and help with debugging:

```sh
set -a
. "$HOME/.config/times-gate-dashboard/env"
set +a
curl -X POST -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/collect"     # 202, runs in the background
curl -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/probe?group=threads&handle=your.handle"
curl -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/last_error"
```
