#!/bin/bash
# 冷启动推荐测试脚本

BASE_URL="http://localhost:5000"
COOKIE_FILE="/tmp/test_session_503.cookie"

echo "========================================"
echo "冷启动推荐测试 - 用户503"
echo "========================================"

# 1. 登录（使用旧的user_id方式，如果用户503存在）
echo -e "\n[1] 尝试登录用户503..."
LOGIN_RESULT=$(curl -s -c $COOKIE_FILE -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 503}')

echo "登录结果: $LOGIN_RESULT"

# 2. 测试用户推荐API
echo -e "\n[2] 测试 /api/user/503/recommend (应使用冷启动)..."
curl -s -b $COOKIE_FILE "$BASE_URL/api/user/503/recommend?topN=3" | python3.8 -m json.tool

# 3. 测试强制刷新推荐
echo -e "\n[3] 测试 /api/movies/recommendations?force=1 (应使用冷启动)..."
curl -s -b $COOKIE_FILE "$BASE_URL/api/movies/recommendations?topN=3&force=1" | python3.8 -m json.tool

# 4. 查看用户503的评分记录
echo -e "\n[4] 查看用户503的评分记录..."
mysql -u root -proot123 movie_db -e "SELECT user_id, movie_id, rating FROM user_ratings WHERE user_id = 503 LIMIT 5;" 2>/dev/null

# 5. 测试用户501（在训练集中的用户）
echo -e "\n[5] 对比：用户501推荐 (应使用ALS模型)..."
curl -s "$BASE_URL/api/user/501/recommend?topN=3" | python3.8 -m json.tool | grep -E "method|movie_id|title" | head -10

echo -e "\n========================================"
echo "测试完成"
echo "========================================"

# 清理
rm -f $COOKIE_FILE
