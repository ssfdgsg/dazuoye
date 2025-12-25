PROJECT_DIR="/home/a1386/Desktop/BigData/movieRecommendSystemV1"
JAR_PATH="$PROJECT_DIR/target/movie-recommendation-system-1.0.jar"
PYTHON_SCRIPT="$PROJECT_DIR/code/python/movie_recommender.py"
JDBC_JAR="$PROJECT_DIR/lib/mysql-connector-j-8.0.33.jar"

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
