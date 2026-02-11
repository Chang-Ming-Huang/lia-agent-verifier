# 使用官方 Playwright 映像檔 (包含 Python 環境與瀏覽器依賴)
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# 設定工作目錄
WORKDIR /app

# 安裝 ddddocr 所需的額外系統依賴
# Playwright 映像檔是基於 Ubuntu (jammy)，所以使用 apt-get
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt 並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Chromium 瀏覽器
RUN playwright install chromium

# 複製所有程式碼到工作目錄
COPY . .

# 設定環境變數 (防止 Python 產生 .pyc 檔)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# 啟動 Gunicorn 伺服器
# Render 會自動提供 PORT 環境變數，我們讓 Gunicorn 監聽該 Port
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 app:app"]
