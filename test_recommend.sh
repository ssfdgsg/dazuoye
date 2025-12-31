#!/bin/bash

# 测试电影推荐系统
USER_ID=${1:-1}
TOP_N=${2:-5}

echo "=========================================="
echo "测试用户 $USER_ID 的推荐功能"
echo "=========================================="

cd "$(dirname "$0")"

# 1. 测试 User-CF 推荐（不需要 Spark/HDFS）
echo ""
echo ">>> 测试 User-CF 协同过滤推荐..."
python3 -m recommend-engine.algorithms.cli --user_cf $USER_ID --topN $TOP_N
echo ""

# 2. 测试内容推荐（基于电影相似度）
echo ">>> 测试内容推荐（电影ID=19995 Avatar）..."
python3 -m recommend-engine.algorithms.cli --movie_id 19995 --topN $TOP_N
echo ""

# 3. 测试按类型推荐
echo ">>> 测试按类型推荐 (Action)..."
python3 -m recommend-engine.algorithms.cli --genre Action --topN $TOP_N
echo ""

# 4. 测试 ALS 推荐（需要 Spark + HDFS）
echo ">>> 测试 ALS 推荐（需要 Spark 和 HDFS）..."
python3 -m recommend-engine.algorithms.cli --user_id $USER_ID --topN $TOP_N
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
