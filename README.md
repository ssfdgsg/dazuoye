# 电影推荐系统

基于 Spark + FastAPI + React 的电影推荐系统。

## 项目结构

```
├── recommend-engine/          # 推荐引擎
│   ├── spark/                 # Spark 批处理
│   │   ├── preprocess/        # 数据预处理 (MoviePreprocess.scala)
│   │   └── model/             # 模型训练 (RecommendationModel.scala)
│   ├── algorithms/            # Python 推荐算法
│   │   ├── user_cf.py         # 用户协同过滤
│   │   ├── content_based.py   # 内容推荐
│   │   ├── als_recommend.py   # ALS 推荐
│   │   ├── db.py              # 数据库连接
│   │   └── cli.py             # 命令行入口
│   ├── sql/init.sql           # 数据库初始化
│   └── pom.xml
│
├── webapp/                    # Web 应用
│   ├── backend/               # FastAPI 后端
│   │   ├── routers/           # API 路由
│   │   ├── services/          # 业务逻辑
│   │   ├── models/            # 数据模型
│   │   ├── static/            # 静态文件 (含 img/)
│   │   └── main.py            # 入口
│   └── frontend/              # React 前端
│       └── src/
│
├── data/                      # 数据 (tmdb_5000_movies.csv)
├── conf/                      # 配置 (log4j.properties)
└── scan/                      # 爬虫脚本
```

## 环境要求

- Java 8
- Scala 2.12.10
- Spark 3.1.3
- Hadoop 3.1.3
- Python 3.7+
- Node.js 14+
- PostgreSQL 12+

## 快速开始

### 1. 启动 Hadoop

```bash
ssh localhost
cd ~/Desktop
./starthadoop.sh
```

### 2. 初始化数据库

```bash
psql -U postgres -f recommend-engine/sql/init.sql
```

### 3. 数据预处理

```bash
cd recommend-engine
mvn clean package

# 运行预处理
spark-submit --class com.movie.preprocess.MoviePreprocess \
  --master local[*] \
  target/recommend-engine-1.0.jar
```

### 4. 训练推荐模型

```bash
spark-submit --class com.movie.model.RecommendationModel \
  --master local[*] \
  target/recommend-engine-1.0.jar
```

### 5. 启动后端服务

```bash
cd webapp/backend

# 安装依赖
pip install fastapi uvicorn psycopg2-binary pyspark numpy

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 6. 启动前端

```bash
cd webapp/frontend
npm install
npm start
```

访问 http://localhost:3000

## 推荐算法命令行

```bash
cd recommend-engine

# ALS 个性化推荐
python -m algorithms.cli --user_id 123 --topN 10

# User-CF 协同过滤
python -m algorithms.cli --user_cf 123 --topN 10

# 相似电影推荐
python -m algorithms.cli --movie_id 19995 --topN 10

# 按类型推荐
python -m algorithms.cli --genre Comedy --topN 10
```

## API 接口

后端启动后访问 http://localhost:5000/docs 查看 Swagger 文档。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录 |
| `/api/auth/register` | POST | 用户注册 |
| `/api/movies/search` | GET | 搜索电影 |
| `/api/movies/{id}` | GET | 电影详情 |
| `/api/recommendations/user/{id}` | GET | 用户推荐 |
| `/api/recommendations/similar/{id}` | GET | 相似电影 |
| `/api/ratings` | POST | 提交评分 |
| `/api/ratings/user/{id}` | GET | 用户评分列表 |

## 推荐算法

| 算法 | 文件 | 说明 |
|------|------|------|
| ALS | `als_recommend.py` | 矩阵分解，适合有评分历史的用户 |
| User-CF | `user_cf.py` | 用户协同过滤，基于相似用户 |
| Content | `content_based.py` | TF-IDF 内容相似度 |

## 数据库配置

修改 `recommend-engine/algorithms/db.py` 和 `webapp/backend/config.py`：

```python
host = "localhost"
port = 5432
user = "postgres"
password = "postgres"
dbname = "movie_db"
```

## 注意事项

1. 图片文件需放在 `webapp/backend/static/img/` 目录下
2. HDFS 路径默认为 `hdfs://node1:9000/user/a1386/`
3. ALS 模型保存在 HDFS: `/user/a1386/movie_model/als_tmdb`
