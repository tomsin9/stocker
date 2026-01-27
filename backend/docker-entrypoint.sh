#!/bin/bash

# 1. 收集靜態檔案 (Static files)
# 這會把所有 App 的靜態資源集中到 STATIC_ROOT 資料夾，供 Nginx 使用
# echo "Collect static files"
# python manage.py collectstatic --noinput --clear --verbosity 3

# 2. 執行資料庫遷移 (Database migrations)
# 確保資料庫 Table 與 Models 同步
echo "Apply database migrations"
python manage.py migrate --noinput

# 2. 啟動 Gunicorn 伺服器
# 注意：靜態文件已在 Docker 構建階段收集完成
# 注意：這裡將 tom_website.wsgi 改成了 stocker.wsgi
echo "Starting server with Gunicorn"
exec gunicorn stocker.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -