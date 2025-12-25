"""推荐路由"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from dependencies import get_current_user_optional
from services.recommendation_service import (
    get_similar_movies,
    get_user_recommendations,
    get_personalized_recommendations,
)

router = APIRouter(prefix="/api", tags=["推荐"])


@router.get("/similar-movies/{movie_id}")
async def similar_movies(movie_id: int, limit: int = Query(12, ge=1, le=50)):
    """获取相似电影"""
    results = get_similar_movies(movie_id, limit)
    if results is None:
        # 返回空数组而不是404，让前端可以正常处理
        return []
    return results


@router.get("/movie/{movie_id}/similar")
async def movie_similar(movie_id: int, topN: int = Query(5, ge=1, le=50)):
    """获取相似电影（兼容旧 API）"""
    results = get_similar_movies(movie_id, topN)
    if results is None:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found")
    
    # 返回旧格式
    return {
        "movie_id": movie_id,
        "recommendations": [
            {
                "movie_id": r["id"],
                "title": r["title"],
                "genres": ",".join(r["genres"]) if r["genres"] else None,
                "similarity": r["similarity"],
            }
            for r in results
        ],
    }


@router.get("/user/{user_id}/recommend")
async def user_recommend(user_id: int, topN: int = Query(10, ge=1, le=50)):
    """获取用户推荐"""
    return get_user_recommendations(user_id, topN)


@router.get("/user/{user_id}/recommend-cf")
async def user_recommend_cf(user_id: int, topN: int = Query(10, ge=1, le=50)):
    """获取 User-CF 协同过滤推荐"""
    import subprocess
    import json
    import os
    
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "code", "python", "movie_recommender.py")
    )
    cmd = ["python3", script_path, "--user_cf", str(user_id), "--topN", str(topN)]
    
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout.strip())
            return data
        else:
            raise HTTPException(status_code=500, detail="User-CF 推荐计算失败")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="推荐计算超时")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="推荐结果解析失败")


@router.get("/movies/recommendations")
async def recommendations(
    topN: int = Query(10, ge=1, le=50),
    force: str = Query("0", description="是否强制刷新"),
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """获取个性化推荐"""
    user_id = user.get("user_id") if user else None
    force_refresh = force == "1"
    return get_personalized_recommendations(user_id, topN, force_refresh)
