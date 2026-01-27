# Stage 1: Build Vue app
FROM node:20-alpine AS build-stage

WORKDIR /app

# 接受構建參數（用於環境變數）
ARG VITE_ALLOWED_HOSTS
ARG VITE_DJANGO_HOST

# 設置環境變數（Vite 在構建時會讀取 VITE_* 開頭的環境變數）
ENV VITE_ALLOWED_HOSTS=${VITE_ALLOWED_HOSTS} \
    VITE_DJANGO_HOST=${VITE_DJANGO_HOST}

# 先複製 package 文件，利用 Docker 緩存層
COPY package*.json ./

# 安裝所有依賴（包括 devDependencies，構建需要）
RUN npm ci && \
    npm cache clean --force

# 複製源碼
COPY . .

# 構建應用並清理
RUN npm run build && \
    npm cache clean --force && \
    rm -rf node_modules

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine AS production-stage

# 複製編譯好的靜態檔案到 Nginx 目錄
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 覆蓋 Nginx 預設設定（選用，見下方說明）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]