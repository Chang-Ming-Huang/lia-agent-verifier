# Render 佈署與 Playwright 整合實戰筆記

**日期**: 2025年11月27日  
**環境**: Windows 10, Python 3, Flask, Docker, Render

---

## 1. 專案目標
建立一個 Python Flask 網頁應用程式，佈署至 Render 免費伺服器，並實現以下功能：
*   基礎網頁顯示 (Hello World)。
*   讀取環境變數並動態顯示內容。
*   遮罩敏感資訊 (如 API Key)。
*   整合 Playwright 進行網頁截圖並即時回傳。

---

## 2. 基礎佈署流程 (Flask + Render)

### 2.1 本機環境設定
1.  **建立虛擬環境**: 確保專案依賴隔離。
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
2.  **安裝套件**:
    ```powershell
    pip install flask gunicorn
    ```
3.  **產生 `requirements.txt`**:
    ```powershell
    pip freeze > requirements.txt
    ```
    *(注意：Render 需要此檔案來安裝依賴，且必須包含 `gunicorn` 作為 WSGI 伺服器)*
4.  **建立 `app.py`**: 撰寫 Flask 程式。
5.  **設定 `.gitignore`**: 排除 `venv/`, `__pycache__/` 等檔案。

### 2.2 推送至 GitHub
1.  初始化 Git: `git init`, `git add .`, `git commit -m "..."`
2.  使用 GitHub CLI 建立並推送:
    ```powershell
    gh repo create render-test --public --source=. --push
    ```

### 2.3 Render 佈署設定 (Native Python)
*   **Type**: Web Service
*   **Runtime**: Python 3
*   **Build Command**: `pip install -r requirements.txt`
*   **Start Command**: `gunicorn app:app`

---

## 3. 環境變數 (Environment Variables)

### 3.1 為什麼使用？
*   **安全性**: 避免將 API Key、密碼直接寫在程式碼中並上傳至 GitHub。
*   **靈活性**: 允許不同環境 (開發/測試/生產) 使用不同設定。

### 3.2 Python 實作
```python
import os
# 讀取變數，若不存在則使用預設值
secret = os.environ.get('MY_SECRET', 'DefaultValue')
```

### 3.3 Render 設定
在 Dashboard -> Environment -> Add Environment Variable 設定 Key-Value。

---

## 4. 進階：Playwright 截圖與 Docker 佈署

### 4.1 遇到的挑戰
*   **問題**: 在 Render 原生 Python 環境中，Playwright 無法安裝瀏覽器依賴 (`playwright install-deps` 需要 root 權限，且基礎環境缺漏函式庫)。
*   **解決方案**: 使用 **Docker** 自定義執行環境。

### 4.2 Dockerfile 實作
建立 `Dockerfile`，基於官方 Playwright 映像檔打包應用：

```dockerfile
# 使用官方 Playwright 映像檔 (包含 Python + 瀏覽器 + 系統依賴)
# 選擇穩定的版本標籤
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Chromium 瀏覽器
RUN playwright install chromium

# 複製程式碼
COPY . .

# 啟動 Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]
```

### 4.3 Render Docker 佈署設定
*   **Runtime**: 切換為 **Docker** (Render 會自動偵測 Dockerfile)。
*   **結果**: 成功建置並運行，解決了權限與依賴問題。

---

## 5. 核心概念解析

### 5.1 截圖是怎麼回傳的？ (Memory Stream)
在 `app.py` 中：
```python
# 1. 截圖不存檔，直接回傳二進位數據 (bytes)
screenshot_bytes = page.screenshot()

# 2. 使用 BytesIO 在記憶體中建立虛擬檔案
# 3. 使用 send_file 將數據串流 (Stream) 回傳給瀏覽器
return send_file(io.BytesIO(screenshot_bytes), mimetype='image/png')
```
*   **優點**: 不佔用伺服器硬碟空間 (Disk I/O)，速度快，適合動態生成內容。

### 5.2 Docker 的優勢
*   **一致性**: "Build once, run anywhere"。在本機 Docker 能跑，推上雲端就能跑。
*   **完整控制**: 不受雲端供應商預設環境 (如 Python 版本、系統函式庫) 的限制。

---

## 6. 常用指令備忘

*   **啟動虛擬環境**: `.\venv\Scripts\Activate.ps1`
*   **本機執行 Flask**: `python app.py`
*   **GitHub 推送**: `git add .`, `git commit -m "msg"`, `git push`
