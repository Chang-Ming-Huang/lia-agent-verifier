# verify-agent-license API 測試指南

> 此 API 端點定義於 `api_flow/routes.py`，透過 Flask Blueprint 註冊到主應用程式。

## 1. 啟動本地 Server

```bash
python app.py
```

看到以下訊息代表啟動成功：

```
 * Running on http://127.0.0.1:5000
```

停止 server：按 `Ctrl+C`

---

## 2. 本地測試

### 方法 A：使用測試腳本

```bash
python test_verify_api.py --local
```

會自動跑 6 個測試案例並印出 PASS/FAIL 結果。

### 方法 B：使用 curl 手動測試

審核通過（新人）：
```bash
curl -X POST http://localhost:5000/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0113403577\"}"
```

資格不符（超過一年）：
```bash
curl -X POST http://localhost:5000/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0102204809\"}"
```

查無此證號：
```bash
curl -X POST http://localhost:5000/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"01134035\"}"
```

格式無效（含英文字母）：
```bash
curl -X POST http://localhost:5000/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"A123456789\"}"
```

---

## 3. 線上 Render 測試（測試環境）

### 方法 A：使用測試腳本

```bash
python test_verify_api.py
```

注意：Render 免費版有冷啟動問題，首次請求可能需等 1-2 分鐘，腳本已設定 180 秒 timeout。

### 方法 B：使用 curl

```bash
curl -X POST https://lia-agent-verifier.onrender.com/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0113403577\"}"
```

---

## 4. Finfo Production 測試（正式環境）

### 方法 A：使用測試腳本

```bash
python test_verify_api.py --production
```

### 方法 B：使用 curl

```bash
curl -X POST https://agent-verify.finfo.tw/api/verify-agent-license -H "Content-Type: application/json" -d "{\"license_number\": \"0113403577\"}"
```

---

## 5. 測試案例與預期結果

| # | license_number | HTTP Status | status_code | 意義 |
|---|----------------|-------------|-------------|------|
| 1 | `0113403577` | 200 | 0 | 審核通過（新人） |
| 2 | `0102204809` | 200 | 1 | 資格不符（超過一年） |
| 3 | `01134035` | 200 | 3 | 查無此證號 |
| 4 | `A123456789` | 200 | 2 | 格式無效 |
| 5 | `{}`（空 JSON） | 200 | 2 | 缺少 license_number |
| 6 | 非 JSON body | 400 | 2 | 無法解析 JSON |

注意：test #3 依賴壽險公會外部服務，若該服務維護中會回傳 `status_code: 999`。
