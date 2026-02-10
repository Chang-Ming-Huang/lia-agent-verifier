from flask import Blueprint, request, send_file, jsonify
import os
import io
import base64
import ddddocr
from playwright.sync_api import sync_playwright

from lia_bot import LIAQueryBot
from trello_flow import trello_utils

web_bp = Blueprint('web_flow', __name__)

# 初始化 OCR (供 /ocr 路由測試用)
ocr = ddddocr.DdddOcr()

# 輔助函式：用於遮罩敏感資訊
def mask_sensitive_data(data):
    if data and len(data) > 6:
        return data[:3] + '***' + data[-3:]
    return '***' # 如果資料太短或不存在，直接遮罩

@web_bp.route('/')
def home():
    # 讀取環境變數僅用於顯示資訊
    user_name = os.environ.get('MY_NAME', 'Guest')

    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>業務員登錄查詢自動化</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}

        .input-group {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        input[type="text"] {{ flex: 1; padding: 12px; border: 2px solid #e9ecef; border-radius: 5px; font-size: 16px; transition: border-color 0.3s; }}
        input[type="text"]:focus {{ border-color: #007bff; outline: none; }}

        button {{ padding: 12px 25px; background-color: #007bff; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; transition: background-color 0.3s; }}
        button:hover {{ background-color: #0056b3; }}
        button:disabled {{ background-color: #6c757d; cursor: not-allowed; }}

        #result-area {{ margin-top: 30px; text-align: center; min-height: 200px; display: none; }}
        #loading {{ display: none; text-align: center; margin: 20px 0; }}
        .spinner {{ width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}

        .status-box {{ padding: 15px; margin-bottom: 20px; border-radius: 5px; text-align: left; }}
        .status-info {{ background-color: #e2e3e5; color: #383d41; }}
        .status-success {{ background-color: #d4edda; color: #155724; border-left: 5px solid #28a745; }}
        .status-error {{ background-color: #f8d7da; color: #721c24; border-left: 5px solid #dc3545; }}

        .result-img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-top: 15px; }}

        /* Email 範本區塊樣式 */
        .email-section {{ margin-top: 30px; text-align: left; border-top: 2px dashed #eee; padding-top: 20px; }}
        .email-box {{ background-color: #f1f3f5; padding: 15px; border-radius: 5px; margin-bottom: 15px; position: relative; }}
        .email-label {{ font-weight: bold; color: #555; display: block; margin-bottom: 5px; }}
        .email-content {{ white-space: pre-wrap; font-family: 'Consolas', 'Monaco', monospace; font-size: 0.95em; background: white; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
        .copy-btn {{ position: absolute; top: 10px; right: 10px; padding: 5px 10px; font-size: 12px; background-color: #6c757d; }}
        .copy-btn:hover {{ background-color: #5a6268; }}

        .info-section {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.9em; color: #666; }}
        .variable {{ margin-bottom: 5px; }}
        .key {{ font-weight: bold; color: #555; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>業務員登錄查詢自動化</h1>

        <div class="input-group">
            <input type="text" id="query-input" placeholder="請輸入「登錄證號」或「Trello 卡片網址」..." />
            <button id="submit-btn" onclick="performQuery()">查詢</button>
        </div>
        <p style="font-size: 0.9em; color: #666; margin-top: -10px;">
            支援格式：數字證號 (例如：0113403577) 或 Trello 卡片連結 (如 https://trello.com/c/...)
            <br/>
            範例測試：<code>0113403577</code> (審核通過) | <code>0102204809</code> (資格不符) | <code>01134035</code> (無效證號)
        </p>

        <div id="loading">
            <div class="spinner"></div>
            <p>正在查詢中，請稍候...<br/><span style="font-size: 0.8em; color: #888;">(可能需要 15-30 秒，包含驗證碼識別與重試)</span></p>
        </div>

        <div id="result-area">
            <!-- 結果將顯示於此 -->
        </div>

        <div class="info-section">
            <p><strong>系統狀態:</strong> <span style="color: green;">線上</span></p>
        </div>
    </div>

    <script>
        function copyToClipboard(elementId) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                alert('已複製到剪貼簿！');
            }}).catch(err => {{
                console.error('複製失敗', err);
            }});
        }}

        async function performQuery() {{
            const input = document.getElementById('query-input').value.trim();
            if (!input) return alert('請輸入內容！');

            const btn = document.getElementById('submit-btn');
            const loading = document.getElementById('loading');
            const resultArea = document.getElementById('result-area');

            // 重置介面
            resultArea.style.display = 'none';
            resultArea.innerHTML = '';
            btn.disabled = true;
            loading.style.display = 'block';

            try {{
                // 呼叫後端 API
                const response = await fetch(`/check?id=${{encodeURIComponent(input)}}`);
                const data = await response.json(); // 改為解析 JSON

                loading.style.display = 'none';
                resultArea.style.display = 'block';
                btn.disabled = false;

                if (data.success) {{
                    // 成功：顯示圖片和成功訊息
                    const filename = data.filename;
                    const imgUrl = data.image;
                    const email = data.email;

                    let statusClass = 'status-success';
                    let statusText = '查詢成功';
                    if (filename.includes('資格不符')) {{ // 檔名已改為資格不符
                        statusClass = 'status-error';
                        statusText = '審核失敗 (超過一年)';
                    }} else if (filename.includes('無效證號')) {{ // 檔名已改為無效證號
                        statusClass = 'status-error';
                        statusText = '無效的證號';
                    }}

                    resultArea.innerHTML = `
                        <div class="status-box ${{statusClass}}">
                            <strong>${{statusText}}</strong><br/>
                            檔案名稱: ${{filename}}
                        </div>
                        <img src="${{imgUrl}}" class="result-img" alt="查詢結果截圖" />
                        <br/><br/>
                        <a href="${{imgUrl}}" download="${{filename}}" style="color: #007bff; text-decoration: none;">下載截圖</a>

                        ${{ data.trello_card_url ?
                            `<div style="margin-top: 20px; text-align: center; background-color: #e6f7ff; padding: 15px; border-radius: 8px; border: 1px solid #91d5ff;">
                                <p style="font-size: 1.1em; color: #0056b3; margin-bottom: 15px;">
                                    已將驗證結果回覆在票上，你可以繼續回到 Trello 進行回信步驟。
                                </p>
                                <button onclick="window.open('${{data.trello_card_url}}', '_blank')"
                                        style="background-color: #1890ff; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; border: none; font-size: 1em;">
                                    回到 Trello 票
                                </button>
                            </div>`
                            : ''
                        }}

                        <div class="email-section">
                            <h3>回信範本</h3>

                            <div class="email-box">
                                <span class="email-label">信件標題：</span>
                                <div id="email-subject" class="email-content">${{email.subject}}</div>
                                <button class="copy-btn" onclick="copyToClipboard('email-subject')">複製</button>
                            </div>

                            <div class="email-box">
                                <span class="email-label">信件內文：</span>
                                <div id="email-body" class="email-content">${{email.body}}</div>
                                <button class="copy-btn" onclick="copyToClipboard('email-body')">複製</button>
                            </div>
                        </div>
                    `;
                }} else {{
                    // 失敗：顯示錯誤訊息
                    resultArea.innerHTML = `
                        <div class="status-box status-error">
                            <strong>查詢失敗</strong><br/>
                            ${{data.message || '未知錯誤'}}
                        </div>
                    `;
                }}
            }} catch (err) {{
                loading.style.display = 'none';
                btn.disabled = false;
                resultArea.style.display = 'block';
                resultArea.innerHTML = `
                    <div class="status-box status-error">
                        <strong>系統錯誤</strong><br/>
                        ${{err.message}}
                    </div>
                `;
            }}
        }}
    </script>
</body>
</html>
"""

@web_bp.route('/check')
def check_registration():
    input_value = request.args.get('id')
    if not input_value:
        return jsonify({"success": False, "message": "請提供 id 參數"}), 400

    trello_card_id = None
    reg_no = input_value
    contact_email = None

    try:
        # 1. 解析輸入 (判斷是否為 Trello 網址)
        try:
             reg_no, trello_card_id, contact_email = trello_utils.resolve_trello_input(input_value)
        except ValueError as ve:
             return jsonify({"success": False, "message": f"輸入解析錯誤: {str(ve)}"}), 400

        # 2. 驗證證號格式
        if not reg_no.isdigit() or len(reg_no) < 8 or len(reg_no) > 10:
            return jsonify({"success": False, "message": f"無效的登錄字號格式: {reg_no}"}), 400

        # 自動補零
        if len(reg_no) < 10:
            reg_no = reg_no.zfill(10)

        # 3. 執行機器人查詢
        bot = None
        try:
            bot = LIAQueryBot(headless=True)
            bot.start()

            result = bot.perform_query(reg_no)

            if result['success'] and result.get('screenshot_bytes'):
                # 查詢成功
                filename = result.get('suggested_filename', f'{reg_no}_result.png')

                # 將 bytes 轉為 base64 字串回傳
                img_base64 = base64.b64encode(result['screenshot_bytes']).decode('utf-8')
                img_data_url = f"data:image/png;base64,{img_base64}"

                # 4. 如果有 Trello 卡片 ID，回傳結果到 Trello
                if trello_card_id:
                    try:
                        print(f"正在回傳結果到 Trello 卡片 {trello_card_id}...")
                        trello_utils.upload_result_to_trello(
                            trello_card_id,
                            result['screenshot_bytes'],
                            filename,
                            result['msg'] # 將訊息傳入，作為截圖留言的一部分
                        )
                        trello_utils.post_email_template_to_trello(
                            trello_card_id,
                            result['email_info'],
                            contact_email
                        )
                    except Exception as te:
                        print(f"Trello 回傳失敗 (但不影響主流程): {te}")

                # 回傳 JSON
                return jsonify({
                    "success": True,
                    "image": img_data_url,
                    "filename": filename,
                    "email": result.get("email_info", {}),
                    "trello_card_url": input_value if trello_card_id else None # 回傳 Trello 原始連結
                })
            else:
                return jsonify({"success": False, "message": f"查詢失敗或查無資料: {result['msg']}"}), 404

        finally:
            if bot:
                bot.close()

    except Exception as e:
        return jsonify({"success": False, "message": f"系統發生錯誤: {e}"}), 500

@web_bp.route('/ocr')
def test_ocr_route():
    # (保留原有的 OCR 測試路由)
    target_url = "https://public.liaroc.org.tw/lia-public/DIS/Servlet/RD?returnUrl=..%2F..%2FindexUsr.jsp&xml=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22BIG5%22%3F%3E%3CRoot%3E%3CForm%3E%3CreturnUrl%3E..%2F..%2FindexUsr.jsp%3C%2FreturnUrl%3E%3Cxml%2F%3E%3Cfuncid%3EPGQ010++++++++++++++++++++++++%3C%2Ffuncid%3E%3CprogId%3EPGQ010S01%3C%2FprogId%3E%3C%2FForm%3E%3C%2FRoot%3E&funcid=PGQ010++++++++++++++++++++++++&progId=PGQ010S01"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url)
            captcha_element = page.wait_for_selector('img#captcha', state='visible', timeout=10000)
            captcha_bytes = captcha_element.screenshot()
            browser.close()
            result = ocr.classification(captcha_bytes)
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

@web_bp.route('/screenshot')
def take_screenshot():
    # (保留原有的截圖測試路由)
    target_url = request.args.get('url', 'https://example.com')
    if not target_url.startswith('http://') and not target_url.startswith('https://'):
        target_url = 'https://' + target_url
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url)
            screenshot_bytes = page.screenshot()
            browser.close()
            return send_file(io.BytesIO(screenshot_bytes), mimetype='image/png')
    except Exception as e:
        return f"截圖失敗: {e}", 500
