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
*   **Webhook 自動化**: 透過 Trello Webhook 實現新卡片建立時自動觸發驗證流程。

---

## 2. 架構設計

### 2.1 核心模組
*   **`app.py` (Flask)**: 處理 HTTP 請求，提供 Web 介面與 API 端點、Webhook 接收器。
*   **`lia_bot.py` (Playwright + ddddocr)**: 核心爬蟲邏輯，負責瀏覽器操作、驗證碼識別、結果解析、Email 範本生成。
*   **`trello_utils.py` (Trello API)**: 處理 Trello 卡片資訊讀取、截圖上傳與留言。
*   **`register_webhook.py`**: 一次性執行腳本，用於向 Trello 註冊 Webhook。

### 2.2 資料流 (Web UI 觸發)
1.  **User** -> **Web UI**: 輸入證號或 Trello 網址。
2.  **Web UI** -> **API (`/check`)**: 發送非同步請求 (AJAX)。
3.  **API** -> **`trello_utils`**: (若是 Trello 網址) 解析卡片取得證號、聯絡信箱。
4.  **API** -> **`lia_bot`**: 啟動瀏覽器查詢，回傳結果 (截圖 bytes + 狀態 + Email 範本)。
5.  **API** -> **`trello_utils`**: (若是 Trello 網址) 將截圖上傳回 Trello 卡片，並留言結果摘要。
6.  **API** -> **`trello_utils`**: (若是 Trello 網址) 將包含聯絡信箱和 Email 範本的內容作為**獨立留言**回傳至 Trello 卡片。
7.  **Web UI**: 回傳 JSON (Base64 圖片 + Email 範本)。
8.  **Web UI**: 渲染結果。

### 2.3 資料流 (Webhook 自動觸發)
1.  **Trello User** -> **Trello Board**: 建立新卡片 (標題包含觸發關鍵字)。
2.  **Trello** -> **Webhook (`/webhook/trello`)**: Trello 自動發送 POST 請求到 Render 服務。
3.  **Render (`app.py`)**: 接收 Webhook 請求，立即回傳 `200 OK`，並在**背景執行緒**中啟動 `process_trello_card`。
4.  **`process_trello_card` (背景任務)**:
    *   從 Webhook 數據中獲取 `card_id` 和 `card_url`。
    *   呼叫 `trello_utils` 解析卡片描述，取得證號、聯絡信箱。
    *   呼叫 `lia_bot` 執行查詢。
    *   呼叫 `trello_utils` 上傳截圖、留言結果摘要和 Email 範本到 Trello 卡片。

---

## 3. 環境變數與敏感資料

### 3.1 本地開發 (`.env`)
使用 `python-dotenv` 套件讀取 `.env` 檔案，避免將 Key 硬編碼在程式中。
**.gitignore 務必加入 `.env`**。

