import React, { useState } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoginModal from './LoginModal';
import './Layout.css';

function Layout() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="layout">
      <header className="header">
        <div className="container header-content">
          <Link to="/" className="logo">
            <span className="logo-icon">🎬</span>
            <span className="logo-text">CineMatch</span>
          </Link>

          <nav className={`nav ${menuOpen ? 'open' : ''}`}>
            <Link to="/" className="nav-link" onClick={() => setMenuOpen(false)}>首页</Link>
            <Link to="/rankings" className="nav-link" onClick={() => setMenuOpen(false)}>排行榜</Link>
          </nav>

          <div className="header-actions">
            {user ? (
              <div className="user-dropdown">
                <button className="user-btn">
                  <span className="user-avatar">{user.username[0].toUpperCase()}</span>
                  <span className="user-name">{user.username}</span>
                  <span className="dropdown-arrow">▼</span>
                </button>
                <div className="dropdown-menu">
                  <div className="dropdown-header">
                    <span className="dropdown-username">{user.username}</span>
                    <span className="dropdown-id">ID: {user.id}</span>
                  </div>
                  <Link to="/user/ratings" className="dropdown-item">📊 我的评分</Link>
                  <button onClick={handleLogout} className="dropdown-item logout">🚪 退出登录</button>
                </div>
              </div>
            ) : (
              <button className="login-btn" onClick={() => setLoginModalOpen(true)}>登录</button>
            )}
          </div>

          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? '✕' : '☰'}
          </button>
        </div>
      </header>

      <LoginModal isOpen={loginModalOpen} onClose={() => setLoginModalOpen(false)} />

      <main className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="container footer-content">
          <p>© 2024 CineMatch 电影推荐系统</p>
        </div>
      </footer>
    </div>
  );
}

export default Layout;
