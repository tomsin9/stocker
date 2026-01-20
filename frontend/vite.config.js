// frontend/vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  // 載入環境變數 (從專案根目錄或 frontend 目錄)
  const env = loadEnv(mode, process.cwd(), '');
  
  // 處理 ALLOWED_HOSTS 字串轉陣列
  const allowedHosts = env.VITE_ALLOWED_HOSTS 
    ? env.VITE_ALLOWED_HOSTS.split(',') 
    : ['localhost'];

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 8082,
      // 關鍵：加入從 .env 讀取的允許名單
      allowedHosts: allowedHosts,
      // 為了在 Docker 內能即時監控檔案變化
      watch: {
        usePolling: true,
      }
    },
  }
})