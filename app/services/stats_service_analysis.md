# 今日统计指标梳理文档

## 概述
本文档详细梳理 `get_today_stats()` 方法中各个统计指标的计算逻辑，以及需要扣减或调整的情况。

## ⚠️ 重要说明：统计范围

**`get_today_stats()` 方法的所有指标都只统计单个图片分类和单个缓存查询请求，不包括批量操作和图像编辑。**

### 数据来源
- **唯一数据源**: `request_log` 表
- **时间过滤**: `WHERE created_date = CURDATE()` （今日数据）
- **注意**: 表中有生成列 `created_date = DATE(created_at)`，已统一使用 `created_date` 以提高性能

### ✅ request_log 表包含的请求类型
1. **单个图片分类请求** (`/api/v1/classify`)
   - 缓存命中：记录 `from_cache=1, inference_method='cache'`
   - 缓存未命中：记录 `from_cache=0, inference_method='llm'/'local'/'llm_fallback'/'local_fallback'/'local_test'`

2. **单个缓存查询请求** (`/api/v1/classify/check-cache`)
   - 缓存命中：记录 `from_cache=1, inference_method='cache'`
   - 缓存未命中：**不记录**（只查询，不分类）

### ❌ request_log 表不包含的请求类型
1. **批量分类请求** (`/api/v1/classify/batch`)
   - 记录到 `batch_classify_stats` 表，**不**记录到 `request_log` 表
   - 使用 `get_batch_classify_stats()` 方法查询

2. **批量缓存查询** (`/api/v1/classify/batch-check-cache`)
   - 记录到 `batch_cache_stats` 表，**不**记录到 `request_log` 表
   - 使用 `get_batch_cache_stats()` 方法查询

3. **图像编辑请求** (`/api/v1/image-edit/*`)
   - 记录到 `image_edit_tasks` 表，**不**记录到 `request_log` 表
   - 使用 `get_image_edit_stats()` 方法查询

### 📊 统计指标范围总结
`get_today_stats()` 返回的所有9个指标都基于 `request_log` 表：
- `total_requests` - 总请求数
- `cache_hits` - 缓存命中数
- `cache_misses` - 缓存未命中数
- `cache_hit_rate` - 缓存命中率
- `unique_users` - 唯一用户数
- `unique_ips` - 唯一IP数
- `avg_processing_time` - 平均处理时间
- `estimated_cost` - 估算成本
- `cost_saved` - 节省成本

**所有指标都只统计单个图片分类和单个缓存查询（命中时），不包括批量操作和图像编辑。**

---

## 统计指标详细分析

### 1. total_requests（总请求数）

**计算逻辑**:
```sql
COALESCE(COUNT(*), 0) as total_requests
```

**说明**:
- 统计今日所有**单个图片分类和单个缓存查询**的请求记录数
- 包含缓存命中和未命中的所有请求
- **不包括**：批量分类、批量缓存查询、图像编辑
- **无扣减项**

**潜在问题**:
- ⚠️ **命名可能引起误解**: 指标名为 `total_requests`，但实际上只统计了部分请求类型
- **建议**: 考虑重命名为 `total_classify_requests` 或 `total_single_classify_requests` 以更准确地反映统计范围

---

### 2. cache_hits（缓存命中数）

**计算逻辑**:
```sql
COALESCE(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END), 0) as cache_hits
```

**说明**:
- 统计 `from_cache = 1` 的记录数
- 表示从缓存中获取结果的请求数
- **无扣减项**

**潜在问题**:
- ✅ 无

---

### 3. cache_misses（缓存未命中数）

**计算逻辑**:
```sql
COALESCE(SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END), 0) as cache_misses
```

**说明**:
- 统计 `from_cache = 0` 的记录数
- 表示需要调用API进行推理的请求数
- **无扣减项**

**潜在问题**:
- ⚠️ **需要确认**: `from_cache` 字段是否可能为 NULL？如果为 NULL，这些记录既不会被计入 cache_hits，也不会被计入 cache_misses
- **建议**: 检查是否有 `from_cache IS NULL` 的记录，如果有，需要决定如何处理

**验证SQL**:
```sql
SELECT COUNT(*) FROM request_log 
WHERE DATE(created_at) = CURDATE() AND from_cache IS NULL;
```

---

### 4. cache_hit_rate（缓存命中率）

**计算逻辑**:
```sql
CASE 
    WHEN COUNT(*) > 0 THEN ROUND(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
    ELSE 0.00
END as cache_hit_rate
```

**说明**:
- 计算公式: `(cache_hits / total_requests) * 100`
- 保留2位小数
- **无扣减项**

**潜在问题**:
- ⚠️ 如果存在 `from_cache IS NULL` 的记录，命中率计算可能不准确
- **建议**: 确保所有记录的 `from_cache` 字段都有明确的值（0 或 1）

