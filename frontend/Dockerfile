# frontend/Dockerfile
FROM node:22-alpine

WORKDIR /app

# 複製 package 設定
COPY package*.json ./

# 安裝依賴
RUN npm install

# 複製其餘檔案
COPY . .

# 開放 Vite 預設 port
EXPOSE 8082

# 啟動開發伺服器 (--host 0.0.0.0 是為了讓 Docker 外部能訪問)
CMD ["npm", "run", "dev", "--", "--host"]