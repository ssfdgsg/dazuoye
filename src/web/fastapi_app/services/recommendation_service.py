"""推荐业务逻辑"""
import os
import json
import random
import subprocess
import numpy as np
from typing import Optional
from database import get_connection
from psycopg2.extras import RealDictCursor
from utils.tfidf import decode_tfidf, cosine_similarity


def get_similar_movies(movie_id: int, limit: int = 12) -> Optional[list]:
    """获取相似电影（基于 TF-IDF）"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 获取目标电影
    cursor.execute("""
        SELECT m.movie_id, f.tfidf_features
        FROM movie_basic m
        JOIN movie_features f ON m.movie_id = f.movie_id
        WHERE m.movie_id = %s
    """, (movie_id,))
    
    target = cursor.fetchone()
    if not target:
        cursor.close()
        conn.close()
        return None
    
    target_vec = decode_tfidf(target.get("tfidf_features"))
    if target_vec is None or np.linalg.norm(target_vec) == 0:
        cursor.close()
        conn.close()
        return None
    
    # 获取候选电影
    cursor.execute("""
        SELECT m.movie_id, m.title, m.genres, m.vote_average, m.vote_count, f.tfidf_features
        FROM movie_basic m
        JOIN movie_features f ON m.movie_id = f.movie_id
        WHERE m.movie_id != %s AND f.tfidf_features IS NOT NULL
        LIMIT 500
    """, (movie_id,))
    
    candidates = cursor.fetchall()
    cursor.close()
    conn.close()
    
    results = []
    for row in candidates:
        vec = decode_tfidf(row.get("tfidf_features"))
        if vec is None:
            continue
        sim = cosine_similarity(target_vec, vec)
        results.append({
            "id": row["movie_id"],
            "title": row["title"],
            "genres": row["genres"].split(",") if row["genres"] else [],
            "rating": float(row["vote_average"]) if row["vote_average"] else 0.0,
            "vote_count": row["vote_count"],
            "similarity": round(sim, 4),
            "poster": f"img/{row['movie_id']}.webp",
        })
    
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]


def get_user_recommendations(user_id: int, topN: int = 10) -> dict:
    """获取用户推荐（优先 ALS，回退热门）"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 尝试预计算推荐
    cursor.execute("""
        SELECT r.movie_id, m.title, m.genres, m.vote_average, m.release_date, r.predicted_rating
        FROM user_recommendations r
        JOIN movie_basic m ON r.movie_id = m.movie_id
        WHERE r.user_id = %s
        ORDER BY r.predicted_rating DESC LIMIT %s
    """, (user_id, topN))
    
    als_rows = cursor.fetchall()
    if als_rows:
        cursor.close()
        conn.close()
        return {
            "user_id": user_id,
            "recommendations": [
                {
                    "movie_id": r["movie_id"],
                    "title": r["title"],
                    "genres": r["genres"].split("|") if r["genres"] else [],
                    "release_date": str(r["release_date"]) if r["release_date"] else None,
                    "vote_average": float(r["vote_average"]) if r["vote_average"] else None,
                    "predicted_rating": float(r["predicted_rating"]) if r["predicted_rating"] else None,
                }
                for r in als_rows
            ],
            "method": "als_model",
        }
    
    # 回退：热门电影排除已评分
    cursor.execute("SELECT movie_id FROM user_ratings WHERE user_id = %s", (user_id,))
    seen = {row["movie_id"] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT movie_id, title, genres, release_date, vote_average, popularity_score
        FROM movie_basic ORDER BY popularity_score DESC NULLS LAST, vote_average DESC NULLS LAST LIMIT 80
    """)
    
    candidates = [r for r in cursor.fetchall() if r["movie_id"] not in seen]
    cursor.close()
    conn.close()
    
    return {
        "user_id": user_id,
        "recommendations": [
            {
                "movie_id": r["movie_id"],
                "title": r["title"],
                "genres": r.get("genres"),
                "release_date": str(r.get("release_date")) if r.get("release_date") else None,
                "vote_average": float(r.get("vote_average")) if r.get("vote_average") else None,
            }
            for r in candidates[:topN]
        ],
        "method": "fallback",
    }


def get_personalized_recommendations(user_id: Optional[int], topN: int = 10, force_refresh: bool = False) -> dict:
    """获取个性化推荐"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 强制刷新：调用 ALS 脚本
    if user_id and force_refresh:
        try:
            script_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "code", "python", "movie_recommender.py")
            )
            cmd = ["python3.8", script_path, "--user_id", str(user_id), "--topN", str(topN)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and proc.stdout:
                data = json.loads(proc.stdout.strip())
                recs = data.get("recommendations") or []
                if recs:
                    cursor.close()
                    conn.close()
                    return {
                        "movies": [
                            {
                                "id": r.get("movie_id"),
                                "title": r.get("title"),
                                "genre": r.get("genre", "").split("|") if r.get("genre") else [],
                                "rating": float(r.get("vote_average")) if r.get("vote_average") else 0.0,
                                "poster": f"/img/{r.get('movie_id')}.webp",
                                "prediction": float(r.get("predict_rating")) if r.get("predict_rating") else 0.0,
                            }
                            for r in recs
                        ],
                        "user_id": user_id,
                        "method": "als_model",
                    }
        except Exception as e:
            print(f"强制刷新 ALS 失败: {e}")
    
    # 已登录用户：尝试预计算推荐
    if user_id and not force_refresh:
        cursor.execute("""
            SELECT r.movie_id, m.title, m.genres, m.vote_average, m.release_date, r.predicted_rating as prediction
            FROM user_recommendations r
            JOIN movie_basic m ON r.movie_id = m.movie_id
            WHERE r.user_id = %s
            ORDER BY r.predicted_rating DESC LIMIT %s
        """, (user_id, topN))
        
        recs = cursor.fetchall()
        if recs:
            cursor.close()
            conn.close()
            return {
                "movies": [
                    {
                        "id": r["movie_id"],
                        "title": r["title"],
                        "genre": r["genres"].split("|") if r["genres"] else [],
                        "rating": float(r["vote_average"]) if r["vote_average"] else 0.0,
                        "poster": f"/img/{r['movie_id']}.webp",
                        "prediction": float(r["prediction"]) if r["prediction"] else 0.0,
                        "release_date": r["release_date"].year if r["release_date"] else None,
                    }
                    for r in recs
                ],
                "user_id": user_id,
                "method": "als_model",
            }
    
    # 回退策略
    if user_id:
        cursor.execute("""
            SELECT m.movie_id, m.title, m.genres, m.vote_average, m.popularity_score
            FROM movie_basic m
            WHERE m.movie_id NOT IN (SELECT movie_id FROM user_ratings WHERE user_id = %s)
            AND m.vote_average IS NOT NULL
            ORDER BY m.popularity_score DESC NULLS LAST, m.vote_average DESC NULLS LAST LIMIT %s
        """, (user_id, topN * 2))
    else:
        cursor.execute("""
            SELECT movie_id, title, genres, vote_average, popularity_score
            FROM movie_basic WHERE vote_average IS NOT NULL
            ORDER BY popularity_score DESC NULLS LAST, vote_average DESC NULLS LAST LIMIT %s
        """, (topN * 2,))
    
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not movies:
        return {"movies": [], "user_id": user_id, "method": "fallback"}
    
    random.shuffle(movies)
    return {
        "movies": [
            {
                "id": m["movie_id"],
                "title": m["title"],
                "genre": m["genres"].split(",") if m["genres"] else [],
                "rating": float(m["vote_average"]) if m["vote_average"] else 0.0,
                "poster": f"img/{m['movie_id']}.webp",
            }
            for m in movies[:topN]
        ],
        "user_id": user_id,
        "method": "fallback",
    }
