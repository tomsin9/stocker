// frontend/vite.config.js
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  // 載入環境變數 (從專案根目錄或 frontend 目錄)
  const env = loadEnv(mode, process.cwd(), '');
  
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
      // 如需從其他裝置存取，可改為 '0.0.0.0'（會觸發瀏覽器權限提示）
      host: process.env.VITE_DEV_HOST || 'localhost',
      port: 8082,
      allowedHosts: allowedHosts,
      watch: {
        usePolling: true,
      }
    },
  }
})