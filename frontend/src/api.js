import axios from 'axios';

const api = axios.create({
  baseURL: '/', // 因為 Nginx 已經幫我們處理了 /api/ 路徑
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
      localStorage.removeItem('access_token');
      window.location.href = '/login'; // 強制跳回登入頁
    }
    return Promise.reject(error);
  }
);

export default api;