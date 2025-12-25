import argparse
import pandas as pd
import numpy as np
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALSModel
from pyspark.ml.linalg import Vectors
import psycopg2
from psycopg2.extras import RealDictCursor
import base64
import json
import os
import subprocess
import sys

# 初始化SparkSession
def init_spark():
    return SparkSession.builder \
        .appName("MovieRecommenderService") \
        .master("local[*]") \
        .config("spark.driver.memory", "2g") \
        .config("spark.jars", "/home/a1386/Desktop/BigData/movieRecommendSystemV1/lib/postgresql-42.7.1.jar") \
        .getOrCreate()

# 初始化PostgreSQL连接
def init_db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        dbname="movie_db"
    )

# 解码Base64特征向量
def decode_vector(encoded_str):
    if encoded_str is None:
        return Vectors.zeros(100)  # 返回默认向量
    try:
        bytes_data = base64.b64decode(encoded_str)
        # 我们已将 Scala 写入改为小端序（little-endian），因此在 Python 中以 '<f8'（little-endian double）解码
        arr = np.frombuffer(bytes_data, dtype='<f8')
        return Vectors.dense(arr)
    except:
        return Vectors.zeros(100)  # 解码失败返回默认向量

# 检查表是否存在 (PostgreSQL)
def check_table_exists(db_conn, table_name):
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]

# 检查ALS模型是否存在
def check_als_model_exists(model_path):
    try:
        # 检查HDFS路径
        check_cmd = f"hdfs dfs -test -e {model_path}/metadata"
        result = subprocess.run(check_cmd, shell=True, capture_output=True)
        return result.returncode == 0
    except:
        return False

def recommend_by_genre(db_conn, genre, topN):
    """
    推荐指定类别的前N个电影，按评分（vote_average）降序。
    """
    cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    # 检查表是否存在
    if not check_table_exists(db_conn, "movie_basic"):
        return {"error": "movie_basic 表不存在，请先运行数据预处理"}
    # 支持模糊匹配类别（如 Comedy、Action）- PostgreSQL 使用 ILIKE
    query = """
        SELECT movie_id, title, genres, release_date, vote_average 
        FROM movie_basic 
        WHERE genres ILIKE %s 
        ORDER BY vote_average DESC, vote_count DESC 
        LIMIT %s
    """
    like_pattern = f"%{genre}%"
    cursor.execute(query, (like_pattern, topN))
    movies = cursor.fetchall()
    if not movies:
        return {"error": f"没有找到类别为 '{genre}' 的电影"}
    # 处理日期类型，转为字符串，避免 JSON 序列化报错
    for m in movies:
        if "release_date" in m and m["release_date"] is not None:
            m["release_date"] = str(m["release_date"])
    return {"genre": genre, "recommendations": movies}

# 基于电影ID推荐相似电影
def recommend_by_movie(spark, db_conn, movie_id, topN):
    cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    
    # 检查表是否存在
    if not check_table_exists(db_conn, "movie_features"):
        return {"error": "movie_features 表不存在，请先运行数据预处理"}
    
    # 获取目标电影特征 - 从 movie_basic 获取标题和类型
    cursor.execute("""
        SELECT m.movie_id, m.title, m.genres, f.tfidf_features 
        FROM movie_basic m 
        JOIN movie_features f ON m.movie_id = f.movie_id 
        WHERE m.movie_id = %s
    """, (movie_id,))
    target_movie = cursor.fetchone()
    
    if not target_movie:
        # 尝试直接从 movie_basic 获取（因为 movie_basic 也有 tfidf_features）
        cursor.execute("""
            SELECT movie_id, title, genres, tfidf_features 
            FROM movie_basic 
            WHERE movie_id = %s
        """, (movie_id,))
        target_movie = cursor.fetchone()
        
    if not target_movie:
        return {"error": f"电影ID {movie_id} 不存在"}
    
    if not target_movie["tfidf_features"]:
        return {"error": f"电影ID {movie_id} 没有特征数据"}
    
    # 解码目标电影特征向量
    target_vec = decode_vector(target_movie["tfidf_features"])
    
    # 获取所有电影特征
    cursor.execute("""
        SELECT m.movie_id, m.title, m.genres, f.tfidf_features 
        FROM movie_basic m 
        JOIN movie_features f ON m.movie_id = f.movie_id 
        WHERE m.movie_id != %s AND f.tfidf_features IS NOT NULL
    """, (movie_id,))
    all_movies = cursor.fetchall()
    
    if not all_movies:
        # 尝试直接从 movie_basic 获取
        cursor.execute("""
            SELECT movie_id, title, genres, tfidf_features 
            FROM movie_basic 
            WHERE movie_id != %s AND tfidf_features IS NOT NULL
        """, (movie_id,))
        all_movies = cursor.fetchall()
    
    if not all_movies:
        return {"error": "没有其他电影可用于相似度计算"}
    
    # 计算相似度
    results = []
    for movie in all_movies:
        try:
            if not movie["tfidf_features"]:
                continue
                
            vec = decode_vector(movie["tfidf_features"])
            # 避免除零和 NaN/Inf 问题
            norm_target = float(Vectors.norm(target_vec, 2))
            norm_movie = float(Vectors.norm(vec, 2))
            denom = norm_target * norm_movie
            similarity = 0.0
            # 使用阈值并检查有限性以避免 numpy 的 RuntimeWarning
            if np.isfinite(norm_target) and np.isfinite(norm_movie) and denom > 1e-12:
                try:
                    dot = float(target_vec.dot(vec))
                    if np.isfinite(dot):
                        similarity = dot / denom
                    else:
                        similarity = 0.0
                except Exception:
                    similarity = 0.0
            
            results.append({
                "movie_id": movie["movie_id"],
                "title": movie["title"],
                "genre": movie["genres"],
                "similarity": round(similarity, 3)
            })
        except Exception as e:
            print(f"计算电影 {movie['movie_id']} 相似度失败: {e}")
            continue
    
    # 排序取TopN
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return {
        "movie_id": movie_id, 
        "title": target_movie["title"], 
        "recommendations": results[:topN]
    }

