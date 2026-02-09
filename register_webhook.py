import os
import requests
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

API_KEY = os.environ.get("TRELLO_API_KEY")
TOKEN = os.environ.get("TRELLO_TOKEN")
BOARD_ID = os.environ.get("TRELLO_BOARD_ID")

# 請填入您的 Render 完整網址 (不要有尾隨的 slash)
CALLBACK_URL = "https://render-test-docker-4xjz.onrender.com/webhook/trello"

def register_webhook():
    if not API_KEY or not TOKEN or not BOARD_ID:
        print("錯誤：請確認 .env 中已設定 TRELLO_API_KEY, TRELLO_TOKEN, TRELLO_BOARD_ID")
        return

    url = f"https://api.trello.com/1/webhooks/"
    
    params = {
        "key": API_KEY,
        "token": TOKEN,
        "callbackURL": CALLBACK_URL,
        "idModel": BOARD_ID, # 監聽的看板 ID
        "description": "Render 自動驗證服務 Webhook",
        "active": "true"
    }
    
    print(f"正在註冊 Webhook 到: {CALLBACK_URL} ...")
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        print("Webhook 註冊成功！")
        print(response.json())
    else:
        print(f"註冊失敗: {response.status_code}")
        print(response.text)
        
def list_webhooks():
    """列出目前 Token 下所有的 Webhook (方便除錯或刪除舊的) """
    url = f"https://api.trello.com/1/tokens/{TOKEN}/webhooks"
    params = {"key": API_KEY}
    response = requests.get(url, params=params)
    print("\n目前已註冊的 Webhooks:")
    for hook in response.json():
        print(f"- ID: {hook['id']}")
        print(f"  URL: {hook['callbackURL']}")
        print(f"  Description: {hook['description']}")
        print(f"  Model: {hook['idModel']}")
        print("-" * 20)

if __name__ == "__main__":
    # 1. 先列出舊的 (避免重複註冊)
    list_webhooks()
    
    # 2. 詢問是否註冊
    ans = input("\n要註冊新的 Webhook 嗎？(y/n): ")
    if ans.lower() == 'y':
        register_webhook()
