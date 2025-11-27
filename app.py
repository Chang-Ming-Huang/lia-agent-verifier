from flask import Flask, request, send_file
import os
from playwright.sync_api import sync_playwright
import io

app = Flask(__name__)

# 輔助函式：用於遮罩敏感資訊
def mask_sensitive_data(data):
    if data and len(data) > 6:
        return data[:3] + '***' + data[-3:]
    return '***' # 如果資料太短或不存在，直接遮罩

@app.route('/')
def home():
    # 讀取 MY_NAME (先前的練習)
    user_name = os.environ.get('MY_NAME', 'Guest')

    # 讀取 Trello 相關的環境變數
    trello_api_key = os.environ.get('TRELLO_API_KEY', '未設定')
    trello_token = os.environ.get('TRELLO_TOKEN', '未設定')
    trello_board_id = os.environ.get('TRELLO_BOARD_ID', '未設定')
    trigger_keyword = os.environ.get('TRIGGER_KEYWORD', '未設定')

    # 對敏感資訊進行遮罩
    trello_api_key_masked = mask_sensitive_data(trello_api_key)
    trello_token_masked = mask_sensitive_data(trello_token)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>環境變數測試</title>
    <style>
        body {{ font-family: sans-serif; margin: 2em; background-color: #f4f4f4; color: #333; }}
        h1 {{ color: #0056b3; }}
        .variable {{ margin-bottom: 0.8em; padding: 0.5em; background-color: #fff; border-left: 5px solid #007bff; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
        .key {{ font-weight: bold; margin-right: 0.5em; color: #0056b3; }}
        .value {{ font-family: 'Courier New', Courier, monospace; color: #555; }}
    </style>
</head>
<body>
    <h1>環境變數測試頁面</h1>
    <p>Hello, <span class="value">{user_name}</span>! 這是一個使用多個環境變數的測試。</p>

    <div class="variable"><span class="key">TRELLO_API_KEY:</span> <span class="value">{trello_api_key_masked}</span></div>
    <div class="variable"><span class="key">TRELLO_TOKEN:</span> <span class="value">{trello_token_masked}</span></div>
    <div class="variable"><span class="key">TRELLO_BOARD_ID:</span> <span class="value">{trello_board_id}</span></div>
    <div class="variable"><span class="key">TRIGGER_KEYWORD:</span> <span class="value">{trigger_keyword}</span></div>

    <p style="font-size: 0.8em; color: #777;">敏感資訊已進行遮罩處理。</p>
    <hr/>
    <h2>Playwright 截圖功能測試</h2>
    <p>請嘗試訪問 <a href="/screenshot?url=https://www.google.com">/screenshot?url=https://www.google.com</a> 來測試截圖。</p>
</body>
</html>
"""

@app.route('/screenshot')
def take_screenshot():
    target_url = request.args.get('url', 'https://example.com')
    if not target_url.startswith('http://') and not target_url.startswith('https://'):
        target_url = 'https://' + target_url # 預設使用 HTTPS

    try:
        with sync_playwright() as p:
            # 在伺服器上務必使用 headless=True
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url)
            screenshot_bytes = page.screenshot() # 直接獲取截圖的位元組
            browser.close()
            
            # 將位元組資料作為圖片檔案回傳
            return send_file(io.BytesIO(screenshot_bytes), mimetype='image/png')
    except Exception as e:
        return f"截圖失敗: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)