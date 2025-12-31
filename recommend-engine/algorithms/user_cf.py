"""User-CF 用户协同过滤推荐算法"""
import numpy as np
from .db import DatabaseManager


class UserCFRecommender:
    """基于用户协同过滤的推荐器"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def recommend(self, user_id, top_n=10, sim_user_count=20):
        """
        User-CF 推荐算法：
        1. 计算目标用户与其他用户的评分相似度（皮尔逊相关系数）
        2. 找到最相似的 K 个用户
        3. 用相似用户的评分加权预测目标用户未看过的电影评分
        """
        cursor = self.db.cursor()
        
        if not self.db.table_exists("user_ratings"):
            return {"error": "user_ratings 表不存在"}
        
        # 获取目标用户评分
        cursor.execute("SELECT movie_id, rating FROM user_ratings WHERE user_id = %s", (user_id,))
        target_ratings = {r['movie_id']: float(r['rating']) for r in cursor.fetchall()}
        
        if not target_ratings:
            return {"error": f"用户 {user_id} 没有评分记录"}
        
        # 获取其他用户评分
        cursor.execute("SELECT user_id, movie_id, rating FROM user_ratings WHERE user_id != %s", (user_id,))
        user_ratings_map = {}
        for r in cursor.fetchall():
            uid = r['user_id']
            if uid not in user_ratings_map:
                user_ratings_map[uid] = {}
            user_ratings_map[uid][r['movie_id']] = float(r['rating'])
        
        # 计算相似度
        similarities = self._compute_similarities(target_ratings, user_ratings_map)
        
        if not similarities:
            return self._fallback_recommend(cursor, user_id, target_ratings, top_n)
        
        # 取最相似用户
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similar_users = similarities[:sim_user_count]
        
        # 预测评分
        predictions = self._predict_ratings(target_ratings, top_similar_users)
        predictions.sort(key=lambda x: x['pred_rating'], reverse=True)
        top_predictions = predictions[:top_n]
        
        if not top_predictions:
            return {"user_id": user_id, "recommendations": [], "method": "user_cf"}
        
        # 获取电影详情
        movie_ids = [p['movie_id'] for p in top_predictions]
        movies = self.db.get_movie_details(movie_ids)
        
        results = []
        for pred in top_predictions:
            mid = pred['movie_id']
            if mid in movies:
                m = movies[mid]
                results.append({
                    "movie_id": mid,
                    "title": m["title"],
                    "genre": m["genres"],
                    "release_date": str(m["release_date"]) if m["release_date"] else "未知",
                    "vote_average": float(m["vote_average"]) if m["vote_average"] else 0.0,
                    "predict_rating": round(pred['pred_rating'], 2),
                    "poster": f"/static/img/{mid}.webp"
                })
        
        return {
            "user_id": user_id,
            "recommendations": results,
            "method": "user_cf",
            "similar_users_count": len(top_similar_users)
        }
    
    def _compute_similarities(self, target_ratings, user_ratings_map):
        """计算用户相似度"""
        similarities = []
        target_mean = np.mean(list(target_ratings.values()))
        
        for other_uid, other_ratings in user_ratings_map.items():
            common_movies = set(target_ratings.keys()) & set(other_ratings.keys())
            if len(common_movies) < 1:
                continue
            
            if len(common_movies) < 3:
                # 余弦相似度
                sim = self._cosine_similarity(target_ratings, other_ratings, common_movies)
                sim *= (len(common_movies) / 3.0)
                if sim > 0.1:
                    similarities.append((other_uid, sim, other_ratings))
            else:
                # 皮尔逊相关系数
                sim = self._pearson_correlation(target_ratings, other_ratings, common_movies, target_mean)
                if sim > 0:
                    similarities.append((other_uid, sim, other_ratings))
        
        return similarities
    
    def _cosine_similarity(self, ratings1, ratings2, common_movies):
        """计算余弦相似度"""
        dot_product = sum(ratings1[mid] * ratings2[mid] for mid in common_movies)
        norm1 = np.sqrt(sum(ratings1[mid]**2 for mid in common_movies))
        norm2 = np.sqrt(sum(ratings2[mid]**2 for mid in common_movies))
        if norm1 > 0 and norm2 > 0:
            return dot_product / (norm1 * norm2)
        return 0.0
    
    def _pearson_correlation(self, ratings1, ratings2, common_movies, mean1):
        """计算皮尔逊相关系数"""
        mean2 = np.mean(list(ratings2.values()))
        numerator = 0.0
        denom1 = 0.0
        denom2 = 0.0
        
        for mid in common_movies:
            diff1 = ratings1[mid] - mean1
            diff2 = ratings2[mid] - mean2
            numerator += diff1 * diff2
            denom1 += diff1 ** 2
            denom2 += diff2 ** 2
        
        denom = np.sqrt(denom1) * np.sqrt(denom2)
        return numerator / denom if denom > 1e-9 else 0.0
    
    def _predict_ratings(self, target_ratings, similar_users):
        """预测未评分电影的分数"""
        candidate_movies = set()
        for _, _, ratings in similar_users:
            candidate_movies.update(ratings.keys())
        candidate_movies -= set(target_ratings.keys())
        
        predictions = []
        for mid in candidate_movies:
            weighted_sum = 0.0
            sim_sum = 0.0
            for _, sim, other_ratings in similar_users:
                if mid in other_ratings:
                    weighted_sum += sim * other_ratings[mid]
                    sim_sum += abs(sim)
            if sim_sum > 0:
                predictions.append({'movie_id': mid, 'pred_rating': weighted_sum / sim_sum})
        
        return predictions
    
    def _fallback_recommend(self, cursor, user_id, target_ratings, top_n):
        """回退策略：基于用户喜欢的类型推荐"""
        cursor.execute("""
            SELECT m.genres FROM movie_basic m
            JOIN user_ratings ur ON m.movie_id = ur.movie_id
            WHERE ur.user_id = %s AND m.genres IS NOT NULL
        """, (user_id,))
        
        genre_counts = {}
        for row in cursor.fetchall():
            if row['genres']:
                for g in row['genres'].split(','):
                    g = g.strip()
                    genre_counts[g] = genre_counts.get(g, 0) + 1
        
        if genre_counts:
            top_genre = max(genre_counts, key=genre_counts.get)
            cursor.execute("""
                SELECT movie_id, title, genres, release_date, vote_average
                FROM movie_basic
                WHERE genres ILIKE %s
                AND movie_id NOT IN (SELECT movie_id FROM user_ratings WHERE user_id = %s)
                ORDER BY vote_average DESC, vote_count DESC
                LIMIT %s
            """, (f"%{top_genre}%", user_id, top_n))
            
            results = [{
                "movie_id": m['movie_id'],
                "title": m["title"],
                "genre": m["genres"],
                "release_date": str(m["release_date"]) if m["release_date"] else "未知",
                "vote_average": float(m["vote_average"]) if m["vote_average"] else 0.0,
                "predict_rating": float(m["vote_average"]) if m["vote_average"] else 0.0,
                "poster": f"/static/img/{m['movie_id']}.webp"
            } for m in cursor.fetchall()]
            
            return {
                "user_id": user_id,
                "recommendations": results,
                "method": "genre_fallback",
                "message": f"基于您喜欢的类型 '{top_genre}' 推荐"
            }
        
        return {"user_id": user_id, "recommendations": [], "method": "user_cf", "message": "没有找到相似用户"}
