# Times Gate 區網 API

[English](times-gate-api.md) · **繁體中文** · [← 回到 README](../README.zh-TW.md)

Divoom 沒有公開 Times Gate 的完整文件。以下是這個專案實際用到、測過的部分：

```sh
curl -X POST http://燈的IP/post -d '{"Command":"Draw/GetHttpGifId","LocalToken":123456}'
# → {"error_code":0,"PicId":57}
```

`Draw/SendHttpGif` 推一張圖到指定螢幕：

| 參數 | 值 |
|---|---|
| `LcdArray` | `[0,0,1,0,0]` 表示第 3 格，一次推一格 |
| `PicNum` / `PicOffset` | 單張圖填 `1` / `0` |
| `PicWidth` | `128` |
| `PicID` | 必須**大於** `GetHttpGifId` 回的 `PicId`，否則燈不換圖 |
| `PicSpeed` | 動畫每幀毫秒數，單張隨意 |
| `PicData` | base64 的 JPEG（128×128） |
