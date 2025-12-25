PROJECT_DIR="/home/a1386/Desktop/BigData/movieRecommendSystemV1"
PYTHON_SCRIPT="$PROJECT_DIR/code/python/movie_recommender.py"
# -------------------------- 测试推荐服务 --------------------------
echo -e "\n==================================== 测试推荐服务 ===================================="
# 测试1：基于电影ID推荐（阿凡达 movie_id=19995）
#echo "=== 测试1：电影《阿凡达》的Top5相似推荐 ==="
#python3.8 $PYTHON_SCRIPT --movie_id 19995 --topN 5

# 测试2：基于用户ID推荐（用户ID=502）
echo -e "\n=== 测试1：用户ID=501的Top5个性化推荐 ==="
python3.8 $PYTHON_SCRIPT --user_id 501 --topN 5
echo -e "\n=== 测试4：用户ID=504的Top5个性化推荐 ==="
python3.8 $PYTHON_SCRIPT --user_id 504 --topN 5

if [ $? -eq 0 ]; then
    echo "✅ 推荐服务测试成功"
else
    echo "错误：推荐服务测试失败"
    exit 1
fi
