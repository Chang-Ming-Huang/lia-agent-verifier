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
*   **整合 ddddocr 進行驗證碼識別。**
*   **將以上所有功能容器化 (Docker) 佈署。**

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
# 使用官方 Playwright 映像檔 (包含 Python 環境與瀏覽器依賴)
# 選擇穩定的版本標籤
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# 安裝 ddddocr 所需的額外系統依賴 (例如 libgl1-mesa-glx for OpenCV)
# Playwright 映像檔是基於 Ubuntu (jammy)，所以使用 apt-get
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Chromium 瀏覽器 (雖然基礎映像檔已有，此步確保安裝到位)
RUN playwright install chromium

# 複製所有程式碼到工作目錄
COPY . .

# 設定環境變數 (防止 Python 產生 .pyc 檔，並確保輸出不緩衝)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 啟動 Gunicorn 伺服器
# Render 會自動提供 PORT 環境變數，我們讓 Gunicorn 監聽該 Port
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]
```

### 4.3 `.dockerignore`
建立 `.dockerignore` 排除不需要打包到 Docker 映像檔的檔案 (如 `venv/`, `.git/`)。

### 4.4 Render Docker 佈署設定
*   **Runtime**: 切換為 **Docker** (Render 會自動偵測 Dockerfile)。
*   **結果**: 成功建置並運行，解決了權限與依賴問題。

---

## 5. ddddocr (OCR) 整合

### 5.1 本機安裝
```powershell
pip install ddddocr requests
```
*(注意：`requests` 庫用於下載圖片或與 API 互動)*

### 5.2 `app.py` 中的整合
*   匯入 `ddddocr` 和 `requests`。
*   初始化 `ocr = ddddocr.DdddOcr()` (建議作為全域變數，避免重複載入模型)。
*   **`/ocr` 路由邏輯**:
    1.  Playwright 前往目標網頁 (例如：`https://public.liaroc.org.tw/lia-public/...`)。
    2.  利用 CSS Selector (例如 `img#captcha`) 定位驗證碼圖片元素。
    3.  `captcha_element.screenshot()` 直接截取該元素。
    4.  將截圖的位元組數據傳給 `ocr.classification(captcha_bytes)` 進行識別。
    5.  將結果和圖片預覽回傳至網頁。

---

## 6. 核心概念解析

### 6.1 截圖是怎麼回傳的？ (Memory Stream)
在 `app.py` 中：
```python
# 1. 截圖不存檔，直接回傳二進位數據 (bytes)
screenshot_bytes = page.screenshot()

# 2. 使用 BytesIO 在記憶體中建立虛擬檔案
# 3. 使用 send_file 將數據串流 (Stream) 回傳給瀏覽器
return send_file(io.BytesIO(screenshot_bytes), mimetype='image/png')
```
*   **優點**: 不佔用伺服器硬碟空間 (Disk I/O)，速度快，適合動態生成內容。

### 6.2 Docker 的優勢
*   **一致性**: "Build once, run anywhere"。在本機 Docker 能跑，推上雲端就能跑。
*   **完整控制**: 不受雲端供應商預設環境 (如 Python 版本、系統函式庫) 的限制。

---

## 7. 常用指令備忘

*   **啟動虛擬環境**: `.\venv\Scripts\Activate.ps1`
*   **本機執行 Flask**: `python app.py`
*   **GitHub 推送**: `git add .`, `git commit -m "msg"`, `git push`