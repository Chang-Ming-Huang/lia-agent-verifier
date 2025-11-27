import os
import re
import requests

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
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).zfill(10)
    return None

def resolve_trello_input(input_value: str) -> tuple:
    """
    解析輸入值，如果是 Trello 網址則解析出證號，否則回傳原值
    Returns: (registration_number, trello_card_id_or_None)
    """
    if "trello.com" in input_value.lower():
        card_id = extract_card_id_from_url(input_value)
        if not card_id:
            raise ValueError("無效的 Trello 網址")
            
        desc = get_trello_card_description(card_id)
        reg_no = extract_registration_number_from_text(desc)
        
        if not reg_no:
            raise ValueError("Trello 卡片描述中找不到登錄證字號")
            
        return reg_no, card_id
    else:
        # 假設是直接輸入證號
        return input_value, None

def upload_result_to_trello(card_id: str, screenshot_bytes: bytes, filename: str):
    """上傳截圖並留言到 Trello"""
    if not TRELLO_API_KEY or not TRELLO_TOKEN:
        print("⚠️ 未設定 Trello 憑證，無法回傳結果")
        return

    # 1. 上傳附件
    attachment_url = f"https://api.trello.com/1/cards/{card_id}/attachments"
    files = {'file': (filename, screenshot_bytes, 'image/png')}
    params = {"key": TRELLO_API_KEY, "token": TRELLO_TOKEN}
    
    try:
        requests.post(attachment_url, params=params, files=files)
        
        # 2. 留言
        comment_url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
        comment_params = {
            "key": TRELLO_API_KEY,
            "token": TRELLO_TOKEN,
            "text": f"查詢完成：{Path(filename).stem}"
        }
        requests.post(comment_url, params=comment_params)
        print(f"✅ 已回傳結果至 Trello 卡片 {card_id}")
    except Exception as e:
        print(f"❌ Trello 回傳失敗: {e}")

from pathlib import Path
