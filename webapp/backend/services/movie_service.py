"""电影业务逻辑"""
import random
from typing import Optional
from database import get_connection
from psycopg2.extras import RealDictCursor


def get_movie_detail(movie_id: int) -> Optional[dict]:
    """获取电影详情"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            b.movie_id, b.title, b.genres, b.release_date, b.runtime,
            b.vote_average, b.vote_count, b.popularity_score,
            b.budget_million, b.revenue,
            b.keywords as basic_keywords, b.production_companies as basic_companies,
            f.keywords as feature_keywords, f.production_companies as feature_companies
        FROM movie_basic b
        LEFT JOIN movie_features f ON b.movie_id = f.movie_id
        WHERE b.movie_id = %s
    """, (movie_id,))
    
    movie = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not movie:
        return None
    
    keywords_str = movie["basic_keywords"] or movie["feature_keywords"] or ""
    companies_str = movie["basic_companies"] or movie["feature_companies"] or ""
    
    return {
        "id": movie["movie_id"],
        "title": movie["title"],
        "genres": movie["genres"].split(",") if movie["genres"] else [],
        "release_date": str(movie["release_date"]) if movie["release_date"] else None,
        "runtime": movie["runtime"],
        "rating": float(movie["vote_average"]) if movie["vote_average"] else 0.0,
        "vote_count": movie["vote_count"],
        "popularity": float(movie["popularity_score"]) if movie["popularity_score"] else 0.0,
        "budget": float(movie["budget_million"]) if movie["budget_million"] else 0.0,
        "revenue": movie["revenue"] or "0",
        "overview": f"{movie['title']} - {movie['genres']}" if movie["genres"] else "No overview",
        "keywords": [k.strip() for k in keywords_str.split(",") if k.strip()],
        "production_companies": [c.strip() for c in companies_str.split(",") if c.strip()],
        "language": "en",
        "poster": f"static/img/{movie['movie_id']}.webp",
    }


def search_movies(query: str, limit: int = 20) -> list:
    """搜索电影"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    pattern = f"%{query}%"
    cursor.execute("""
        SELECT movie_id, title, genres, release_date, runtime, vote_average, vote_count, popularity_score
        FROM movie_basic
        WHERE title ILIKE %s OR genres ILIKE %s OR keywords ILIKE %s
        ORDER BY popularity_score DESC NULLS LAST, vote_average DESC NULLS LAST
        LIMIT %s
    """, (pattern, pattern, pattern, limit))
    
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        {
            "id": m["movie_id"],
            "title": m["title"],
            "genres": m["genres"].split(",") if m["genres"] else [],
            "release_date": str(m["release_date"]) if m["release_date"] else None,
            "runtime": m["runtime"],
            "rating": float(m["vote_average"]) if m["vote_average"] else 0.0,
            "vote_count": m["vote_count"],
            "popularity": float(m["popularity_score"]) if m["popularity_score"] else 0.0,
            "poster": f"static/img/{m['movie_id']}.webp",
        }
        for m in movies
    ]


def get_rankings(rank_type: str, genre: str = "all", year_from: str = "", year_to: str = "", limit: int = 50) -> list:
    """获取排行榜"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    sql = """
        SELECT movie_id, title, genres, release_date, runtime, vote_average, vote_count, popularity_score, revenue
        FROM movie_basic WHERE 1=1
    """
    params = []
    
    if genre != "all":
        genre_map = {
            "action": "Action", "comedy": "Comedy", "drama": "Drama",
            "sci-fi": "Science Fiction", "romance": "Romance", "thriller": "Thriller"
        }
        db_genre = genre_map.get(genre.lower(), genre.title())
        sql += " AND genres ILIKE %s"
        params.append(f"%{db_genre}%")
    
    if year_from:
        sql += " AND EXTRACT(YEAR FROM release_date) >= %s"
        params.append(int(year_from))
    if year_to:
        sql += " AND EXTRACT(YEAR FROM release_date) <= %s"
        params.append(int(year_to))
    
    if rank_type == "rating":
        sql += " AND vote_count >= 100 AND vote_average > 0 ORDER BY vote_average DESC, vote_count DESC"
    elif rank_type == "popularity":
        sql += " AND popularity_score IS NOT NULL ORDER BY popularity_score DESC"
    elif rank_type == "new":
        sql += " AND release_date IS NOT NULL ORDER BY release_date DESC"
    elif rank_type == "boxoffice":
        sql += " AND revenue IS NOT NULL AND revenue != '' ORDER BY CAST(revenue AS BIGINT) DESC"
    else:
        cursor.close()
        conn.close()
        return []
    
    sql += f" LIMIT {limit}"
    cursor.execute(sql, params)
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [
        {
            "rank": idx,
            "id": m["movie_id"],
            "title": m["title"],
            "genres": m["genres"].split(",") if m["genres"] else [],
            "release_date": str(m["release_date"]) if m["release_date"] else None,
            "runtime": m["runtime"],
            "rating": float(m["vote_average"]) if m["vote_average"] else 0.0,
            "vote_count": m["vote_count"],
            "popularity": float(m["popularity_score"]) if m["popularity_score"] else 0.0,
            "revenue": m["revenue"] or "0",
            "poster": f"static/img/{m['movie_id']}.webp",
        }
        for idx, m in enumerate(movies, 1)
    ]


def get_all_genres() -> list:
    """获取所有电影类型"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT DISTINCT genres FROM movie_basic WHERE genres IS NOT NULL AND genres != ''")
    
    genres_set = set()
    for row in cursor.fetchall():
        if row["genres"]:
            for genre in row["genres"].split(","):
                g = genre.strip()
                if g:
                    genres_set.add(g)
    
    cursor.close()
    conn.close()
    return sorted(list(genres_set))


def get_movies_by_genre(genre: str = "all", limit: int = 12) -> list:
    """按类型获取电影"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if genre == "all" or not genre:
        cursor.execute("""
            SELECT movie_id, title, genres, release_date, vote_average, popularity_score
            FROM movie_basic WHERE vote_average IS NOT NULL
            ORDER BY popularity_score DESC NULLS LAST, vote_average DESC NULLS LAST LIMIT %s
        """, (limit * 3,))
    else:
        cursor.execute("""
            SELECT movie_id, title, genres, release_date, vote_average, popularity_score
            FROM movie_basic WHERE genres ILIKE %s AND vote_average IS NOT NULL
            ORDER BY popularity_score DESC NULLS LAST, vote_average DESC NULLS LAST LIMIT %s
        """, (f"%{genre}%", limit * 3))
    
    movies = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not movies:
        return []
    
    random.shuffle(movies)
    return [
        {
            "id": m["movie_id"],
            "title": m["title"],
            "genre": m["genres"].split(",") if m["genres"] else [],
            "rating": float(m["vote_average"]) if m["vote_average"] else 0.0,
            "poster": f"static/img/{m['movie_id']}.webp",
        }
        for m in movies[:limit]
    ]
