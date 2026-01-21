// frontend/vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { readFileSync } from 'fs'

export default defineConfig(({ mode }) => {
  // 載入環境變數 (從專案根目錄或 frontend 目錄)
  const env = loadEnv(mode, process.cwd(), '');
  
  // 讀取 package.json 版本號（用於注入到環境變數）
  let packageVersion = '0.0.0'
  try {
    const packageJson = JSON.parse(readFileSync(path.resolve(__dirname, 'package.json'), 'utf-8'))
    packageVersion = packageJson.version || '0.0.0'
  } catch (e) {
    console.warn('Could not read package.json version:', e)
  }
  
  const allowedHosts = env.VITE_ALLOWED_HOSTS 
    ? env.VITE_ALLOWED_HOSTS.split(',') 
    : ['localhost'];

  // 可選：如果需要連接到不同的後端地址
  // 在 .env 文件中設置：VITE_DJANGO_HOST=http://localhost:8002 或 https://stocker.tomsinp.com
  const djangoHost = env.VITE_DJANGO_HOST || 'http://localhost:8000';
  
  // 判斷是否為 HTTPS
  const isHttps = djangoHost.startsWith('https://');
  // 可選：如果遇到 SSL 證書錯誤，在 .env 中設置 VITE_PROXY_SECURE=false
  const proxySecure = env.VITE_PROXY_SECURE !== 'false';

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    define: {
      // 注入 package.json 版本號到應用程式
      'import.meta.env.PACKAGE_VERSION': JSON.stringify(packageVersion),
    },
    server: {
      // 如需從其他裝置存取，可改為 '0.0.0.0'（會觸發瀏覽器權限提示）
      host: process.env.VITE_DEV_HOST || 'localhost',
      port: 8082,
      allowedHosts: allowedHosts,
      watch: {
        usePolling: true,
      },
      // Vite Proxy: 開發環境自動將 /api 請求轉發到後端
      proxy: {
        '/api': {
          target: djangoHost,
          changeOrigin: true,
          secure: isHttps ? proxySecure : false, // HTTPS 後端時驗證 SSL 證書（可通過 VITE_PROXY_SECURE=false 禁用）
          // 可選：如果需要重寫路徑
          // rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },
  }
})