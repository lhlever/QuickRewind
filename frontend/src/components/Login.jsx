import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const Login = ({ onToggleForm }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { login } = useAuth();

  // 处理输入变化
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    // 清除对应字段的错误
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: ''
      });
    }
  };

  // 表单验证
  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.username.trim()) {
      newErrors.username = '请输入用户名';
    }
    
    if (!formData.password) {
      newErrors.password = '请输入密码';
    } else if (formData.password.length < 6) {
      newErrors.password = '密码长度至少为6位';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const result = await login(formData.username, formData.password);
      
      if (!result.success) {
        setErrors({ form: result.error });
      }
      // 登录成功后，AuthProvider会自动处理状态更新
    } catch (error) {
      setErrors({ form: '登录失败，请稍后重试' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      {errors.form && (
        <div className="auth-error">{errors.form}</div>
      )}
      
      <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username" className="form-label">用户名</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className={`form-input ${errors.username ? 'error' : ''}`}
              placeholder="请输入用户名"
              disabled={isSubmitting}
            />
            {errors.username && (
              <div className="error-message">{errors.username}</div>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="password" className="form-label">密码</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className={`form-input ${errors.password ? 'error' : ''}`}
              placeholder="请输入密码"
              disabled={isSubmitting}
            />
            {errors.password && (
              <div className="error-message">{errors.password}</div>
            )}
          </div>
          
          <button 
            type="submit" 
            className="auth-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? '登录中...' : '登录'}
          </button>
        </form>
        
        <div className="auth-footer">
          <p>
            还没有账号？ 
            <button 
              type="button" 
              className="link-button"
              onClick={onToggleForm}
            >
              立即注册
            </button>
          </p>
        </div>
    </div>
  );
};

export default Login;