---

### 5. unique_users（唯一用户数）

**计算逻辑**:
```sql
COALESCE(COUNT(DISTINCT user_id), 0) as unique_users
```

**说明**:
- 统计去重后的 `user_id` 数量
- **扣减项**: `COUNT(DISTINCT)` 会自动排除 NULL 值

**潜在问题**:
- ⚠️ **NULL 值处理**: 如果 `user_id` 为 NULL，这些用户不会被计入统计
- ⚠️ **空字符串处理**: 如果 `user_id` 为空字符串 `''`，会被计入（可能不是期望的行为）
- **建议**: 
  - 明确是否需要统计匿名用户（user_id 为 NULL 的情况）
  - 如果需要统计匿名用户，可以使用: `COUNT(DISTINCT COALESCE(user_id, 'anonymous'))`

**验证SQL**:
```sql
-- 检查 NULL 和空字符串的情况
SELECT 
    COUNT(*) as total,
    COUNT(user_id) as with_user_id,
    COUNT(*) - COUNT(user_id) as null_user_id,
    SUM(CASE WHEN user_id = '' THEN 1 ELSE 0 END) as empty_user_id
FROM request_log 
WHERE DATE(created_at) = CURDATE();
```

---

### 6. unique_ips（唯一IP数）

**计算逻辑**:
```sql
COALESCE(COUNT(DISTINCT ip_address), 0) as unique_ips
```

**说明**:
- 统计去重后的 `ip_address` 数量
- **扣减项**: `COUNT(DISTINCT)` 会自动排除 NULL 值

**潜在问题**:
- ⚠️ **NULL 值处理**: 如果 `ip_address` 为 NULL，这些IP不会被计入统计
- ⚠️ **空字符串处理**: 如果 `ip_address` 为空字符串 `''`，会被计入
- ⚠️ **IPv4/IPv6 格式**: 需要确认是否需要对IP地址进行标准化处理
- **建议**: 
  - 明确是否需要统计无IP的请求（ip_address 为 NULL 的情况）
  - 如果需要统计，可以使用: `COUNT(DISTINCT COALESCE(ip_address, 'unknown'))`

**验证SQL**:
```sql
-- 检查 NULL 和空字符串的情况
SELECT 
    COUNT(*) as total,
    COUNT(ip_address) as with_ip,
    COUNT(*) - COUNT(ip_address) as null_ip,
    SUM(CASE WHEN ip_address = '' THEN 1 ELSE 0 END) as empty_ip
FROM request_log 
WHERE DATE(created_at) = CURDATE();
```

---

### 7. avg_processing_time（平均处理时间）

**计算逻辑**:
```sql
COALESCE(ROUND(AVG(processing_time_ms), 2), 0) as avg_processing_time
```

**说明**:
- 计算所有请求的平均处理时间（毫秒）
- 保留2位小数
- **扣减项**: `AVG()` 会自动排除 NULL 值

**潜在问题**:
- ⚠️ **NULL 值处理**: 如果 `processing_time_ms` 为 NULL，这些记录不会被计入平均值计算
- ⚠️ **缓存命中请求的处理时间**: 缓存命中的请求处理时间通常很短，是否应该单独统计？
- ⚠️ **异常值处理**: 如果存在异常大的处理时间（如网络超时），可能影响平均值
- **建议**: 
  - 考虑分别统计缓存命中和未命中的平均处理时间
  - 考虑使用中位数（MEDIAN）或去除异常值后的平均值

**验证SQL**:
```sql
-- 检查 NULL 值和异常值
SELECT 
    COUNT(*) as total,
    COUNT(processing_time_ms) as with_time,
    COUNT(*) - COUNT(processing_time_ms) as null_time,
    MIN(processing_time_ms) as min_time,
    MAX(processing_time_ms) as max_time,
    AVG(processing_time_ms) as avg_time
FROM request_log 
WHERE DATE(created_at) = CURDATE();
```

**改进建议**:
```sql
-- 分别统计缓存命中和未命中的平均处理时间
SELECT 
    AVG(CASE WHEN from_cache = 1 THEN processing_time_ms END) as avg_time_cache_hit,
    AVG(CASE WHEN from_cache = 0 THEN processing_time_ms END) as avg_time_cache_miss
FROM request_log 
WHERE DATE(created_at) = CURDATE();
```

---

### 8. estimated_cost（估算成本）

**计算逻辑**:
```sql
COALESCE(SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) * %s, 0) as estimated_cost
```

**说明**:
- 计算公式: `cache_misses * COST_PER_API_CALL`
- 表示今日实际调用API产生的成本
- **无扣减项**

