"""ALS 矩阵分解推荐算法"""
import sys
import subprocess
import numpy as np
from .db import DatabaseManager


class ALSRecommender:
    """基于 ALS 的推荐器"""
    
    def __init__(self, db: DatabaseManager, spark_session=None):
        self.db = db
        self.spark = spark_session
        self.model_path = "hdfs://node1:9000/user/a1386/movie_model/als_tmdb"
    
    def set_spark(self, spark_session):
        """设置 Spark Session"""
        self.spark = spark_session
    
    def recommend(self, user_id, top_n=10):
        """为用户推荐电影"""
        if not self._check_model_exists():
            return {"error": "ALS模型不存在，请先运行模型训练"}
        
        if not self.spark:
            return {"error": "Spark Session 未初始化"}
        
        try:
            from pyspark.ml.recommendation import ALSModel
            
            als_model = ALSModel.load(self.model_path)
            print("[PROGRESS] model_loaded", file=sys.stderr, flush=True)
            
            # 生成推荐
            user_df = self.spark.createDataFrame([(user_id,)], ["user_id"])
            rec_df = als_model.recommendForUserSubset(user_df, top_n)
            
            if rec_df.count() == 0:
                # 冷启动用户
                return self._cold_start_recommend(als_model, user_id, top_n)
            
            # 解析推荐结果
            collected = rec_df.collect()
            if not collected:
                return {"user_id": user_id, "recommendations": []}
            
            rec_list = collected[0]["recommendations"]
            print("[PROGRESS] als_recommendations_built", file=sys.stderr, flush=True)
            
            movie_ids = [str(rec["movie_id"]) for rec in rec_list]
            predict_ratings = [round(rec["rating"], 2) for rec in rec_list]
            
            # 获取电影详情
            movies = self.db.get_movie_details([int(mid) for mid in movie_ids])
            print("[PROGRESS] details_loaded", file=sys.stderr, flush=True)
            
            results = []
            for mid, rating in zip(movie_ids, predict_ratings):
                movie = movies.get(int(mid))
                if movie:
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
    
    def _cold_start_recommend(self, als_model, user_id, top_n):
        """冷启动用户推荐"""
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT movie_id, rating FROM user_ratings WHERE user_id = %s", (user_id,))
            user_ratings = cursor.fetchall()
            
            if not user_ratings:
                return {"user_id": user_id, "recommendations": []}
            
            print("[PROGRESS] ratings_loaded", file=sys.stderr, flush=True)
            
            # 加载电影隐向量
            item_factors_df = als_model.itemFactors
            item_factors_dict = {row['id']: row['features'] for row in item_factors_df.collect()}
            print("[PROGRESS] item_factors_loaded", file=sys.stderr, flush=True)
            
            # 构建矩阵
            X_list, y_list, rated_movie_ids = [], [], []
            for rating_row in user_ratings:
                movie_id = rating_row['movie_id']
                if movie_id in item_factors_dict:
                    X_list.append(np.array(item_factors_dict[movie_id]))
                    y_list.append(float(rating_row['rating']))
                    rated_movie_ids.append(movie_id)
            
            if not X_list:
                return {"user_id": user_id, "recommendations": []}
            
            # 最小二乘法求解用户隐向量
            X = np.array(X_list)
            y = np.array(y_list)
            lambda_reg = 0.1
            n_factors = X.shape[1]
            
            XtX_reg = X.T.dot(X) + lambda_reg * np.eye(n_factors)
            Xty = X.T.dot(y)
            user_vector = np.linalg.solve(XtX_reg, Xty)
            print("[PROGRESS] user_vector_solved", file=sys.stderr, flush=True)
            
            # 预测评分
            predictions = []
            for movie_id, item_vector in item_factors_dict.items():
                if movie_id not in rated_movie_ids:
                    pred_rating = float(np.dot(user_vector, np.array(item_vector)))
                    predictions.append({'movie_id': movie_id, 'pred_rating': pred_rating})
            
            predictions.sort(key=lambda x: x['pred_rating'], reverse=True)
            top_predictions = predictions[:top_n]
            print("[PROGRESS] predictions_scored", file=sys.stderr, flush=True)
            
            if not top_predictions:
                return {"user_id": user_id, "recommendations": []}
            
            # 获取电影详情
            movie_ids = [p['movie_id'] for p in top_predictions]
            movies = self.db.get_movie_details(movie_ids)
            print("[PROGRESS] details_loaded", file=sys.stderr, flush=True)
            
            results = []
            for pred in top_predictions:
                movie = movies.get(pred['movie_id'])
                if movie:
                    results.append({
                        "movie_id": pred['movie_id'],
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
    
    def _check_model_exists(self):
        """检查 ALS 模型是否存在"""
        try:
            check_cmd = f"hdfs dfs -test -e {self.model_path}/metadata"
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            return result.returncode == 0
        except:
            return False
