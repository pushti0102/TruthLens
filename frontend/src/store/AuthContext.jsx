import { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('tl_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      authService
        .getMe()
        .then((u) => setUser(u))
        .catch(() => {
          setToken(null);
          localStorage.removeItem('tl_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    const data = await authService.login(email, password);
    localStorage.setItem('tl_token', data.access_token);
    setToken(data.access_token);
    const userInfo = {
      email: data.email,
      full_name: data.full_name,
      role: data.role,
    };
    setUser(userInfo);
    try {
      const fullUser = await authService.getMe();
      setUser(fullUser);
      return fullUser;
    } catch {
      return userInfo;
    }
  };

  const register = async (email, password, full_name, role) => {
    const data = await authService.register(email, password, full_name, role);
    return data;
  };

  const logout = () => {
    authService.logout();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
