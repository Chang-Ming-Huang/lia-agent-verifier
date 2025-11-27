from flask import Flask, request, send_file
import os
import io
import ddddocr
import requests
from playwright.sync_api import sync_playwright

# 引入我們剛剛寫好的機器人
from lia_bot import LIAQueryBot

app = Flask(__name__)

# 初始化 OCR (保留供 /ocr 路由測試用)
ocr = ddddocr.DdddOcr()

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
        .api-link {{ display: inline-block; margin-top: 1em; padding: 10px 15px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; }}
        .api-link:hover {{ background-color: #218838; }}
    </style>
</head>
<body>
    <h1>業務員登錄查詢 API</h1>
    <p>Hello, <span class="value">{user_name}</span>! 系統運行正常。</p>

    <div class="variable"><span class="key">TRELLO_API_KEY:</span> <span class="value">{trello_api_key_masked}</span></div>
    <div class="variable"><span class="key">TRELLO_TOKEN:</span> <span class="value">{trello_token_masked}</span></div>
    <div class="variable"><span class="key">TRELLO_BOARD_ID:</span> <span class="value">{trello_board_id}</span></div>
    <div class="variable"><span class="key">TRIGGER_KEYWORD:</span> <span class="value">{trigger_keyword}</span></div>

    <hr/>
    <h2>功能測試區</h2>
    <p>
        <a href="/ocr" class="api-link" style="background-color: #007bff;">測試 1: 驗證碼截圖與識別 (/ocr)</a>
        <br/>
        <small>單純測試能否連上網站並抓取驗證碼</small>
    </p>
    <p>
        <a href="/check?id=0113403577" class="api-link">測試 2: 完整查詢流程 (/check?id=...)</a>
        <br/>
        <small>輸入證號，自動查詢並回傳結果截圖 (檔案名會包含審核結果)</small>
    </p>
</body>
</html>
"""

@app.route('/check')
def check_registration():
    reg_no = request.args.get('id')
    if not reg_no:
        return "請提供 id 參數 (登錄字號)", 400
    
    # 簡單驗證格式 (8-10位數字)
    if not reg_no.isdigit() or len(reg_no) < 8 or len(reg_no) > 10:
        return f"登錄字號格式錯誤: {reg_no}", 400
        
    # 自動補零
    if len(reg_no) < 10:
        reg_no = reg_no.zfill(10)

    bot = None
    try:
        # 初始化機器人
        bot = LIAQueryBot(headless=True)
        bot.start()
        
        # 執行查詢
        result = bot.perform_query(reg_no)
        
        if result['success'] and result.get('screenshot_bytes'):
            # 查詢成功，回傳截圖
            # 設定檔名讓瀏覽器下載時能看到結果
            filename = result.get('suggested_filename', f'{reg_no}_result.png')
            
            # 為了讓中文檔名正常顯示，這是一個小技巧
            from urllib.parse import quote
            encoded_filename = quote(filename)
            
            return send_file(
                io.BytesIO(result['screenshot_bytes']),
                mimetype='image/png',
                as_attachment=False, # 設為 False 可以在瀏覽器直接看，設為 True 會強制下載
                download_name=filename
            )
        else:
            # 查詢失敗或查無資料
            return f"查詢失敗或查無資料: {result['msg']}", 404
            
    except Exception as e:
        return f"系統發生錯誤: {e}", 500
    finally:
        if bot:
            bot.close()

@app.route('/ocr')
def test_ocr_route():
    target_url = "https://public.liaroc.org.tw/lia-public/DIS/Servlet/RD?returnUrl=..%2F..%2FindexUsr.jsp&xml=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22BIG5%22%3F%3E%3CRoot%3E%3CForm%3E%3CreturnUrl%3E..%2F..%2FindexUsr.jsp%3C%2FreturnUrl%3E%3Cxml%2F%3E%3Cfuncid%3EPGQ010++++++++++++++++++++++++%3C%2Ffuncid%3E%3CprogId%3EPGQ010S01%3C%2FprogId%3E%3C%2FForm%3E%3C%2FRoot%3E&funcid=PGQ010++++++++++++++++++++++++&progId=PGQ010S01"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 前往目標網頁
            page.goto(target_url)
            
            # 等待驗證碼圖片載入
            captcha_element = page.wait_for_selector('img#captcha', state='visible', timeout=10000)
            
            # 截取驗證碼圖片元素
            captcha_bytes = captcha_element.screenshot()
            
            browser.close()
            
            # 進行識別
            result = ocr.classification(captcha_bytes)
            
            # 將截圖的 bytes 轉換成 base64 顯示在網頁上
            import base64
            captcha_base64 = base64.b64encode(captcha_bytes).decode('utf-8')
            
            return f"""
            <h1>OCR 識別測試 (目標網頁)</h1>
            <p>目標網頁: <a href="{target_url}" target="_blank">{target_url}</a></p>
            <p>識別結果: <strong>{result}</strong></p>
            <p>截圖的驗證碼:</p>
            <img src="data:image/png;base64,{captcha_base64}" alt="驗證碼圖片" />
            """
    except Exception as e:
        return f"OCR 識別失敗: {e}", 500

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

if __name__ == "__main__":
    app.run(debug=True)