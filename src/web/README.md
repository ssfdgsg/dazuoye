# Web 界面 - 电影推荐系统

目录: `src/web/`

## 项目概述

这是一个完整的电影推荐系统 Web 应用，包含前端界面和后端 API 服务。后端使用 Flask 连接 MySQL 数据库，提供电影浏览、搜索、推荐、排行榜等功能。前端使用现代化设计，支持响应式布局。

## 主要功能

### 用户功能
- **用户注册/登录** - 仅需用户名和密码
- **会话管理** - 7天持久化会话
- **个性化推荐** - 基于 ALS 协同过滤模型（已登录用户）或热门推荐（未登录用户）；首页“猜你喜欢”支持一键刷新重新计算

### 电影浏览
- **首页** (`index.html`) - 按类型筛选、个性化推荐、实时搜索
- **电影详情** (`movie.html`) - 横版布局展示电影信息、相似电影推荐
- **排行榜** (`movie_rank.html`) - 评分榜、热度榜、新片榜、票房榜，支持类型和年份范围筛选
- **搜索功能** - 支持标题、类型、关键词多字段模糊搜索

### API 端点

#### 用户相关
- `POST /api/register` - 用户注册（用户名、密码）
- `POST /api/login` - 用户登录
- `POST /api/logout` - 退出登录
- `GET /api/session` - 获取当前会话状态

#### 电影相关
- `GET /api/genres` - 获取所有电影类型
- `GET /api/movies/by-genre?genre=<genre>` - 按类型筛选电影
- `GET /api/movies/recommendations` - 个性化推荐（ALS 模型或热门推荐）
   - 可选参数：`topN`（默认12），`force=1` 强制跳过预计算结果并基于最新评分回退策略重新计算
- `GET /api/movie/<movie_id>` - 获取电影详情
- `POST /api/movie/<movie_id>/rate` - 提交电影评分
- `GET /api/similar-movies/<movie_id>?topN=12` - 基于 TF-IDF 的相似电影推荐
- `GET /api/search?q=<query>&limit=<limit>` - 搜索电影（标题/类型/关键词）
- `GET /api/rankings?type=<type>&genre=<genre>&year_from=<year>&year_to=<year>` - 电影排行榜
  - type: `rating`（评分）, `popularity`（热度）, `new`（新片）, `boxoffice`（票房）

#### 静态资源
- `GET /img/<filename>` - 电影海报图片服务（从 `static/img/` 目录）

## 安装依赖

建议在虚拟环境中安装：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

主要依赖：
- Flask 3.0+
- flask-cors
- mysql-connector-python
- numpy（用于 TF-IDF 向量计算）

## 运行方式

### 方式一：开发模式
```bash
cd ./src/web
python3.8 app.py
```

### 方式二：后台运行（推荐）
```bash
cd ./src/web
# 匹配包含 "python3.8 app.py" 的进程并杀死（最推荐）
pkill -f "python3.8 app.py"
nohup python3.8 app.py > flask.log 2>&1 &
```

### 方式三：使用 Gunicorn（生产环境）
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 访问界面

服务启动后，在浏览器访问以下页面：

- **首页**: `http://127.0.0.1:5000/` 或 `http://127.0.0.1:5000/static/index.html`
   - “猜你喜欢”右侧提供“刷新”按钮，可立即重新计算当前用户推荐
- **登录**: `http://127.0.0.1:5000/static/login.html`
- **注册**: `http://127.0.0.1:5000/static/register.html`
- **电影详情**: `http://127.0.0.1:5000/static/movie.html?id=<movie_id>`
- **排行榜**: `http://127.0.0.1:5000/static/movie_rank.html`
- **推荐页**: `http://127.0.0.1:5000/static/recommend.html`

## 数据库配置

应用连接到 MySQL 数据库，配置如下：
- **Host**: localhost
- **User**: root
- **Password**: root123
- **Database**: movie_db

数据表结构：
- `movie_basic` - 电影基本信息（movie_id, title, genres, release_date, runtime, vote_average, vote_count, popularity_score, keywords）
- `movie_features` - 电影特征（movie_id, tfidf_features）
- `user_ratings` - 用户评分记录
- `user_recommendations` - 用户推荐结果（ALS 模型生成）

**注意**：TF-IDF 向量使用 Base64 编码存储，解码时使用小端序（little-endian）`'<f8'` 格式。

## 技术特性

### 前端
- 响应式设计，支持移动端和桌面端
- 毛玻璃效果和渐变背景
- 动态数据加载和实时搜索
- Font Awesome 图标库
- 横版电影详情页布局
- 密码强度检测器
- 表单验证和错误提示

### 后端
- Flask RESTful API 架构
- CORS 跨域支持
- Session 会话管理（7天过期）
- TF-IDF 余弦相似度计算
- ALS 协同过滤推荐（可选）
- 热门/评分/新片/票房多维度排行
- 多字段模糊搜索（LIKE 查询）
- 自定义图片服务路由

### 数据处理
- Base64 TF-IDF 向量解码（小端序）
- NumPy 向量运算优化
- MySQL 连接池管理
- 异常处理和错误日志

## 目录结构

```
src/web/
├── app.py                 # Flask 后端主程序
├── requirements.txt       # Python 依赖
├── README.md             # 本文档
└── static/               # 静态资源
    ├── index.html        # 首页
    ├── login.html        # 登录页
    ├── register.html     # 注册页
    ├── movie.html        # 电影详情页
    ├── movie_rank.html   # 排行榜页
    ├── recommend.html    # 推荐页
    └── img/              # 电影海报图片（.webp 格式）
```

## 注意事项

1. **安全性**
   - 生产环境应修改 `app.secret_key`
   - 不要在代码中硬编码数据库密码
   - 建议使用环境变量或配置文件管理敏感信息

2. **性能优化**
   - TF-IDF 相似度计算可能较慢，建议添加缓存
   - 大量海报图片应使用 CDN 或图片服务器
   - 数据库查询可添加索引优化

3. **扩展建议**
   - 实现完整的用户认证系统
   - 添加用户个人主页和评分历史
   - 实现评论和社交功能
   - 集成真实的 ALS 推荐模型
   - 添加分页功能处理大量数据

## API 测试示例
# 强制刷新个性化推荐（登录态下）
curl "http://127.0.0.1:5000/api/movies/recommendations?topN=12&force=1"

```bash
# 测试搜索 API
curl "http://127.0.0.1:5000/api/search?q=Matrix&limit=5"

# 测试相似电影 API
curl "http://127.0.0.1:5000/api/similar-movies/862?topN=5"

# 测试排行榜 API
curl "http://127.0.0.1:5000/api/rankings?type=rating&genre=Action&year_from=2010&year_to=2020"

# 测试类型筛选
curl "http://127.0.0.1:5000/api/movies/by-genre?genre=Sci-Fi"
```