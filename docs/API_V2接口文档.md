# API V2 接口文档

本文档描述了 ImageClassifierBackend API V2 版本的所有接口定义。

## 目录

- [健康检查](#健康检查)
- [图片分类](#图片分类)
- [图像编辑](#图像编辑)
- [地理位置](#地理位置)

---

## 健康检查

### GET /api/v2/health

健康检查接口 v2版本，相比 v1 版本增加了 user_id、设备类型和客户端提交时间字段。

#### 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID/设备ID |
| device_type | string | 否 | 设备类型（如：iOS、Android、Web等） |
| client_timestamp | string | 否 | 客户端提交的时间（ISO 8601格式） |

#### 响应模型

```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T12:00:00",
  "database": "connected",
  "model_api": "available",
  "user_id": "user123",
  "device_type": "iOS",
  "client_timestamp": "2025-12-29T11:59:00"
}
```

#### 字段说明

- **status**: 状态，可能值：`healthy`、`unhealthy`
- **timestamp**: 服务器时间戳
- **database**: 数据库状态，可能值：`connected`、`disconnected`、`unknown`
- **model_api**: 模型API状态，可能值：`available`、`not_configured`
- **user_id**: 用户ID/设备ID（可选）
- **device_type**: 设备类型（可选）
- **client_timestamp**: 客户端提交的时间（可选）

#### 请求示例

```bash
# 不带参数
GET /api/v2/health

# 带参数
GET /api/v2/health?user_id=user123&device_type=iOS&client_timestamp=2025-12-29T11:59:00Z
```

---

## 图片分类

### POST /api/v2/classify/batch

批量图片分类接口（v2版本）

#### 特点

- 只提供批量接口，不提供单张接口
- 使用v2版本的llm_service和unified_llm_cache
- 支持自定义分类提示词
- 统计用户分类图片张数（不统计类别分布）
- 最多支持20张图片

#### 请求格式

**Content-Type**: `multipart/form-data`

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| images | File[] | 是 | 图片文件列表 |
| image_metadata | string | 是 | JSON字符串，包含图片元数据 |
| X-User-ID | Header | 否 | 用户ID（Header方式） |
| X-OpenID | Header | 否 | 微信OpenID（Header方式） |

#### image_metadata 格式

```json
{
  "items": [
    {
      "index": 0,
      "image_uri": "uri1",
      "image_hash": "hash1"
    },
    {
      "index": 1,
      "image_uri": "uri2",
      "image_hash": null
    }
  ],
  "prompt": "optional",
  "user_id": "optional"
}
```

#### 响应模型

```json
{
  "error_type": "success",
  "error": null,
  "results": [
    {
      "index": 0,
      "image_uri": "uri1",
      "error": null,
      "category": "landscape",
      "confidence": 0.95,
      "description": "美丽的风景",
      "background_color": "blue",
      "raw_content": "...",
      "inference_method": "cache",
      "processing_time_ms": 50
    }
  ],
  "summary": {
    "total_count": 2,
    "success_count": 2,
    "failed_count": 0,
    "cached_count": 1,
    "llm_count": 1,
    "total_time_ms": 1500
  },
  "request_id": "req_xxx"
}
```

#### 字段说明

**BatchClassifyItemV2**:
- **index**: 图片索引（对应请求中的index）
- **image_uri**: 图片URI（客户端传入的）
- **error**: 错误信息（失败时才有）
- **category**: 分类结果
- **confidence**: 置信度（0-1）
- **description**: 描述
- **background_color**: 背景颜色
- **raw_content**: LLM返回的原始响应内容
- **inference_method**: 推理方式（`cache`、`llm`、`qrcode_detection`）
- **processing_time_ms**: 处理耗时(毫秒)

**BatchSummary**:
- **total_count**: 总数
- **success_count**: 成功数
- **failed_count**: 失败数
- **cached_count**: 缓存命中数
- **llm_count**: LLM处理数
- **total_time_ms**: 总处理耗时(毫秒)

---

### POST /api/v2/classify/batch-check-cache

批量查询缓存接口（v2版本）

#### 特点

- 一次性检查多个图片哈希的缓存状态
- 最多支持200个哈希
- 使用JSON格式请求体

#### 请求格式

**Content-Type**: `application/json`

```json
{
  "items": [
    {
      "index": 0,
      "image_uri": "uri1",
      "image_hash": "hash1"
    },
    {
      "index": 1,
      "image_uri": "uri2",
      "image_hash": "hash2"
    }
  ],
  "prompt": "optional",
  "user_id": "optional"
}
```

#### Header参数

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| X-User-ID | string | 否 | 用户ID |
| X-OpenID | string | 否 | 微信OpenID |

#### 响应模型

```json
{
  "error_type": "success",
  "error": null,
  "results": [
    {
      "index": 0,
      "image_uri": "uri1",
      "image_hash": "hash1",
      "cached": true,
      "category": "landscape",
      "confidence": 0.95,
      "description": "美丽的风景",
      "background_color": "blue",
      "raw_content": "..."
    }
  ],
  "summary": {
    "total": 2,
    "cached_count": 1,
    "miss_count": 1
  },
  "request_id": "req_xxx"
}
```

#### 字段说明

**CacheItemV2**:
- **index**: 图片索引
- **image_uri**: 图片URI（客户端传入的）
- **image_hash**: 图片哈希
- **cached**: 是否有缓存
- **category**: 分类结果（缓存命中时才有）
- **confidence**: 置信度（缓存命中时才有）
- **description**: 描述（缓存命中时才有）
- **background_color**: 背景颜色（缓存命中时才有）
- **raw_content**: LLM返回的原始响应内容（缓存命中时才有）

---

## 图像编辑

### POST /api/v2/image-edit/batch

批量图像编辑（v2版本，异步任务模式）

#### 特点

1. 使用 unified_llm_cache（v2版本）进行缓存
2. 使用 llm_service.edit_image 统一接口
3. 异步处理，立即返回 task_id
4. 客户端通过 /task/{task_id} 轮询查询状态
5. 最多支持9张图片

#### 请求格式

**Content-Type**: `multipart/form-data`

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| images | File[] | 是 | 图片文件列表（最多9张） |
| image_metadata | string | 是 | JSON字符串，包含图片元数据和编辑提示词 |
| X-User-ID | Header | 否 | 用户ID |

#### image_metadata 格式

```json
{
  "items": [
    {
      "index": 0,
      "image_uri": "uri1",
      "image_hash": "hash1"
    }
  ],
  "prompt": "将图片转换为卡通风格",
  "user_id": "optional"
}
```

#### 响应模型

```json
{
  "error_type": "success",
  "error": null,
  "task_id": "task_xxx",
  "total_images": 1,
  "request_id": "req_xxx"
}
```

#### 字段说明

- **error_type**: 内部服务错误类型（`success` 表示成功）
- **error**: 内部服务错误信息（仅在error_type不为success时存在）
- **task_id**: 任务ID（用于查询任务状态）
- **total_images**: 总图片数
- **request_id**: 请求ID

---

### GET /api/v2/image-edit/task/{task_id}

查询任务状态（v2版本）

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

#### 响应模型

```json
{
  "task_id": "task_xxx",
  "status": "completed",
  "total_images": 1,
  "completed_images": 1,
  "results": [
    {
      "index": 0,
      "image_uri": "uri1",
      "status": "completed",
      "result_url": "https://...",
      "error": null,
      "from_cache": false
    }
  ],
  "created_at": "2025-12-29T12:00:00",
  "updated_at": "2025-12-29T12:01:00"
}
```

#### 字段说明

- **task_id**: 任务ID
- **status**: 任务状态（`pending`、`processing`、`completed`、`failed`）
- **total_images**: 总图片数
- **completed_images**: 已完成数
- **results**: 结果列表
  - **index**: 图片索引
  - **image_uri**: 图片URI（客户端传入的）
  - **status**: 状态（`completed`、`failed`、`processing`）
  - **result_url**: 编辑后的图片URL（成功时才有）
  - **error**: 错误信息（失败时才有）
  - **from_cache**: 是否来自缓存（成功时才有）
- **created_at**: 创建时间（ISO 8601格式）
- **updated_at**: 更新时间（ISO 8601格式）

---

## 地理位置

### GET /api/v2/location/stats

获取位置数据库统计信息（v2版本，需要认证）

#### 认证

需要管理员认证（Bearer Token）

#### 响应模型

```json
{
  "database": {
    "total_cities": 10000,
    "unique_name_en": 8000,
    "mappable_count": 7500,
    "mapping_table_size": 7500
  },
  "external_api": {
    "today": {
      "amap_calls": 10,
      "nominatim_calls": 5
    },
    "total": {
      "amap_calls": 1000,
      "nominatim_calls": 500
    }
  },
  "data_sources": {
    "amap": 6000,
    "nominatim": 4000
  }
}
```

#### 字段说明

- **database**: 数据库统计
  - **total_cities**: 总城市数
  - **unique_name_en**: 唯一英文名数量
  - **mappable_count**: 可通过映射表获取中文名的城市数
  - **mapping_table_size**: 映射表大小
- **external_api**: 外部API调用统计
  - **today**: 今日调用统计
  - **total**: 累计调用统计
- **data_sources**: 数据来源分布

---

### POST /api/v2/location/nearest-cities

批量查询多个坐标点的最近城市（v2版本）

#### 特点

1. 先在本地数据库查询3km内的城市
2. 如果未找到，根据国家代码调用外部API（中国->高德，海外->Nominatim）
3. 如果外部API成功，将结果保存到本地数据库
4. 如果外部API失败，降级到v1逻辑（查询最近的城市，不限制距离）
5. 最多支持500个坐标点

#### 请求格式

**Content-Type**: `application/json`

```json
{
  "coordinates": [
    {
      "id": "photo_001",
      "latitude": 39.9042,
      "longitude": 116.4074
    },
    {
      "id": "photo_002",
      "latitude": 31.2304,
      "longitude": 121.4737
    }
  ],
  "user_id": "optional"
}
```

#### 请求字段说明

- **coordinates**: 坐标点列表（最多500个）
  - **id**: 位置ID（可选，客户端自定义，用于响应映射）
  - **latitude**: 纬度，范围 -90 到 90
  - **longitude**: 经度，范围 -180 到 180
- **user_id**: 用户ID（可选）

#### 响应模型

```json
{
  "success": true,
  "results": [
    {
      "location_id": "photo_001",
      "coordinate": {
        "latitude": 39.9042,
        "longitude": 116.4074
      },
      "success": true,
      "city": {
        "id": 1,
        "name_en": "Beijing",
        "name_zh": "北京",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "country_code": "CN",
        "admin1_code": "11",
        "admin2_code": null,
        "province": "北京市",
        "city": "北京市",
        "district": null,
        "data_source": "gaode",
        "geoname_id": 1816670,
        "population": 21540000,
        "distance_km": 0.5,
        "api_city_id": "110000",
        "api_adcode": "110000"
      },
      "error": null,
      "data_source": "gaode",
      "query_time_ms": 200
    },
    {
      "location_id": "photo_002",
      "coordinate": {
        "latitude": 31.2304,
        "longitude": 121.4737
      },
      "success": true,
      "city": {
        "id": 2,
        "name_en": "Shanghai",
        "name_zh": "上海",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "country_code": "CN",
        "data_source": "local",
        "distance_km": 0.2
      },
      "error": null,
      "data_source": "local",
      "query_time_ms": 50
    }
  ],
  "total_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "total_time_ms": 500,
  "request_id": "req_xxx"
}
```

#### 字段说明

**结果项（CityQueryResult）**:
- **location_id**: 位置ID（与请求中的id对应，用于响应映射）
- **coordinate**: 查询的坐标点
  - **latitude**: 纬度
  - **longitude**: 经度
- **success**: 是否查询成功
- **city**: 城市信息（成功时才有）
  - **id**: 主键ID
  - **name_en**: 英文名
  - **name_zh**: 中文名（通过映射表获取）
  - **latitude**: 纬度
  - **longitude**: 经度
  - **country_code**: 国家代码（ISO 3166-1 alpha-2）
  - **admin1_code**: 一级行政区代码
  - **admin2_code**: 二级行政区代码
  - **province**: 省份/州名称
  - **city**: 城市名称
  - **district**: 区县名称
  - **data_source**: 数据来源（`local`、`gaode`、`nominatim`）
  - **geoname_id**: GeoNames ID
  - **population**: 人口数
  - **distance_km**: 距离查询点的距离(公里)
  - **api_city_id**: 外部API返回的城市ID
  - **api_adcode**: 高德地图的行政区划代码
- **error**: 错误信息（失败时才有）
- **data_source**: 数据来源（`local`、`gaode`、`nominatim`、`fallback`）
- **query_time_ms**: 查询耗时（毫秒）

**响应汇总**:
- **success**: 整体是否成功
- **total_count**: 总查询数
- **success_count**: 成功查询数
- **failed_count**: 失败查询数
- **total_time_ms**: 总耗时（毫秒）
- **request_id**: 请求ID

#### 性能说明

- 本地数据库查询：并发处理，响应快速（<1秒）
- 外部API调用：按需调用，可能较慢（高德通常<1秒，Nominatim约1秒/请求）
- 建议客户端异步调用，避免阻塞主流程

#### 客户端使用建议

- 批量照片分类时，可以一张一张处理
- 本地照片处理时异步访问获取位置信息
- 不需要等待位置查询完成即可继续处理下一张照片

---

## 错误处理

### 错误类型

所有接口都使用统一的错误类型（`InternalErrorType`）：

- **success**: 成功（无内部服务异常）
- **database_connection_failed**: 数据库连接失败
- **database_operation_failed**: 数据库操作失败（查询/插入/更新）
- **cache_service_unavailable**: 缓存服务不可用
- **cache_query_failed**: 缓存查询失败
- **image_processing_failed**: 图片处理服务异常（批量处理时）
- **unknown_internal_error**: 未知的内部错误

### 错误响应格式

```json
{
  "error_type": "database_connection_failed",
  "error": "数据库连接失败：...",
  "results": [],
  "summary": {...},
  "request_id": "req_xxx"
}
```

---

## 通用说明

### 认证

- 大部分接口不需要认证
- `/api/v2/location/stats` 需要管理员认证（Bearer Token）
- 部分接口支持通过 Header 传递用户信息：
  - `X-User-ID`: 用户ID
  - `X-OpenID`: 微信OpenID

### 请求ID

所有接口响应都包含 `request_id` 字段，用于追踪请求和日志查询。

### 时间格式

所有时间字段使用 ISO 8601 格式，例如：`2025-12-29T12:00:00` 或 `2025-12-29T12:00:00Z`

### 图片格式

支持的图片格式：JPG、PNG、WebP、GIF、MPO等

### 限制

- 批量分类：最多20张图片
- 批量图像编辑：最多9张图片
- 批量查询缓存：最多200个哈希
- 批量查询位置：最多500个坐标点

---

## 版本说明

本文档描述的是 API V2 版本的接口。V1 版本的接口仍然可用，但建议新项目使用 V2 版本。

V2 版本的主要改进：
- 统一的错误处理机制
- 更详细的响应信息
- 更好的缓存支持
- 异步任务处理（图像编辑）
- 批量操作优化

