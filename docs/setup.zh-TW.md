# 安裝設定

[English](setup.md) · **繁體中文** · [← 回到 README](../README.zh-TW.md)

## 需要什麼

先照 [README 的快速開始](../README.zh-TW.md#快速開始)建好虛擬環境並看過範例畫面。

- Divoom Times Gate，和電腦在同一個區網（同網段，例如都是 `192.168.1.x`）。
- 燈的 IP 和 **LocalToken**。少了 token，燈會回 `DeviceToken is err`。
- macOS、Python 3.9 以上。Pillow 會安裝在下方的虛擬環境裡。渲染使用 macOS 系統字型，中文字用蘋方；排程使用 launchd。其他作業系統需要調整字型與排程。
- （選配收集器）Cloudflare 帳號、Node **22.12.0 以上**，這是 `worker/package-lock.json` 鎖定的 Wrangler 版本要求。免費方案限制見[坑](troubleshooting.zh-TW.md#坑)。

## 1. 推到燈上

```sh
mkdir -p ~/.config/times-gate-dashboard
cp -n env.example ~/.config/times-gate-dashboard/env
chmod 600 ~/.config/times-gate-dashboard/env
cp -n examples/scenes.json examples/accounts.json config/
.venv/bin/python -c 'import sys; print(sys.executable)'
```

上述複製指令會保留已存在的檔案。編輯 `~/.config/times-gate-dashboard/env`：
把 `DIVOOM_IP`、`DIVOOM_TOKEN` 換成你的桌燈設定，`PYTHON` 填入剛才印出的完整路徑，
路徑含空白時加上引號。第一次本機更新先讓 `COLLECTOR_URL`、`PULL_TOKEN` 保持空白。
launchd 不會讀你的 shell 設定，也不會自動啟用虛擬環境。

```sh
./run.sh
```

檢查燈上五格：應看到時鐘與本機 Claude 用量，尚未收集資料的格子顯示佔位畫面。
確認成功後，再開啟排程：

```sh
./install-launchd.sh
```

之後每分鐘更新，日誌在 `~/Library/Logs/times-gate-dashboard.log`。
要移除排程，執行 `./install-launchd.sh uninstall`。

## 2. 架收集器（Cloudflare Worker）

只看本機 Claude 用量與時鐘可跳過這段；要收集遠端資料，請先完成第 2 步。
編輯 `config/accounts.json`，換成自己的帳號並刪除不用的來源。
網站數據需要自備 JSON 端點，見[網站流量與 SEO 怎麼接](configuration.zh-TW.md#網站流量與-seo-怎麼接)。
帳號 ID 須與 `config/scenes.json` 一致。

從 repo 根目錄開始：

```sh
cd worker
node --version                             # 須為 22.12.0 以上
npm ci
npm test
cp -n wrangler.example.jsonc wrangler.jsonc
npx wrangler login
npx wrangler kv namespace create KV
```

把回傳的 namespace ID 填進 `worker/wrangler.jsonc` 的 `kv_namespaces[0].id`。
若是既有安裝，保留原本的 namespace ID，跳過建立步驟。
接著仍在 `worker/` 執行：

```sh
openssl rand -hex 24                        # 產生一組 token
npx wrangler secret put PULL_TOKEN          # 提示輸入時貼上剛才的 token
```

在 `~/.config/times-gate-dashboard/env` 的 `PULL_TOKEN` 填同一組 token。
每個 JSON 來源若有 `auth_secret`，也要建立同名 Worker secret，例如
`npx wrangler secret put SITE_API_TOKEN`，輸入該端點的 token。

```sh
npx wrangler deploy                         # 會印出 https://times-gate-collector.<你>.workers.dev
cd ..
```

**上傳設定之前**，先把部署網址填入 env 的 `COLLECTOR_URL`（結尾不要加 `/`），
並確認 `PULL_TOKEN` 與 Worker secret 相同。

```sh
./lamp.sh push-config                       # 把 config/accounts.json 上傳到 KV
```

應回傳 `{"ok":true}`。下一輪 cron 成功後（每 15 分鐘排程一次），`/latest` 會有快照，
Mac 下次拉取時就能取得。Threads／X 通常每兩小時更新，原因見[坑](troubleshooting.zh-TW.md#坑)。
之後改帳號只要改 `config/accounts.json` 再 `./lamp.sh push-config`，不用重新部署。

手動觸發與除錯：

```sh
set -a
. "$HOME/.config/times-gate-dashboard/env"
set +a
curl -X POST -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/collect"     # 202，背景跑
curl -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/probe?group=threads&handle=你的帳號"
curl -H "Authorization: Bearer $PULL_TOKEN" "$COLLECTOR_URL/last_error"
```
