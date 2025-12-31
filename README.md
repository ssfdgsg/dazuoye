# 电影推荐系统

基于 Spark + FastAPI + React 的电影推荐系统，支持 ALS 协同过滤、User-CF、TF-IDF 内容推荐。

## 项目结构

```
├── recommend-engine/          # 推荐引擎
│   ├── spark/                 # Spark 批处理 (Scala)
│   ├── algorithms/            # Python 推荐算法
│   ├── sql/init.sql           # 数据库初始化
│   └── pom.xml
├── webapp/
│   ├── backend/               # FastAPI 后端 (Python)
│   └── frontend/              # React 前端
├── data/                      # TMDB 电影数据
└── test_recommend.sh          # 测试脚本
```

## 环境要求

- Java 8 + Scala 2.12
- Spark 3.1.3 + Hadoop 3.1.3
- Python 3.8+ (uv 包管理)
- Node.js 16+
- PostgreSQL 14+

## 快速开始

### 1. 初始化数据库

```bash
# 创建数据库和表
cp recommend-engine/sql/init.sql /tmp/
sudo -u postgres psql -f /tmp/init.sql
```

### 2. 数据预处理 (Spark)

```bash
cd recommend-engine

# 编译 Spark 项目
mvn clean package -DskipTests

# 上传数据到 HDFS
hdfs dfs -mkdir -p /user/$(whoami)/movie_data/raw
hdfs dfs -put ../data/tmdb_5000_movies.csv /user/$(whoami)/movie_data/raw/

# 运行预处理
spark-submit --class com.movie.preprocess.MoviePreprocess \
  --master local[*] \
  target/recommend-engine-1.0.jar
```

### 3. 启动后端

```bash
cd webapp/backend

# 使用 uv 运行
uv run ./main.py

# 或使用 pip
pip install -r requirements.txt
python main.py
```

后端运行在 http://localhost:5000

### 4. 启动前端

```bash
cd webapp/frontend
npm install
npm start
```

前端运行在 http://localhost:3000

## 推荐算法测试

```bash
# 运行测试脚本
./test_recommend.sh [用户ID] [推荐数量]

# 示例
./test_recommend.sh 1 10
```

### 命令行调用

```bash
cd recommend-engine

# User-CF 协同过滤 (无需 Spark)
python3 -m algorithms.cli --user_cf 1 --topN 10

# 相似电影推荐
python3 -m algorithms.cli --movie_id 19995 --topN 10

# 按类型推荐
python3 -m algorithms.cli --genre Action --topN 10

# ALS 推荐 (需要 Spark)
python3 -m algorithms.cli --user_id 1 --topN 10
```

## API 接口

访问 http://localhost:5000/docs 查看完整 API 文档。

| 接口 | 说明 |
|------|------|
| `POST /api/auth/register` | 用户注册 |
| `POST /api/auth/login` | 用户登录 |
| `GET /api/movies/search?q=xxx` | 搜索电影 |
| `GET /api/movies/{id}` | 电影详情 |
| `GET /api/movies/rankings/{type}` | 排行榜 (rating/popularity/new/boxoffice) |
| `GET /api/movies/recommendations` | 个性化推荐 |
| `GET /api/movies/{id}/similar` | 相似电影 |
| `POST /api/ratings` | 提交评分 |
| `GET /api/ratings/user/{id}` | 用户评分记录 |

## 数据库配置

编辑 `webapp/backend/config.py`:

```python
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/movie_db"
```

## 电影封面

封面图片放在 `webapp/backend/static/img/` 目录，命名格式: `{movie_id}.webp`

## 推荐算法说明

| 算法 | 特点 | 适用场景 |
|------|------|----------|
| ALS | 矩阵分解，准确度高 | 有评分历史的用户 |
| User-CF | 基于相似用户，实时性好 | 冷启动用户 |
| Content | TF-IDF 文本相似度 | 相似电影推荐 |

## 常见问题

**Q: PostgreSQL 连接失败 (Peer authentication failed)**
```bash
# 使用 -h localhost 强制 TCP 连接
psql -U postgres -h localhost -d movie_db
```

**Q: Spark 提交报错 Invalid signature file**
确保 pom.xml 中 maven-shade-plugin 配置了排除签名文件。

**Q: 图片加载 404**
检查图片是否在 `webapp/backend/static/img/` 目录，文件名是否为 `{movie_id}.webp`。
