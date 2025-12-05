# 今日统计指标重新设计

## 用户需求

根据用户需求，今日统计应包含以下指标：

1. **今日独立IP个数** - 不管什么请求，使用任何接口的独立IP
2. **今日用户数** - 今日的用户数
3. **今日图片分类的照片数**：
   - 总数
   - 缓存数
   - 大模型推理数
   - 本地推理数
4. **今日图像编辑的照片数**：
   - 总数
   - 缓存数
   - 大模型处理数

## 数据来源分析

### 1. 独立IP和用户数统计
需要从以下表聚合：
- `request_log` - 单个分类请求
- `batch_cache_stats` - 批量缓存查询
- `batch_classify_stats` - 批量分类
- `image_edit_tasks` - 图像编辑任务

### 2. 图片分类统计

#### 总数
- `batch_classify_stats.total_count` - 批量分类的图片总数
- `request_log` 中 `from_cache=0` 的数量（单个分类请求，缓存未命中）

#### 缓存数
- `batch_cache_stats.cached_count` - 批量缓存查询的命中数
- `request_log` 中 `from_cache=1` 的数量（单个分类请求，缓存命中）

#### 大模型推理数
- `request_log` 中 `from_cache=0 AND inference_method IN ('llm', 'llm_fallback')` 的数量
- **注意**：批量分类的每张图片都会记录到 `request_log`，所以可以从 `request_log` 统计

#### 本地推理数
- `request_log` 中 `from_cache=0 AND inference_method IN ('local', 'local_fallback', 'local_test')` 的数量

### 3. 图像编辑统计

#### 总数
- `image_edit_tasks.total_images` - 今日创建的图像编辑任务的总图片数

#### 缓存数
- `image_edit_cache` 中 `hit_count > 1` 的数量（缓存命中次数）
- 计算方式：`SUM(hit_count - 1) WHERE DATE(created_at) = CURDATE()`

#### 大模型处理数
- `image_edit_cache` 中 `hit_count = 1` 的数量（首次调用，大模型处理）
- 计算方式：`COUNT(*) WHERE hit_count = 1 AND DATE(created_at) = CURDATE()`

## 新的统计方法设计

```python
async def get_today_stats(self) -> dict:
    """
    获取今日统计（重新设计）
    
    返回：
    {
        "unique_ips": int,  # 今日独立IP个数
        "unique_users": int,  # 今日用户数
        "classify": {
            "total": int,  # 图片分类总数
            "cached": int,  # 缓存数
            "llm_inference": int,  # 大模型推理数
            "local_inference": int  # 本地推理数
        },
        "image_edit": {
            "total": int,  # 图像编辑总数
            "cached": int,  # 缓存数
            "llm_processed": int  # 大模型处理数
        }
    }
    """
```

## SQL 查询设计

### 1. 独立IP统计
```sql
SELECT COUNT(DISTINCT ip_address) as unique_ips
FROM (
    SELECT ip_address FROM request_log WHERE created_date = CURDATE() AND ip_address IS NOT NULL
    UNION
    SELECT ip_address FROM batch_cache_stats WHERE created_date = CURDATE() AND ip_address IS NOT NULL
    UNION
    SELECT ip_address FROM batch_classify_stats WHERE created_date = CURDATE() AND ip_address IS NOT NULL
    UNION
    SELECT ip_address FROM image_edit_tasks WHERE DATE(created_at) = CURDATE() AND ip_address IS NOT NULL
) as all_ips
```

### 2. 用户数统计
```sql
SELECT COUNT(DISTINCT user_id) as unique_users
FROM (
    SELECT user_id FROM request_log WHERE created_date = CURDATE() AND user_id IS NOT NULL
    UNION
    SELECT user_id FROM batch_cache_stats WHERE created_date = CURDATE() AND user_id IS NOT NULL
    UNION
    SELECT user_id FROM batch_classify_stats WHERE created_date = CURDATE() AND user_id IS NOT NULL
    UNION
    SELECT user_id FROM image_edit_tasks WHERE DATE(created_at) = CURDATE() AND user_id IS NOT NULL
) as all_users
```

### 3. 图片分类统计

#### 总数
```sql
SELECT 
    COALESCE(SUM(total_count), 0) as batch_total,
    COALESCE(COUNT(*), 0) as single_total
FROM (
    SELECT total_count FROM batch_classify_stats WHERE created_date = CURDATE()
    UNION ALL
    SELECT 1 FROM request_log WHERE created_date = CURDATE() AND from_cache = 0
) as classify_total
```

#### 缓存数
```sql
SELECT 
    COALESCE(SUM(cached_count), 0) as batch_cached,
    COALESCE(COUNT(*), 0) as single_cached
FROM (
    SELECT cached_count FROM batch_cache_stats WHERE created_date = CURDATE()
    UNION ALL
    SELECT 1 FROM request_log WHERE created_date = CURDATE() AND from_cache = 1
) as cached_total
```

#### 大模型推理数
```sql
SELECT COUNT(*) as llm_count
FROM request_log
WHERE created_date = CURDATE()
  AND from_cache = 0
  AND inference_method IN ('llm', 'llm_fallback')
```

#### 本地推理数
```sql
SELECT COUNT(*) as local_count
FROM request_log
WHERE created_date = CURDATE()
  AND from_cache = 0
  AND inference_method IN ('local', 'local_fallback', 'local_test')
```

### 4. 图像编辑统计

#### 总数
```sql
SELECT COALESCE(SUM(total_images), 0) as total
FROM image_edit_tasks
WHERE DATE(created_at) = CURDATE()
```

#### 缓存数
```sql
SELECT COALESCE(SUM(hit_count - 1), 0) as cached
FROM image_edit_cache
WHERE DATE(created_at) = CURDATE()
  AND hit_count > 1
```

#### 大模型处理数
```sql
SELECT COUNT(*) as llm_processed
FROM image_edit_cache
WHERE DATE(created_at) = CURDATE()
  AND hit_count = 1
```

## 注意事项

1. **批量分类的统计**：批量分类的每张图片都会记录到 `request_log`，所以可以从 `request_log` 统计推理方式，但总数需要加上 `batch_classify_stats.total_count`

2. **批量缓存查询**：批量缓存查询不会记录到 `request_log`，需要从 `batch_cache_stats` 统计

3. **图像编辑的缓存统计**：`image_edit_cache` 表的 `hit_count` 字段：
   - `hit_count = 1`：首次调用，大模型处理
   - `hit_count > 1`：缓存命中，需要计算 `hit_count - 1` 作为缓存命中数

4. **去重问题**：独立IP和用户数需要从所有表聚合并去重

