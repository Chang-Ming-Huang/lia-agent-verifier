# 壽險公會業務員登錄查詢自動化系統 (LIA Auto Query Bot)

這是一個自動化工具，旨在協助快速查詢「中華民國人壽保險商業同業公會」的業務員登錄狀態。
系統整合了 Web 網頁介面與 Trello 自動化流程，透過 Playwright 進行網頁爬蟲操作，並結合 ddddocr 進行驗證碼識別，能自動判斷業務員是否符合特定的年繳方案資格（例如：是否為一年內新進業務員），並自動產生對應的 Email 回信範本。

## 主要功能

*   **自動化查詢**: 自動前往壽險公會網站，填寫證號、識別並輸入驗證碼，直到查詢成功。
*   **OCR 驗證碼識別**: 使用 `ddddocr` 自動克服圖片驗證碼，並具備錯誤重試機制。
*   **資格判斷邏輯**:
    *   自動解析「初次登錄日期」。
    *   判斷是否在「一年內」登錄，以此區分「審核通過」或「資格不符」。
*   **Web 使用者介面**: 提供簡易的網頁介面，輸入證號或 Trello 卡片網址即可查詢，並即時預覽截圖與 Email 範本。
*   **Trello 深度整合** (`trello_flow/`):
    *   支援輸入 Trello 卡片網址自動解析證號與聯絡信箱。
    *   查詢結果截圖自動上傳至 Trello 卡片附件。
    *   Email 回信範本（標題與內文）自動留言至 Trello 卡片。
    *   **Webhook 自動化**: 監聽 Trello 看板的新卡片事件，當標題包含特定關鍵字（如「年繳方案申請」）時，自動觸發查詢流程。
*   **REST API 驗證** (`api_flow/`): 提供 `POST /api/verify-agent-license` 端點，接收證號並回傳 JSON 格式的驗證結果。
*   **容器化部署**: 提供 `Dockerfile`，支援 Render 等雲端平台部署。

## 技術棧

*   **語言**: Python 3.9+
*   **Web 框架**: Flask
*   **瀏覽器自動化**: Playwright (Chromium)
*   **OCR 引擎**: ddddocr
*   **部署**: Docker, Render

## 快速開始 (本地開發)

### 1. 前置需求

*   安裝 Python 3.9 或以上版本
*   安裝 Git

### 2. 下載專案

```bash
git clone https://github.com/Chang-Ming-Huang/render-test.git
cd render-test
```

### 3. 建立虛擬環境與安裝套件

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
.\venv\Scripts\Activate.ps1
# Mac/Linux: source venv/bin/activate

# 安裝依賴套件
pip install -r requirements.txt
```

### 4. 設定環境變數

在專案根目錄建立 `.env` 檔案，填入以下資訊：

```ini
# Trello API 設定 (若不使用 Trello 整合功能可留空，但相關功能會失效)
TRELLO_API_KEY=你的_Trello_API_Key
TRELLO_TOKEN=你的_Trello_Token
TRELLO_BOARD_ID=你的_Trello_看板_ID

# 觸發自動化的關鍵字
TRIGGER_KEYWORD=年繳方案申請
```

*   *如何取得 Trello API Key 與 Token：請參考 [Trello Developer 頁面](https://trello.com/power-ups/admin)*

### 5. 啟動應用程式

```bash
# 首次執行需安裝 Playwright 瀏覽器核心
playwright install chromium

# 啟動 Flask Server
python app.py
```

瀏覽器打開 `http://localhost:5000` 即可看到操作介面。

## Docker 部署

本專案已包含優化過的 `Dockerfile`，可直接部署至支援 Docker 的雲端平台（如 Render, Railway, Fly.io）。

### Render 部署注意事項

1.  在 Render 建立新的 **Web Service**。
2.  連結此 GitHub Repository。
3.  Runtime 選擇 **Docker**。
4.  在 Environment Variables 設定頁面填入上述的環境變數 (`TRELLO_API_KEY` 等)。
5.  部署完成後，Render 會自動執行 `gunicorn` 啟動服務。

## 專案結構

```
render-test/
├── app.py                          # Flask 主程式 (Web UI + /check 路由，組裝 Blueprints)
├── lia_bot.py                      # 核心模組：Playwright 爬蟲與 ddddocr 驗證 (共用)
│
├── trello_flow/                    # Trello Webhook 自動化流程 (舊流程，未來可整個刪除)
│   ├── __init__.py
│   ├── routes.py                   # /webhook/trello 路由 + process_trello_card()
│   ├── trello_utils.py             # Trello API 工具函式 (讀取卡片、上傳、留言)
│   ├── register_webhook.py         # 一次性腳本：向 Trello 註冊 Webhook
│   └── trello_intro.md             # Trello 整合功能介紹
│
├── api_flow/                       # REST API 驗證流程 (新流程)
│   ├── __init__.py
│   ├── routes.py                   # /api/verify-agent-license 路由
│   └── TESTING.md                  # API 測試指南
│
├── docs/
│   └── learning_notes.md           # 開發筆記 (架構設計與技術細節)
│
├── requirements.txt                # Python 依賴清單
├── Dockerfile                      # Docker 建置設定
└── README.md                       # 專案說明文件
```

## Webhook 設定 (進階)

若要啟用 Trello 自動觸發功能，需將服務部署到公開網路 (有 HTTPS 網址)，並執行註冊腳本：

```bash
# 確保 Web Service 已在線上，並修改 register_webhook.py 中的 callbackURL
python trello_flow/register_webhook.py
```

## 備註

*   本工具僅供內部行政流程優化使用。
*   查詢結果僅包含公開可查詢之資訊。
