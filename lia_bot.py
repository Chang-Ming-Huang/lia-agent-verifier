from playwright.sync_api import sync_playwright
import ddddocr
import time
import re
from datetime import datetime, timedelta
from pathlib import Path # 引入 Path 模組

class LIAQueryBot:
    """壽險公會業務員登錄查詢機器人 (核心邏輯)"""
    
    URL = (
        "https://public.liaroc.org.tw/lia-public/DIS/Servlet/RD?"
        "returnUrl=..%2F..%2FindexUsr.jsp&xml=%3C%3Fxml+version%3D%221.0%22+"
        "encoding%3D%22BIG5%22%3F%3E%3CRoot%3E%3CForm%3E%3CreturnUrl%3E"
        "..%2F..%2FindexUsr.jsp%3C%2FreturnUrl%3E%3Cxml%2F%3E%3Cfuncid%3E"
        "PGQ010++++++++++++++++++++++++%3C%2Ffuncid%3E%3CprogId%3EPGQ010S01"
        "%3C%2FprogId%3E%3C%2FForm%3E%3C%2FRoot%3E&funcid="
        "PGQ010++++++++++++++++++++++++&progId=PGQ010S01"
    )
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        print("初始化 OCR 引擎...")
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.playwright = None
        self.browser = None
        self.page = None
        
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
        """擷取並識別驗證碼"""
        # 等待圖片載入
        time.sleep(1)
        element = self.page.locator('#captcha')
        element.wait_for(state="visible")
        
        # 截圖並識別
        img_bytes = element.screenshot()
        result = self.ocr.classification(img_bytes)
        print(f"    識別驗證碼: {result}")
        return result.lower().strip()

    def _refresh_captcha(self):
        """點擊刷新驗證碼"""
        print("    刷新驗證碼...")
        self.page.locator('#btn3').click()
        time.sleep(1)
    
    def _parse_roc_date(self, date_text: str) -> tuple:
        """
        解析民國年日期
        Args:
            date_text: 如 "114年 5月 13日" 或 "114年5月13日"
        Returns:
            (year, month, day) 民國年的元組，解析失敗返回 None
        """
        # 清理多餘空白
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
        """
        western_year = roc_year + 1911
        return datetime(western_year, month, day)
    
    def _is_within_one_year(self, roc_year: int, month: int, day: int) -> bool:
        """
        判斷日期是否在今天的一年內
        """
        target_date = self._roc_to_western(roc_year, month, day)
        today = datetime.now()
        one_year_ago = today - timedelta(days=365) # 近一年
        
        return target_date >= one_year_ago
    
    def _extract_registration_date(self) -> tuple:
        """
        從頁面表格中提取初次登錄日期
        """
        try:
            # 取得表格內容
            table = self.page.locator('table.formStyle02')
            if table.count() == 0:
                print("    找不到 formStyle02 表格")
                return None
            
            # 尋找包含「初次登錄日期」的列
            rows = table.locator('tr')
            for i in range(rows.count()):
                row_text = rows.nth(i).inner_text()
                if '初次登錄日期' in row_text:
                    # 解析日期
                    return self._parse_roc_date(row_text)
            
            print("    找不到初次登錄日期")
            return None
        except Exception as e:
            print(f"    提取日期時發生錯誤: {e}")
            return None
            
    def _generate_screenshot_filename(self, registration_number: str, result_status: str) -> str:
        """
        根據查詢結果生成截圖檔名
        """
        base_name = f"{registration_number}"
        
        if result_status == "not_found":
            return f"{base_name}_查無資料.png"
        elif result_status == "found_valid":
            date_tuple = self._extract_registration_date()
            if date_tuple:
                year, month, day = date_tuple
                date_str = f"{year}_{month:02d}_{day:02d}"
                return f"{base_name}_審核通過_{date_str}.png"
            else:
                return f"{base_name}_審核通過_日期未知.png"
        elif result_status == "found_invalid":
            date_tuple = self._extract_registration_date()
            if date_tuple:
                year, month, day = date_tuple
                date_str = f"{year}_{month:02d}_{day:02d}"
                return f"{base_name}_資格不符_{date_str}.png"
            else:
                return f"{base_name}_資格不符_日期未知.png"
        else: # unknown 或 error
            return f"{base_name}_無效證號.png"

    def _generate_email_template(self, status: str) -> dict:
        """根據狀態生成回信範本"""
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)
        # 格式化為 "113年5月13日" (民國年)
        one_year_ago_str = f"{one_year_ago.year - 1911}年{one_year_ago.month}月{one_year_ago.day}日"

        templates = {
            "found_valid": {
                "subject": "Finfo 年繳方案付款通知 (審核通過，提供您刷卡升級連結)",
                "body": f"""您好,

這裡是 Finfo 客服團隊的審核專員，我會協助您這次的年繳方案申請，感謝您申請年繳方案。
我們已確認您符合優惠資格，以下是您的付款連結：

[粗體文字：TODO，附上付款連結]

請於三天內完成付款 (付款連結將於三天後失效)。
收到款項後的一個工作天內，我們會為您升級帳號權限，並再次以 Email 通知您。

如有任何問題，隨時回覆此信與我們聯繫。

