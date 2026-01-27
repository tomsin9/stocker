# Stage 1: Build stage - 安裝依賴（需要編譯工具）
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安裝編譯工具（只在構建階段需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 建立虛擬環境並確保之後的 pip 裝入去
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安裝 Python 依賴到 /usr/local（系統路徑）
COPY requirements_base.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements_base.txt

# 複製程式碼並收集靜態文件
COPY . .
ENV DJANGO_SETTINGS_MODULE=stocker.settings
RUN python manage.py collectstatic --noinput --clear || true

# Stage 2: Runtime stage - 只保留運行時需要的
FROM python:3.12-slim

# 1. 建立一個系統用戶 (appuser)，唔畀佢有 login 權限以增加安全性
RUN useradd --create-home --shell /bin/bash appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 只安裝運行時需要的系統依賴（不需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 複製編譯好的 Python 包
COPY --from=builder /opt/venv /opt/venv

# 從構建階段複製已收集的靜態文件
RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles
COPY --from=builder /app/staticfiles /app/staticfiles

# 確保 public 同 static 資料夾存在，並且 appuser 有權讀寫
RUN mkdir -p /app/public /app/staticfiles && \
    chown -R appuser:appuser /app/public /app/staticfiles

# 如果你有用 SQLite，連個 DB file 或者資料夾都要改權限
# RUN chown appuser:appuser /app/db.sqlite3 || true

# 4. 複製 Entrypoint 同 Source code，並將擁有者設為 appuser
COPY --chown=appuser:appuser docker-entrypoint.sh .
RUN sed -i 's/\r$//' docker-entrypoint.sh && \
    chmod +x docker-entrypoint.sh

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/public && chown -R appuser:appuser /app/public

# 5. 切換到該用戶執行
USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]