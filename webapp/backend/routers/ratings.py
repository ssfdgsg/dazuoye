"""评分路由"""
from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from models.schemas import RatingCreate, ALSStatus, ALSTaskStatus, ALSLogsResponse
from dependencies import get_current_user
from database import get_connection, ensure_tables
from services.als_worker import (
    enqueue_user_for_recompute,
    get_als_status,
    get_task_status,
    get_task_logs,
)

router = APIRouter(prefix="/api", tags=["评分"])


@router.post("/movie/{movie_id}/rate")
async def rate_movie(movie_id: int, rating: RatingCreate, user: dict = Depends(get_current_user)):
    """提交电影评分"""
    user_id = user["user_id"]
    
    conn = get_connection()
    cursor = conn.cursor()
    ensure_tables(cursor)
    conn.commit()
    
    # 检查是否已评分
    cursor.execute(
        "SELECT 1 FROM user_ratings WHERE user_id = %s AND movie_id = %s",
        (user_id, movie_id),
    )
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute(
            "UPDATE user_ratings SET rating = %s, rating_time = CURRENT_TIMESTAMP WHERE user_id = %s AND movie_id = %s",
            (rating.rating, user_id, movie_id),
        )
    else:
        cursor.execute(
            "INSERT INTO user_ratings (user_id, movie_id, rating, rating_time) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
            (user_id, movie_id, rating.rating),
        )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # 异步重算推荐
    try:
        enqueue_user_for_recompute(user_id)
    except Exception:
        pass
    
    return {"success": True, "message": "Rating submitted successfully"}


@router.get("/user/{user_id}/ratings")
async def user_ratings(user_id: int):
    """获取用户评分历史"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    ensure_tables(cursor)
    conn.commit()
    
    cursor.execute("""
        SELECT ur.movie_id, ur.rating, ur.rating_time,
               mb.title, mb.release_date, mb.genres, mb.vote_average, mb.popularity_score
        FROM user_ratings ur
        LEFT JOIN movie_basic mb ON ur.movie_id = mb.movie_id
        WHERE ur.user_id = %s
        ORDER BY ur.rating_time DESC
    """, (user_id,))
    
    ratings = cursor.fetchall()
    cursor.close()
    conn.close()
    
    total = len(ratings)
    avg = sum(float(r["rating"]) for r in ratings) / total if total > 0 else 0
    
    return {
        "success": True,
        "user_id": user_id,
        "total_ratings": total,
        "avg_rating": round(avg, 2),
        "ratings": [
            {
                "movie_id": r["movie_id"],
                "title": r["title"] or f"电影 {r['movie_id']}",
                "rating": float(r["rating"]),
                "rating_time": r["rating_time"].isoformat() if r["rating_time"] else None,
                "release_date": r["release_date"].isoformat() if r["release_date"] else None,
                "genres": r["genres"].split("|") if r["genres"] else [],
                "vote_average": float(r["vote_average"]) if r["vote_average"] else 0,
                "popularity": float(r["popularity_score"]) if r["popularity_score"] else 0,
                "poster": f"/img/{r['movie_id']}.webp",
            }
            for r in ratings
        ],
    }


@router.get("/als/status", response_model=ALSStatus)
async def als_status():
    """获取 ALS 任务状态"""
    return get_als_status()


@router.get("/als/task/{user_id}")
async def als_task(user_id: int):
    """获取用户任务状态"""
    return get_task_status(user_id)


@router.get("/als/logs/{user_id}", response_model=ALSLogsResponse)
async def als_logs(user_id: int):
    """获取用户任务日志"""
    logs = get_task_logs(user_id)
    return ALSLogsResponse(user_id=user_id, logs=logs, count=len(logs))
