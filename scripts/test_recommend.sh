#!/bin/bash

# 测试电影推荐系统
USER_ID=${1:-1}
TOP_N=${2:-5}

echo "=========================================="
echo "测试用户 $USER_ID 的推荐功能"
echo "=========================================="

cd "$(dirname "$0")/.."

# 1. 测试 User-CF 推荐（不需要 Spark/HDFS）
echo ""
echo ">>> 测试 User-CF 协同过滤推荐..."
python3 code/python/movie_recommender.py --user_cf $USER_ID --topN $TOP_N
echo ""

# 2. 测试 ALS 推荐（需要 Spark + HDFS）
echo ">>> 测试 ALS 推荐（需要 Spark 和 HDFS）..."
python3 code/python/movie_recommender.py --user_id $USER_ID --topN $TOP_N
echo ""

# 3. 测试按类型推荐
echo ">>> 测试按类型推荐 (Action)..."
python3 code/python/movie_recommender.py --genre Action --topN $TOP_N
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
