# Divoom Times Gate Dashboard

[![test](https://github.com/kelvin-sl/divoom-times-gate-dashboard/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/kelvin-sl/divoom-times-gate-dashboard/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.9%2B-3776ab)
![cloudflare](https://img.shields.io/badge/collector-Cloudflare%20Workers-f38020)
![macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[English](README.md) · **繁體中文**

**把 Divoom Times Gate 的五塊螢幕，變成看自己數字的桌面儀表板。**

網站造訪、搜尋曝光與點擊、自己帳號的粉絲數，還有今天的 Claude Code 用量。
資料由 Cloudflare 排程收集，Mac 每分鐘畫一次就結束。

[快速開始](#快速開始) · [為什麼做這個](#為什麼做這個) ·
[架構](#架構) · [文件](#文件)

## 實際畫面

![Times Gate 五格：網站、粉絲、Claude Code，以及從候選池抽出的兩格](docs/preview.png)

這張圖由 `python3 dash.py --demo` 用 [`examples/`](examples/) 的虛構資料畫出，解析度就是燈上的
128×128。第 1 到 3 格固定，第 4、5 格每 5 分鐘從候選池隨機抽兩張，不會連續兩輪是同一對。

| 格子 | 顯示什麼 | 數字從哪來 |
| :--- | :------- | :--------- |
| 網站 | 7 天造訪、搜尋曝光和漲跌 %、8 週長條 | 你自己的唯讀 JSON 端點 |
| 粉絲 | 所有帳號加總、各平台小計、一週變化 | YouTube、Threads、X 的公開頁 |
| Claude Code | 時鐘、今天的 session 數和輸出 token | 本機 `~/.claude` 的對話紀錄，不上傳 |
| 候選池 | 搜尋點擊、YouTube、Threads、X，還沒接的平台顯示點線框 | 同上 |

## 為什麼做這個

- **Mac 睡著也照樣收。** Cloudflare Worker 每 15 分鐘收一次，每天存一份快照，「跟一週前比」才一直有資料。
- **Mac 上不常駐。** launchd 每分鐘跑一次就結束，有快取時一次 0.2 秒、47 MB。
- **粉絲數不需要 API 金鑰。** YouTube 直接讀頻道頁；Threads 和 X 用 Cloudflare 免費方案的無頭瀏覽器讀。
- **分析工具的金鑰不進收集器。** 流量和 SEO 從你自己控制的 JSON 端點讀，GA4 和 Search Console 的金鑰不會碰到燈。
- **資料就是一個檔案。** `data/latest.json` 是最新快照，其他工具可以直接讀。

### 和其他 Times Gate 專案比較

依各 repo 在 GitHub 上的描述整理（2026-11-19）：

| 專案 | 做什麼 | 跟這個 repo 的差別 |
| :--- | :----- | :----------------- |
| [averhaegen/hacs-divoom-times-gate-dev](https://github.com/averhaegen/hacs-divoom-times-gate-dev) | Home Assistant 整合 | 需要 Home Assistant；這個只要 Python 和 curl |
| [raishack/divoom-times-gate-controller](https://github.com/raishack/divoom-times-gate-controller) | 本機控制器：圖片、GIF、小工具、播放清單 | 通用控制；這個專注在你的數字和成長 |
| [shallow-seek-nothing/divoom-times-gate](https://github.com/shallow-seek-nothing/divoom-times-gate) | 五格電腦儀表板（GPU／CPU／服務／時鐘／天氣） | 看電腦狀態；這個看網站和帳號 |
| [johnpc/divoom-time-gate](https://github.com/johnpc/divoom-time-gate) | 在 Times Gate 顯示 Home Assistant 狀態（TypeScript） | 同上 |
| [4ch1m/pixoo-rest](https://github.com/4ch1m/pixoo-rest) | Divoom **Pixoo** 的 REST API | 不同裝置 |

## 架構

```
 Cloudflare（一直開著）                       你的 Mac（不常駐）
┌───────────────────────────────┐          ┌───────────────────────────────────────┐
│ Worker cron，每 15 分鐘        │  GET     │ launchd 每 60 秒跑一次 run.sh 就結束  │
│  YouTube   公開頻道頁          │ /latest  │  1. curl 拉快照 → data/latest         │
│  Threads/X 無頭瀏覽器          │ ───────▶ │     （每 5 分鐘；拉失敗就沿用舊檔）    │
│  JSON      你的流量／SEO 端點  │ Bearer   │  2. dash.py 讀 data/ + ~/.claude      │
│ KV：latest、day:<日期>（60 天）│ token    │     → 五張 128×128 → 推到燈           │
└───────────────────────────────┘          └──────────────────┬────────────────────┘
                                                              │ POST http://<燈的IP>/post
                                                              ▼  （區網、LocalToken）
                                                       Divoom Times Gate
```

收集放雲端，因為 Threads 和 X 要跑瀏覽器，一週變化也需要歷史資料。畫圖放本機，因為燈只接受區網請求，
Claude 的紀錄也只在你的電腦上。只想看時鐘和 Claude 用量，可以不架 Cloudflare。

## 快速開始

需要 macOS 和 Python 3.9 以上。看範例畫面不需要燈、token 或 Cloudflare 帳號：

```sh
git clone https://github.com/kelvin-sl/divoom-times-gate-dashboard
cd divoom-times-gate-dashboard
python3 -m venv .venv
.venv/bin/python -m pip install pillow
.venv/bin/python -m unittest discover tests
.venv/bin/python dash.py --demo          # → out/preview.png
open out/preview.png
```

接著照[安裝設定](docs/setup.zh-TW.md)推到燈上、用 launchd 排程，需要的話再架收集器。

**也可以交給 AI 助理裝。** 在 Claude Code、Codex 或其他能操作終端機的助理貼上：

```text
請協助我在 Mac 上安裝這個 Divoom Times Gate 儀表板：
https://github.com/kelvin-sl/divoom-times-gate-dashboard

先把 repo clone 到本機的專案資料夾，讀 README.zh-TW.md、SKILL.md 和 docs/。
先建立 Python 虛擬環境、安裝 Pillow、跑測試，讓我看範例預覽；這一步不需要燈或 Cloudflare 帳號。
接著帶我設定燈，缺的設定問我。token 讓我在本機自己輸入，保留既有的設定。
只有我選擇使用時，才設定選配的 Cloudflare 收集器。每完成一步都要驗證，
最後告訴我哪些還沒測過。
```

[SKILL.md](SKILL.md) 是給助理照著做的安裝指南。

## 文件

| 指南 | 內容 |
| :--- | :--- |
| [安裝設定](docs/setup.zh-TW.md) | 需要什麼、推到燈上、launchd、架 Cloudflare 收集器 |
| [設定檔](docs/configuration.zh-TW.md) | 帳號、網站流量與 SEO 怎麼接、格子種類、輪播候選池、佈景主題 |
| [Times Gate 區網 API](docs/times-gate-api.zh-TW.md) | 這個專案用到的兩個指令，以及 `PicID` 的規則 |
| [疑難排解](docs/troubleshooting.zh-TW.md) | launchd 與本地網路權限、網段、免費額度、爬公開頁的風險 |

## 範圍與限制

- **目前只支援 macOS。** 畫圖用 macOS 系統字型，排程用 launchd。
- **分析數據要自備端點。** 這個 repo 沒有內建 GA4 或 Search Console 的連接器。
- **讀公開頁，不是官方 API。** 平台改版可能讓抓取失敗，平台條款也可能限制自動存取。只用在自己的帳號；詳見[疑難排解](docs/troubleshooting.zh-TW.md#爬公開頁的風險)。

背景說明文章：[把 Divoom Times Gate 變成網站成績看板](https://kelvinwang.info/zh-hant/blog/divoom-times-gate-dashboard/?utm_source=github&utm_medium=readme&utm_campaign=divoom-times-gate-dashboard)
（[English](https://kelvinwang.info/en/blog/divoom-times-gate-dashboard/?utm_source=github&utm_medium=readme&utm_campaign=divoom-times-gate-dashboard)）。

## 驗證與貢獻

```sh
.venv/bin/python -m unittest discover tests      # 畫圖、輪播、沒資料／資料壞掉
(cd worker && npm ci && npm test)                # 收集器解析
```

| 項目 | 怎麼驗 | 結果（2026-11-19） |
| :--- | :----- | :----------------- |
| 畫圖 | 9 個 Python 測試，包含 `latest.json` 壞掉時仍畫出五格點線框 | 通過 |
| 輪播 | 不會連續兩輪同一對；沒到時間不重抽 | 通過 |
| 收集器解析 | 6 個 Node 測試：K/M 單位、登入牆、失敗沿用舊資料 | 通過 |
| YouTube 實際讀取 | 用 `sources.youtube` 讀 YouTube 官方頻道 | 取得訂閱、觀看、影片數 |
| Threads／X 實際讀取 | 本機 Chrome 開公開頁，用同一份 `parse.js` 解析 | 取得粉絲數 |
| Worker 打包 | `npx wrangler deploy --dry-run` | 成功（137 KB gzip） |
| 推到燈上 | 對實機跑 `./lamp.sh show x threads` | 五格都回 `error_code: 0` |

歡迎開 [Issue](https://github.com/kelvin-sl/divoom-times-gate-dashboard/issues) 或送小修正。
請附上 macOS 版本、Python 版本和指令輸出；行為有變動請補測試。覺得有用的話，給個 GitHub star 能讓更多人找到它。

## 安全

- 燈和收集器的 token 放在 `~/.config/times-gate-dashboard/env`（權限 600）和 Worker secrets，不進 repo。
- 收集器的每個端點都要 Bearer token。燈只透過你的區網連線。
- Claude Code 的紀錄只在本機讀取；離開 Mac 的只有畫好的圖，而且只送到燈上。

## 授權

[MIT](LICENSE)。平台 logo 取自 [Simple Icons](https://simpleicons.org/) 16.36.0（CC0）。
Divoom、Times Gate、YouTube、Threads、X、Claude 皆為各自公司的商標，本專案與它們無關。
