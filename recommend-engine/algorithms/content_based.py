"""基于内容的推荐算法"""
import numpy as np
import base64
from .db import DatabaseManager


class ContentBasedRecommender:
    """基于内容的推荐器（TF-IDF 相似度）"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def recommend_similar(self, movie_id, top_n=10):
        """推荐与指定电影相似的电影"""
        cursor = self.db.cursor()
        
        if not self.db.table_exists("movie_features"):
            return {"error": "movie_features 表不存在"}
        
        # 获取目标电影
        target_movie = self._get_movie_with_features(cursor, movie_id)
        if not target_movie:
            return {"error": f"电影ID {movie_id} 不存在"}
        
        if not target_movie["tfidf_features"]:
            return {"error": f"电影ID {movie_id} 没有特征数据"}
        
        target_vec = self._decode_vector(target_movie["tfidf_features"])
        
        # 获取所有其他电影
        all_movies = self._get_all_movies_with_features(cursor, movie_id)
        if not all_movies:
            return {"error": "没有其他电影可用于相似度计算"}
        
        # 计算相似度
        results = []
        for movie in all_movies:
            if not movie["tfidf_features"]:
                continue
            
            vec = self._decode_vector(movie["tfidf_features"])
            similarity = self._cosine_similarity(target_vec, vec)
            
            results.append({
                "movie_id": movie["movie_id"],
                "title": movie["title"],
                "genre": movie["genres"],
                "similarity": round(similarity, 3)
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return {
            "movie_id": movie_id,
            "title": target_movie["title"],
            "recommendations": results[:top_n]
        }
    
    def recommend_by_genre(self, genre, top_n=10):
        """按类型推荐电影"""
        cursor = self.db.cursor()
        
        if not self.db.table_exists("movie_basic"):
            return {"error": "movie_basic 表不存在"}
        
        cursor.execute("""
            SELECT movie_id, title, genres, release_date, vote_average 
            FROM movie_basic 
            WHERE genres ILIKE %s 
            ORDER BY vote_average DESC, vote_count DESC 
            LIMIT %s
        """, (f"%{genre}%", top_n))
        
        movies = cursor.fetchall()
        if not movies:
            return {"error": f"没有找到类别为 '{genre}' 的电影"}
        
        for m in movies:
            if m["release_date"]:
                m["release_date"] = str(m["release_date"])
            if m["vote_average"]:
                m["vote_average"] = float(m["vote_average"])
        
        return {"genre": genre, "recommendations": movies}
    
    def _get_movie_with_features(self, cursor, movie_id):
        """获取电影及其特征"""
        cursor.execute("""
            SELECT m.movie_id, m.title, m.genres, f.tfidf_features 
            FROM movie_basic m 
            JOIN movie_features f ON m.movie_id = f.movie_id 
            WHERE m.movie_id = %s
        """, (movie_id,))
        movie = cursor.fetchone()
        
        if not movie:
            cursor.execute("""
                SELECT movie_id, title, genres, tfidf_features 
                FROM movie_basic WHERE movie_id = %s
            """, (movie_id,))
            movie = cursor.fetchone()
        
        return movie
    
    def _get_all_movies_with_features(self, cursor, exclude_movie_id):
        """获取所有电影及其特征"""
        cursor.execute("""
            SELECT m.movie_id, m.title, m.genres, f.tfidf_features 
            FROM movie_basic m 
            JOIN movie_features f ON m.movie_id = f.movie_id 
            WHERE m.movie_id != %s AND f.tfidf_features IS NOT NULL
        """, (exclude_movie_id,))
        movies = cursor.fetchall()
        
        if not movies:
            cursor.execute("""
                SELECT movie_id, title, genres, tfidf_features 
                FROM movie_basic 
                WHERE movie_id != %s AND tfidf_features IS NOT NULL
            """, (exclude_movie_id,))
            movies = cursor.fetchall()
        
        return movies
    
    def _decode_vector(self, encoded_str):
        """解码 Base64 特征向量"""
        if not encoded_str:
            return np.zeros(100)
        try:
            bytes_data = base64.b64decode(encoded_str)
            return np.frombuffer(bytes_data, dtype='<f8')
        except:
            return np.zeros(100)
    
    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if not np.isfinite(norm1) or not np.isfinite(norm2) or norm1 * norm2 < 1e-12:
            return 0.0
        
        dot = np.dot(vec1, vec2)
        if not np.isfinite(dot):
            return 0.0
        
        return dot / (norm1 * norm2)
