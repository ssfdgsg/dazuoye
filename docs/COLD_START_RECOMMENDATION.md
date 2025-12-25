# 冷启动用户推荐机制

## 问题背景

在协同过滤（ALS）推荐系统中，新用户或未参与模型训练的用户无法直接获得推荐结果，这就是经典的"冷启动问题"。

### 问题表现
- 用户503有8条评分记录
- 但ALS模型训练时未包含该用户
- 调用`recommendForUserSubset`返回空结果

## 解决方案

### 核心思想
利用已有的**电影隐向量矩阵（itemFactors）**和用户的评分数据，通过最小二乘法快速求解用户隐向量，然后基于ALS风格进行推荐。

### 算法原理

对于新用户 u，假设其评分向量为 R_u = [r₁, r₂, ..., rₙ]，对应电影的隐向量矩阵为 V = [v₁, v₂, ..., vₙ]ᵀ。

ALS模型中，预测评分 r̂ᵢ = uᵀ · vᵢ，我们需要求解用户隐向量 u：

```
minimize: ||R_u - uᵀVᵀ||² + λ||u||²
```

闭式解为：
```
u = (VᵀV + λI)⁻¹Vᵀ R_u
```

其中 λ 为正则化参数（默认0.1），防止过拟合和数值不稳定。

### 实现步骤

1. **获取用户评分数据**
   - 从`user_ratings`表查询用户的所有评分记录

2. **加载电影隐向量**
   - 从ALS模型的`itemFactors`中获取所有电影的隐向量
   - 模型路径：`hdfs://node1:9000/user/a1386/movie_model/als_tmdb`

3. **构建矩阵**
   - X：用户评分电影的隐向量矩阵 (n_ratings × n_factors)
   - y：用户评分向量 (n_ratings,)

4. **求解用户隐向量**
   ```python
   XtX = X.T.dot(X)
   XtX_reg = XtX + lambda_reg * np.eye(n_factors)
   Xty = X.T.dot(y)
   user_vector = np.linalg.solve(XtX_reg, Xty)
   ```

5. **计算预测评分**
   - 对所有候选电影（排除已评分），计算 pred = user_vector · item_vector
   - 按预测评分降序排序，取TopN

6. **返回推荐结果**
   - 附加字段：`"method": "cold_start_als"`

## 使用示例

### 命令行测试
```bash
python3.8 code/python/movie_recommender.py --user_id 503 --topN 5
```

### 输出示例
```json
{
  "user_id": 503,
  "recommendations": [
    {
      "movie_id": 163,
      "title": "Ocean's Twelve",
      "genre": "Thriller,Crime",
      "release_date": "2004-12-09",
      "vote_average": 6.4,
      "predict_rating": 28.92
    },
    ...
  ],
  "method": "cold_start_als"
}
```

## 集成说明

### 自动切换逻辑
在`recommend_by_user`函数中，当`recommendForUserSubset`返回空结果时，自动切换到冷启动模式：

```python
if rec_df.count() == 0:
    # 用户不在训练集中，启用冷启动推荐
    return recommend_for_cold_start_user(spark, mysql_conn, als_model, user_id, topN)
```

### 适用场景
1. **新注册用户**：未参与模型训练，但有少量评分数据
2. **边缘用户**：评分数量低于训练阈值，被模型过滤
3. **增量用户**：在上次模型训练后新增的活跃用户

### 后端异步重算支持
- Web后端`app.py`中的`_recompute_user_recommendations`函数调用该脚本
- 评分后自动触发异步重算
- 冷启动推荐结果会写入`user_recommendations`表

## 性能特点

### 优势
- **快速响应**：无需重训模型，秒级求解
- **准确性高**：基于真实评分数据和ALS隐向量
- **一致性好**：保持ALS推荐风格
- **可扩展**：支持任意评分数量（最少1条）

### 限制
- 需要至少1条评分记录
- 评分电影必须在模型的itemFactors中
- 预测评分依赖评分数据的质量

## 参数调优

### 正则化参数 λ
```python
lambda_reg = 0.1  # 默认值
```
- 增大λ：更保守，防止过拟合，适合评分少的用户
- 减小λ：更激进，拟合更紧，适合评分多的用户

### 推荐数量 topN
建议范围：5-200
- 前端展示：5-20
- 后端存储：50-200

## 测试验证

### 测试用户
- 用户501：训练集中 → 使用ALS直接推荐
- 用户502：训练集中 → 使用ALS直接推荐
- 用户503：不在训练集 → 冷启动推荐 ✓
- 用户504：不在训练集 → 冷启动推荐 ✓

### 测试脚本
```bash
bash scripts/testForModule/testPython.sh
```

## 技术栈
- **Spark MLlib**：ALS模型和隐向量管理
- **NumPy**：矩阵运算和最小二乘求解
- **MySQL**：评分数据和电影信息存储
- **Python 3.8**：脚本运行环境

## 未来优化方向
1. **增量更新**：用户新增评分后，增量更新用户隐向量
2. **缓存机制**：缓存计算好的用户隐向量，避免重复计算
3. **混合推荐**：结合内容特征（TF-IDF）进一步提升冷启动效果
4. **动态正则化**：根据评分数量自适应调整λ值

---
**更新时间**：2025-12-23  
**作者**：Movie Recommendation System Team
