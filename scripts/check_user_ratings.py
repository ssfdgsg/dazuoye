#!/usr/bin/env python3
"""检查用户评分数据"""
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="movie_db"
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# 检查用户1的评分
print("=== 用户 1 的评分记录 ===")
cursor.execute("SELECT * FROM user_ratings WHERE user_id = 1")
ratings = cursor.fetchall()
print(f"评分数量: {len(ratings)}")
for r in ratings[:10]:
    print(f"  电影 {r['movie_id']}: {r['rating']}")

# 检查评分表总体情况
print("\n=== 评分表统计 ===")
cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users, COUNT(DISTINCT movie_id) as movies FROM user_ratings")
stats = cursor.fetchone()
print(f"总评分数: {stats['total']}")
print(f"用户数: {stats['users']}")
print(f"电影数: {stats['movies']}")

# 检查有多少用户与用户1有共同评分
print("\n=== 与用户 1 有共同评分的用户 ===")
cursor.execute("""
    SELECT ur2.user_id, COUNT(*) as common_count
    FROM user_ratings ur1
    JOIN user_ratings ur2 ON ur1.movie_id = ur2.movie_id AND ur2.user_id != 1
    WHERE ur1.user_id = 1
    GROUP BY ur2.user_id
    HAVING COUNT(*) >= 1
    ORDER BY common_count DESC
    LIMIT 10
""")
common_users = cursor.fetchall()
print(f"有共同评分的用户数: {len(common_users)}")
for u in common_users:
    print(f"  用户 {u['user_id']}: {u['common_count']} 部共同电影")

cursor.close()
conn.close()
