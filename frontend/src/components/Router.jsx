import React, { useState, useEffect } from 'react';
import AuthPage from './AuthPage';
import { useAuth } from '../contexts/AuthContext';

// 这里应该导入你的主应用页面组件
// import MainApp from './MainApp';

const Router = () => {
  const { user, loading } = useAuth();
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  // 监听路由变化
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // 简单的导航函数
  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  // 加载中状态
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }

  // 如果用户未登录，显示认证页面
  if (!user) {
    return <AuthPage />;
  }

  // 用户已登录，根据路径显示不同页面
  // 这里暂时只显示一个简单的已登录状态页面
  // 实际应用中应该根据路径显示不同的组件
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>QuickRewind</h1>
        <nav>
          <button onClick={() => navigate('/dashboard')}>仪表盘</button>
          <button onClick={() => navigate('/videos')}>视频管理</button>
          <button onClick={() => navigate('/profile')}>个人资料</button>
          <button onClick={() => {
            // 这里应该调用登出函数
            localStorage.removeItem('token');
            window.location.reload();
          }}>登出</button>
        </nav>
      </header>
      
      <main className="app-main">
        {currentPath === '/dashboard' && (
          <div className="dashboard">
            <h2>仪表盘</h2>
            <p>欢迎, {user.username}!</p>
            {/* 这里应该是仪表盘内容 */}
          </div>
        )}
        
        {currentPath === '/videos' && (
          <div className="videos">
            <h2>视频管理</h2>
            <p>这里将显示视频列表和管理功能</p>
            {/* 这里应该是视频管理内容 */}
          </div>
        )}
        
        {currentPath === '/profile' && (
          <div className="profile">
            <h2>个人资料</h2>
            <p>用户名: {user.username}</p>
            <p>邮箱: {user.email}</p>
            {/* 这里应该是个人资料编辑功能 */}
          </div>
        )}
        
        {/* 默认显示仪表盘 */}
        {currentPath === '/' && (
          <div className="dashboard">
            <h2>仪表盘</h2>
            <p>欢迎, {user.username}!</p>
            {/* 这里应该是仪表盘内容 */}
          </div>
        )}
      </main>
      
      {/* app-footer已移除 */}
    </div>
  );
};

export default Router;