package com.movie.model

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.ml.recommendation.ALS
import org.apache.spark.ml.evaluation.RegressionEvaluator
import org.apache.spark.ml.linalg.Vectors
import java.util.Base64

/**
 * 基于 TMDB 数据集的推荐模型
 * 适配 Spark 3.1.3 + Scala 2.12.10 + PostgreSQL
 */
object RecommendationModel {
  // PostgreSQL 连接配置
  private val jdbcUrl = "jdbc:postgresql://localhost:5432/movie_db"
  private val jdbcUser = "postgres"
  private val jdbcPassword = "postgres"

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("TMDBMovieRecommendation")
      .master("local[*]")
      .config("spark.driver.memory", "4g")
      .config("spark.executor.memory", "8g")
      .getOrCreate()

    import spark.implicits._

    try {
      // 加载数据 - 使用 PostgreSQL
      val movieFeatureDF = loadFromPostgreSQL(
        spark,
        "SELECT m.movie_id, m.title, m.genres, m.release_date, f.tfidf_features " +
        "FROM movie_basic m JOIN movie_features f ON m.movie_id = f.movie_id"
      )

      val userRatingDF = loadFromPostgreSQL(
        spark,
        "SELECT user_id, movie_id, rating FROM user_ratings"
      )
      // 修正 cast 语法：先获取列再 cast
      val ratingDF = userRatingDF
        .select(
          col("user_id").cast(IntegerType),
          col("movie_id").cast(IntegerType),
          col("rating").cast(DoubleType)
        )

      // 模型1：物品协同过滤
      val itemCFResult = trainItemCFModel(movieFeatureDF, spark)
      val avatarSimilar = getSimilarMovies(19995, 10, itemCFResult, movieFeatureDF, spark)
      println("=== 《阿凡达》(movie_id=19995) 的 Top10 相似电影 ===")
      avatarSimilar.show(false)

      // 模型2：ALS 矩阵分解
      val alsModel = trainALSModel(ratingDF)
      alsModel.write.overwrite().save("hdfs://node1:9000/user/a1386/movie_model/als_tmdb")
      println("✅ ALS 模型已保存至 HDFS")

      // 生成用户推荐并保存到 PostgreSQL
      val userRecsDF = generateUserRecommendations(alsModel, 10, movieFeatureDF, spark)
      saveToPostgreSQL(
        userRecsDF.select("user_id", "movie_id", "predicted_rating", "recommend_rank"),
        "user_recommendations"
      )

      println("✅ 全量推荐模型训练完成")

    } catch {
      case e: Exception =>
        println(s"❌ 模型训练失败：${e.getMessage}")
        e.printStackTrace()
    } finally {
      spark.stop()
    }
  }

  /** 从 PostgreSQL 加载数据 */
  def loadFromPostgreSQL(spark: SparkSession, sql: String): DataFrame = {
    val jdbcProps = new java.util.Properties()
    jdbcProps.setProperty("user", jdbcUser)
    jdbcProps.setProperty("password", jdbcPassword)
    jdbcProps.setProperty("driver", "org.postgresql.Driver")

    spark.read.jdbc(jdbcUrl, s"($sql) AS tmp_table", jdbcProps)
  }

  /** 训练物品协同过滤模型 - 简化修复 */
def trainItemCFModel(movieDF: DataFrame, spark: SparkSession): DataFrame = {
    import spark.implicits._

    // 解码特征向量
    val decodeVectorUDF = udf((encoded: String) => {
      try {
        val bytes = Base64.getDecoder.decode(encoded)
        Vectors.dense(java.nio.ByteBuffer.wrap(bytes).asDoubleBuffer().array())
      } catch {
        case _: Exception => null
      }
    })

    // 计算余弦相似度
    val cosineSimilarityUDF = udf((vec1: org.apache.spark.ml.linalg.Vector, vec2: org.apache.spark.ml.linalg.Vector) => {
      if (vec1 == null || vec2 == null) 0.0
      else {
        val dot = vec1.dot(vec2)
        val norm1 = Vectors.norm(vec1, 2.0)
        val norm2 = Vectors.norm(vec2, 2.0)
        if (norm1 == 0 || norm2 == 0) 0.0 else dot / (norm1 * norm2)
      }
    })

    // 处理特征并计算相似度
    val featureDF = movieDF
      .filter(col("tfidf_features").isNotNull)
      .withColumn("tfidf_vector", decodeVectorUDF(col("tfidf_features")))
      .filter(col("tfidf_vector").isNotNull)

    featureDF.alias("a")
      .join(featureDF.alias("b"), col("a.movie_id") =!= col("b.movie_id"))
      .select(
        col("a.movie_id").alias("source_movie_id"),
        col("b.movie_id").alias("target_movie_id"),
        cosineSimilarityUDF(col("a.tfidf_vector"), col("b.tfidf_vector")).alias("similarity")
      )
      .filter(col("similarity") > 0.3)
      .orderBy(col("source_movie_id"), col("similarity").desc)
}

  /** 获取相似电影 - 修复第145行问题 */