Finfo 客服團隊 敬上"""
            },
            "found_invalid": {
                "subject": "Finfo 有收到您的年繳方案申請，您並非一年內的新進業務，可考慮月繳方案",
                "body": f"""您好,

這裡是 Finfo 客服團隊的審核專員，感謝您申請年繳方案。

目前年繳方案屬於測試階段，第一階段先開放給新進一年的業務員。

也就是要在 {one_year_ago_str} 之後登錄的新進業務員，會是這次新進業務年繳方案的測試對象。

根據您提供的資料，您的登錄日期是比較早期的，不符合針對新進業務的資格，不好意思。

若您對年繳方案有興趣，可以等之後 Finfo 正式推出年繳方案後再填寫即可，感謝您的來信申請。

Finfo 客服團隊 敬上"""
            },
            "not_found": {
                "subject": "Finfo 有收到您的年繳方案申請，想詢問您的登錄證字號",
                "body": """您好,

這裡是 Finfo 客服團隊的審核專員，感謝您申請年繳方案。
根據您提供的登錄證字號，於 壽險公會 無法查詢到資格，
請再次確認提供的資料是否正確，再次感謝您的申請與支持。

如有任何問題，隨時回覆此信與我們聯繫。

如果有其他任何網站上的操作問題，也都歡迎您在此封信件中一併提出，我們會盡快協助，感謝您！

Finfo 客服團隊 敬上"""
            }
        }
        
        # 預設回傳 not_found 的模板
        if status in templates:
            return templates[status]
        else:
            return templates["not_found"]

    def perform_query(self, reg_no: str, max_retries=5):
        """執行查詢動作 (含驗證碼重試機制)"""
        final_result = {
            "success": False,
            "status": "error",
            "msg": "未完成查詢",
            "screenshot_path": None,
            "email_info": None
        }

        print(f"前往查詢頁面: {reg_no}")
        self.page.goto(self.URL, wait_until='domcontentloaded')
        
        for attempt in range(1, max_retries + 1):
            print(f"第 {attempt} 次嘗試...")
            
            # 1. 識別驗證碼
            captcha_text = self._get_captcha_text()
            
            # 2. 填寫表單
            self.page.locator('#iusr').fill(reg_no)
            self.page.locator('input[name="captchaAnswer"]').fill(captcha_text)
            
            # 3. 處理 Alert 對話框
            dialog_message = None
            def handle_dialog(dialog):
                nonlocal dialog_message
                dialog_message = dialog.message
                print(f"    攔截到對話框: {dialog_message}")
                dialog.accept()
            
            self.page.once("dialog", handle_dialog)
            
            # 4. 點擊查詢
            self.page.locator('#btn1').click()
            
            # 等待處理結果
            self.page.wait_for_load_state('networkidle')
            time.sleep(1)
            
            # 5. 判斷結果
            if dialog_message and "驗證碼錯誤" in dialog_message:
                print("    驗證碼錯誤，重試中...")
                self._refresh_captcha()
                dialog_message = None
                continue

            if dialog_message and "查無資料" in dialog_message:
                final_result.update({"success": True, "status": "not_found", "msg": "查無此登錄字號資料"})
                break
            
            # 檢查頁面內容
            page_content = self.page.content()
            
            if "查無資料" in page_content:
                final_result.update({"success": True, "status": "not_found", "msg": "查無此登錄字號資料"})
                break
                
            elif "formStyle02" in page_content and "初次登錄日期" in page_content:
                date_tuple = self._extract_registration_date()
                if date_tuple:
                    year, month, day = date_tuple
                    if self._is_within_one_year(year, month, day):
                        final_result.update({"success": True, "status": "found_valid", "msg": f"審核成功（初次登錄 {year}年{month}月{day}日，在一年內）", "date": f"{year}_{month:02d}_{day:02d}"})
                    else:
                        final_result.update({"success": True, "status": "found_invalid", "msg": f"審核失敗（初次登錄 {year}年{month}月{day}日，超過一年）", "date": f"{year}_{month:02d}_{day:02d}"})
                else:
                    final_result.update({"success": True, "status": "found_undetermined", "msg": "找到資料但無法解析日期"})
                break
            
            final_result.update({"success": True, "status": "unknown", "msg": "表單已送出，無明確結果或非預期頁面"})
            break
        
        # 截取最終結果頁面 (記憶體截圖)
        if final_result["success"]:
            suggested_filename = self._generate_screenshot_filename(reg_no, final_result["status"])
            # 截取最終結果頁面 (記憶體截圖)，只截取頁面上方 60%
            page_height = self.page.evaluate("document.body.scrollHeight")
            clip_height = page_height * 0.6 # 截取 60% 的高度

            screenshot_bytes = self.page.screenshot(
                clip={"x": 0, "y": 0, "width": self.page.viewport_size['width'], "height": clip_height}
            )
            
            final_result["screenshot_bytes"] = screenshot_bytes
            final_result["suggested_filename"] = suggested_filename
            print(f"截圖已擷取 (記憶體中), 建議檔名: {suggested_filename}")

        # 生成 Email 範本
        final_result["email_info"] = self._generate_email_template(final_result["status"])

        return final_result