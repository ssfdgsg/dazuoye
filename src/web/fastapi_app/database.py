"""数据库连接管理 (PostgreSQL)"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import get_settings


def get_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        dbname=settings.db_name
    )


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def ensure_tables(cursor):
    """确保必要的表存在"""
    # users 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # user_ratings 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_ratings (
            user_id INT,
            movie_id INT,
            rating NUMERIC(3,1),
            rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        )
    """)
    
    # user_recommendations 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_recommendations (
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            predicted_rating FLOAT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        )
    """)
