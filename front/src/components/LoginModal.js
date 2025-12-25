import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { login as apiLogin } from '../services/api';
import './LoginModal.css';

function LoginModal({ isOpen, onClose }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('请输入用户名和密码');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await apiLogin(username, password);
      if (data.success) {
        login({ id: data.user_id, username: data.username });
        onClose();
        setUsername('');
        setPassword('');
      } else {
        setError(data.error || '登录失败');
      }
    } catch (err) {
      setError(err.message || '登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-content">
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <div className="modal-header">
          <span className="modal-logo">🎬</span>
          <h2 className="modal-title">欢迎回来</h2>
          <p className="modal-subtitle">登录以获取个性化推荐</p>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="modal-form-group">
            <label htmlFor="modal-username">用户名</label>
            <input
              type="text"
              id="modal-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              autoComplete="username"
            />
          </div>

          <div className="modal-form-group">
            <label htmlFor="modal-password">密码</label>
            <input
              type="password"
              id="modal-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoComplete="current-password"
            />
          </div>

          {error && <div className="modal-error">{error}</div>}

          <button type="submit" className="modal-btn" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="modal-footer">
          <span>还没有账号？</span>
          <Link to="/register" onClick={onClose}>立即注册</Link>
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
