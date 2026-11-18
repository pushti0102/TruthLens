import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || (typeof window !== 'undefined' && (window.location.port === '5173' || window.location.port === '5174') ? '' : 'http://127.0.0.1:8000');

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 180000,
});

// Inject JWT token on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tl_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('tl_token');
      localStorage.removeItem('tl_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
