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
*   **將 Playwright + ddddocr 自動化查詢流程容器化 (Docker) 佈署。**

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

<h2>3. 環境變數 (Environment Variables) 與敏感資料處理</h2>

<h3>3.1 為什麼使用？</h3>
<ul>
    <li><strong>安全性</strong>: 避免將 API Key、密碼直接寫在程式碼中並上傳至 GitHub。</li>
    <li><strong>靈活性</strong>: 允許不同環境 (開發/測試/生產) 使用不同設定。</li>
</ul>

<h3>3.2 Python 實作</h3>
<pre><code class="language-python">import os
# 讀取變數，若不存在則使用預設值
secret = os.environ.get('MY_SECRET', 'DefaultValue')
</code></pre>

<h3>3.3 Render 設定</h3>
在 Dashboard -> Environment -> Add Environment Variable 設定 Key-Value。

<h3>3.4 Git 敏感資料處理</h3>
<ul>
    <li><strong>問題</strong>: 不小心將包含敏感憑證的檔案提交到 Git 歷史紀錄。</li>
    <li><strong>最佳實踐</strong>:
        <ol>
            <li><strong>憑證撤銷 (Revoke)</strong>: 立即前往服務提供商 (如 Trello, Atlassian) 撤銷洩露的憑證，並生成新憑證。</li>
            <li><strong>程式碼移除</strong>: 將敏感資訊從檔案中移除，改用環境變數讀取。</li>
            <li><strong>Git 歷史清理</strong>:
                <ul>
                    <li>如果尚未推送到遠端: 使用 <code>git reset --mixed HEAD~1</code> 或 <code>git reset --hard &lt;commit_hash&gt;</code> 清理本地歷史。</li>
                    <li>如果已推送到遠端: 需要使用 <code>git push --force</code> 強制推送清理後的歷史，但這會改寫公共歷史，需謹慎。</li>
                </ul>
            </li>
        </ol>
    </li>
    <li><strong>本次解決方案</strong>:
        <ul>
            <li>將 <code>lia_query_automation.py</code> (參考檔案) 中的硬編碼憑證替換為從環境變數讀取。</li>
            <li>使用 <code>git reset --mixed origin/master</code> 將本地工作區與遠端同步 (保留本地檔案變更)，然後重新提交乾淨的程式碼並推送。</li>
        </ul>
    </li>
</ul>

---

<h2>4. 進階：Playwright + ddddocr 自動化與 Docker 容器化佈署</h2>

<h3>4.1 遇到的挑戰</h3>
<ul>
    <li>在 Render 原生 Python 環境中，Playwright 無法安裝瀏覽器依賴 (<code>playwright install-deps</code> 需要 root 權限，且基礎環境缺漏函式庫)。</li>
    <li><code>ddddocr</code> 也可能依賴特定的系統函式庫 (如 <code>libgl1-mesa-glx</code> for OpenCV)。</li>
    <li><strong>解決方案</strong>: 使用 <strong>Docker</strong> 自定義執行環境，提供完整的依賴。</li>
</ul>

<h3>4.2 Dockerfile 實作</h3>
建立 <code>Dockerfile</code>，基於官方 Playwright 映像檔打包應用：

<pre><code class="language-dockerfile"># 使用官方 Playwright 映像檔 (包含 Python 環境與瀏覽器依賴)
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
</code></pre>

<h3>4.3 <code>.dockerignore</code></h3>
建立 <code>.dockerignore</code> 排除不需要打包到 Docker 映像檔的檔案 (如 <code>venv/</code>, <code>.git/</code>, <code>lia_query_automation.py</code>)。

<h3>4.4 Render Docker 佈署設定</h3>
<ul>
    <li><strong>Runtime</strong>: 切換為 <strong>Docker</strong> (Render 會自動偵測 Dockerfile)。</li>
    <li><strong>結果</strong>: 成功建置並運行，解決了權限與依賴問題。</li>
</ul>

---

<h2>5. 核心自動化流程整合 (LIAQueryBot API 化)</h2>

<h3>5.1 <code>lia_bot.py</code> 核心邏輯</h3>
<ul>
    <li>將 Playwright + ddddocr 查詢壽險公會網站的核心邏輯封裝在 <code>LIAQueryBot</code> 類別中。</li>
    <li>實作了: 瀏覽器啟動、導航、驗證碼識別與填寫、表單提交、Alert 處理、驗證碼錯誤重試、結果頁面解析 (初次登錄日期)、日期判斷 (一年內)。</li>
    <li>將截圖功能修改為<strong>記憶體內截圖</strong> (<code>page.screenshot()</code> 不指定 <code>path</code>)，回傳原始 <code>bytes</code>，避免伺服器寫入磁碟。</li>
</ul>

<h3>5.2 <code>app.py</code> 中的 API 端點</h3>
<ul>
    <li>引入 <code>LIAQueryBot</code>。</li>
    <li>新增 <code>/check</code> 路由，接收 <code>id</code> (登錄字號) 參數。</li>
    <li>在路由中:
        <ol>
            <li>呼叫 <code>LIAQueryBot</code> 執行查詢。</li>
            <li>取得 <code>LIAQueryBot</code> 回傳的結果字典，其中包含 <code>screenshot_bytes</code> 和 <code>suggested_filename</code>。</li>
            <li>使用 Flask 的 <code>send_file(io.BytesIO(screenshot_bytes), mimetype='image/png', download_name=filename)</code> 將截圖作為 API 回應。</li>
        </ol>
    </li>
</ul>

---

<h2>6. 核心概念解析</h2>

<h3>6.1 截圖是怎麼回傳的？ (Memory Stream)</h3>
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

<h3>6.2 Docker 的優勢</h3>
<ul>
    <li><strong>一致性</strong>: "Build once, run anywhere"。在本機 Docker 能跑，推上雲端就能跑。</li>
    <li><strong>完整控制</strong>: 不受雲端供應商預設環境 (如 Python 版本、系統函式庫) 的限制。</li>
</ul>

---

<h2>7. 常用指令備忘</h2>

<ul>
    <li><strong>啟動虛擬環境</strong>: <code>.\venv\Scripts\Activate.ps1</code></li>
    <li><strong>本機執行 Flask</strong>: <code>python app.py</code></li>
    <li><strong>Git 基本操作</strong>: <code>git add .</code>, <code>git commit -m "msg"</code>, <code>git push</code></li>
    <li><strong>Git 敏感資料清理 (本地歷史)</strong>: <code>git reset --mixed origin/master</code> (謹慎使用，會覆蓋本地未追蹤的 commit 歷史)</li>
</ul>
