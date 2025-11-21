// 认证相关的API服务

// API基础URL
const API_BASE_URL = 'http://localhost:8000';

// 通用请求函数
const request = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  // 获取本地存储的token
  const token = localStorage.getItem('token');
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      // 尝试获取响应中的错误信息
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorResponse = await response.json();
        if (errorResponse.detail) {
          errorMessage = errorResponse.detail;
        }
      } catch (e) {
        // 如果响应不是JSON格式，使用默认错误信息
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

// 认证服务对象
export const authService = {
  // 用户登录
  login: async (username, password) => {
    try {
      const response = await request('/api/v1/auth/login/json', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      return response;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  },

  // 用户注册
  register: async (userData) => {
    try {
      const response = await request('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify(userData),
      });
      return response;
    } catch (error) {
      console.error('注册失败:', error);
      throw error;
    }
  },

  // 获取当前用户信息
  getCurrentUser: async () => {
    try {
      const response = await request('/api/v1/auth/me');
      return response;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  },

  // 用户登出
  logout: async () => {
    try {
      const response = await request('/api/v1/auth/logout', {
        method: 'POST',
      });
      return response;
    } catch (error) {
      console.error('登出失败:', error);
      throw error;
    }
  }
};