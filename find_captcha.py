from playwright.sync_api import sync_playwright

def run():
    target_url = "https://public.liaroc.org.tw/lia-public/DIS/Servlet/RD?returnUrl=..%2F..%2FindexUsr.jsp&xml=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22BIG5%22%3F%3E%3CRoot%3E%3CForm%3E%3CreturnUrl%3E..%2F..%2FindexUsr.jsp%3C%2FreturnUrl%3E%3Cxml%2F%3E%3Cfuncid%3EPGQ010++++++++++++++++++++++++%3C%2Ffuncid%3E%3CprogId%3EPGQ010S01%3C%2FprogId%3E%3C%2FForm%3E%3C%2FRoot%3E&funcid=PGQ010++++++++++++++++++++++++&progId=PGQ010S01"

    with sync_playwright() as p:
        print("正在啟動瀏覽器...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"正在前往目標網頁...")
        page.goto(target_url)
        
        print("正在搜尋所有圖片...")
        images = page.query_selector_all("img")
        
        print(f"找到 {len(images)} 張圖片：\n")
        
        for i, img in enumerate(images):
            src = img.get_attribute("src")
            img_id = img.get_attribute("id")
            img_class = img.get_attribute("class")
            alt = img.get_attribute("alt")
            
            print(f"圖片 #{i+1}:")
            print(f"  - ID: {img_id}")
            print(f"  - Class: {img_class}")
            print(f"  - Src: {src}")
            print(f"  - Alt: {alt}")
            print("-" * 30)
            
        browser.close()

if __name__ == "__main__":
    run()
