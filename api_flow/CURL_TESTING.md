# Finfo 正式環境 curl 測試指令

> 端點：`https://agent-verify.finfo.tw/api/verify-agent-license`

---

## 1. 審核通過 — 新人 (status_code: 0)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0113403577\"}"
```

## 2. 資格不符 — 超過一年 (status_code: 1)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0102204809\"}"
```

## 3. 查無此證號 (status_code: 3)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"01134035\"}"
```

## 4. 未辦理登錄 (status_code: 1)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0104300989\"}"
```

## 5. 格式無效 — 含英文字母 (status_code: 2)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"A123456789\"}"
```

## 6. 缺少 license_number — 空 JSON (status_code: 2)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{}"
```

## 7. 非 JSON body (HTTP 400, status_code: 2)

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: text/plain" -d "not json"
```

---

## 預期結果對照表

| # | license_number | HTTP Status | status_code | 意義 |
|---|----------------|-------------|-------------|------|
| 1 | `0113403577` | 200 | 0 | 審核通過（新人） |
| 2 | `0102204809` | 200 | 1 | 資格不符（超過一年） |
| 3 | `01134035` | 200 | 3 | 查無此證號 |
| 4 | `0104300989` | 200 | 1 | 未辦理登錄 |
| 5 | `A123456789` | 200 | 2 | 格式無效 |
| 6 | `{}`（空 JSON） | 200 | 2 | 缺少 license_number |
| 7 | 非 JSON body | 400 | 2 | 無法解析 JSON |

> 注意：測試 #3 依賴壽險公會外部服務，若該服務維護中會回傳 `status_code: 999`。
