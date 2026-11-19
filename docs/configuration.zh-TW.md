# 設定檔

[English](configuration.md) · **繁體中文** · [← 回到 README](../README.zh-TW.md)

## `config/accounts.json`：要抓誰

```json
{
  "youtube": [{ "id": "yt-me", "label": "Me", "channel": "UC…頻道 ID" }],
  "threads": [{ "id": "threads-me", "label": "Me", "handle": "your.handle" }],
  "x":       [{ "id": "x-me", "label": "Me", "handle": "your_handle" }],
  "json":    [{ "id": "site", "url": "https://…", "auth_secret": "SITE_API_TOKEN",
                "fields": { "visits_7d": "traffic.visits", "weekly_visits": "traffic.weekly" } }]
}
```

- `id` 是格子引用的代號。`label` 是格子上的短名。`theme` 可以指定這個帳號用哪個佈景主題。
- YouTube 的頻道 ID 在頻道頁原始碼裡搜尋 `channelId`，或在「關於 → 分享頻道 → 複製頻道 ID」找到。
- `json` 來源會用 GET 讀 `url`。如果有 `auth_secret`，就從 Worker 的同名 secret 讀出值，加上 `Authorization: Bearer …`。`fields` 用點路徑把回應攤平成數字，例如 `a.b.0`。做法見下一節。

## 網站流量與 SEO 怎麼接

GA4 和 Search Console 的 API 都要 OAuth 或服務帳號，金鑰不適合放在燈的收集器裡。比較乾淨的做法，是你自己準備一個**唯讀 JSON 端點**，收集器每 15 分鐘讀一次：

```
GA4 Data API ─────┐
                  ├─▶ 你的小服務（排程拉資料、存起來） ─▶ GET /api/summary（Bearer token）─▶ 收集器
Search Console ───┘
```

端點只要回傳你想上燈的數字，例如：

```json
{
  "through": "11/18",
  "traffic": { "visits": 4820, "visits_prev": 4100, "weekly": [2100, 2600, 2450, 3100, 3500, 3900, 4100, 4820] },
  "search":  { "impressions": 18400, "impressions_prev": 14900, "clicks": 512, "clicks_prev": 431,
               "weekly": [120, 180, 210, 260, 330, 390, 431, 512] }
}
```

然後在 `accounts.json` 的 `fields` 對應路徑（見 `examples/accounts.json`），再用 `stats` 格顯示：

- **網站格**：主數字是 7 天造訪，次數字是搜尋曝光和漲跌 %，長條是 8 週造訪。
- **搜尋格**：主數字是 7 天搜尋點擊，次數字是曝光，長條是 8 週點擊。

對新網站來說，這幾個數字最值得每天看：

- **造訪**：有沒有人來。
- **搜尋曝光**：Google 有沒有開始把你排進結果；通常比點擊早幾週動。
- **搜尋點擊**：排名有沒有轉成流量。

Search Console 的資料大約晚 2–3 天，所以格子底下會顯示「through 日期」。

如果你已經有網站分析工具，而且它提供 API token（GET＋Bearer），可以直接把 `url` 指過去，用 `fields` 挑欄位，不必另寫服務。

## `config/scenes.json`：五格放什麼

```json
{
  "theme": "night",
  "rotate": { "auto": true, "every_minutes": 5 },
  "fixed": [ 第 1 格, 第 2 格, 第 3 格 ],
  "pool":  [ { "id": "youtube", "tile": "big", "account": "yt-me" }, … ]
}
```

| `tile` | 內容 | 參數 |
|---|---|---|
| `claude` | 時鐘＋今天的 Claude Code session 數與輸出 token | — |
| `big` | 單一帳號：粉絲（大字）、週變化、帳號 | `account` |
| `rows` | 同平台 2–3 個帳號，每列：簡稱｜粉絲｜週變化 | `accounts` |
| `total` | 多個帳號的粉絲合計＋各平台小計 | `accounts`、`title` |
| `stats` | JSON 來源：主數字、次數字與漲跌 %、8 根長條 | `account`、`main`、`second`、`bars`、`note` |
| `pending` | 還沒接的格子：點線框＋說明 | `title`、`pending` |

每格都可以加 `title`、`theme`。格子上的英文字可以用 `labels` 改成中文，例如 `"labels": {"total": "總粉絲", "collecting": "收集中"}`，可改的鍵見 `dash.py` 的 `LABELS`。

切換第 4–5 格：

```sh
./lamp.sh list                   # 候選池，▶ 是現在顯示的兩張
./lamp.sh next                   # 立刻重抽
./lamp.sh show youtube x         # 指定兩張；只給一張的話，第 5 格隨機
./lamp.sh auto off               # 停止自動重抽
```

## 佈景主題

內建兩套：

- `night`：細分隔線，往上的數字用強調色。
- `poster`：窄體大寫標題、2px 粗線，往上的數字放在強調色小方塊裡。

要用自己的配色和 logo，就新增 `config/themes.json`，沒寫的欄位沿用 `night`：

```json
{ "mine": { "bg": "#101418", "ink": "#f2f2f2", "accent": "#ff7a00", "mark": "/abs/path/logo.png", "wordmark": "My Site" } }
```

平台色只用在主要數字、長條和 logo，例如 YouTube 紅、Claude 橘；底色和漲跌顏色都交給佈景主題決定。

## repo 裡的檔案

| 路徑 | 用途 |
|---|---|
| `dash.py` | 渲染＋推送（單檔，只依賴 Pillow） |
| `run.sh` / `lamp.sh` / `install-launchd.sh` | 一次更新 / 切換第 4–5 格 / 安裝排程 |
| `worker/` | Cloudflare 收集器（`parse.js` 純函式、`sources.js` 各平台、`index.js` 排程與端點） |
| `examples/` | 虛構的設定與快照，`--demo` 和測試用 |
| `assets/logos/` | 平台 logo，`tools/build_logos.py` 從 SVG 產生 |
| `docs/preview.png` | README 的圖，先跑 `dash.py --demo` 再用 `tools/build_preview.py` 重畫 |
| `SKILL.md` | 給 Claude Code 等 AI 助手照著幫你安裝 |
