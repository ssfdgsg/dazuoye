"""数据库连接管理"""
import mysql.connector
from contextlib import contextmanager
from config import get_settings


def get_connection():
    """获取数据库连接"""
    settings = get_settings()
    return mysql.connector.connect(
        host=settings.db_host,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
        charset="utf8mb4"
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
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # user_ratings 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_ratings (
            user_id INT COMMENT '用户ID',
            movie_id INT COMMENT '电影ID',
            rating DECIMAL(2,1) COMMENT '评分（1-10分）',
            rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评分时间',
            PRIMARY KEY (user_id, movie_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # user_recommendations 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_recommendations (
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            predicted_rating FLOAT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
