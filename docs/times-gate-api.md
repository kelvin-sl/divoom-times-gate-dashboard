# Times Gate local API

**English** · [繁體中文](times-gate-api.zh-TW.md) · [← Back to README](../README.md)

Divoom has not published full documentation for the Times Gate. This is the part this project uses and has tested:

```sh
curl -X POST http://<lamp-ip>/post -d '{"Command":"Draw/GetHttpGifId","LocalToken":123456}'
# → {"error_code":0,"PicId":57}
```

`Draw/SendHttpGif` sends one image to the screens you pick:

| Parameter | Value |
|---|---|
| `LcdArray` | `[0,0,1,0,0]` targets screen 3; send one screen at a time |
| `PicNum` / `PicOffset` | `1` / `0` for a single image |
| `PicWidth` | `128` |
| `PicID` | Must be **greater than** the `PicId` returned by `GetHttpGifId`, or the lamp keeps the old image |
| `PicSpeed` | Milliseconds per animation frame; any value works for a single image |
| `PicData` | Base64 JPEG, 128×128 |