# 冷启动用户推荐：利用用户评分和电影隐向量求解用户隐向量
def recommend_for_cold_start_user(spark, db_conn, als_model, user_id, topN):
    """
    对于不在训练集中的新用户，使用其评分数据和已有的电影隐向量，
    通过最小二乘法求解用户隐向量，然后进行推荐。
    
    算法：
    1. 获取用户的评分数据 R_u = [r_1, r_2, ..., r_n]
    2. 获取对应电影的隐向量 V = [v_1, v_2, ..., v_n]^T
    3. 求解用户隐向量 u = argmin ||R_u - u^T V^T||^2 + λ||u||^2
    4. 闭式解：u = (V^T V + λI)^{-1} V^T R_u
    5. 计算所有候选电影的预测评分并排序
    """
    try:
        # 1. 获取用户的评分数据
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT movie_id, rating 
            FROM user_ratings 
            WHERE user_id = %s
        """, (user_id,))
        user_ratings = cursor.fetchall()
        
        if not user_ratings or len(user_ratings) == 0:
            return {"user_id": user_id, "recommendations": []}
        print("[PROGRESS] ratings_loaded", file=sys.stderr, flush=True)
        
        # 2. 加载电影隐向量（itemFactors）
        item_factors_df = als_model.itemFactors
        item_factors_dict = {row['id']: row['features'] for row in item_factors_df.collect()}
        print("[PROGRESS] item_factors_loaded", file=sys.stderr, flush=True)
        
        # 3. 构建用户评分的电影隐向量矩阵和评分向量
        X_list = []  # 电影隐向量矩阵
        y_list = []  # 用户评分向量
        rated_movie_ids = []
        
        for rating_row in user_ratings:
            movie_id = rating_row['movie_id']
            rating = float(rating_row['rating'])
            
            if movie_id in item_factors_dict:
                X_list.append(np.array(item_factors_dict[movie_id]))
                y_list.append(rating)
                rated_movie_ids.append(movie_id)
        
        if len(X_list) == 0:
            return {"user_id": user_id, "recommendations": []}
        
        # 4. 使用最小二乘法求解用户隐向量
        X = np.array(X_list)  # shape: (n_ratings, n_factors)
        y = np.array(y_list)   # shape: (n_ratings,)
        
        # 加入正则化，避免过拟合和数值不稳定
        lambda_reg = 0.1
        n_factors = X.shape[1]
        
        # 求解：u = (X^T X + λI)^{-1} X^T y
        XtX = X.T.dot(X)  # (n_factors, n_factors)
        XtX_reg = XtX + lambda_reg * np.eye(n_factors)
        Xty = X.T.dot(y)  # (n_factors,)
        
        user_vector = np.linalg.solve(XtX_reg, Xty)  # (n_factors,)
        print("[PROGRESS] user_vector_solved", file=sys.stderr, flush=True)
        
        # 5. 计算所有电影的预测评分
        predictions = []
        for movie_id, item_vector in item_factors_dict.items():
            if movie_id in rated_movie_ids:
                continue  # 排除用户已评分的电影
            
            pred_rating = float(np.dot(user_vector, np.array(item_vector)))
            predictions.append({
                'movie_id': movie_id,
                'pred_rating': pred_rating
            })
        
        # 6. 按预测评分排序，取TopN
        predictions.sort(key=lambda x: x['pred_rating'], reverse=True)
        top_predictions = predictions[:topN]
        print("[PROGRESS] predictions_scored", file=sys.stderr, flush=True)
        
        # 7. 从PostgreSQL获取电影详情
        if not top_predictions:
            return {"user_id": user_id, "recommendations": []}
        
        movie_ids = [str(p['movie_id']) for p in top_predictions]
        placeholders = ','.join(['%s'] * len(movie_ids))
        cursor.execute(f"""
            SELECT movie_id, title, genres, release_date, vote_average 
            FROM movie_basic 
            WHERE movie_id IN ({placeholders})
        """, movie_ids)
        movies = cursor.fetchall()
        print("[PROGRESS] details_loaded", file=sys.stderr, flush=True)
        
        # 8. 构建结果
        movie_map = {m['movie_id']: m for m in movies}
        results = []
        
        for pred in top_predictions:
            movie_id = pred['movie_id']
            if movie_id in movie_map:
                movie = movie_map[movie_id]
                results.append({
                    "movie_id": movie_id,
                    "title": movie["title"],
                    "genre": movie["genres"],
                    "release_date": str(movie["release_date"]) if movie["release_date"] else "未知",
                    "vote_average": float(movie["vote_average"]) if movie["vote_average"] else 0.0,
                    "predict_rating": round(pred['pred_rating'], 2)
                })
        
        print("[PROGRESS] done", file=sys.stderr, flush=True)
        return {"user_id": user_id, "recommendations": results, "method": "cold_start_als"}
        
    except Exception as e:
        import traceback
        print(f"冷启动推荐失败: {str(e)}", file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return {"user_id": user_id, "recommendations": []}


# 基于用户ID推荐个性化电影
def recommend_by_user(spark, db_conn, user_id, topN):
    # 检查ALS模型是否存在
    model_path = "hdfs://node1:9000/user/a1386/movie_model/als_tmdb"
    
    if not check_als_model_exists(model_path):
        return {"error": "ALS模型不存在，请先运行模型训练"}
    
    try:
        # 加载ALS模型
        als_model = ALSModel.load(model_path)
        print("[PROGRESS] model_loaded", file=sys.stderr, flush=True)
        
        # 生成用户推荐
        user_df = spark.createDataFrame([(user_id,)], ["user_id"])
        rec_df = als_model.recommendForUserSubset(user_df, topN)
        
        # 检查是否有推荐结果
        count = rec_df.count()
        
        if count == 0:
            # 用户不在训练集中，启用冷启动推荐
            return recommend_for_cold_start_user(spark, db_conn, als_model, user_id, topN)
        
        # 解析推荐结果
        collected = rec_df.collect()
        
        if len(collected) == 0:
            return {"user_id": user_id, "recommendations": []}
        
        first_row = collected[0]
        rec_list = first_row["recommendations"]
        print("[PROGRESS] als_recommendations_built", file=sys.stderr, flush=True)
        
        movie_ids = [str(rec["movie_id"]) for rec in rec_list]
        predict_ratings = [round(rec["rating"], 2) for rec in rec_list]
        
        # 从PostgreSQL获取电影详情
        cursor = db_conn.cursor(cursor_factory=RealDictCursor)
        if movie_ids:
            placeholders = ','.join(['%s'] * len(movie_ids))
            query = f"""
                SELECT movie_id, title, genres, release_date, vote_average 
                FROM movie_basic 
                WHERE movie_id IN ({placeholders})
            """
            cursor.execute(query, movie_ids)
            movies = cursor.fetchall()
        else:
            movies = []
        print("[PROGRESS] details_loaded", file=sys.stderr, flush=True)
        
        # 匹配推荐排序和预测评分
        movie_map = {str(m["movie_id"]): m for m in movies}
        
        results = []
        for mid, rating in zip(movie_ids, predict_ratings):
            if mid in movie_map:
                movie = movie_map[mid]
                results.append({
                    "movie_id": int(mid),
                    "title": movie["title"],
                    "genre": movie["genres"],
                    "release_date": str(movie["release_date"]) if movie["release_date"] else "未知",
                    "vote_average": float(movie["vote_average"]) if movie["vote_average"] else 0.0,
                    "predict_rating": rating
                })
        print("[PROGRESS] done", file=sys.stderr, flush=True)
        return {"user_id": user_id, "recommendations": results}
        
    except Exception as e:
        import traceback
        print(f"推荐失败: {str(e)}", file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return {"error": f"加载ALS模型失败: {str(e)}"}

def main():
    parser = argparse.ArgumentParser(description="电影推荐服务")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--movie_id", type=int, help="电影ID（相似推荐）")
    group.add_argument("--user_id", type=int, help="用户ID（个性化推荐）")
    group.add_argument("--genre", type=str, help="电影类别（如 Comedy、Action 等）")
    parser.add_argument("--topN", type=int, default=10, help="推荐数量")

    args = parser.parse_args()

    spark = None
    db_conn = None

    try:
        # 只有基于用户/电影推荐才需要 Spark
        if args.movie_id or args.user_id:
            spark = init_spark()
        db_conn = init_db()

        if args.movie_id:
            result = recommend_by_movie(spark, db_conn, args.movie_id, args.topN)
        elif args.user_id:
            result = recommend_by_user(spark, db_conn, args.user_id, args.topN)
        elif args.genre:
            result = recommend_by_genre(db_conn, args.genre, args.topN)
        else:
            result = {"error": "未指定推荐类型"}

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
    finally:
        if spark:
            spark.stop()
        if db_conn:
            db_conn.close()

if __name__ == "__main__":
    main()