**潜在问题**:
- ⚠️ **推理方式差异**: 不同推理方式（llm/local/llm_fallback/local_fallback）的成本可能不同
  - `local` 和 `local_fallback` 使用本地模型，成本为 0
  - `llm` 和 `llm_fallback` 使用大模型API，有成本
- ⚠️ **当前逻辑问题**: 当前计算方式假设所有 `from_cache = 0` 的请求都有成本，但实际上：
  - `inference_method = 'local'` 的请求成本为 0
  - `inference_method = 'local_fallback'` 的请求成本为 0
  - `inference_method = 'local_test'` 的请求成本为 0
- **建议**: 应该根据 `inference_method` 字段来区分计算成本

**改进建议**:
```sql
-- 只统计实际调用大模型API的成本
COALESCE(
    SUM(CASE 
        WHEN from_cache = 0 
        AND inference_method IN ('llm', 'llm_fallback') 
        THEN 1 
        ELSE 0 
    END) * %s, 
    0
) as estimated_cost
```

**验证SQL**:
```sql
-- 检查不同推理方式的分布
SELECT 
    inference_method,
    COUNT(*) as count,
    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) as cache_misses
FROM request_log 
WHERE DATE(created_at) = CURDATE()
GROUP BY inference_method;
```

---

### 9. cost_saved（节省成本）

**计算逻辑**:
```sql
COALESCE(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * %s, 0) as cost_saved
```

**说明**:
- 计算公式: `cache_hits * COST_PER_API_CALL`
- 表示通过缓存节省的成本
- **无扣减项**

**潜在问题**:
- ⚠️ **计算逻辑问题**: 当前计算方式假设所有缓存命中都节省了 `COST_PER_API_CALL`，但实际上：
  - 如果原始请求本来就会使用本地模型（`inference_method = 'local'`），那么缓存命中节省的成本应该是 0
  - 只有原本会调用大模型API的请求，缓存命中才真正节省了成本
- **建议**: 需要结合历史数据或推理方式来判断节省的成本，或者简化处理，假设所有缓存命中都节省了成本

**改进建议**:
```sql
-- 简化版本：假设所有缓存命中都节省了成本（当前逻辑）
-- 或者更精确的版本：需要知道原始请求的推理方式（需要额外字段或历史数据）
```

---

## 总结与建议

### 需要修复的问题

1. **时间字段不一致**
   - 当前: `DATE(created_at) = CURDATE()`
   - 建议: `created_date = CURDATE()` （使用生成列，性能更好）

2. **estimated_cost 计算不准确**
   - 问题: 包含了本地推理（无成本）的请求
   - 建议: 只统计 `inference_method IN ('llm', 'llm_fallback')` 的请求

3. **NULL 值处理不明确**
   - `from_cache` 为 NULL 的记录未被统计
   - `user_id` 为 NULL 的用户未被计入 unique_users
   - `ip_address` 为 NULL 的IP未被计入 unique_ips
   - `processing_time_ms` 为 NULL 的记录未被计入平均值

### 需要验证的数据

1. 检查是否有 `from_cache IS NULL` 的记录
2. 检查 `user_id` 和 `ip_address` 的 NULL 值比例
3. 检查 `processing_time_ms` 的 NULL 值比例
4. 检查不同 `inference_method` 的分布情况

### 改进建议

1. **统一使用 `created_date` 字段**（性能优化）
2. **修复 `estimated_cost` 计算逻辑**（准确性）
3. **明确 NULL 值的处理策略**（数据完整性）
4. **考虑增加分类统计**（如缓存命中/未命中的平均处理时间）

---

## 验证SQL脚本

```sql
-- 1. 检查 from_cache 字段的完整性
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as cache_hits,
    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) as cache_misses,
    SUM(CASE WHEN from_cache IS NULL THEN 1 ELSE 0 END) as null_cache
FROM request_log 
WHERE DATE(created_at) = CURDATE();

-- 2. 检查 user_id 和 ip_address 的 NULL 值
SELECT 
    COUNT(*) as total,
    COUNT(user_id) as with_user_id,
    COUNT(*) - COUNT(user_id) as null_user_id,
    COUNT(ip_address) as with_ip,
    COUNT(*) - COUNT(ip_address) as null_ip
FROM request_log 
WHERE DATE(created_at) = CURDATE();

-- 3. 检查 processing_time_ms 的 NULL 值
SELECT 
    COUNT(*) as total,
    COUNT(processing_time_ms) as with_time,
    COUNT(*) - COUNT(processing_time_ms) as null_time
FROM request_log 
WHERE DATE(created_at) = CURDATE();

-- 4. 检查不同推理方式的分布
SELECT 
    inference_method,
    COUNT(*) as total,
    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as cache_hits,
    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) as cache_misses
FROM request_log 
WHERE DATE(created_at) = CURDATE()
GROUP BY inference_method
ORDER BY total DESC;
```