```bash
# .env 範例
TRELLO_API_KEY=your_key
TRELLO_TOKEN=your_token
TRELLO_BOARD_ID=your_board_id
TRIGGER_KEYWORD=年繳方案申請
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

# 複製 requirements.txt 並安裝 Python 套件
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

<h2>5. 關鍵技術實作細節</h2>

<h3>5.1 <code>lia_bot.py</code> 核心邏輯</h3>
<ul>
    <li>將 Playwright + ddddocr 查詢壽險公會網站的核心邏輯封裝在 <code>LIAQueryBot</code> 類別中。</li>
    <li>實作了: 瀏覽器啟動、導航、驗證碼識別與填寫、表單提交、Alert 處理、驗證碼錯誤重試、結果頁面解析 (初次登錄日期)、日期判斷 (一年內)。</li>
    <li>將截圖功能修改為<strong>記憶體內截圖</strong> (<code>page.screenshot()</code> 不指定 <code>path</code>，只截取頁面上方 60%)，回傳原始 <code>bytes</code>，避免伺服器寫入磁碟。</li>
    <li>新增 <code>_generate_email_template</code> 方法，根據查詢結果狀態動態生成回信 Email 的標題與內文。</li>
    <li>截圖檔名優化:
        <ul>
            <li>「審核成功」改為「審核通過」</li>
            <li>「審核失敗」改為「資格不符」</li>
            <li>「查詢異常」改為「無效證號」</li>
        </ul>
    </li>
</ul>

<h3>5.2 <code>trello_utils.py</code> 中的 Trello 整合優化</h3>
<ul>
    <li>新增 <code>extract_email_from_text</code> 函式，用於從 Trello 卡片描述中精確提取「聯絡信箱」。
        <ul>
            <li>特別處理了 Trello Markdown 中可能存在的反斜線 <code>\</code> 轉義字元，確保 Email 能被完整抓取。</li>
        </ul>
    </li>
    <li>更新 <code>resolve_trello_input</code> 函式，使其除了回傳證號和卡片 ID 外，也回傳提取到的聯絡信箱。</li>
    <li><code>upload_result_to_trello</code> 函式:
        <ul>
            <li>負責上傳截圖附件。</li>
            <li>留言驗證結果摘要 (例如：「查詢完成：0113403577_審核通過_114_05_13」)。</li>
        </ul>
    </li>
    <li>新增 <code>post_email_template_to_trello</code> 函式:
        <ul>
            <li>負責將格式化後的 Email 標題與內文 (包含聯絡信箱，若有提取到) 作為**獨立的留言**發布到 Trello 卡片。</li>
            <li>調整排版，確保「Finfo 客服團隊 敬上」不會被誤判為標題而放大。</li>
            <li>移除了分隔線，並在「建議回信範本：」下方多空一行，提升可讀性。</li>
        </ul>
    </li>
</ul>

<h3>5.3 <code>app.py</code> 中的 API 端點</h3>
<ul>
    <li>引入 <code>lia_bot</code> 和 <code>trello_utils</code>。</li>
    <li>**更新 <code>/check</code> 路由**: 接收 <code>id</code> (登錄字號或 Trello 網址) 參數。
        <ol>
            <li>透過 <code>trello_utils.resolve_trello_input()</code> 解析輸入，如果是 Trello 網址則提取證號、卡片 ID 和**聯絡信箱**。</li>
            <li>呼叫 <code>LIAQueryBot</code> 執行查詢。</li>
            <li>取得 <code>LIAQueryBot</code> 回傳的結果字典，其中包含 <code>screenshot_bytes</code>、<code>suggested_filename</code> 和 <code>email_info</code>。</li>
            <li>將 <code>screenshot_bytes</code> 轉為 Base64 字串。</li>
            <li>若有 Trello 卡片 ID，呼叫 <code>trello_utils.upload_result_to_trello()</code> 將結果上傳，並**依序呼叫 <code>trello_utils.post_email_template_to_trello()</code> 留言 Email 範本 (含聯絡信箱)**。</li>
            <li>最終回傳 JSON 格式的結果，包含 Base64 圖片、檔名、Email 範本和原始 Trello 連結 (若有)。</li>
        </ol>
    </li>
    <li>**新增 <code>/webhook/trello</code> 路由**:
        <ul>
            <li>接收 Trello 的 Webhook 請求。</li>
            <li>處理 Trello 註冊 Webhook 時發送的 <code>HEAD</code> 請求。</li>
            <li>過濾事件類型 (僅處理 <code>createCard</code>) 和卡片標題關鍵字 (<code>TRIGGER_KEYWORD</code>)。</li>
            <li>符合條件時，將實際的驗證邏輯放入**背景執行緒** (<code>threading</code>) 處理，並立即回傳 `200 OK` 給 Trello，避免 Webhook 超時。</li>
        </ul>
    </li>
    <li>**更新 <code>/</code> 首頁路由**: 提供包含輸入框、按鈕、Loading 動畫、結果顯示區的互動式 Web UI。
        <ul>
            <li>介面中提供測試範例。</li>
            <li>若為 Trello 網址輸入，顯示「已將驗證結果回覆在票上」的提示文字及「回到 Trello 票」按鈕。</li>
        </ul>
    </li>
</ul>

<h3>5.4 <code>register_webhook.py</code></h3>
<ul>
    <li>一次性執行腳本，用於向 Trello API 註冊 Webhook。</li>
    <li>監聽指定的 <code>TRELLO_BOARD_ID</code>。</li>
    <li>指定 Render 服務的 <code>/webhook/trello</code> 路由作為回呼網址 (<code>callbackURL</code>)。</li>
</ul>

---

<h2>6. 核心概念解析</h2>

<h3>6.1 Webhook 機制 (Trello 自動化)</h3>
<ul>
    <li>**概念**: Trello 在事件發生時主動「推播」通知到指定 URL，而非程式週期性「輪詢」。</li>
    <li>**優點**: 即時性高、資源消耗低。</li>
    <li>**挑戰**: Trello 要求 Webhook 接收端在 10 秒內回覆 `200 OK`。</li>
    <li>**解決方案**: 在 Flask 接收到 Webhook 後，立即啟動一個**背景執行緒 (<code>threading</code>)** 來處理耗時的爬蟲任務，主執行緒則立即回覆 `200 OK`。</li>
</ul>

<h3>6.2 截圖是怎麼回傳的？ (Memory Stream)</h3>
在 <code>app.py</code> 中：
<pre><code class="language-python"># 1. 截圖不存檔，直接回傳二進位數據 (bytes)
screenshot_bytes = page.screenshot()

# 2. 使用 BytesIO 在記憶體中建立虛擬檔案
# 3. 使用 send_file 將數據串流 (Stream) 回傳給瀏覽器
return send_file(io.BytesIO(screenshot_bytes), mimetype='image/png')
</code></pre>
<ul>
    <li><strong>優點</strong>: 不佔用伺服器硬碟空間 (Disk I/O)，速度快，適合動態生成內容。</li>
</ul>

<h3>6.3 Docker 的優勢</h3>
<ul>
    <li><strong>一致性</strong>: "Build once, run anywhere"。在本機 Docker 能跑，推上雲端就能跑。</li>
    <li><strong>完整控制</strong>: 不受雲端供應商預設環境 (如 Python 版本、系統函式庫) 的限制。</li>
</ul>

---

<h2>7. 常用指令</h2>

<ul>
    <li><strong>啟動虛擬環境</strong>: <code>.\venv\Scripts\Activate.ps1</code></li>
    <li><strong>安裝依賴</strong>: <code>pip install -r requirements.txt</code></li>
    <li><strong>啟動 App (本地)</strong>: <code>python app.py</code></li>
    <li><strong>註冊 Trello Webhook (一次性)</strong>: <code>python register_webhook.py</code> (需 Render 服務已上線)</li>
    <li><strong>Git 提交</strong>: <code>git add .</code> -> <code>git commit -m "..."</code> -> <code>git push</code></li>
    <li><strong>Git 敏感資料清理 (本地歷史)</strong>: <code>git reset --mixed origin/master</code> (謹慎使用，會覆蓋本地未追蹤的 commit 歷史)</li>
</ul>
