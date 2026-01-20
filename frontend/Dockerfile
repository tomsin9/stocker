# Stage 1: Build Vue app
FROM node:20-alpine AS build-stage

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Vite 會根據這個指令生成 dist/ 資料夾
RUN npm run build


# Stage 2: Serve with Nginx
FROM nginx:stable-alpine AS production-stage

# 複製編譯好的靜態檔案到 Nginx 目錄
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 覆蓋 Nginx 預設設定（選用，見下方說明）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]