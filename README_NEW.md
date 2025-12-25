# 电影推荐系统

一个基于Spark MLlib ALS算法的分布式电影推荐系统，支持协同过滤、内容推荐和冷启动用户推荐。

## 核心特性

- ✨ **ALS协同过滤推荐**：基于用户-电影评分矩阵的矩阵分解
- 🎯 **TF-IDF内容推荐**：基于电影类型、标签的相似度计算
- 🆕 **冷启动推荐**：新用户无需重训模型，即时获得个性化推荐
- ⚡ **异步重算**：评分后自动触发后台推荐重算
- 📊 **实时进度展示**：推荐计算进度与日志实时显示
- 🌐 **Web界面**：现代化的电影浏览、评分、推荐展示界面

## 快速开始

### 1. 启动Hadoop
```bash
ssh localhost
cd ~/Desktop
./starthadoop.sh
```

### 2. 运行完整流程
```bash
cd ~/Desktop/BigData/movieRecommendSystemV1
./run.sh
```

### 3. 启动Web服务
```bash
cd src/web
python3.8 app.py
# 访问 http://localhost:5000
```

## 冷启动推荐说明

### 问题背景
传统ALS推荐系统对于新用户（未参与模型训练）无法生成推荐结果。本系统通过**用户隐向量求解**解决此问题。

### 解决方案
利用用户的评分数据和已有的电影隐向量矩阵，通过最小二乘法快速求解用户隐向量：

```
u = (V^T V + λI)^{-1} V^T R_u
```

其中：
- V: 用户评分电影的隐向量矩阵
- R_u: 用户评分向量
- λ: 正则化参数（0.1）
- u: 求解得到的用户隐向量

### 使用示例

**命令行测试：**
```bash
# 测试冷启动用户503
python3.8 code/python/movie_recommender.py --user_id 503 --topN 5

# 输出包含 "method": "cold_start_als"
```

**Web API测试：**
```bash
# 完整测试脚本
bash scripts/test_cold_start.sh

# 或手动测试
curl http://localhost:5000/api/user/503/recommend?topN=5
```

### 详细文档
查看 [冷启动推荐详细说明](docs/COLD_START_RECOMMENDATION.md)

## 测试

```bash
# 测试Python推荐服务（包含冷启动测试）
bash scripts/testForModule/testPython.sh

# 测试Spark作业
bash scripts/testForModule/testJavaSparkSubmit.sh

# 测试冷启动推荐
bash scripts/test_cold_start.sh
```

## 项目结构

```
.
├── code/
│   ├── python/
│   │   └── movie_recommender.py      # 推荐服务（含冷启动）
│   ├── scala/
│   │   └── src/main/scala/com/movie/
│   │       ├── model/                # ALS模型训练
│   │       └── preprocess/           # 数据预处理
│   └── sql/
│       └── movie_tables.sql          # 数据库表结构
├── src/
│   └── web/
│       ├── app.py                    # Flask后端（异步重算）
│       └── static/                   # 前端页面
├── scripts/
│   ├── testForModule/                # 模块测试脚本
│   └── test_cold_start.sh           # 冷启动测试脚本
├── docs/
│   └── COLD_START_RECOMMENDATION.md  # 冷启动详细文档
└── run.sh                            # 一键运行脚本
```

## 技术栈

- **大数据处理**: Hadoop HDFS, Apache Spark 3.1.3
- **机器学习**: Spark MLlib (ALS)
- **数值计算**: NumPy (最小二乘求解)
- **数据库**: MySQL 8.0
- **后端**: Flask, Python 3.8
- **前端**: HTML5, JavaScript, Font Awesome

## 系统架构

```
用户评分 → 异步队列 → 后台Worker
                        ↓
                    推荐脚本
                    ↙     ↘
            ALS模型推荐  冷启动推荐
                    ↘     ↙
              写入user_recommendations表
                        ↓
                    前端展示
```

## 性能特点

- **冷启动速度**: 5-15秒（取决于评分数量和电影数量）
- **ALS推荐**: 预计算，秒级响应
- **并发支持**: 异步队列，支持多用户同时请求
- **可扩展性**: 分布式计算，支持大规模数据

## 常见问题

**Q: 新用户没有推荐结果怎么办？**  
A: 系统自动启用冷启动推荐，只需至少1条评分即可获得个性化推荐。

**Q: 冷启动推荐的准确性如何？**  
A: 基于ALS隐向量和真实评分，准确性随评分数量增加而提升。建议5条以上评分。

**Q: 如何区分ALS推荐和冷启动推荐？**  
A: 返回结果中包含`"method"`字段：`"als_model"`或`"cold_start_als"`。

**Q: 推荐结果多久更新一次？**  
A: 评分后立即加入异步队列，通常30-60秒完成重算。

## 贡献者

- 数据预处理: Scala + Spark
- 模型训练: Spark MLlib ALS
- 冷启动推荐: Python + NumPy
- Web服务: Flask + 异步队列
- 前端界面: HTML5 + JavaScript

## 许可证

MIT License

---

**更新时间**: 2025-12-23  
**版本**: 2.0 (支持冷启动推荐)
