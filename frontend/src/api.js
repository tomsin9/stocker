import axios from 'axios';

// API 連線設定
// 開發環境：Vite Proxy 會自動將 /api 轉發到 http://localhost:8000
// 生產環境：Nginx 會將 /api 轉發到後端
// 因此無論開發或生產環境，都只需要使用 '/api' 即可
const api = axios.create({
  baseURL: '/api',
});

// 請求攔截器：自動加上 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// 響應攔截器：處理 Token 過期 (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // 檢查當前是否在登入頁，如果是則不跳轉（讓登入頁自己處理錯誤）
      const isLoginPage = window.location.pathname === '/login' || window.location.pathname === '/login/'
      if (!isLoginPage) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login'; // 強制跳回登入頁
      }
    }
    return Promise.reject(error);
  }
);

export default api;