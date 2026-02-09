# Trello 整合功能介紹

> 本文件說明 `trello_flow/` 模組的功能。未來棄用 Trello 流程時，刪除整個 `trello_flow/` 資料夾即可。

## 功能概述

Trello 流程是系統的「舊流程」，透過 Trello Webhook 實現「開票即驗證」的自動化：當客服在 Trello 看板建立包含特定關鍵字的卡片時，系統自動觸發業務員資格查詢，並將結果回報至卡片。

## 模組結構

```
trello_flow/
├── __init__.py             # 匯出 trello_bp Blueprint
├── routes.py               # /webhook/trello 路由 + process_trello_card() 背景任務
├── trello_utils.py         # Trello API 工具函式 (讀取卡片、上傳截圖、留言)
├── register_webhook.py     # 一次性腳本：向 Trello 註冊 Webhook
└── trello_intro.md         # 本文件
```

## 核心功能

1.  **Webhook 自動觸發** (`routes.py`)：
    *   監聽 `POST /webhook/trello`，當 Trello 卡片標題包含關鍵字（如「年繳方案申請」）時，在背景執行緒中自動啟動查詢。
    *   處理 Trello 註冊 Webhook 時的 `HEAD` 請求驗證。
2.  **結果回報** (`trello_utils.py`)：
    *   查詢後的**截圖**自動上傳至卡片附件。
    *   **Draft 回信**：根據查詢結果（通過/不通過），自動產生對應的 Email 標題與內文，並留言在卡片上，方便客服人員直接複製使用。
3.  **卡片解析** (`trello_utils.py`)：
    *   從 Trello 卡片描述中提取登錄證字號與聯絡信箱。
    *   支援 Web UI (`/check` 路由) 直接貼入 Trello 卡片網址查詢。

## 使用技術

*   **API 整合**: Trello REST API & Webhook
*   **核心查詢引擎**: `lia_bot.py` (根目錄共用模組)
*   **背景處理**: Python `threading` (避免 Webhook 10 秒超時限制)
