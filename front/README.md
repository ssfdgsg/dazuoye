# 影视阁 - 电影推荐系统前端

基于 React 的现代化电影推荐系统前端界面。

## 技术栈

- React 18
- React Router 6
- CSS3 (无框架，纯 CSS)

## 功能特性

- 🏠 首页：个性化推荐 + 分类浏览
- 🔍 搜索：电影搜索功能
- 🎬 电影详情：详细信息 + 相似推荐 + 评分
- 🏆 排行榜：多维度排序
- 👤 用户系统：登录/注册/评分记录

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm start

# 构建生产版本
npm run build
```

## 项目结构

```
front/
├── public/
│   └── index.html
├── src/
│   ├── components/     # 通用组件
│   ├── context/        # React Context
│   ├── pages/          # 页面组件
│   ├── services/       # API 服务
│   ├── styles/         # 全局样式
│   ├── App.js
│   └── index.js
└── package.json
```

## API 代理

开发模式下，API 请求会代理到 `http://localhost:5000`（Flask 后端）。
