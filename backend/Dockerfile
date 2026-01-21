# backend/Dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (Postgres client 需要)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_base.txt .
RUN pip install --no-cache-dir -r requirements_base.txt

# 複製程式碼 (雖然 Compose 會 mount volume，但 build 時複製一份是好習慣)
COPY . .

# 如果你在 Windows 上編輯過 entrypoint.sh，沒有這行在 VPS 可能會報 "file not found"
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh

# 處理 entrypoint.sh 的權限
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]