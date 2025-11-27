from lia_bot import LIAQueryBot

def test():
    # 使用一個範例證號 (這裡隨便填一個測試用)
    test_reg_no = "0113403577" 
    
    # 初始化機器人 (headless=True 在背景執行，您可以改成 False 看到瀏覽器跳出來)
    bot = LIAQueryBot(headless=True)
    
    try:
        bot.start()
        result = bot.perform_query(test_reg_no)
        
        print("\n" + "="*30)
        print("測試結果:")
        print(f"狀態: {result['status']}")
        print(f"訊息: {result['msg']}")
        print("="*30)
        
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        bot.close()

if __name__ == "__main__":
    test()

