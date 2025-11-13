import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import RouterWithAuth from './components/Router_with_auth';
import './App.css';

// 这是一个包装了认证系统的App组件
function AppWithAuth() {
  return (
    <AuthProvider>
      <RouterWithAuth />
    </AuthProvider>
  );
}

export default AppWithAuth;