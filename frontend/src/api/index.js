import axios from 'axios';
import { useAuthStore } from '../stores/auth';
import { ElMessage } from 'element-plus';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1/',
  timeout: 300000, // 增加到 5分钟 以支持超大数据集导入
});

// Request Interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const authStore = useAuthStore();
    if (error.response) {
      if (error.response.status === 401) {
        // Avoid redirect loop if already on login page or if it's a login attempt failure
        if (!window.location.pathname.includes('/login') && !error.config.url.includes('/auth/login/')) {
            authStore.logout();
            window.location.href = '/login';
        }
      } else {
        ElMessage.error(error.response.data.error || 'Request failed');
      }
    }
    return Promise.reject(error);
  }
);

export default api;
