#!/bin/bash
# 电影推荐系统一键部署运行脚本
# 适用环境：Java 1.8 + Hadoop 3.1.3 + Spark 3.1.3 + PostgreSQL 14+ + Python 3.8
# 作者：a1386
# 日期：2024

# -------------------------- 环境检查 --------------------------
echo "==================================== 环境检查 ===================================="
check_env() {
    local cmd=$1
    local name=$2
    if ! command -v $cmd &> /dev/null; then
        echo "错误：未找到 $name 命令，请确保环境变量配置正确！"
        exit 1
    fi
}

check_env "java" "Java"
check_env "scala" "Scala"
check_env "hadoop" "Hadoop"
check_env "spark-submit" "Spark"
check_env "python3.8" "Python 3.8"
check_env "psql" "PostgreSQL"
check_env "mvn" "Maven"

# 检查HDFS是否启动
if ! hdfs dfs -test -d /; then
    echo "错误：HDFS未启动，请先执行 start-dfs.sh 和 start-yarn.sh"
    exit 1
fi

# 检查PostgreSQL是否启动
if ! systemctl is-active --quiet postgresql; then
    echo "错误：PostgreSQL未启动，请执行 sudo systemctl start postgresql"
    exit 1
fi

echo "✅ 所有环境检查通过"

# -------------------------- 配置参数 --------------------------
echo -e "\n==================================== 配置参数 ===================================="
LOCAL_CSV_PATH="/home/a1386/Desktop/tmdb_5000_movies.csv"
HDFS_RAW_PATH="hdfs://node1:9000/user/a1386/movie_data/raw/"
HDFS_PROCESSED_PATH="hdfs://node1:9000/user/a1386/movie_data/processed/"
HDFS_FEATURE_PATH="hdfs://node1:9000/user/a1386/movie_data/features/"
HDFS_MODEL_PATH="hdfs://node1:9000/user/a1386/movie_model/"
PG_DB="movie_db"
PG_USER="postgres"
PG_PASS="postgres"
PROJECT_DIR="/home/a1386/Desktop/BigData/movieRecommendSystemV1"
JAR_PATH="$PROJECT_DIR/target/movie-recommendation-system-1.0.jar"
PYTHON_SCRIPT="$PROJECT_DIR/code/python/movie_recommender.py"
JDBC_JAR="$PROJECT_DIR/lib/postgresql-42.6.0.jar"

echo "本地CSV路径：$LOCAL_CSV_PATH"
echo "HDFS原始数据路径：$HDFS_RAW_PATH"
echo "PostgreSQL数据库：$PG_DB"
echo "项目目录：$PROJECT_DIR"

# -------------------------- 数据准备 --------------------------
echo -e "\n==================================== 数据准备 ===================================="
# 创建HDFS目录
hdfs dfs -mkdir -p $HDFS_RAW_PATH $HDFS_PROCESSED_PATH $HDFS_FEATURE_PATH $HDFS_MODEL_PATH

# 上传本地CSV到HDFS
if ! hdfs dfs -test -f $HDFS_RAW_PATH/movies.csv; then
    echo "正在上传本地CSV到HDFS..."
    hdfs dfs -put $LOCAL_CSV_PATH $HDFS_RAW_PATH
    echo "✅ CSV文件上传完成"
else
    echo "⚠️ HDFS原始数据已存在，跳过上传"
fi

# 初始化PostgreSQL数据库
echo "正在初始化PostgreSQL数据库..."
PGPASSWORD=$PG_PASS psql -U $PG_USER -f $PROJECT_DIR/code/sql/movie_tables.sql
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL数据库初始化完成"
else
    echo "错误：PostgreSQL数据库初始化失败"
    exit 1
fi

# -------------------------- 编译打包 --------------------------
echo -e "\n==================================== 编译打包 ===================================="
cd $PROJECT_DIR
mvn clean package -Dmaven.test.skip=true
if [ -f $JAR_PATH ]; then
    echo "✅ Maven编译打包完成"
else
    echo "错误：Maven打包失败"
    exit 1
fi

# -------------------------- 执行数据预处理 --------------------------
echo -e "\n==================================== 数据预处理 ===================================="
spark-submit \
    --class com.movie.preprocess.MoviePreprocess \
    --master yarn \
    --deploy-mode client \
    --driver-memory 2g \
    --executor-memory 4g \
    --jars $JDBC_JAR \
    $JAR_PATH

if [ $? -eq 0 ]; then
    echo "✅ 数据预处理完成（HDFS+PostgreSQL）"
else
    echo "错误：数据预处理失败"
    exit 1
fi

# -------------------------- 训练推荐模型 --------------------------
echo -e "\n==================================== 模型训练 ===================================="
spark-submit \
    --class com.movie.model.RecommendationModel \
    --master yarn \
    --deploy-mode client \
    --driver-memory 2g \
    --executor-memory 4g \
    --jars $JDBC_JAR \
    $JAR_PATH

if [ $? -eq 0 ]; then
    echo "✅ 推荐模型训练完成（物品CF+ALS）"
else
    echo "错误：模型训练失败"
    exit 1
fi

# -------------------------- 测试推荐服务 --------------------------
echo -e "\n==================================== 测试推荐服务 ===================================="
# 测试1：基于电影ID推荐（阿凡达 movie_id=19995）
echo "=== 测试1：电影《阿凡达》的Top5相似推荐 ==="
python3.8 $PYTHON_SCRIPT --movie_id 19995 --topN 5

# 测试2：基于用户ID推荐（用户ID=100）
echo -e "\n=== 测试2：用户ID=100的Top5个性化推荐 ==="
python3.8 $PYTHON_SCRIPT --user_id 100 --topN 5

if [ $? -eq 0 ]; then
    echo "✅ 推荐服务测试成功"
else
    echo "错误：推荐服务测试失败"
    exit 1
fi

# -------------------------- 部署完成 --------------------------
echo -e "\n==================================== 部署完成 ===================================="
echo "🎉 电影推荐系统一键部署运行成功！"
echo -e "\n核心组件状态："
echo "1. HDFS数据：已存储（原始/预处理/特征/模型）"
echo "2. PostgreSQL数据：movie_basic/movie_features/user_ratings/user_recommendations"
echo "3. 推荐模型：物品CF（相似推荐）+ ALS（个性化推荐）"
echo "4. 推荐服务：Python脚本支持命令行调用"
echo -e "\n常用命令："
echo "• 相似电影推荐：python3.8 $PYTHON_SCRIPT --movie_id [电影ID] --topN [数量]"
echo "• 个性化推荐：python3.8 $PYTHON_SCRIPT --user_id [用户ID] --topN [数量]"
echo "• 查看HDFS数据：hdfs dfs -ls $HDFS_PROCESSED_PATH"
echo "• 停止Hadoop：stop-dfs.sh && stop-yarn.sh"
