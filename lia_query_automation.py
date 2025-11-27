#!/usr/bin/env python3
"""
業務員登錄查詢自動化腳本
使用 Playwright + ddddocr 自動識別驗證碼並查詢

安裝依賴：
    pip install playwright ddddocr requests
    playwright install chromium
"""

import ddddocr
from playwright.sync_api import sync_playwright
import time
import sys
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
import os # 引入 os 模組


# ============================================================ 
# Trello API 設定（從環境變數讀取，避免硬編碼敏感資訊）
# 取得方式：https://trello.com/app-key
# ============================================================ 
TRELLO_API_KEY = os.environ.get("TRELLO_API_KEY", "YOUR_TRELLO_API_KEY_NOT_SET")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN", "YOUR_TRELLO_TOKEN_NOT_SET")


def extract_card_id_from_url(trello_url: str) -> str:
    """
    從 Trello 卡片網址提取卡片 ID
    
    Args:
        trello_url: Trello 卡片網址，如 https://trello.com/c/CBHV7xLy/1418-...
        
    Returns:
        卡片短 ID，如 "CBHV7xLy"
    """
    # 支援格式：https://trello.com/c/CBHV7xLy/...
    match = re.search(r'trello\.com/c/([a-zA-Z0-9]+)', trello_url)
    if match:
        return match.group(1)
    return None


def get_trello_card_description(card_id: str) -> str:
    """
    使用 Trello API 取得卡片描述
    
    Args:
        card_id: 卡片短 ID
        
    Returns:
        卡片描述文字
    """
    if not TRELLO_API_KEY or not TRELLO_TOKEN or "YOUR_TRELLO" in TRELLO_API_KEY: # 檢查是否已設定
        raise ValueError("請先設定 TRELLO_API_KEY 和 TRELLO_TOKEN 環境變數")
    
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
        raise Exception(f"Trello API 錯誤: {response.status_code} - {response.text}")


def extract_registration_number_from_text(text: str) -> str:
    """
    從文字中提取登錄證字號
    
    Args:
        text: 包含登錄證字號的文字
        
    Returns:
        登錄證字號（10位數字），找不到返回 None
    """
    # 嘗試匹配「登錄證字號：XXXXXXXXXX」格式
    patterns = [
        r'登錄證字號[：:]\s*(\d{8,10})',
        r'登錄字號[：:]\s*(\d{8,10})',
        r'證號[：:]\s*(\d{8,10})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            number = match.group(1)
            # 自動補零到 10 位
            return number.zfill(10)
    
    return None


def get_registration_number_from_trello(trello_url: str) -> tuple:
    """
    從 Trello 卡片網址取得登錄證字號
    
    Args:
        trello_url: Trello 卡片網址
        
    Returns:
        (登錄證字號, 卡片ID) 元組
    """
    print(f"🔗 正在解析 Trello 卡片...")
    
    # 提取卡片 ID
    card_id = extract_card_id_from_url(trello_url)
    if not card_id:
        raise ValueError(f"無法從網址提取卡片 ID: {trello_url}")
    
    print(f"   卡片 ID: {card_id}")
    
    # 取得卡片描述
    description = get_trello_card_description(card_id)
    print(f"   已取得卡片描述")
    
    # 提取登錄證字號
    reg_number = extract_registration_number_from_text(description)
    if not reg_number:
        raise ValueError(f"卡片描述中找不到登錄證字號")
    
    print(f"   登錄證字號: {reg_number}")
    
    return reg_number, card_id


def add_comment_with_attachment_to_trello(card_id: str, comment_text: str, file_path: str):
    """
    在 Trello 卡片上新增留言並附上圖片
    
    Args:
        card_id: 卡片短 ID
        comment_text: 留言內容
        file_path: 截圖檔案路徑
    """
    if not TRELLO_API_KEY or not TRELLO_TOKEN or "YOUR_TRELLO" in TRELLO_API_KEY:
        raise ValueError("請先設定 TRELLO_API_KEY 和 TRELLO_TOKEN 環境變數")
    
    print(f"\n📤 正在將結果發布到 Trello 卡片...")
    
    # 1. 先上傳附件
    print(f"   上傳截圖...")
    attachment_url = f"https://api.trello.com/1/cards/{card_id}/attachments"
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (Path(file_path).name, f, 'image/png')
        }
        params = {
            "key": TRELLO_API_KEY,
            "token": TRELLO_TOKEN,
        }
        response = requests.post(attachment_url, params=params, files=files)
    
    if response.status_code == 200:
        print(f"   ✅ 截圖上傳成功")
    else:
        print(f"   ⚠️ 截圖上傳失敗: {response.status_code} - {response.text}")
    
    # 2. 新增留言
    print(f"   新增留言: {comment_text}")
    comment_url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
        "text": comment_text
    }
    
    response = requests.post(comment_url, params=params)
    
    if response.status_code == 200:
        print(f"   ✅ 留言新增成功")
    else:
        print(f"   ⚠️ 留言新增失敗: {response.status_code} - {response.text}")


