package com.movie.preprocess

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import com.alibaba.fastjson.JSON
import java.util.Base64

/**
 * TMDB 电影数据预处理
 * 功能：数据清洗、特征提取、TF-IDF 向量化
 */
object MoviePreprocess {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("TMDBMoviePreprocess")
      .master("local[*]")
      .config("spark.driver.memory", "2g")
      .config("spark.executor.memory", "4g")
      .getOrCreate()

    import spark.implicits._

    try {
      val rawDF = readTMDBData(spark, "hdfs://node1:9000/user/a1386/movie_data/raw/tmdb_5000_movies.csv")
      val total = rawDF.count()
      println(s"✅ 加载 $total 条记录")

      val cleanedDF = cleanTMDBData(rawDF)
      val featureDF = buildMovieFeatures(cleanedDF, spark)
        .filter(col("movie_id").isNotNull && col("title").isNotNull && col("title") =!= "")

      saveToHDFS(featureDF, "hdfs://node1:9000/user/a1386/movie_data/processed/tmdb_movies")

      // movie_basic
      val movieBasicDF = featureDF.select(
        col("movie_id"), col("title"), col("release_date"), col("runtime"),
        col("vote_average"), col("vote_count"), col("budget"), col("budget_million"),
        col("revenue"), col("revenue_million"), col("profit_ratio"), col("popularity"),
        col("popularity_score"), col("genres"), col("genre_diversity"),
        col("keywords"), col("production_companies"), col("status")
      )
      saveToPostgreSQL(movieBasicDF, "movie_basic", "jdbc:postgresql://localhost:5432/movie_db")

      // movie_features
      val movieFeaturesDF = featureDF.select(
        col("movie_id"), col("overview"), col("keywords"), col("keyword_count"),
        col("production_companies"), col("original_language"),
        col("spoken_languages"), col("tfidf_features")
      )
      saveToPostgreSQL(movieFeaturesDF, "movie_features", "jdbc:postgresql://localhost:5432/movie_db")

      // user_ratings
      val userRatingDF = generateSimulatedRatings(spark, featureDF)
      saveToPostgreSQL(userRatingDF, "user_ratings", "jdbc:postgresql://localhost:5432/movie_db")

      println("✅ 全量数据预处理完成（HDFS + PostgreSQL）")
    } catch {
      case e: Exception =>
        println(s"❌ 预处理失败：${e.getMessage}")
        e.printStackTrace()
    } finally {
      spark.stop()
    }
  }

  def readTMDBData(spark: SparkSession, path: String): DataFrame = {
    val tmdbSchema = new StructType()
      .add("budget", LongType).add("genres", StringType).add("homepage", StringType)
      .add("id", IntegerType).add("keywords", StringType).add("original_language", StringType)
      .add("original_title", StringType).add("overview", StringType).add("popularity", DoubleType)
      .add("production_companies", StringType).add("production_countries", StringType)
      .add("release_date", StringType).add("revenue", LongType).add("runtime", DoubleType)
      .add("spoken_languages", StringType).add("status", StringType).add("tagline", StringType)
      .add("title", StringType).add("vote_average", DoubleType).add("vote_count", IntegerType)

    spark.read.option("header", "true").option("quote", "\"").option("escape", "\"")
      .schema(tmdbSchema).csv(path)
  }

  def cleanTMDBData(rawDF: DataFrame): DataFrame = {
    val parseJsonUDF = udf((jsonStr: String) => {
      try {
        if (jsonStr == null || jsonStr.trim.isEmpty) "Unknown"
        else JSON.parseArray(jsonStr.replace("'", "\""))
          .toArray().map(_.asInstanceOf[com.alibaba.fastjson.JSONObject].getString("name")).mkString(",")
      } catch { case _: Exception => "Unknown" }
    })

    val parseLanguagesUDF = udf((jsonStr: String) => {
      try {
        if (jsonStr == null || jsonStr.trim.isEmpty) "Unknown"
        else JSON.parseArray(jsonStr.replace("'", "\""))
          .toArray().map(_.asInstanceOf[com.alibaba.fastjson.JSONObject].getString("iso_639_1")).mkString(",")
      } catch { case _: Exception => "Unknown" }
    })

    rawDF.withColumnRenamed("id", "movie_id")
      .withColumn("genre_names", parseJsonUDF(col("genres")))
      .withColumn("keywords_str", parseJsonUDF(col("keywords")))
      .withColumn("production_companies_str", parseJsonUDF(col("production_companies")))
      .withColumn("spoken_languages_str", parseLanguagesUDF(col("spoken_languages")))
      .withColumn("overview", when(col("overview").isNull || col("overview") === "", "No overview available").otherwise(col("overview")))
      .withColumn("release_date", to_date(col("release_date"), "yyyy-MM-dd"))
      .withColumn("runtime", col("runtime").cast(IntegerType))
      .withColumn("budget", col("budget").cast(LongType))
      .withColumn("revenue", col("revenue").cast(LongType))
      .withColumn("status", when(col("status").isNull, "Released").otherwise(col("status")))
  }

  def buildMovieFeatures(cleanDF: DataFrame, spark: SparkSession): DataFrame = {
    import spark.implicits._

    val keywordCountUDF = udf((keywords: String) => if (keywords == "Unknown") 0 else keywords.split(",").length)
    val profitRatioUDF = udf((budget: java.lang.Long, revenue: java.lang.Long) => {
      if (budget == null || revenue == null || budget == 0L) 0.0 else revenue.toDouble / budget.toDouble
    })
    val popularityScoreUDF = udf((popularity: java.lang.Double, voteCount: java.lang.Integer) => {
      val p = if (popularity == null) 0.0 else popularity.doubleValue()
      val v = if (voteCount == null) 0.0 else voteCount.doubleValue()
      p * 0.6 + (v / 1000) * 0.4
    })

    val tokenizer = new org.apache.spark.ml.feature.Tokenizer().setInputCol("overview").setOutputCol("words")
    val remover = new org.apache.spark.ml.feature.StopWordsRemover().setInputCol("words").setOutputCol("filtered_words")
    val hashingTF = new org.apache.spark.ml.feature.HashingTF().setInputCol("filtered_words").setOutputCol("tf_vector").setNumFeatures(1000)
    val idf = new org.apache.spark.ml.feature.IDF().setInputCol("tf_vector").setOutputCol("tfidf_vector")

    val tokenizedDF = tokenizer.transform(cleanDF)
    val filteredDF = remover.transform(tokenizedDF)
    val tfDF = hashingTF.transform(filteredDF)
    val idfModel = idf.fit(tfDF)
    val textFeatureDF = idfModel.transform(tfDF)

    textFeatureDF
      .withColumn("keyword_count", keywordCountUDF(col("keywords_str")))
      .withColumn("genre_diversity", size(split(col("genre_names"), ",")))
      .withColumn("profit_ratio", profitRatioUDF(col("budget"), col("revenue")).cast(DecimalType(10, 2)))
      .withColumn("popularity_score", popularityScoreUDF(col("popularity"), col("vote_count")).cast(DecimalType(10, 6)))
      .withColumn("budget_million", (col("budget").cast(DoubleType) / 1000000).cast(DecimalType(10, 2)))
      .withColumn("revenue_million", (col("revenue").cast(DoubleType) / 1000000).cast(DecimalType(10, 2)))
      .withColumn("tfidf_features", udf((vec: org.apache.spark.ml.linalg.Vector) => {
        val bytes = java.nio.ByteBuffer.allocate(vec.size * 8)
        bytes.order(java.nio.ByteOrder.LITTLE_ENDIAN)
        vec.toArray.foreach(bytes.putDouble)
        Base64.getEncoder.encodeToString(bytes.array())
      }).apply(col("tfidf_vector")))
      .select(
        col("movie_id"), col("title"), col("release_date"), col("runtime"),
        col("vote_average").cast(DecimalType(3, 1)), col("vote_count"),
        col("budget"), col("budget_million"), col("revenue"), col("revenue_million"),
        col("profit_ratio"), col("popularity").cast(DecimalType(10, 6)), col("popularity_score"),
        col("genre_names").alias("genres"), col("genre_diversity"),
        col("keywords_str").alias("keywords"), col("production_companies_str").alias("production_companies"),
        col("status"), col("overview"), col("original_language"),
        col("spoken_languages_str").alias("spoken_languages"), col("keyword_count"), col("tfidf_features")
      )
  }

  def generateSimulatedRatings(spark: SparkSession, movieDF: DataFrame, userCount: Int = 500): DataFrame = {
    import spark.implicits._
    val validMovies = movieDF.select(col("movie_id").cast(IntegerType), col("genres"))
      .filter(col("movie_id").isNotNull).collect()
      .flatMap(row => try { Some((row.getInt(0), row.getString(1))) } catch { case _: Exception => None })
      .groupBy(_._1).map(_._2.head).toArray  // Deduplicate by movie_id

    if (validMovies.isEmpty) return Seq.empty[(Int, Int, Double)].toDF("user_id", "movie_id", "rating")

    val ratings = (1 to userCount).flatMap { userId =>
      val userPref = userId % 5 match {
        case 0 => "Action,Adventure"; case 1 => "Animation,Family"; case 2 => "Drama,Romance"
        case 3 => "Comedy,Crime"; case 4 => "Science Fiction,Fantasy"
      }
      val numRatings = scala.util.Random.nextInt(11) + 10
      val shuffledMovies = scala.util.Random.shuffle(validMovies.toSeq).take(numRatings)
      shuffledMovies.map { case (movieId, movieGenre) =>
        val baseRating = scala.util.Random.nextDouble() * 4 + 1
        val rating = if (movieGenre != null && userPref.split(",").exists(movieGenre.contains)) math.min(baseRating + 1, 5.0) else baseRating
        (userId, movieId, BigDecimal(rating).setScale(1, BigDecimal.RoundingMode.HALF_UP).toDouble)
      }
    }
    println(s"✅ 生成 ${ratings.size} 条模拟评分")
    ratings.toDF("user_id", "movie_id", "rating")
  }

  def saveToHDFS(df: DataFrame, path: String): Unit = {
    df.write.mode("overwrite").option("compression", "snappy").parquet(path)
    println(s"✅ HDFS: $path")
  }

  def saveToPostgreSQL(df: DataFrame, tableName: String, jdbcUrl: String): Unit = {
    val props = new java.util.Properties()
    props.setProperty("user", "postgres")
    props.setProperty("password", "postgres")
    props.setProperty("driver", "org.postgresql.Driver")

    try {
      val conn = java.sql.DriverManager.getConnection(jdbcUrl, "postgres", "postgres")
      val stmt = conn.createStatement()
      try { stmt.execute(s"TRUNCATE TABLE $tableName CASCADE") } catch { case _: Exception => }
      stmt.close(); conn.close()

      df.write.mode("append").jdbc(jdbcUrl, tableName, props)
      println(s"✅ PostgreSQL: $tableName (${df.count()} rows)")
    } catch {
      case e: Exception => println(s"❌ $tableName 失败: ${e.getMessage}"); throw e
    }
  }
}
