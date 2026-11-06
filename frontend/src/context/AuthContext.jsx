import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi, shopApi } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('shopfaq_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [shop, setShop] = useState(() => {
    const saved = localStorage.getItem('shopfaq_shop');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('shopfaq_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const res = await authApi.me();
          if (res.data?.success) {
            setUser(res.data.data.user);
            setShop(res.data.data.shop);
            localStorage.setItem('shopfaq_user', JSON.stringify(res.data.data.user));
            localStorage.setItem('shopfaq_shop', JSON.stringify(res.data.data.shop));
          }
        } catch (err) {
          console.error("Auth validation failed", err);
          logout();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [token]);

  const login = async (email, password) => {
    const res = await authApi.login({ email, password });
    if (res.data?.success) {
      const { token: newToken, user: newUser, shop: newShop } = res.data.data;
      setToken(newToken);
      setUser(newUser);
      setShop(newShop);
      localStorage.setItem('shopfaq_token', newToken);
      localStorage.setItem('shopfaq_user', JSON.stringify(newUser));
      localStorage.setItem('shopfaq_shop', JSON.stringify(newShop));
      return { success: true };
    }
    return { success: false, message: res.data?.message || 'Login failed' };
  };

  const register = async (payload) => {
    const res = await authApi.register(payload);
    if (res.data?.success) {
      const { token: newToken, user: newUser, shop: newShop } = res.data.data;
      setToken(newToken);
      setUser(newUser);
      setShop(newShop);
      localStorage.setItem('shopfaq_token', newToken);
      localStorage.setItem('shopfaq_user', JSON.stringify(newUser));
      localStorage.setItem('shopfaq_shop', JSON.stringify(newShop));
      return { success: true };
    }
    return { success: false, message: res.data?.message || 'Registration failed' };
  };

  const refreshShopProfile = async () => {
    try {
      const res = await shopApi.getProfile();
      if (res.data?.success) {
        setShop(res.data.data);
        localStorage.setItem('shopfaq_shop', JSON.stringify(res.data.data));
      }
    } catch (err) {
      console.error("Failed to refresh shop profile", err);
    }
  };

  const logout = () => {
    try {
      authApi.logout();
    } catch (e) {
      // ignore
    }
    setToken(null);
    setUser(null);
    setShop(null);
    localStorage.removeItem('shopfaq_token');
    localStorage.removeItem('shopfaq_user');
    localStorage.removeItem('shopfaq_shop');
  };

  return (
    <AuthContext.Provider value={{
      user,
      shop,
      token,
      loading,
      isAuthenticated: !!token && !!user,
      login,
      register,
      logout,
      refreshShopProfile
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

