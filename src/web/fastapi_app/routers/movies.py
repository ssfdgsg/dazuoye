"""电影路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.movie_service import (
    get_movie_detail,
    search_movies,
    get_rankings,
    get_all_genres,
    get_movies_by_genre,
)

router = APIRouter(prefix="/api", tags=["电影"])


@router.get("/movie/{movie_id}")
async def movie_detail(movie_id: int):
    """获取电影详情"""
    movie = get_movie_detail(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail=f"Movie ID {movie_id} not found")
    return movie


@router.get("/search")
async def search(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
):
    """搜索电影"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query is required")
    
    results = search_movies(q, limit)
    return {"query": q, "total": len(results), "results": results}


@router.get("/rankings")
async def rankings(
    type: str = Query("rating", description="排行榜类型: rating/popularity/new/boxoffice"),
    genre: str = Query("all", description="类型筛选"),
    year_from: str = Query("", description="起始年份"),
    year_to: str = Query("", description="结束年份"),
    limit: int = Query(50, ge=1, le=200),
):
    """获取排行榜"""
    if type not in ["rating", "popularity", "new", "boxoffice"]:
        raise HTTPException(status_code=400, detail="Invalid rank type")
    
    return get_rankings(type, genre, year_from, year_to, limit)


@router.get("/genres")
async def genres():
    """获取所有电影类型"""
    return {"genres": get_all_genres()}


@router.get("/movies/by-genre")
async def movies_by_genre(
    genre: str = Query("all", description="电影类型"),
    limit: int = Query(12, ge=1, le=50),
):
    """按类型获取电影"""
    movies = get_movies_by_genre(genre, limit)
    return {"movies": movies, "genre": genre}
