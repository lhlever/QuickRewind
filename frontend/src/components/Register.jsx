import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const Register = ({ onToggleForm }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    full_name: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { register } = useAuth();

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
    } else if (formData.username.length < 3) {
      newErrors.username = '用户名长度至少为3位';
    }
    
    if (!formData.full_name.trim()) {
      newErrors.full_name = '请输入姓名';
    }
    
    if (!formData.password) {
      newErrors.password = '请输入密码';
    } else if (formData.password.length < 6) {
      newErrors.password = '密码长度至少为6位';
    }
    
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = '请确认密码';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
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
      const { confirmPassword, ...userData } = formData;
      const result = await register(userData);
      
      if (!result.success) {
        setErrors({ form: result.error });
      } else {
        // 注册成功，切换到登录表单
        setErrors({});
        onToggleForm();
        // 可以添加一个成功提示
        alert('注册成功！请登录');
      }
    } catch (error) {
      setErrors({ form: '注册失败，请稍后重试' });
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
              placeholder="请输入用户名（至少3位）"
              disabled={isSubmitting}
            />
            {errors.username && (
              <div className="error-message">{errors.username}</div>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="full_name" className="form-label">姓名</label>
            <input
              type="text"
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              className={`form-input ${errors.full_name ? 'error' : ''}`}
              placeholder="请输入您的姓名"
              disabled={isSubmitting}
            />
            {errors.full_name && (
              <div className="error-message">{errors.full_name}</div>
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
              placeholder="请输入密码（至少6位）"
              disabled={isSubmitting}
            />
            {errors.password && (
              <div className="error-message">{errors.password}</div>
            )}
          </div>
          
          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">确认密码</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
              placeholder="请再次输入密码"
              disabled={isSubmitting}
            />
            {errors.confirmPassword && (
              <div className="error-message">{errors.confirmPassword}</div>
            )}
          </div>
          
          <button 
            type="submit" 
            className="auth-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? '注册中...' : '注册'}
          </button>
        </form>
        
        <div className="auth-footer">
          <p>
            已有账号？ 
            <button 
              type="button" 
              className="link-button"
              onClick={onToggleForm}
            >
              立即登录
            </button>
          </p>
        </div>
    </div>
  );
};

export default Register;