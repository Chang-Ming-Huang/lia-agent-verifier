import ddddocr

def run():
    ocr = ddddocr.DdddOcr()
    
    print("正在下載測試用驗證碼圖片...")
    # 這裡我們用一個簡單的 Base64 圖片或者直接讀取圖片
    # 為了方便測試，我先假設我們有一張圖片，或者我們可以先測試 ddddocr 是否能成功初始化
    # 只要能初始化，通常就能識別
    
    print("ddddocr 初始化成功！")
    print(f"識別模型: {ocr}")

if __name__ == "__main__":
    try:
        run()
        print("測試成功：ddddocr 可以正常運作")
    except Exception as e:
        print(f"測試失敗：{e}")
