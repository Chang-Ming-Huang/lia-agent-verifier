from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, World! 這是從 Render 佈署前的本機測試。"

if __name__ == '__main__':
    app.run(debug=True)
