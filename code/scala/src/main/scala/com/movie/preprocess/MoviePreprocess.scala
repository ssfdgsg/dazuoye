package com.movie.preprocess

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import com.alibaba.fastjson.JSON
import java.util.Base64

/**
 * TMDB 电影数据集预处理类（修复文本空值问题）
 * 适配 Spark 3.1.3 + Scala 2.12.10
 */
object MoviePreprocess {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("TMDBMoviePreprocess")
      .master("local[*]")
      .config("spark.driver.memory", "2g")
      .config("spark.executor.memory", "4g")
      .config("spark.jars", "/home/a1386/Desktop/BigData/movieRecommendSystemV1/lib/postgresql-42.7.1.jar")
      .getOrCreate()

    import spark.implicits._

    try {
      // 读取原始数据
      val rawDF = readTMDBData(
        spark,
        "hdfs://node1:9000/user/a1386/movie_data/raw/tmdb_5000_movies.csv"
      )
      println(s"✅ 原始数据加载完成，共 ${rawDF.count()} 条记录")

      // 数据探查（重点关注 overview 空值）
      printDataProfiling(rawDF)

      // 数据清洗（新增文本空值处理）
      val cleanedDF = cleanTMDBData(rawDF)

      // 特征工程（确保无空值进入文本处理）
      val featureDF = buildMovieFeatures(cleanedDF, spark)

      // 保存结果
      saveToHDFS(
        featureDF,
        "hdfs://node1:9000/user/a1386/movie_data/processed/tmdb_movies"
      )

      saveToPostgreSQL(
        featureDF,
        "movie_basic",
        "jdbc:postgresql://localhost:5432/movie_db"
      )

      saveToPostgreSQL(
        featureDF.select("movie_id", "keywords", "keyword_count", "production_companies", "tfidf_features"),
        "movie_features",
        "jdbc:postgresql://localhost:5432/movie_db"
      )

      // 生成模拟评分
      val userRatingDF = generateSimulatedRatings(spark, featureDF)
      saveToPostgreSQL(
        userRatingDF,
        "user_ratings",
        "jdbc:postgresql://localhost:5432/movie_db"
      )

      println("✅ 全量数据预处理完成（HDFS + MySQL）")

    } catch {
      case e: Exception =>
        println(s"❌ 预处理失败：${e.getMessage}")
        e.printStackTrace()
    } finally {
      spark.stop()
    }
  }

  /** 读取 TMDB 数据集 */
  def readTMDBData(spark: SparkSession, path: String): DataFrame = {
    val tmdbSchema = new StructType()
      .add("budget", LongType)
      .add("genres", StringType)
      .add("homepage", StringType)
      .add("id", IntegerType)
      .add("keywords", StringType)
      .add("original_language", StringType)
      .add("original_title", StringType)
      .add("overview", StringType)
      .add("popularity", DoubleType)
      .add("production_companies", StringType)
      .add("production_countries", StringType)
      .add("release_date", StringType)
      .add("revenue", LongType)
      .add("runtime", DoubleType)
      .add("spoken_languages", StringType)
      .add("status", StringType)
      .add("tagline", StringType)
      .add("title", StringType)
      .add("vote_average", DoubleType)
      .add("vote_count", IntegerType)

    spark.read
      .option("header", "true")
      .option("sep", ",")
      .option("quote", "\"")
      .option("escape", "\"")
      .option("dateFormat", "yyyy-MM-dd")
      .schema(tmdbSchema)
      .csv(path)
  }

  /** 数据探查（重点输出 overview 空值统计） */
  def printDataProfiling(df: DataFrame): Unit = {
    println("=== 数据缺失值统计 ===")
    df.columns.foreach(colName => {
      val missingCnt = df.filter(col(colName).isNull || col(colName) === "").count()
      val missingRate = (missingCnt.toDouble / df.count()) * 100
      println(f"$colName: $missingCnt 条缺失 (${missingRate}%.2f%%)")
    })

    // 单独强调 overview 空值（Tokenizer 输入字段）
    val overviewNullCnt = df.filter(col("overview").isNull || col("overview") === "").count()
    println(s"\n⚠️ 关键提示：overview 字段空值/空字符串共 $overviewNullCnt 条，将在清洗阶段填充默认值")

    println("\n=== 关键字段异常值统计 ===")
    println(f"budget=0 的记录数：${df.filter(col("budget") === 0).count()}")
    println(f"revenue=0 的记录数：${df.filter(col("revenue") === 0).count()}")
    println(f"runtime 为空的记录数：${df.filter(col("runtime").isNull).count()}")
  }

  /** 数据清洗（核心修改：新增文本字段空值处理） */
  def cleanTMDBData(rawDF: DataFrame): DataFrame = {
    val parseJsonUDF = udf((jsonStr: String) => {
      try {
        if (jsonStr == null || jsonStr.trim.isEmpty) "Unknown"
        else JSON.parseArray(jsonStr.replace("'", "\""))
          .toArray()
          .map(_.asInstanceOf[com.alibaba.fastjson.JSONObject].getString("name"))
          .mkString(",")
      } catch {
        case _: Exception => "Unknown"
      }
    })

    rawDF
      .withColumnRenamed("id", "movie_id")
      // 解析 JSON 字段（先判断空值）
      .withColumn("genre_names", parseJsonUDF(col("genres")))
      .withColumn("keywords_str", parseJsonUDF(col("keywords")))
      .withColumn("production_companies_str", parseJsonUDF(col("production_companies")))
      // 文本字段空值处理（重点处理 overview，避免 Tokenizer 报错）
      .withColumn("overview", when(
        col("overview").isNull || col("overview") === "",
        "No overview available"  // 默认文本，避免空值
      ).otherwise(col("overview")))
      .withColumn("tagline", when(
        col("tagline").isNull || col("tagline") === "",
        "No tagline available"
      ).otherwise(col("tagline")))
      .withColumn("original_title", when(
        col("original_title").isNull || col("original_title") === "",
        col("title")  // 用 title 填充 original_title 空值
      ).otherwise(col("original_title")))
      // 其他字段清洗
      .withColumn("homepage", when(col("homepage").isNull || col("homepage") === "", "Unknown").otherwise(col("homepage")))
      .withColumn("release_date", to_date(col("release_date"), "yyyy-MM-dd"))
      .withColumn("runtime", when(col("runtime").isNull, 
        expr("percentile_approx(runtime, 0.5) OVER (PARTITION BY genre_names)")
      ).cast(IntegerType))
      .withColumn("budget", when(col("budget") === 0, "No Data").otherwise(col("budget").cast(StringType)))
      .withColumn("revenue", when(col("revenue") === 0, "No Data").otherwise(col("revenue").cast(StringType)))
  }

  /** 特征工程（新增 overview 空值二次校验） */
  def buildMovieFeatures(cleanDF: DataFrame, spark: SparkSession): DataFrame = {
    import spark.implicits._

    // 1. 二次校验 overview 字段，确保无空值（双重保险）
    val safeOverviewDF = cleanDF.withColumn("overview", when(
      col("overview").isNull || col("overview") === "",
      "No overview available"
    ).otherwise(col("overview")))

    // 2. 基础特征 UDF
    val keywordCountUDF = udf((keywords: String) => {
      if (keywords == "Unknown") 0 else keywords.split(",").length
    })

    val profitRatioUDF = udf((budget: String, revenue: String) => {
    	try {
	        if (budget == null || revenue == null || 
        	    budget == "No Data" || revenue == "No Data" || 
        	    budget.trim.isEmpty || revenue.trim.isEmpty) {
        	    0.0
        	} else {
        	    val budgetVal = budget.toDouble
        	    val revenueVal = revenue.toDouble
        	    if (budgetVal == 0) 0.0 else revenueVal / budgetVal
        	}
    	} catch {
   	     case _: Exception => 0.0  // 捕获所有转换异常
	}
    })

    val popularityScoreUDF = udf((popularity: Double, voteCount: Int) => {
      popularity * 0.6 + (voteCount.toDouble / 1000) * 0.4
    })

    // 3. 文本处理组件（使用安全的 overview 数据）
    val tokenizer = new org.apache.spark.ml.feature.Tokenizer()
      .setInputCol("overview")
      .setOutputCol("words")

    val remover = new org.apache.spark.ml.feature.StopWordsRemover()
      .setInputCol("words")
      .setOutputCol("filtered_words")

    val hashingTF = new org.apache.spark.ml.feature.HashingTF()
      .setInputCol("filtered_words")
      .setOutputCol("tf_vector")
      .setNumFeatures(1000)

    val idf = new org.apache.spark.ml.feature.IDF()
      .setInputCol("tf_vector")
      .setOutputCol("tfidf_vector")

    // 4. 文本处理流水线（基于已填充空值的 overview）
    val tokenizedDF = tokenizer.transform(safeOverviewDF)  // 输入已确保无空值
    val filteredDF = remover.transform(tokenizedDF)
    val tfDF = hashingTF.transform(filteredDF)
    val idfModel = idf.fit(tfDF)
    val textFeatureDF = idfModel.transform(tfDF)

    // 5. 整合所有特征
    textFeatureDF
      .withColumn("keyword_count", keywordCountUDF(col("keywords_str")))
      .withColumn("genre_diversity", size(split(col("genre_names"), ",")))
      .withColumn("profit_ratio", profitRatioUDF(col("budget"), col("revenue")))
      .withColumn("popularity_score", popularityScoreUDF(col("popularity"), col("vote_count")))
      .withColumn("budget_million", when(
        col("budget") =!= "No Data",
        col("budget").cast(DoubleType) / 1000000
      ).cast(DecimalType(10, 2)))
      .withColumn("tfidf_features", udf((vec: org.apache.spark.ml.linalg.Vector) => {
        val bytes = java.nio.ByteBuffer.allocate(vec.size * 8)
        // 使用小端序写入，与部分 Python 客户端默认字节序对齐
        bytes.order(java.nio.ByteOrder.LITTLE_ENDIAN)
        vec.toArray.foreach(bytes.putDouble)
        Base64.getEncoder.encodeToString(bytes.array())
      }).apply(col("tfidf_vector")))
      .select(
        col("movie_id"),
        col("title"),
        col("genre_names").alias("genres"),
        col("release_date"),
        col("runtime"),
        col("vote_average"),
        col("vote_count"),
        col("budget"),
        col("budget_million"),
        col("revenue"),
        col("profit_ratio"),
        col("popularity"),
        col("popularity_score"),
        col("genre_diversity"),
        col("keywords_str").alias("keywords"),
        col("keyword_count"),
        col("production_companies_str").alias("production_companies"),
        col("tfidf_features")
      )
  }

  /** 生成模拟评分 - 安全版本 */
