from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Render! 這是自動佈署的成果！"

if __name__ == '__main__':
    app.run(debug=True)
