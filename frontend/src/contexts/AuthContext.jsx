import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService } from '../services/auth';

// 创建认证上下文
const AuthContext = createContext();

// 自定义Hook，用于使用认证上下文
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// 认证提供者组件
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // 初始化时检查本地存储中的token
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // 验证token并获取用户信息
          const userData = await authService.getCurrentUser();
          setUser(userData);
          setIsAuthenticated(true);
        } catch (error) {
          console.error('Token验证失败:', error);
          // 清除无效token
          localStorage.removeItem('token');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  // 登录函数
  const login = async (username, password) => {
    try {
      const response = await authService.login(username, password);
      const { access_token } = response;
      
      // 保存token到本地存储
      localStorage.setItem('token', access_token);
      
      // 获取用户信息
      const userData = await authService.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);
      
      return { success: true };
    } catch (error) {
      console.error('登录失败:', error);
      return { 
        success: false, 
        error: error.message || '登录失败，请检查用户名和密码' 
      };
    }
  };

  // 注册函数
  const register = async (userData) => {
    try {
      await authService.register(userData);
      return { success: true };
    } catch (error) {
      console.error('注册失败:', error);
      return { 
        success: false, 
        error: error.message || '注册失败，请稍后重试' 
      };
    }
  };

  // 登出函数
  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('登出请求失败:', error);
    } finally {
      // 无论请求是否成功，都清除本地状态
      localStorage.removeItem('token');
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  // 提供的值
  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    register,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;