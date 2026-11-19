# 疑難排解

[English](troubleshooting.md) · **繁體中文** · [← 回到 README](../README.zh-TW.md)

## 坑

- **launchd 跑的 Python 連不到燈**（`No route to host`）。macOS 的「本地網路」隱私權會擋 launchd 啟動的 Python，系統內建的 `/usr/bin/curl` 不受影響。所以 `dash.py` 推圖時呼叫 curl，不用 Python 的 HTTP。
- **電腦和燈不在同一網段**：Wi‑Fi 和有線網路常常由不同的路由器發 IP，例如數據機和 mesh 路由器各發一段。燈和電腦要拿同一台發的 IP。
- **Cloudflare Browser Run 免費方案一天 10 分鐘**，超過會回 429，直到隔天（UTC）。讀幾個 Threads／X 帳號一輪約 25 秒，所以只在每兩小時（UTC 偶數點）第一次 cron 時讀，其他輪次沿用上一份數字。帳號多或要更即時，改 `parse.js` 的 `browserDue`，或升級付費方案。
- **Threads 和 X 的頁面永遠不會 network idle**：要等頁面出現 `followers` 字樣，不能等網路靜止。
- **手動 `/collect` 會被提早切斷**。在 `waitUntil` 裡跑的手動觸發大約 30 秒就會被中斷，cron 觸發的時間比較長。要看完整一輪，就等下一次 cron。
- **Threads 的 recent views 只有登入才看得到**。公開頁只有粉絲數，這個專案不使用登入狀態。
- **某個來源失敗時**，沿用上一份數字，並標上 `stale_since`。燈不會變空白。

## 爬公開頁的風險

YouTube、Threads、X 的數字是讀公開頁面，沒有走官方 API。平台改版可能讓抓取失敗；條款也可能限制自動存取。請自己判斷，只用在你自己的帳號。請求之間間隔 1.5–4.5 秒亂數，每兩小時才讀一次瀏覽器來源。想走正式管道，可以改用 YouTube Data API 或 Threads API，再透過 `json` 來源接進來。
