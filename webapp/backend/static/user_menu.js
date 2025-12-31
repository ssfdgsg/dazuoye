/**
 * 通用导航栏用户菜单功能
 * 用于所有页面的用户登录状态显示和下拉菜单
 */

let USER_MENU_INITIALIZED = false;

/**
 * 初始化用户菜单功能
 * 在页面加载时调用此函数
 */
async function initUserMenu() {
    if (USER_MENU_INITIALIZED) return;
    USER_MENU_INITIALIZED = true;
    try {
        const res = await fetch('/api/session');
        const data = await res.json();
        
        const loginBtn = document.getElementById('loginBtn');
        const userMenu = document.getElementById('userMenu');
        
        if (data.logged_in) {
            // 用户已登录，显示用户菜单
            if (loginBtn) loginBtn.style.display = 'none';
            if (userMenu) {
                userMenu.classList.add('active');
                
                // 设置用户信息
                const userNameText = document.getElementById('userNameText');
                const dropdownUsername = document.getElementById('dropdownUsername');
                const dropdownUserId = document.getElementById('dropdownUserId');
                
                if (userNameText) userNameText.textContent = data.username || '用户';
                if (dropdownUsername) dropdownUsername.textContent = data.username || '未知';
                if (dropdownUserId) dropdownUserId.textContent = data.user_id || '-';
                
                // 设置用户评分表链接
                const ratingHistoryLink = document.getElementById('ratingHistoryLink');
                if (ratingHistoryLink) {
                    ratingHistoryLink.href = `/static/user_ratings.html?user_id=${data.user_id}`;
                }
                
                // 设置退出登录事件
                const logoutLink = document.getElementById('logoutLink');
                if (logoutLink) {
                    logoutLink.addEventListener('click', async (e) => {
                        e.preventDefault();
                        try {
                            await fetch('/api/logout', { method: 'POST' });
                            window.location.reload();
                        } catch (err) {
                            console.error('退出登录失败:', err);
                            alert('退出登录失败，请重试');
                        }
                    });
                }
            }
        } else {
            // 用户未登录，显示登录按钮
            if (loginBtn) loginBtn.style.display = 'block';
            if (userMenu) userMenu.classList.remove('active');
        }
    } catch (err) {
        console.error('检查登录状态失败:', err);
    }
}

// 自动在页面加载时执行，确保无需每页单独调用
document.addEventListener('DOMContentLoaded', () => {
    initUserMenu();
});

/**
 * 获取用户菜单HTML代码
 * 返回可插入到导航栏的HTML字符串
 */
function getUserMenuHTML() {
    return `
        <!-- 登录按钮 -->
        <a href="/static/login.html" class="login-btn" id="loginBtn">登录</a>
        <!-- 用户菜单 -->
        <div class="user-menu" id="userMenu">
            <div class="user-name" id="userName">
                <i class="fas fa-user-circle"></i>
                <span id="userNameText">用户</span>
                <i class="fas fa-chevron-down"></i>
            </div>
            <div class="dropdown-menu">
                <div class="dropdown-item user-info">
                    <i class="fas fa-user"></i>
                    <span>用户名: <strong id="dropdownUsername">-</strong></span>
                </div>
                <div class="dropdown-item user-info">
                    <i class="fas fa-id-card"></i>
                    <span>ID: <strong id="dropdownUserId">-</strong></span>
                </div>
                <a href="#" class="dropdown-item" id="ratingHistoryLink">
                    <i class="fas fa-star"></i>
                    <span>用户评分表</span>
                </a>
                <a href="#" class="dropdown-item" id="logoutLink">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>退出登录</span>
                </a>
            </div>
        </div>
    `;
}

/**
 * 获取用户菜单CSS样式
 * 返回可插入到页面的CSS字符串
 */
function getUserMenuCSS() {
    return `
        /* 用户下拉菜单样式 */
        .user-menu {
            position: relative;
            display: none;
        }

        .user-menu.active {
            display: block;
        }

        .user-name {
            padding: 0.6rem 1.2rem;
            border-radius: 20px;
            background: linear-gradient(135deg, var(--primary), var(--primary-strong));
            color: #0b1220;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .user-name:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(34, 211, 238, 0.3);
        }

        .user-name i {
            font-size: 0.9rem;
        }

        .dropdown-menu {
            position: absolute;
            top: calc(100% + 0.5rem);
            right: 0;
            background: rgba(17, 24, 39, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            min-width: 200px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            opacity: 0;
            visibility: hidden;
            transform: translateY(-10px);
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .user-menu:hover .dropdown-menu {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }

        .dropdown-item {
            padding: 0.8rem 1.2rem;
            color: var(--text);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.8rem;
            transition: all 0.2s ease;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .dropdown-item:last-child {
            border-bottom: none;
        }

        .dropdown-item:hover {
            background: rgba(34, 211, 238, 0.1);
            padding-left: 1.5rem;
        }

        .dropdown-item i {
            width: 20px;
            color: var(--primary);
        }

        .dropdown-item.user-info {
            cursor: default;
            background: rgba(34, 211, 238, 0.05);
            font-size: 0.9rem;
            color: var(--muted);
        }

        .dropdown-item.user-info:hover {
            background: rgba(34, 211, 238, 0.05);
            padding-left: 1.2rem;
        }

        .dropdown-item.user-info strong {
            color: var(--text);
        }
    `;
}