def add_comment_to_trello_card(card_id: str, comment_text: str) -> bool:
    """
    在 Trello 卡片上新增留言
    
    Args:
        card_id: 卡片短 ID
        comment_text: 留言內容
        
    Returns:
        True 如果成功，否則 False
    """
    if not TRELLO_API_KEY or not TRELLO_TOKEN or "YOUR_TRELLO" in TRELLO_API_KEY:
        raise ValueError("請先設定 TRELLO_API_KEY 和 TRELLO_TOKEN 環境變數")
    
    url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
        "text": comment_text
    }
    
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        return True
    else:
        print(f"    ⚠️ 新增留言失敗: {response.status_code} - {response.text}")
        return False


def upload_attachment_to_trello_card(card_id: str, file_path: str) -> bool:
    """
    上傳附件到 Trello 卡片
    
    Args:
        card_id: 卡片短 ID
        file_path: 檔案路徑
        
    Returns:
        True 如果成功，否則 False
    """
    if not TRELLO_API_KEY or not TRELLO_TOKEN or "YOUR_TRELLO" in TRELLO_API_KEY:
        raise ValueError("請先設定 TRELLO_API_KEY 和 TRELLO_TOKEN 環境變數")
    
    url = f"https://api.trello.com/1/cards/{card_id}/attachments"
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_TOKEN,
    }
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (Path(file_path).name, f, 'image/png')
        }
        response = requests.post(url, params=params, files=files)
    
    if response.status_code == 200:
        return True
    else:
        print(f"    ⚠️ 上傳附件失敗: {response.status_code} - {response.text}")
        return False


def post_result_to_trello(card_id: str, screenshot_path: str):
    """
    將查詢結果發布到 Trello 卡片
    
    Args:
        card_id: 卡片短 ID
        screenshot_path: 截圖檔案路徑
    """
    print(f"\n📤 正在將結果發布到 Trello 卡片...")
    
    # 取得檔名（不含路徑和副檔名）作為留言內容
    filename = Path(screenshot_path).stem
    
    # 上傳截圖附件
    print(f"   上傳截圖...")
    if upload_attachment_to_trello_card(card_id, screenshot_path):
        print(f"   ✅ 截圖上傳成功")
    else:
        print(f"   ❌ 截圖上傳失敗")
    
    # 新增留言
    print(f"   新增留言: {filename}")
    if add_comment_to_trello_card(card_id, filename):
        print(f"   ✅ 留言新增成功")
    else:
        print(f"   ❌ 留言新增失敗")


