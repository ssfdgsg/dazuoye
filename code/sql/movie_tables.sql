-- 电影基础信息表
CREATE DATABASE IF NOT EXISTS movie_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movie_db;

CREATE TABLE IF NOT EXISTS movie_basic (
    movie_id INT PRIMARY KEY COMMENT '电影ID',
    title VARCHAR(255) NOT NULL COMMENT '电影标题',
    release_date DATE COMMENT '上映日期',
    runtime INT COMMENT '时长（分钟）',
    vote_average DECIMAL(3,1) COMMENT '平均评分',
    vote_count INT COMMENT '评分人数',
    budget BIGINT COMMENT '预算（美元）',
    budget_million DECIMAL(10,2) COMMENT '预算（百万美元）',
    revenue BIGINT COMMENT '票房（美元）',
    revenue_million DECIMAL(10,2) COMMENT '票房（百万美元）',
    profit_ratio DECIMAL(10,2) COMMENT '票房/预算比值',
    popularity DECIMAL(10,6) COMMENT '流行度',
    popularity_score DECIMAL(10,6) COMMENT '综合流行度得分',
    genre_names VARCHAR(255) COMMENT '电影类型（逗号分隔）',
    genre_diversity INT COMMENT '类型数量',
    status VARCHAR(50) DEFAULT 'Released' COMMENT '上映状态'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 电影特征表
CREATE TABLE IF NOT EXISTS movie_features (
    movie_id INT PRIMARY KEY COMMENT '电影ID',
    overview TEXT COMMENT '剧情简介',
    keywords VARCHAR(512) COMMENT '关键词（逗号分隔）',
    keyword_count INT COMMENT '关键词数量',
    production_companies VARCHAR(512) COMMENT '制作公司（逗号分隔）',
    original_language VARCHAR(50) COMMENT '原始语言',
    spoken_languages VARCHAR(255) COMMENT '对白语言（逗号分隔）',
    tfidf_features TEXT COMMENT 'TF-IDF特征向量（Base64编码）',
    FOREIGN KEY (movie_id) REFERENCES movie_basic(movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户评分表（模拟/真实）
CREATE TABLE IF NOT EXISTS user_ratings (
    user_id INT COMMENT '用户ID',
    movie_id INT COMMENT '电影ID',
    rating DECIMAL(2,1) COMMENT '评分（1-5分）',
    rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评分时间',
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (movie_id) REFERENCES movie_basic(movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 推荐结果表（离线生成）
CREATE TABLE IF NOT EXISTS user_recommendations (
    user_id INT COMMENT '用户ID',
    movie_id INT COMMENT '推荐电影ID',
    predict_rating DECIMAL(3,2) COMMENT '预测评分',
    recommend_rank INT COMMENT '推荐排序',
    PRIMARY KEY (user_id, recommend_rank),
    FOREIGN KEY (movie_id) REFERENCES movie_basic(movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
