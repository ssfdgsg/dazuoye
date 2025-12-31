"""命令行入口"""
import argparse
import json
from .db import DatabaseManager
from .user_cf import UserCFRecommender
from .content_based import ContentBasedRecommender
from .als_recommend import ALSRecommender


def init_spark():
    """初始化 SparkSession"""
    from pyspark.sql import SparkSession
    return SparkSession.builder \
        .appName("MovieRecommenderService") \
        .master("local[*]") \
        .config("spark.driver.memory", "2g") \
        .config("spark.jars", "/home/a1386/Desktop/BigData/movieRecommendSystemV1/lib/postgresql-42.7.1.jar") \
        .getOrCreate()


def main():
    parser = argparse.ArgumentParser(description="电影推荐服务")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--movie_id", type=int, help="电影ID（相似推荐）")
    group.add_argument("--user_id", type=int, help="用户ID（个性化推荐，使用ALS）")
    group.add_argument("--user_cf", type=int, help="用户ID（User-CF协同过滤推荐）")
    group.add_argument("--genre", type=str, help="电影类别（如 Comedy、Action 等）")
    parser.add_argument("--topN", type=int, default=10, help="推荐数量")

    args = parser.parse_args()

    spark = None
    db = DatabaseManager()

    try:
        if args.movie_id:
            recommender = ContentBasedRecommender(db)
            result = recommender.recommend_similar(args.movie_id, args.topN)
        elif args.user_id:
            spark = init_spark()
            recommender = ALSRecommender(db, spark)
            result = recommender.recommend(args.user_id, args.topN)
        elif args.user_cf:
            recommender = UserCFRecommender(db)
            result = recommender.recommend(args.user_cf, args.topN)
        elif args.genre:
            recommender = ContentBasedRecommender(db)
            result = recommender.recommend_by_genre(args.genre, args.topN)
        else:
            result = {"error": "未指定推荐类型"}

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
    finally:
        if spark:
            spark.stop()
        db.close()


if __name__ == "__main__":
    main()
