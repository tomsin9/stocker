# backend/Dockerfile
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (Postgres client 需要)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼 (雖然 Compose 會 mount volume，但 build 時複製一份是好習慣)
COPY . .

# 處理 entrypoint.sh 的權限
RUN chmod +x /app/docker-entrypoint.sh

# 使用 entrypoint.sh 啟動
ENTRYPOINT ["/app/docker-entrypoint.sh"]