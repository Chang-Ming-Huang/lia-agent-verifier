from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        print("正在啟動瀏覽器...")
        # headless=True 表示不顯示視窗，這是伺服器環境必須的設定
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("正在前往 example.com ...")
        page.goto("https://example.com")
        
        title = page.title()
        print(f"網頁標題是: {title}")
        
        print("正在截圖...")
        page.screenshot(path="example.png")
        
        browser.close()
        print("完成！請檢查資料夾中是否有 example.png")

if __name__ == "__main__":
    run()
