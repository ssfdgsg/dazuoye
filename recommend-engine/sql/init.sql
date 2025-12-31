-- 电影推荐系统数据库初始化脚本 (PostgreSQL)

CREATE DATABASE IF NOT EXISTS movie_db;
\c movie_db;

-- 电影基础信息表
CREATE TABLE IF NOT EXISTS movie_basic (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_date DATE,
    runtime INT,
    vote_average NUMERIC(3,1),
    vote_count INT,
    budget BIGINT,
    budget_million NUMERIC(10,2),
    revenue BIGINT,
    revenue_million NUMERIC(10,2),
    profit_ratio NUMERIC(10,2),
    popularity NUMERIC(10,6),
    popularity_score NUMERIC(10,6),
    genres VARCHAR(255),
    genre_diversity INT,
    keywords TEXT,
    production_companies TEXT,
    status VARCHAR(50) DEFAULT 'Released'
);

COMMENT ON TABLE movie_basic IS '电影基础信息表';
COMMENT ON COLUMN movie_basic.movie_id IS '电影ID';
COMMENT ON COLUMN movie_basic.title IS '电影标题';
COMMENT ON COLUMN movie_basic.release_date IS '上映日期';
COMMENT ON COLUMN movie_basic.runtime IS '时长（分钟）';
COMMENT ON COLUMN movie_basic.vote_average IS '平均评分';
COMMENT ON COLUMN movie_basic.vote_count IS '评分人数';
COMMENT ON COLUMN movie_basic.budget IS '预算（美元）';
COMMENT ON COLUMN movie_basic.revenue IS '票房（美元）';
COMMENT ON COLUMN movie_basic.popularity_score IS '综合流行度得分';
COMMENT ON COLUMN movie_basic.genres IS '电影类型（逗号分隔）';

-- 电影特征表
CREATE TABLE IF NOT EXISTS movie_features (
    movie_id INT PRIMARY KEY REFERENCES movie_basic(movie_id),
    overview TEXT,
    keywords TEXT,
    keyword_count INT,
    production_companies TEXT,
    original_language VARCHAR(50),
    spoken_languages VARCHAR(255),
    tfidf_features TEXT
);

COMMENT ON TABLE movie_features IS '电影特征表';
COMMENT ON COLUMN movie_features.overview IS '剧情简介';
COMMENT ON COLUMN movie_features.keywords IS '关键词（逗号分隔）';
COMMENT ON COLUMN movie_features.tfidf_features IS 'TF-IDF特征向量（Base64编码）';

-- 用户评分表
CREATE TABLE IF NOT EXISTS user_ratings (
    user_id INT,
    movie_id INT REFERENCES movie_basic(movie_id),
    rating NUMERIC(3,1),
    rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, movie_id)
);

COMMENT ON TABLE user_ratings IS '用户评分表';
COMMENT ON COLUMN user_ratings.user_id IS '用户ID';
COMMENT ON COLUMN user_ratings.movie_id IS '电影ID';
COMMENT ON COLUMN user_ratings.rating IS '评分（1-5分）';

-- 推荐结果表（离线生成）
CREATE TABLE IF NOT EXISTS user_recommendations (
    user_id INT,
    movie_id INT REFERENCES movie_basic(movie_id),
    predicted_rating NUMERIC(3,2),
    recommend_rank INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, movie_id)
);

COMMENT ON TABLE user_recommendations IS '推荐结果表';
COMMENT ON COLUMN user_recommendations.predicted_rating IS '预测评分';

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '用户表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_movie_basic_popularity ON movie_basic(popularity_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_movie_basic_vote ON movie_basic(vote_average DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_user_ratings_user ON user_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_recommendations_user ON user_recommendations(user_id);
