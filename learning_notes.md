# Render 佈署與 Playwright 整合實戰筆記

**日期**: 2025年11月27日  
**環境**: Windows 10, Python 3, Flask, Docker, Render

---

## 1. 專案目標
建立一個 Python Flask 網頁應用程式，佈署至 Render 免費伺服器，並實現以下功能：
*   **自動化查詢**: 整合 Playwright + ddddocr 自動查詢壽險公會業務員登錄資料。
*   **Trello 整合**: 支援解析 Trello 卡片網址，並自動將查詢結果回傳至卡片。
*   **使用者介面 (UI)**: 提供友善的網頁介面，顯示查詢進度、結果截圖及 Email 回信範本。
*   **安全性**: 妥善管理 API Key 等敏感資訊。
*   **容器化**: 使用 Docker 進行標準化佈署。

---

## 2. 架構設計

### 2.1 核心模組
*   **`app.py` (Flask)**: 處理 HTTP 請求，提供 Web 介面與 API 端點。
*   **`lia_bot.py` (Playwright + ddddocr)**: 核心爬蟲邏輯，負責瀏覽器操作、驗證碼識別、結果解析。
*   **`trello_utils.py` (Trello API)**: 處理 Trello 卡片資訊讀取、截圖上傳與留言。

### 2.2 資料流
1.  **User** -> **Web UI**: 輸入證號或 Trello 網址。
2.  **Web UI** -> **API (`/check`)**: 發送非同步請求 (AJAX)。
3.  **API** -> **`trello_utils`**: (若是 Trello 網址) 解析卡片取得證號。
4.  **API** -> **`lia_bot`**: 啟動瀏覽器查詢，回傳結果 (截圖 bytes + 狀態)。
5.  **API** -> **`trello_utils`**: (若是 Trello 網址) 將截圖上傳回 Trello 卡片。
6.  **API** -> **Web UI**: 回傳 JSON (Base64 圖片 + Email 範本)。
7.  **Web UI**: 渲染結果。

---

## 3. 環境變數與敏感資料

### 3.1 本地開發 (`.env`)
使用 `python-dotenv` 套件讀取 `.env` 檔案，避免將 Key 硬編碼在程式中。
**.gitignore 務必加入 `.env`**。

```bash
# .env 範例
TRELLO_API_KEY=your_key
TRELLO_TOKEN=your_token
```

### 3.2 雲端佈署 (Render)
在 Render Dashboard 的 **Environment** 設定頁面填入變數。

---

## 4. Docker 容器化策略

為了支援 Playwright 與 ddddocr (OpenCV 依賴)，我們使用自訂 Dockerfile。

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# 安裝 ddddocr 所需系統依賴 (OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 確保 Chromium 安裝到位
RUN playwright install chromium

COPY . .

# 設定環境變數優化 Python 執行
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]
```

---

## 5. 關鍵技術實作細節

### 5.1 記憶體內截圖 (In-Memory Screenshot)
為了適應 Serverless 環境 (無持久儲存)，我們不將截圖存檔，而是直接操作二進位數據。

```python
# lia_bot.py
# 截取 60% 高度 (優化圖片大小)
page_height = self.page.evaluate("document.body.scrollHeight")
screenshot_bytes = self.page.screenshot(
    clip={"x": 0, "y": 0, "width": self.page.viewport_size['width'], "height": page_height * 0.6}
)
# 回傳 bytes 給 API
```

### 5.2 前後端互動 (JSON + Base64)
API 不直接回傳圖片檔案，而是回傳 JSON，讓前端能同時收到圖片和文字資訊。

```python
# app.py
img_base64 = base64.b64encode(result['screenshot_bytes']).decode('utf-8')
return jsonify({
    "success": True,
    "image": f"data:image/png;base64,{img_base64}",
    "filename": filename,
    "email": email_template
})
```

### 5.3 驗證碼重試機制
使用 `dialog` 事件監聽器處理「驗證碼錯誤」彈窗，並自動刷新重試。

```python
# lia_bot.py
def handle_dialog(dialog):
    if "驗證碼錯誤" in dialog.message:
        should_retry = True
    dialog.accept()

self.page.once("dialog", handle_dialog)
```

---

## 6. Git 操作與故障排除

*   **Git Push Rejected (Secret Scanning)**:
    *   若不小心 commit 了敏感資料，GitHub 會擋下 push。
    *   **解法**: 使用 `git reset --mixed origin/master` 重置本地歷史，修改檔案 (移除 Key)，再重新 commit。
*   **Render 佈署**:
    *   每次 `git push` 會自動觸發。
    *   若需除錯，查看 Render Dashboard 的 Logs。

---

## 7. 常用指令

*   **啟動虛擬環境**: `.\venv\Scripts\Activate.ps1`
*   **安裝依賴**: `pip install -r requirements.txt`
*   **啟動 App**: `python app.py`
*   **Git 提交**: `git add .` -> `git commit -m "..."` -> `git push`