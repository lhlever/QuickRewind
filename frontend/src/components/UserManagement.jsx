import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';

const UserManagement = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterActive, setFilterActive] = useState(null);
  const [filterAdmin, setFilterAdmin] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    is_active: true,
    is_superuser: false
  });

  // 获取用户列表
  const fetchUsers = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (searchTerm) params.append('search', searchTerm);
      if (filterActive !== null) params.append('is_active', filterActive);
      if (filterAdmin !== null) params.append('is_superuser', filterAdmin);
      
      const response = await apiService.user.getUsers(`?${params.toString()}`);
      setUsers(response.data);
      setError(null);
    } catch (err) {
      setError('获取用户列表失败');
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  // 创建用户
  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await apiService.user.createUser(formData);
      setFormData({
        username: '',
        email: '',
        full_name: '',
        password: '',
        is_active: true,
        is_superuser: false
      });
      setShowCreateForm(false);
      fetchUsers();
    } catch (err) {
      setError('创建用户失败');
      console.error('Error creating user:', err);
    }
  };

  // 更新用户
  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      await apiService.user.updateUser(editingUser.id, formData);
      setFormData({
        username: '',
        email: '',
        full_name: '',
        password: '',
        is_active: true,
        is_superuser: false
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err) {
      setError('更新用户失败');
      console.error('Error updating user:', err);
    }
  };

  // 删除用户
  const handleDeleteUser = async (userId) => {
    if (window.confirm('确定要删除这个用户吗？此操作不可撤销。')) {
      try {
        await apiService.user.deleteUser(userId);
        fetchUsers();
      } catch (err) {
        setError('删除用户失败');
        console.error('Error deleting user:', err);
      }
    }
  };

  // 切换用户状态
  const handleToggleStatus = async (userId, isActive) => {
    try {
      await apiService.user.toggleUserStatus(userId, isActive);
      fetchUsers();
    } catch (err) {
      setError('更新用户状态失败');
      console.error('Error toggling user status:', err);
    }
  };

  // 切换用户角色
  const handleToggleRole = async (userId, isAdmin) => {
    try {
      await apiService.user.toggleUserRole(userId, isAdmin);
      fetchUsers();
    } catch (err) {
      setError('更新用户角色失败');
      console.error('Error toggling user role:', err);
    }
  };

  // 打开编辑表单
  const openEditForm = (user) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      full_name: user.full_name || '',
      password: '',
      is_active: user.is_active,
      is_superuser: user.is_superuser
    });
  };

  // 重置表单
  const resetForm = () => {
    setFormData({
      username: '',
      email: '',
      full_name: '',
      password: '',
      is_active: true,
      is_superuser: false
    });
    setShowCreateForm(false);
    setEditingUser(null);
  };

  useEffect(() => {
    fetchUsers();
  }, [searchTerm, filterActive, filterAdmin]);

  // 检查当前用户是否为管理员
  if (!user || !user.is_superuser) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">
          您没有权限访问此页面
        </div>
      </div>
    );
  }

  return (
    <div className="container mt-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>用户管理</h2>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowCreateForm(true)}
        >
          创建用户
        </button>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {/* 搜索和过滤 */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="row">
            <div className="col-md-4 mb-3">
              <input
                type="text"
                className="form-control"
                placeholder="搜索用户名或邮箱"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="col-md-3 mb-3">
              <select
                className="form-select"
                value={filterActive === null ? '' : filterActive.toString()}
                onChange={(e) => setFilterActive(e.target.value === '' ? null : e.target.value === 'true')}
              >
                <option value="">所有状态</option>
                <option value="true">激活</option>
                <option value="false">禁用</option>
              </select>
            </div>
            <div className="col-md-3 mb-3">
              <select
                className="form-select"
                value={filterAdmin === null ? '' : filterAdmin.toString()}
                onChange={(e) => setFilterAdmin(e.target.value === '' ? null : e.target.value === 'true')}
              >
                <option value="">所有角色</option>
                <option value="true">管理员</option>
                <option value="false">普通用户</option>
              </select>
            </div>
            <div className="col-md-2 mb-3">
              <button 
                className="btn btn-outline-secondary w-100" 
                onClick={() => {
                  setSearchTerm('');
                  setFilterActive(null);
                  setFilterAdmin(null);
                }}
              >
                重置
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 创建/编辑用户表单 */}
      {(showCreateForm || editingUser) && (
        <div className="card mb-4">
          <div className="card-header">
            <h5>{editingUser ? '编辑用户' : '创建用户'}</h5>
          </div>
          <div className="card-body">
            <form onSubmit={editingUser ? handleUpdateUser : handleCreateUser}>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label htmlFor="username" className="form-label">用户名</label>
                  <input
                    type="text"
                    className="form-control"
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    required
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="email" className="form-label">邮箱</label>
                  <input
                    type="email"
                    className="form-control"
                    id="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    required
                  />
                </div>
              </div>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label htmlFor="full_name" className="form-label">全名</label>
                  <input
                    type="text"
                    className="form-control"
                    id="full_name"
                    value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label htmlFor="password" className="form-label">
                    密码 {editingUser && '(留空则不修改)'}
                  </label>
                  <input
                    type="password"
                    className="form-control"
                    id="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required={!editingUser}
                  />
                </div>
              </div>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="is_active"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    />
                    <label className="form-check-label" htmlFor="is_active">
                      激活状态
                    </label>
                  </div>
                </div>
                <div className="col-md-6 mb-3">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="is_superuser"
                      checked={formData.is_superuser}
                      onChange={(e) => setFormData({...formData, is_superuser: e.target.checked})}
                    />
                    <label className="form-check-label" htmlFor="is_superuser">
                      管理员权限
                    </label>
                  </div>
                </div>
              </div>
              <div className="d-flex justify-content-end">
                <button 
                  type="button" 
                  className="btn btn-secondary me-2" 
                  onClick={resetForm}
                >
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingUser ? '更新' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 用户列表 */}
      <div className="card">
        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border" role="status">
                <span className="visually-hidden">加载中...</span>
              </div>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-4">没有找到用户</div>
          ) : (
            <div className="table-responsive">
              <table className="table table-striped table-hover">
                <thead>
                  <tr>
                    <th>用户名</th>
                    <th>邮箱</th>
                    <th>全名</th>
                    <th>状态</th>
                    <th>角色</th>
                    <th>API调用</th>
                    <th>存储使用</th>
                    <th>最后登录</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((userItem) => (
                    <tr key={userItem.id}>
                      <td>{userItem.username}</td>
                      <td>{userItem.email}</td>
                      <td>{userItem.full_name || '-'}</td>
                      <td>
                        <span className={`badge ${userItem.is_active ? 'bg-success' : 'bg-danger'}`}>
                          {userItem.is_active ? '激活' : '禁用'}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${userItem.is_superuser ? 'bg-warning' : 'bg-info'}`}>
                          {userItem.is_superuser ? '管理员' : '普通用户'}
                        </span>
                      </td>
                      <td>{userItem.api_calls || 0}</td>
                      <td>{(userItem.storage_used / 1024 / 1024).toFixed(2)} MB</td>
                      <td>
                        {userItem.last_login 
                          ? new Date(userItem.last_login).toLocaleString()
                          : '从未登录'
                        }
                      </td>
                      <td>
                        <div className="btn-group" role="group">
                          <button 
                            className="btn btn-sm btn-outline-primary" 
                            onClick={() => openEditForm(userItem)}
                          >
                            编辑
                          </button>
                          <button 
                            className={`btn btn-sm ${userItem.is_active ? 'btn-outline-warning' : 'btn-outline-success'}`}
                            onClick={() => handleToggleStatus(userItem.id, !userItem.is_active)}
                            disabled={userItem.id === user.id}
                          >
                            {userItem.is_active ? '禁用' : '激活'}
                          </button>
                          <button 
                            className={`btn btn-sm ${userItem.is_superuser ? 'btn-outline-info' : 'btn-outline-warning'}`}
                            onClick={() => handleToggleRole(userItem.id, !userItem.is_superuser)}
                            disabled={userItem.id === user.id}
                          >
                            {userItem.is_superuser ? '取消管理员' : '设为管理员'}
                          </button>
                          <button 
                            className="btn btn-sm btn-outline-danger" 
                            onClick={() => handleDeleteUser(userItem.id)}
                            disabled={userItem.id === user.id}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserManagement;