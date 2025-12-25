# 电影推荐系统 API 文档

## 概述
本文档详细列出了电影推荐系统的所有 API 接口，包括请求方法、参数、响应格式等信息。

---

## 目录
1. [用户认证接口](#用户认证接口)
2. [电影信息接口](#电影信息接口)
3. [推荐系统接口](#推荐系统接口)
4. [用户评分接口](#用户评分接口)
5. [排行榜接口](#排行榜接口)
6. [搜索接口](#搜索接口)
7. [异步任务接口](#异步任务接口)

---

## 用户认证接口

### 1. 用户注册
**端点:** `POST /api/register`

**描述:** 用户注册，使用用户名+密码并将用户信息保存到 users 表

**请求体:**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应:**
```json
{
  "success": true,
  "user_id": 123,
  "message": "注册成功"
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "用户名已存在"
}
```

---

### 2. 用户登录
**端点:** `POST /api/login`

**描述:** 用户登录，支持用户名+密码，兼容旧的 user_id 方式

**请求体:**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应:**
```json
{
  "success": true,
  "user_id": 123,
  "username": "user123",
  "message": "登录成功"
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "用户名或密码错误"
}
```

---

### 3. 用户登出
**端点:** `POST /api/logout`

**描述:** 用户登出，清除会话信息

**请求体:** 无

**响应:**
```json
{
  "success": true,
  "message": "登出成功"
}
```

---

### 4. 获取会话信息
**端点:** `GET /api/session`

**描述:** 获取当前会话信息，包括登录状态和用户信息

**请求参数:** 无

**响应 (已登录):**
```json
{
  "logged_in": true,
  "user_id": 123,
  "username": "user123"
}
```

**响应 (未登录):**
```json
{
  "logged_in": false
}
```

---

## 电影信息接口

### 1. 获取电影详情
**端点:** `GET /api/movie/<movie_id>`

**描述:** 获取单个电影的详细信息

**请求参数:**
- `movie_id` (path): 电影ID (必需)

**响应:**
```json
{
  "id": 123,
  "title": "电影标题",
  "overview": "电影简介",
  "rating": 8.5,
  "vote_count": 1000,
  "release_date": "2023-01-01",
  "runtime": 120,
  "genres": ["动作", "冒险"],
  "poster": "static/img/123.webp",
  "keywords": ["关键词1", "关键词2"]
}
```

---

### 2. 获取相似电影
**端点:** `GET /api/similar-movies/<movie_id>`

**描述:** 获取相似电影列表（基于 TF-IDF 相似度）

**请求参数:**
- `movie_id` (path): 电影ID (必需)
- `limit` (query): 返回数量，默认12

**响应:**
```json
[
  {
    "id": 456,
    "title": "相似电影1",
    "rating": 8.2,
    "poster": "static/img/456.webp",
    "similarity": 0.85
  },
  {
    "id": 789,
    "title": "相似电影2",
    "rating": 7.9,
    "poster": "static/img/789.webp",
    "similarity": 0.78
  }
]
```

---

### 3. 获取电影类型
**端点:** `GET /api/genres`

**描述:** 获取所有电影类型

**请求参数:** 无

**响应:**
```json
{
  "genres": [
    "动作",
    "喜剧",
    "剧情",
    "爱情",
    "科幻",
    "恐怖",
    "动画"
  ]
}
```

---

### 4. 按类型获取电影
**端点:** `GET /api/movies/by-genre`

**描述:** 按类型获取电影列表（随机排序）

**请求参数:**
- `genre` (query): 电影类型，默认 "all" (必需)
- `limit` (query): 返回数量，默认12

**响应:**
```json
{
  "genre": "动作",
  "movies": [
    {
      "id": 123,
      "title": "动作电影1",
      "rating": 8.5,
      "poster": "static/img/123.webp"
    },
    {
      "id": 456,
      "title": "动作电影2",
      "rating": 8.2,
      "poster": "static/img/456.webp"
    }
  ]
}
```

---

## 推荐系统接口

### 1. 获取个性化推荐
**端点:** `GET /api/movies/recommendations`

**描述:** 获取个性化推荐（登录用户使用 ALS 模型，未登录用户随机推荐）

**请求参数:**
- `topN` (query): 返回数量，默认10
- `force` (query): 是否强制重新计算，可选

**响应 (已登录):**
```json
{
  "method": "als",
  "user_id": 123,
  "movies": [
    {
      "id": 123,
      "title": "推荐电影1",
      "rating": 8.5,
      "poster": "static/img/123.webp"
    }
  ]
}
```

**响应 (未登录):**
```json
{
  "method": "random",
  "movies": [
    {
      "id": 456,
      "title": "热门电影",
      "rating": 8.2,
      "poster": "static/img/456.webp"
    }
  ]
}
```

---

### 2. 获取用户个性化推荐
**端点:** `GET /api/user/<user_id>/recommend`

**描述:** 获取指定用户的个性化推荐

**请求参数:**
- `user_id` (path): 用户ID (必需)
- `topN` (query): 返回数量，默认10

**响应:**
```json
{
  "user_id": 123,
  "recommendations": [
    {
      "movie_id": 456,
      "title": "推荐电影",
      "prediction": 8.7,
      "poster": "static/img/456.webp"
    }
  ]
}
```

---

## 用户评分接口

### 1. 用户评分电影
**端点:** `POST /api/movie/<movie_id>/rate`

**描述:** 用户评分电影，需要登录

**请求参数:**
- `movie_id` (path): 电影ID (必需)

**请求体:**
```json
{
  "rating": 8.5,
  "comment": "这是一部很好的电影"
}
```

**响应:**
```json
{
  "success": true,
  "message": "评分成功",
  "rating": 8.5
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "请先登录"
}
```

---

### 2. 获取用户评分记录
**端点:** `GET /api/user/<user_id>/ratings`

**描述:** 获取用户的所有评分记录

**请求参数:**
- `user_id` (path): 用户ID (必需)

**响应:**
```json
{
  "success": true,
  "user_id": 123,
  "username": "user123",
  "total_ratings": 50,
  "avg_rating": 7.8,
  "ratings": [
    {
      "movie_id": 456,
      "title": "已评分电影",
      "rating": 8.5,
      "poster": "static/img/456.webp",
      "release_date": "2023-01-01",
      "rating_time": "2024-01-15T10:30:00"
    }
  ]
}
```

---

## 排行榜接口

### 1. 获取电影排行榜
**端点:** `GET /api/rankings`

**描述:** 获取电影排行榜，支持多种排序方式

**请求参数:**
- `sort_by` (query): 排序方式，可选值：
  - `rating` - 按评分排序 (默认)
  - `popularity` - 按热度排序
  - `vote_count` - 按评分人数排序
- `limit` (query): 返回数量，默认20
- `offset` (query): 分页偏移，默认0

**响应:**
```json
{
  "sort_by": "rating",
  "total": 5000,
  "limit": 20,
  "offset": 0,
  "movies": [
    {
      "id": 123,
      "title": "排行榜电影1",
      "rating": 9.2,
      "vote_count": 5000,
      "poster": "static/img/123.webp",
      "rank": 1
    }
  ]
}
```

---

## 搜索接口

### 1. 搜索电影
**端点:** `GET /api/search`

**描述:** 搜索电影，支持按标题、导演、演员等搜索

**请求参数:**
- `q` (query): 搜索关键词 (必需)
- `limit` (query): 返回数量，默认50

**响应:**
```json
{
  "query": "搜索关键词",
  "total": 10,
  "results": [
    {
      "id": 123,
      "title": "搜索结果1",
      "rating": 8.5,
      "poster": "static/img/123.webp"
    }
  ]
}
```

---

## 异步任务接口

### 1. 获取 ALS 系统状态
**端点:** `GET /api/als/status`

**描述:** 返回后台 ALS 重算线程与队列状态

**请求参数:** 无

**响应:**
```json
{
  "worker_running": true,
  "queue_size": 5,
  "active_tasks": 1
}
```

---

### 2. 查询用户任务状态
**端点:** `GET /api/als/task/<user_id>`

**描述:** 查询指定用户的异步重算任务状态

**请求参数:**
- `user_id` (path): 用户ID (必需)

**响应:**
```json
{
  "user_id": 123,
  "status": "running",
  "progress": 45,
  "started_at": 1705315200,
  "message": "正在计算个性化推荐"
}
```

**状态值:**
- `idle` - 空闲
- `running` - 运行中
- `done` - 已完成

---

### 3. 获取任务日志
**端点:** `GET /api/als/logs/<user_id>`

**描述:** 获取指定用户的推理日志（最近 300 行）

**请求参数:**
- `user_id` (path): 用户ID (必需)

**响应:**
```json
{
  "user_id": 123,
  "logs": [
    "[2024-01-15 10:30:00] 开始加载用户特征",
    "[2024-01-15 10:30:05] 特征加载完成",
    "[2024-01-15 10:30:10] 开始计算推荐"
  ]
}
```

---

## 静态资源接口

### 1. 获取电影海报
**端点:** `GET /img/<filename>`

**描述:** 提供电影海报图片

**请求参数:**
- `filename` (path): 图片文件名 (必需)

**响应:** 图片文件

---

### 2. 获取首页
**端点:** `GET /`

**描述:** 获取首页 HTML

**请求参数:** 无

**响应:** HTML 页面

---

## 错误处理

所有 API 错误响应遵循以下格式：

```json
{
  "success": false,
  "error": "错误信息描述"
}
```

常见错误码：
- `400` - 请求参数错误
- `401` - 未授权（需要登录）
- `404` - 资源不存在
- `500` - 服务器内部错误

---

## 认证方式

系统使用 Flask Session 进行用户认证。登录后，用户信息存储在 session 中，后续请求会自动验证。

**认证流程:**
1. 用户通过 `/api/login` 登录
2. 服务器创建 session 并返回 user_id
3. 后续请求自动包含 session cookie
4. 服务器验证 session 中的 user_id

---

## 速率限制

当前系统未实现速率限制，但建议客户端遵循以下规范：
- 搜索请求：每秒最多 10 次
- 推荐请求：每秒最多 5 次
- 其他请求：每秒最多 20 次

---

## 数据库表结构

### users 表
```sql
CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### user_ratings 表
```sql
CREATE TABLE user_ratings (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  movie_id INT NOT NULL,
  rating FLOAT NOT NULL,
  comment TEXT,
  rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### user_recommendations 表
```sql
CREATE TABLE user_recommendations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  movie_id INT NOT NULL,
  prediction FLOAT NOT NULL,
  rank INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 示例代码

### JavaScript 示例

**登录:**
```javascript
const response = await fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'user123',
    password: 'password123'
  })
});
const data = await response.json();
console.log(data.user_id);
```

**获取推荐:**
```javascript
const response = await fetch('/api/movies/recommendations?topN=10');
const data = await response.json();
console.log(data.movies);
```

**评分电影:**
```javascript
const response = await fetch('/api/movie/123/rate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    rating: 8.5,
    comment: '很好的电影'
  })
});
const data = await response.json();
console.log(data.success);
```

---

## 更新日志

### v1.0 (2024-01-15)
- 初始版本
- 实现基础 API 接口
- 支持用户认证和个性化推荐
- 支持电影搜索和排行榜

---

## 联系方式

如有问题或建议，请联系开发团队。

