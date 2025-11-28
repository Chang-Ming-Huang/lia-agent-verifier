import os
import re
import requests
from pathlib import Path

# 從環境變數讀取 API Key
TRELLO_API_KEY = os.environ.get("TRELLO_API_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")

def extract_card_id_from_url(trello_url: str) -> str:
    """從 Trello 卡片網址提取卡片 ID"""
    match = re.search(r'trello\.com/c/([a-zA-Z0-9]+)', trello_url)
    if match:
        return match.group(1)
    return None

def get_trello_card_description(card_id: str) -> str:
    """使用 Trello API 取得卡片描述"""
    if not TRELLO_API_KEY or not TRELLO_TOKEN:
        raise ValueError("未設定 TRELLO_API_KEY 或 TRELLO_TOKEN")
    
    url = f"https://api.trello.com/1/cards/{card_id}"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
        "fields": "desc"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("desc", "")
    else:
        raise Exception(f"Trello API 錯誤: {response.status_code}")

def extract_registration_number_from_text(text: str) -> str:
    """從文字中提取登錄證字號"""
    patterns = [
        r'登錄證字號[：:]\s*(\d{8,10})',
        r'登錄字號[：:]\s*(\d{8,10})',
        r'證號[：:]\s*(\d{8,10})',
        r'0\d{9}', # 嘗試直接匹配 10 位數 (0開頭)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # 如果 pattern 本身就包含數字群組
            if match.groups():
                return match.group(1).zfill(10)
            # 如果 pattern 是整個匹配 (如 0\d{9})
            else:
                return match.group(0).zfill(10)
    return None

def extract_email_from_text(text: str) -> str:
    """從文字中提取聯絡信箱"""
    # print(f"DEBUG: Trello Card Description Content:\n{text}") # 除錯訊息
    
    # Trello 的 Markdown 可能會對底線進行轉義 (例如 JM_user 變成 JM\_user)
    # 我們先移除反斜線，還原原始字串
    clean_text = text.replace(r'\_', '_').replace('\\', '')
    
    # 嘗試匹配「聯絡信箱」關鍵字，後面跟著 email
    # 允許中間有任何非換行符號
    match = re.search(r'聯絡信箱.*[:：].*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', clean_text)
    
    if match:
        # print(f"DEBUG: Found email: {match.group(1)}")
        return match.group(1)
    
    # print("DEBUG: No email found via regex.")
    return None

def resolve_trello_input(input_value: str) -> tuple:
    """
    解析輸入值，如果是 Trello 網址則解析出證號和 Email
    Returns: (registration_number, trello_card_id_or_None, contact_email_or_None)
    """
    if "trello.com" in input_value.lower():
        card_id = extract_card_id_from_url(input_value)
        if not card_id:
            raise ValueError("無效的 Trello 網址")
            
        desc = get_trello_card_description(card_id)
        reg_no = extract_registration_number_from_text(desc)
        contact_email = extract_email_from_text(desc)
        
        if not reg_no:
            raise ValueError("Trello 卡片描述中找不到登錄證字號")
            
        return reg_no, card_id, contact_email
    else:
        # 假設是直接輸入證號
        return input_value, None, None

def _post_trello_comment(card_id: str, comment_text: str) -> bool:
    """內部函式：新增留言到 Trello 卡片"""
    if not TRELLO_API_KEY or not TRELLO_TOKEN:
        print("⚠️ 未設定 Trello 憑證，無法回傳結果")
        return False

    url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
    params = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN, "text": comment_text}
    
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Trello 留言失敗: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Trello 留言發生錯誤: {e}")
        return False

def upload_result_to_trello(card_id: str, screenshot_bytes: bytes, filename: str, result_msg: str):
    """
    上傳截圖附件並留言驗證結果摘要到 Trello 卡片
    """
    if not TRELLO_API_KEY or not TRELLO_TOKEN:
        print("⚠️ 未設定 Trello 憑證，無法回傳結果")
        return

    # 1. 上傳附件
    attachment_url = f"https://api.trello.com/1/cards/{card_id}/attachments"
    files = {'file': (filename, screenshot_bytes, 'image/png')}
    params = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
    
    try:
        response = requests.post(attachment_url, params=params, files=files)
        if response.status_code == 200:
            print(f"✅ 截圖上傳成功")
            # 2. 留言驗證結果摘要
            comment_text = f"✅ 查詢完成：{Path(filename).stem}\n{result_msg}"
            if _post_trello_comment(card_id, comment_text):
                print(f"✅ 驗證結果留言成功")
            else:
                print(f"❌ 驗證結果留言失敗")
        else:
            print(f"❌ 截圖上傳失敗: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Trello 上傳截圖發生錯誤: {e}")

def post_email_template_to_trello(card_id: str, email_info: dict, contact_email: str = None):
    """
    將 Email 標題與內文作為獨立留言發布到 Trello 卡片
    """
    if not email_info:
        return

    comment_text = f"📧 **建議回信範本：**\n\n" # 多加一個換行
    
    # 如果有抓到聯絡信箱，放在最上面
    if contact_email:
        comment_text += f"**聯絡信箱：** {contact_email}\n\n"
        
    comment_text += f"**標題：** {email_info.get('subject', '')}\n\n"
    comment_text += f"**內文：**\n{email_info.get('body', '')}\n"

    if _post_trello_comment(card_id, comment_text):
        print(f"✅ Email 範本留言成功")
    else:
        print(f"❌ Email 範本留言失敗")