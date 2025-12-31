"""应用配置管理"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 数据库配置 (PostgreSQL)
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_name: str = "movie_db"
    
    # JWT 配置
    secret_key: str = "movie-recommendation-secret-key-2024"
    algorithm: str = "HS256"
    access_token_expire_days: int = 7
    
    # 服务配置
    port: int = 5000
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
