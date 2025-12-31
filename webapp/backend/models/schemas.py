"""Pydantic 数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== 认证相关 =====
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    user_id: Optional[int] = None  # 兼容旧版


class UserResponse(BaseModel):
    success: bool
    user_id: int
    username: Optional[str] = None


class SessionResponse(BaseModel):
    logged_in: bool
    user_id: Optional[int] = None
    username: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===== 电影相关 =====
class MovieBase(BaseModel):
    id: int
    title: str
    genres: List[str] = []
    rating: float = 0.0
    poster: str


class MovieDetail(MovieBase):
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    vote_count: Optional[int] = None
    popularity: float = 0.0
    budget: float = 0.0
    revenue: str = "0"
    overview: str = ""
    keywords: List[str] = []
    production_companies: List[str] = []
    language: str = "en"


class MovieRanking(MovieBase):
    rank: int
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    vote_count: Optional[int] = None
    popularity: float = 0.0
    revenue: str = "0"


class SimilarMovie(MovieBase):
    vote_count: Optional[int] = None
    similarity: float


class SearchResult(BaseModel):
    query: str
    total: int
    results: List[MovieBase]


# ===== 推荐相关 =====
class RecommendedMovie(MovieBase):
    genre: List[str] = []
    prediction: Optional[float] = None
    release_date: Optional[int] = None


class RecommendationResponse(BaseModel):
    movies: List[RecommendedMovie]
    user_id: Optional[int] = None
    method: str = "fallback"


class UserRecommendation(BaseModel):
    movie_id: int
    title: str
    genres: List[str] = []
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    predicted_rating: Optional[float] = None


# ===== 评分相关 =====
class RatingCreate(BaseModel):
    rating: float = Field(..., ge=1.0, le=10.0)
    comment: Optional[str] = ""


class RatingRecord(BaseModel):
    movie_id: int
    title: str
    rating: float
    rating_time: Optional[str] = None
    release_date: Optional[str] = None
    genres: List[str] = []
    vote_average: float = 0.0
    popularity: float = 0.0
    poster: str


class UserRatingsResponse(BaseModel):
    success: bool
    user_id: int
    username: Optional[str] = None
    total_ratings: int
    avg_rating: float
    ratings: List[RatingRecord]


# ===== ALS 任务相关 =====
class ALSStatus(BaseModel):
    worker_started: bool
    queue_size: int
    pending_users: int


class ALSTaskStatus(BaseModel):
    status: str = "idle"
    progress: int = 0
    queued_at: Optional[float] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    message: Optional[str] = None
    result_count: Optional[int] = None
    method: Optional[str] = None
    last_error: Optional[str] = None
    queued: bool = False
    worker_started: bool = False


class ALSLogsResponse(BaseModel):
    user_id: int
    logs: List[str]
    count: int
