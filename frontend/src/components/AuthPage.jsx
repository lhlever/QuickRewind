import React, { useState } from 'react';
import Login from './Login';
import Register from './Register';
import './Auth.css';

const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);

  const toggleForm = () => {
    setIsLogin(!isLogin);
  };

  return (
    <div className="auth-page">
      <div className="auth-content">
        <div className="auth-form-container">
          <div className="auth-logo">
            <h1>QuickRewind</h1>
            <p>视频内容分析和智能检索平台</p>
          </div>
          
          {isLogin ? (
            <Login onToggleForm={toggleForm} />
          ) : (
            <Register onToggleForm={toggleForm} />
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthPage;