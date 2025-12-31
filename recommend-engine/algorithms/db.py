"""数据库连接管理"""
import psycopg2
from psycopg2.extras import RealDictCursor


class DatabaseManager:
    """PostgreSQL 数据库管理器"""
    
    def __init__(self, host="localhost", port=5432, user="postgres", 
                 password="postgres", dbname="movie_db"):
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "dbname": dbname
        }
        self._conn = None
    
    def connect(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.config)
        return self._conn
    
    def cursor(self, dict_cursor=True):
        """获取游标"""
        conn = self.connect()
        if dict_cursor:
            return conn.cursor(cursor_factory=RealDictCursor)
        return conn.cursor()
    
    def close(self):
        """关闭连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
    
    def table_exists(self, table_name):
        """检查表是否存在"""
        cursor = self.cursor(dict_cursor=False)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, (table_name,))
        return cursor.fetchone()[0]
    
    def get_movie_details(self, movie_ids):
        """获取电影详情"""
        if not movie_ids:
            return {}
        cursor = self.cursor()
        placeholders = ','.join(['%s'] * len(movie_ids))
        cursor.execute(f"""
            SELECT movie_id, title, genres, release_date, vote_average 
            FROM movie_basic 
            WHERE movie_id IN ({placeholders})
        """, movie_ids)
        return {m['movie_id']: m for m in cursor.fetchall()}
