from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    # 嘗試讀取名為 'MY_NAME' 的環境變數，如果讀不到，預設值就是 'Guest'
    user_name = os.environ.get('MY_NAME', 'Guest')
    return f"Hello, {user_name}! 這是一個使用環境變數的測試。"

if __name__ == '__main__':
    app.run(debug=True)