def getSimilarMovies(movieId: Int, topN: Int, similarityDF: DataFrame, movieDF: DataFrame, spark: SparkSession): DataFrame = {
    import spark.implicits._

    // 确保输入数据有效
    if (similarityDF.isEmpty || movieDF.isEmpty) {
      println("⚠️ 警告：相似度数据或电影数据为空")
      return spark.emptyDataFrame
    }

    try {
      similarityDF
        .filter(col("source_movie_id") === lit(movieId))  // 使用 lit() 包装字面量
        .limit(topN)
        .join(movieDF, col("target_movie_id") === col("movie_id"))
        .select(
          col("target_movie_id").alias("movie_id"),
          col("title"),
          col("genres"),
          col("release_date"),
          col("similarity").cast(DecimalType(4, 3))
        )
        .orderBy(col("similarity").desc)
    } catch {
      case e: Exception =>
        println(s"❌ 获取相似电影失败: ${e.getMessage}")
        spark.emptyDataFrame
    }
}

  /** 训练 ALS 模型 */
  def trainALSModel(ratingDF: DataFrame): org.apache.spark.ml.recommendation.ALSModel = {
    val Array(trainDF, testDF) = ratingDF.randomSplit(Array(0.8, 0.2), seed = 42L)

    val als = new ALS()
      .setUserCol("user_id")
      .setItemCol("movie_id")
      .setRatingCol("rating")
      .setRank(50)
      .setMaxIter(10)
      .setRegParam(0.01)
      .setColdStartStrategy("drop")
      .setNonnegative(true)

    val model = als.fit(trainDF)

    // 模型评估
    val predictions = model.transform(testDF)
    val evaluator = new RegressionEvaluator()
      .setMetricName("rmse")
      .setLabelCol("rating")
      .setPredictionCol("prediction")

    val rmse = evaluator.evaluate(predictions)
    println(f"✅ ALS 模型评估完成，RMSE: $rmse%.4f")

    model
  }

  /** 生成用户推荐（修正 DecimalType 引用） */
  def generateUserRecommendations(model: org.apache.spark.ml.recommendation.ALSModel, topN: Int, movieDF: DataFrame, spark: SparkSession): DataFrame = {
    import spark.implicits._

    model.recommendForAllUsers(topN)
      .withColumn("recommendations", explode(col("recommendations")))
      .select(
        col("user_id"),
        col("recommendations.movie_id").alias("movie_id"),
        col("recommendations.rating").alias("predicted_rating"),
        (monotonically_increasing_id() % topN + 1).alias("recommend_rank")
      )
      .join(movieDF, "movie_id")
      .select(
        col("user_id"),
        col("movie_id"),
        col("title"),
        col("genres"),
        col("release_date"),
        col("predicted_rating").cast(DecimalType(4, 2)), // 修正 DecimalType 语法
        col("recommend_rank")
      )
  }

  /** 保存至 PostgreSQL */
  def saveToPostgreSQL(df: DataFrame, tableName: String): Unit = {
    val jdbcProps = new java.util.Properties()
    jdbcProps.setProperty("user", jdbcUser)
    jdbcProps.setProperty("password", jdbcPassword)
    jdbcProps.setProperty("driver", "org.postgresql.Driver")

    // 先清空表再写入
    try {
      val conn = java.sql.DriverManager.getConnection(jdbcUrl, jdbcUser, jdbcPassword)
      val stmt = conn.createStatement()
      try { stmt.execute(s"TRUNCATE TABLE $tableName CASCADE") } catch { case _: Exception => }
      stmt.close(); conn.close()
    } catch { case _: Exception => }

    df.write
      .mode("append")
      .jdbc(jdbcUrl, tableName, jdbcProps)
    println(s"✅ 推荐结果已保存至 PostgreSQL 表: $tableName (${df.count()} rows)")
  }
}
