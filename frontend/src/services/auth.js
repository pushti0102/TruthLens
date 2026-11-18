import api from './api';

export const authService = {
  async login(email, password) {
    const res = await api.post('/api/auth/login', {
      email: email.trim(),
      password: password,
    });
    return res.data; // { access_token, token_type, role, email, full_name }
  },

  async register(email, password, full_name, role) {
    const res = await api.post('/api/auth/register', { email, password, full_name, role });
    return res.data;
  },

  async getMe() {
    const res = await api.get('/api/auth/me');
    return res.data;
  },

  logout() {
    localStorage.removeItem('tl_token');
    localStorage.removeItem('tl_user');
  },
};