def generateSimulatedRatings(spark: SparkSession, movieDF: DataFrame, userCount: Int = 500): DataFrame = {
    import spark.implicits._

    try {
      // 安全地获取电影ID和类型
      val validMovies = movieDF
        .select(col("movie_id").cast(IntegerType), col("genres"))
        .filter(col("movie_id").isNotNull && col("genres").isNotNull)
        .collect()
        .flatMap { row =>
          try {
            val movieId = row.getInt(0)
            val genres = row.getString(1)
            if (movieId > 0 && genres != null && genres.nonEmpty) {
              Some((movieId, genres))
            } else {
              None
            }
          } catch {
            case _: Exception => None
          }
        }

      if (validMovies.isEmpty) {
        println("⚠️ 警告：没有有效的电影数据用于生成评分")
        return Seq.empty[(Int, Int, Double)].toDF("user_id", "movie_id", "rating")
      }

      val ratings = (1 to userCount).flatMap { userId =>
        val userPref = userId % 5 match {
          case 0 => "Action,Adventure"
          case 1 => "Animation,Family"
          case 2 => "Drama,Romance"
          case 3 => "Comedy,Crime"
          case 4 => "Science Fiction,Fantasy"
        }
        val ratingCount = scala.util.Random.nextInt(11) + 10
        (1 to ratingCount).map { _ =>
          val (movieId, movieGenre) = validMovies(scala.util.Random.nextInt(validMovies.length))
          val baseRating = scala.util.Random.nextDouble() * 4 + 1
          val rating = if (userPref.split(",").exists(movieGenre.contains)) {
            math.min(baseRating + 1, 5.0)
          } else baseRating
          (userId, movieId, BigDecimal(rating).setScale(1, BigDecimal.RoundingMode.HALF_UP).toDouble)
        }
      }

      println(s"✅ 生成 ${ratings.size} 条模拟评分数据")
      ratings.toDF("user_id", "movie_id", "rating")
      
    } catch {
      case e: Exception =>
        println(s"❌ 生成模拟评分失败: ${e.getMessage}")
        Seq.empty[(Int, Int, Double)].toDF("user_id", "movie_id", "rating")
    }
}

  /** 保存至 HDFS */
  def saveToHDFS(df: DataFrame, path: String): Unit = {
    df.write
      .mode("overwrite")
      .option("compression", "snappy")
      .parquet(path)
    println(s"✅ 数据已保存至 HDFS: $path")
  }

  /** 保存至 PostgreSQL */
  def saveToPostgreSQL(df: DataFrame, tableName: String, jdbcUrl: String): Unit = {
    val jdbcProps = new java.util.Properties()
    jdbcProps.setProperty("user", "postgres")
    jdbcProps.setProperty("password", "postgres")
    jdbcProps.setProperty("driver", "org.postgresql.Driver")

    try {
      // 先清空表（使用 TRUNCATE 避免外键约束问题）
      val conn = java.sql.DriverManager.getConnection(jdbcUrl, "postgres", "postgres")
      val stmt = conn.createStatement()
      try {
        stmt.execute(s"TRUNCATE TABLE $tableName CASCADE")
        println(s"✅ 已清空表: $tableName")
      } catch {
        case _: Exception => // 表可能不存在，忽略
      } finally {
        stmt.close()
        conn.close()
      }
      
      // 使用 append 模式写入
      df.write
        .mode("append")
        .jdbc(jdbcUrl, tableName, jdbcProps)
      println(s"✅ 数据已同步至 PostgreSQL 表: $tableName")
    } catch {
      case e: Exception =>
        println(s"❌ 写入 PostgreSQL 表 $tableName 失败: ${e.getMessage}")
        throw e
    }
  }
}
