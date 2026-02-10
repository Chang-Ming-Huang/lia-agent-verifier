import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

def create_app():
    app = Flask(__name__)

    # REST API — 永遠載入（production 必要）
    from api_flow import api_bp
    app.register_blueprint(api_bp)

    # 實驗用模組 — 僅在 staging 環境載入
    if os.environ.get('FLASK_ENV') == 'staging':
        from trello_flow import trello_bp
        from web_flow import web_bp
        app.register_blueprint(trello_bp)
        app.register_blueprint(web_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
