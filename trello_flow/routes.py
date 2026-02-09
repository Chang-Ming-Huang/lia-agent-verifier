import os
import threading
from flask import Blueprint, request

from lia_bot import LIAQueryBot
from . import trello_utils

trello_bp = Blueprint('trello_flow', __name__)

TRIGGER_KEYWORD = os.environ.get("TRIGGER_KEYWORD", "年繳方案申請")


def process_trello_card(card_id, card_url):
    """
    背景任務：處理 Trello 卡片的自動驗證
    """
    print(f"[Background] 開始處理卡片: {card_id}")
    bot = None
    try:
        # 1. 從卡片解析證號和信箱
        try:
            reg_no, _, contact_email = trello_utils.resolve_trello_input(card_url)
        except ValueError as ve:
            trello_utils._post_trello_comment(
                card_id,
                f"自動驗證失敗：{str(ve)}\n請確認卡片描述中的登錄證字號格式是否正確（應為 8-10 位數字）。"
            )
            print(f"[Background] 解析錯誤已回報 Trello: {ve}")
            return

        print(f"[Background] 解析結果: 證號={reg_no}, 信箱={contact_email}")

        # 2. 驗證證號格式
        if not reg_no.isdigit() or len(reg_no) < 8 or len(reg_no) > 10:
            trello_utils._post_trello_comment(
                card_id,
                f"自動驗證失敗：登錄證字號格式無效「{reg_no}」\n證號應為 8-10 位純數字，請確認後重新建立卡片。"
            )
            # 同時發布 email 範本，讓客服可以直接複製回信
            email_info = {
                "subject": "Finfo 有收到您的年繳方案申請，想詢問您的登錄證字號",
                "body": (
                    "您好,\n\n"
                    "這裡是 Finfo 客服團隊的審核專員，感謝您申請年繳方案。\n"
                    "根據您提供的登錄證字號，於 壽險公會 無法查詢到資格，\n"
                    "請再次確認提供的資料是否正確，再次感謝您的申請與支持。\n\n"
                    "如有任何問題，隨時回覆此信與我們聯繫。\n\n"
                    "如果有其他任何網站上的操作問題，也都歡迎您在此封信件中一併提出，我們會盡快協助，感謝您！\n\n"
                    "Finfo 客服團隊 敬上"
                )
            }
            trello_utils.post_email_template_to_trello(card_id, email_info, contact_email)
            print(f"[Background] 證號格式錯誤已回報 Trello，跳過")
            return

        if len(reg_no) < 10:
            reg_no = reg_no.zfill(10)

        # 3. 執行爬蟲
        bot = LIAQueryBot(headless=True)
        bot.start()
        result = bot.perform_query(reg_no)

        # 4. 回傳結果到 Trello
        if result['success'] and result.get('screenshot_bytes'):
            filename = result.get('suggested_filename', f'{reg_no}_result.png')

            trello_utils.upload_result_to_trello(
                card_id,
                result['screenshot_bytes'],
                filename,
                result['msg']
            )

            trello_utils.post_email_template_to_trello(
                card_id,
                result['email_info'],
                contact_email
            )
            print(f"[Background] 卡片 {card_id} 處理完成並回報")
        else:
            trello_utils._post_trello_comment(
                card_id,
                f"自動驗證失敗：{result['msg']}\n請稍後重試或手動查詢。"
            )
            print(f"[Background] 查詢失敗已回報 Trello: {result['msg']}")

    except Exception as e:
        try:
            trello_utils._post_trello_comment(
                card_id,
                f"自動驗證發生系統錯誤，請通知管理員或手動查詢。"
            )
        except:
            pass
        print(f"[Background] 發生錯誤: {e}")
    finally:
        if bot:
            bot.close()


@trello_bp.route('/webhook/trello', methods=['HEAD', 'POST'])
def trello_webhook():
    """
    接收 Trello Webhook
    HEAD: Trello 建立 Webhook 時會發送 HEAD 請求來驗證網址是否存在
    POST: 實際的事件通知
    """
    if request.method == 'HEAD':
        return "OK", 200

    data = request.json

    try:
        # 檢查事件類型
        action = data.get('action', {})
        action_type = action.get('type')

        # 我們只關心「建立卡片」的事件
        if action_type == 'createCard':
            card = action.get('data', {}).get('card', {})
            card_name = card.get('name', '')
            card_id = card.get('id')
            card_short_link = card.get('shortLink')

            # 檢查關鍵字
            if TRIGGER_KEYWORD in card_name:
                print(f"偵測到關鍵字「{TRIGGER_KEYWORD}」，卡片 ID: {card_id}")

                # 組出卡片網址
                card_url = f"https://trello.com/c/{card_short_link}"

                # 啟動背景執行緒處理，以免 Webhook 超時 (Trello 要求 10秒內回傳 200)
                thread = threading.Thread(target=process_trello_card, args=(card_id, card_url))
                thread.start()
            else:
                print(f"忽略卡片：{card_name} (未包含關鍵字)")

    except Exception as e:
        print(f"Webhook 處理錯誤: {e}")

    # 無論如何都回傳 200，告訴 Trello 我們收到了
    return "OK", 200
