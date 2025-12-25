# 电影推荐系统 FastAPI 重构实现文档

## 项目概述

将原有的 Flask 单文件应用重构为基于 FastAPI 的模块化项目，提供电影推荐、用户认证、评分管理等功能。

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL (psycopg2-binary)
- **认证**: JWT Token (python-jose)
- **密码加密**: passlib[bcrypt]
- **异步任务**: 后台线程 + Queue
- **环境管理**: uv

## 项目结构

```
src/web/fastapi_app/
├── main.py              # 应用入口，FastAPI 实例
├── config.py            # 配置管理（环境变量）
├── database.py          # 数据库连接管理
├── dependencies.py      # 依赖注入（认证、数据库会话）
├── models/
│   └── schemas.py       # Pydantic 数据模型
├── routers/
│   ├── auth.py          # 认证路由（注册/登录/登出）
│   ├── movies.py        # 电影路由（详情/搜索/排行榜）
│   ├── recommendations.py  # 推荐路由（个性化推荐/相似电影）
│   └── ratings.py       # 评分路由（评分/历史记录）
├── services/
│   ├── movie_service.py      # 电影业务逻辑
│   ├── recommendation_service.py  # 推荐业务逻辑
│   └── als_worker.py         # ALS 后台任务
└── utils/
    └── tfidf.py         # TF-IDF 向量解码工具
```

## API 端点

### 认证模块 `/api/auth`
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /register | 用户注册 |
| POST | /login | 用户登录 |
| POST | /logout | 用户登出 |
| GET | /session | 获取当前会话 |

### 电影模块 `/api/movies`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /{movie_id} | 获取电影详情 |
| GET | /search | 搜索电影 |
| GET | /rankings | 获取排行榜 |
| GET | /genres | 获取所有类型 |
| GET | /by-genre | 按类型获取电影 |

### 推荐模块 `/api/recommendations`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | / | 获取个性化推荐 |
| GET | /similar/{movie_id} | 获取相似电影 |
| GET | /user/{user_id} | 获取用户推荐 |

### 评分模块 `/api/ratings`
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /movie/{movie_id} | 提交评分 |
| GET | /user/{user_id} | 获取用户评分历史 |
| GET | /als/status | ALS 任务状态 |
| GET | /als/task/{user_id} | 用户任务状态 |
| GET | /als/logs/{user_id} | 用户任务日志 |

## 数据库表

- `users`: 用户信息
- `user_ratings`: 用户评分
- `user_recommendations`: 预计算推荐
- `movie_basic`: 电影基本信息
- `movie_features`: 电影特征（TF-IDF）

## 运行方式

```bash
cd src/web/fastapi_app
uv run uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| DB_HOST | localhost | 数据库主机 |
| DB_USER | root | 数据库用户 |
| DB_PASS | root123 | 数据库密码 |
| DB_NAME | movie_db | 数据库名 |
| SECRET_KEY | movie-recommendation-secret-key-2024 | JWT 密钥 |
| PORT | 5000 | 服务端口 |