class LIAQueryBot:
    """壽險公會業務員登錄查詢機器人"""
    
    URL = (
        "https://public.liaroc.org.tw/lia-public/DIS/Servlet/RD?"
        "returnUrl=..%2F..%2FindexUsr.jsp&xml=%3C%3Fxml+version%3D%221.0%22+"
        "encoding%3D%22BIG5%22%3F%3E%3CRoot%3E%3CForm%3E%3CreturnUrl%3E"
        "..%2F..%2FindexUsr.jsp%3C%2FreturnUrl%3E%3Cxml%2F%3E%3Cfuncid%3E"
        "PGQ010++++++++++++++++++++++++%3C%2Ffuncid%3E%3CprogId%3EPGQ010S01"
        "%3C%2FprogId%3E%3C%2FForm%3E%3C%2FRoot%3E&funcid="
        "PGQ010++++++++++++++++++++++++&progId=PGQ010S01"
    )
    
    def __init__(self, headless: bool = False):
        """
        初始化查詢機器人
        
        Args:
            headless: 是否使用無頭模式（不顯示瀏覽器視窗）
        """
        self.headless = headless
        print("🤖 正在初始化 OCR 引擎（首次執行可能需要下載模型，請稍候）...")
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        print("✅ OCR 引擎初始化完成")
        self.playwright = None
        self.browser = None
        self.page = None
        
    def __enter__(self):
        """Context manager 進入"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self.close()
        
    def start(self):
        """啟動瀏覽器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        
    def close(self):
        """關閉瀏覽器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
            
    def _get_captcha_text(self) -> str:
        """
        擷取並識別驗證碼
        
        Returns:
            識別出的驗證碼文字
        """
        print("    📷 正在擷取驗證碼圖片...")
        
        # 等待驗證碼圖片載入
        time.sleep(0.5)
        
        # 使用精確的選擇器 #captcha
        captcha_img = self.page.locator('#captcha')
        captcha_img.wait_for(state="visible", timeout=5000)
        
        # 截取驗證碼圖片
        img_bytes = captcha_img.screenshot()
        print(f"    📷 圖片大小: {len(img_bytes)} bytes")
        
        # 使用 ddddocr 識別
        print("    🤖 正在識別驗證碼...")
        result = self.ocr.classification(img_bytes)
        
        return result.lower().strip()
    
    def _refresh_captcha(self):
        """刷新驗證碼"""
        self.page.locator('#btn3').click()
        time.sleep(0.5)  # 等待新驗證碼載入
    
    def _parse_roc_date(self, date_text: str) -> tuple:
        """
        解析民國年日期
        
        Args:
            date_text: 如 "114年 5月 13日" 或 "114年5月13日"
            
        Returns:
            (year, month, day) 民國年的元組，解析失敗返回 None
        """
        # 移除空白字元
        date_text = re.sub(r'\s+', '', date_text)
        
        # 使用正規表達式解析
        match = re.search(r'(\d+)年(\d+)月(\d+)日', date_text)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return (year, month, day)
        return None
    
    def _roc_to_western(self, roc_year: int, month: int, day: int) -> datetime:
        """
        將民國年轉換為西元 datetime
        
        Args:
            roc_year: 民國年
            month: 月
            day: 日
            
        Returns:
            datetime 物件
        """
        western_year = roc_year + 1911
        return datetime(western_year, month, day)
    
    def _is_within_one_year(self, roc_year: int, month: int, day: int) -> bool:
        """
        判斷日期是否在今天的一年內
        
        Args:
            roc_year: 民國年
            month: 月
            day: 日
            
        Returns:
            True 如果在一年內，否則 False
        """
        target_date = self._roc_to_western(roc_year, month, day)
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)
        
        return target_date >= one_year_ago
    
    def _extract_registration_date(self) -> tuple:
        """
        從頁面表格中提取初次登錄日期
        
        Returns:
            (year, month, day) 民國年的元組，找不到返回 None
        """
        try:
            # 取得表格內容
            table = self.page.locator('table.formStyle02')
            if table.count() == 0:
                return None
            
            # 尋找包含「初次登錄日期」的列
            rows = table.locator('tr')
            for i in range(rows.count()):
                row_text = rows.nth(i).inner_text()
                if '初次登錄日期' in row_text:
                    # 解析日期
                    return self._parse_roc_date(row_text)
            
            return None
        except Exception as e:
            print(f"    ⚠️ 提取日期時發生錯誤: {e}")
            return None
    
    def _generate_screenshot_filename(self, registration_number: str, page_content: str) -> str:
        """
        根據查詢結果生成截圖檔名
        
        Args:
            registration_number: 登錄字號
            page_content: 頁面內容
            
        Returns:
            截圖檔名
        """
        # 檢查是否有表格結果
        if 'formStyle02' not in page_content or '初次登錄日期' not in page_content:
            print("    📋 判定結果: 無效的證號（無表格資料）")
            return f"{registration_number}_無效的證號.png"
        
        # 提取初次登錄日期
        date_tuple = self._extract_registration_date()
        
        if date_tuple is None:
            print("    📋 判定結果: 無效的證號（無法解析日期）")
            return f"{registration_number}_無效的證號.png"
        
        year, month, day = date_tuple
        date_str = f"{year}_{month:02d}_{day:02d}"
        
        # 判斷是否在一年內
        is_valid = self._is_within_one_year(year, month, day)
        
        if is_valid:
            print(f"    📋 判定結果: 審核成功（初次登錄 {year}年{month}月{day}日，在一年內）")
            return f"{registration_number}_審核成功_{date_str}.png"
        else:
            print(f"    📋 判定結果: 審核失敗（初次登錄 {year}年{month}月{day}日，超過一年）")
            return f"{registration_number}_審核失敗_{date_str}.png"
        
    def query(self, registration_number: str, max_retries: int = 10) -> dict:
        """
        執行業務員登錄查詢
        
        Args:
            registration_number: 登錄字號（10位數字，例如：0113403577）
            max_retries: 最大重試次數（驗證碼錯誤時自動重試）
            
        Returns:
            查詢結果字典，包含 success, message, screenshot_path 等欄位
        """
        result = {
            "success": False,
            "registration_number": registration_number,
            "message": "",
            "screenshot_path": None,
            "attempts": 0
        }
        
        # 導航到查詢頁面
        print(f"🌐 正在前往查詢頁面...")
        self.page.goto(self.URL, wait_until="networkidle")
        print(f"✅ 頁面載入完成")
        time.sleep(1)
        
        for attempt in range(1, max_retries + 1):
            result["attempts"] = attempt
            print(f"\n📝 第 {attempt} 次嘗試...")
            
            # 識別驗證碼
            captcha_text = self._get_captcha_text()
            print(f"🔍 識別到驗證碼: {captcha_text}")
            
            # 清空並填入登錄字號
            self.page.locator('#iusr').fill('')
            self.page.locator('#iusr').fill(registration_number)
            
            # 清空並填入驗證碼
            self.page.locator('input[name="captchaAnswer"]').fill('')
            self.page.locator('input[name="captchaAnswer"]').fill(captcha_text)
            
            # 設定對話框處理（在點擊前設定）
            dialog_message = None
            def handle_dialog(dialog):
                nonlocal dialog_message
                dialog_message = dialog.message
                print(f"    💬 收到對話框: {dialog_message}")
                dialog.accept()
            
            self.page.once("dialog", handle_dialog)
            
            # 點擊查詢按鈕 (使用 #btn1)
            print("    🖱️ 點擊查詢按鈕...")
            self.page.locator('#btn1').click()
            
            # 等待回應
            time.sleep(1.5)
            
            # 檢查是否有驗證碼錯誤
            if dialog_message and "驗證碼錯誤" in dialog_message:
                print(f"❌ 驗證碼錯誤，準備重試...")
                self._refresh_captcha()
                continue
            
            # 檢查頁面是否有查詢結果
            page_content = self.page.content()
            
            if "查無資料" in page_content:
                result["success"] = True
                result["message"] = "查無此登錄字號資料"
                print(f"⚠️ 查無資料")
                break
                
            elif "登錄字號" in page_content and "所屬公司" in page_content:
                # 查詢成功，有結果
                result["success"] = True
                result["message"] = "查詢成功"
                print(f"✅ 查詢成功！")
                break
                
            elif "驗證碼錯誤" not in page_content:
                # 可能成功了，截圖確認
                result["success"] = True
                result["message"] = "查詢完成，請查看截圖確認結果"
                print(f"✅ 查詢完成")
                break
        
        # 截取結果截圖（根據查詢結果決定檔名）
        page_content = self.page.content()
        screenshot_path = self._generate_screenshot_filename(registration_number, page_content)
        self.page.screenshot(path=screenshot_path, full_page=True)
        result["screenshot_path"] = screenshot_path
        print(f"📸 截圖已儲存: {screenshot_path}")
        
        return result


def main():
    """主程式"""
    headless = "--headless" in sys.argv
    
    # 取得輸入值（從命令列參數或互動式輸入）
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    
    if args:
        # 有命令列參數，使用第一個參數
        input_value = args[0]
    else:
        # 沒有參數，互動式輸入
        print("=" * 60)
        print("業務員登錄查詢自動化工具")
        print("=" * 60)
        input_value = input("請輸入證號或是 Trello 卡片連結：").strip()
        
        if not input_value:
            print("❌ 錯誤：未輸入任何內容")
            sys.exit(1)
    
    print("=" * 60)
    print("業務員登錄查詢自動化工具")
    print("=" * 60)
    
    # 初始化 Trello 卡片 ID（用於後續回傳結果）
    trello_card_id = None
    
    # 判斷輸入是 Trello 網址還是登錄字號
    if "trello.com" in input_value.lower():
        # 從 Trello 卡片取得登錄字號
        try:
            registration_number, trello_card_id = get_registration_number_from_trello(input_value)
        except ValueError as e:
            print(f"❌ 錯誤：{e}")
            if "TRELLO_API_KEY" in str(e) or "TRELLO_TOKEN" in str(e):
                print("\n請在腳本開頭設定你的 Trello API 憑證：")
                print('  TRELLO_API_KEY = "你的API Key"')
                print('  TRELLO_TOKEN = "你的Token"')
                print("\n取得方式：https://trello.com/app-key")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Trello API 錯誤：{e}")
            sys.exit(1)
    else:
        # 直接使用輸入的登錄字號
        registration_number = input_value
        
        # 驗證輸入格式（允許 8-10 位數字）
        if not registration_number.isdigit():
            print(f"❌ 錯誤：登錄字號必須是數字")
            print(f"   您輸入的是: {registration_number}")
            sys.exit(1)
        
        if len(registration_number) < 8 or len(registration_number) > 10:
            print(f"❌ 錯誤：登錄字號必須是 8-10 位數字")
            print(f"   您輸入的是: {registration_number} ({len(registration_number)} 位)")
            sys.exit(1)
        
        # 不足 10 位自動在前面補 0
        original_number = registration_number
        if len(registration_number) < 10:
            registration_number = registration_number.zfill(10)
            print(f"ℹ️  自動補零: {original_number} → {registration_number}")
    
    print(f"📋 查詢登錄字號: {registration_number}")
    print(f"🖥️  顯示模式: {'無頭模式' if headless else '有頭模式（顯示瀏覽器）'}")
    if trello_card_id:
        print(f"🔗 Trello 卡片: {trello_card_id}（完成後將回傳結果）")
    print("=" * 60)
    
    # 執行查詢
    with LIAQueryBot(headless=headless) as bot:
        result = bot.query(registration_number)
    
    # 顯示結果
    print("\n" + "=" * 60)
    print("查詢結果")
    print("=" * 60)
    print(f"📋 登錄字號: {result['registration_number']}")
    print(f"{ '✅' if result['success'] else '❌' } 狀態: {result['message']}")
    print(f"🔄 嘗試次數: {result['attempts']}")
    print(f"📸 截圖路徑: {result['screenshot_path']}")
    print("=" * 60)
    
    # 如果是 Trello 來源，回傳結果到卡片
    if trello_card_id and result['screenshot_path']:
        try:
            # 取得檔名（不含副檔名）作為留言內容
            comment_text = Path(result['screenshot_path']).stem
            add_comment_with_attachment_to_trello(
                trello_card_id, 
                comment_text, 
                result['screenshot_path']
            )
        except Exception as e:
            print(f"⚠️ Trello 回傳失敗：{e}")
    
    return result


if __name__ == "__main__":
    main()