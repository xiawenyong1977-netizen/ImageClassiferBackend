# 图片分类后端系统设计文档

## 1. 项目概述

### 1.1 项目目标
构建一个图片分类后端服务，接收客户端上传的图片，调用大模型进行分类推理，并通过智能缓存机制降低大模型调用成本。

### 1.2 分类体系

系统使用**固定的8个分类类别**，与客户端约定：

| 类别Key | 中文名称 | 英文名称 | 说明 |
|---------|---------|---------|------|
| `social_activities` | 社交活动 | Social Activities | 聚会、合影等社交场景 |
| `pets` | 宠物萌照 | Pet Photos | 猫、狗等宠物照片 |
| `single_person` | 单人照片 | Single Person Photos | 个人照、自拍等 |
| `foods` | 美食记录 | Food Records | 美食、餐饮照片 |
| `travel_scenery` | 旅行风景 | Travel Scenery | 旅游、风景照片 |
| `screenshot` | 手机截图 | Mobile Screenshots | 手机屏幕截图 |
| `idcard` | 证件照 | ID Card | 身份证、护照等证件 |
| `other` | 其它 | Other Images | 无法归类的其他图片 |

**注意**：
- 大模型必须从这8个类别中选择一个
- `category` 字段返回类别Key（如 `social_activities`）
- 客户端根据Key显示对应的中英文名称

### 1.3 核心特性
- ✅ 图片分类（基于大模型）
- ✅ SHA-256哈希去重缓存
- ✅ 成本优化（避免重复调用大模型）
- ✅ 请求统计分析
- ✅ 用户隔离（基于设备ID）
- ❌ 不存储原始图片（隐私保护）
- ❌ 暂不做限流拦截（仅统计）

### 1.3 适用场景
- 多用户个人应用（C端）
- 移动APP图片分类
- 成本敏感型应用

---

## 2. 系统架构

### 2.1 技术架构

```
┌─────────────┐
│   客户端     │ (iOS/Android/Web)
└──────┬──────┘
       │ HTTP/HTTPS
       ▼
┌─────────────────────────────────┐
│      FastAPI后端服务             │
│  ┌──────────────────────────┐  │
│  │   API Layer              │  │
│  │  - 分类接口               │  │
│  │  - 统计接口               │  │
│  │  - 健康检查               │  │
│  └──────────┬───────────────┘  │
│             ▼                   │
│  ┌──────────────────────────┐  │
│  │   Service Layer          │  │
│  │  - 图片处理服务           │  │
│  │  - 缓存服务               │  │
│  │  - 大模型客户端           │  │
│  └──────────┬───────────────┘  │
└─────────────┼───────────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
┌────────────┐  ┌──────────────┐
│   MySQL    │  │  大模型API    │
│  (持久化)   │  │ (OpenAI/     │
│            │  │  Claude等)    │
└────────────┘  └──────────────┘
```

### 2.2 核心流程（带宽优化版）

```
客户端选择图片
    │
    ▼
客户端压缩图片（2MB → 400KB）
    │
    ▼
计算SHA-256哈希（64字节）
    │
    ▼
调用 /check-cache 接口
（仅传输哈希，极快）
    │
    ├─► 缓存命中 ────────────────┐
    │   （无需上传图片！）         │
    │                            │
    └─► 缓存未命中                │
         │                       │
         ▼                       │
    上传压缩图片（400KB）         │
         │                       │
         ▼                       │
    调用大模型API                │
         │                       │
         ▼                       │
    保存到MySQL缓存              │
         │                       │
         └───────────────────────┤
                                ▼
                        记录统计日志
                                │
                                ▼
                        返回分类结果给客户端
```

**关键优化点**：
- ✅ 先查询缓存（只发送64字节哈希）
- ✅ 命中缓存时节省100%上传带宽
- ✅ 未命中时上传压缩图（节省80%带宽）
- ✅ 用户体验更快（缓存命中<1秒）

---

## 3. 接口设计

### 3.1 哈希缓存查询接口（带宽优化核心）

#### 3.1.1 查询缓存接口

**用途**：客户端先发送图片哈希，如果服务端已有缓存，直接返回结果，无需上传图片。

**请求**

```http
POST /api/v1/classify/check-cache
Content-Type: application/json

Headers:
  X-User-ID: <可选，设备ID或用户ID>  # 推荐方式

Body:
{
  "image_hash": "abc123...",  # 必需，客户端计算的SHA-256哈希
  "user_id": "device_uuid_xxx"  # 可选，如果Header中已传则可省略
}
```

**参数说明**：

| 参数 | 位置 | 必需 | 说明 |
|------|------|------|------|
| image_hash | Body | ✅ 必需 | SHA-256哈希值（64字符） |
| user_id | Header 或 Body | ❌ 可选 | 设备ID，用于统计分析 |

**注意**：
- `user_id` 是**可选的**，不传也能正常查询缓存
- 推荐通过 Header `X-User-ID` 传递（更标准）
- 如果 Header 和 Body 都传了，优先使用 Header
- 有 `user_id` 时会记录请求日志，便于统计

**响应1：缓存命中**

```json
{
  "success": true,
  "cached": true,
  "data": {
    "category": "travel_scenery",
    "confidence": 0.95,
    "description": "一张美丽的山景日落照片，展现了自然风光的壮美"
  },
  "from_cache": true,
  "request_id": "req_67890abcdef",
  "timestamp": "2025-10-10T12:00:00Z"
}
```

**字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| category | string | 分类Key（固定8个类别之一） | `travel_scenery` |
| confidence | float | 置信度（0-1） | 0.95 |
| description | string | 图片描述（可选） | "一张美丽的..." |
| request_id | string | 请求唯一标识 | `req_67890abcdef` |

**request_id 说明**：
- **生成方式**：服务端生成，格式为 `req_` + 时间戳 + 随机字符串
- **用途**：
  1. 唯一标识每次分类请求
  2. 问题排查和日志追踪
  3. 用户可凭此ID查询历史记录
  4. 关联请求和响应（便于调试）
- **生成示例**：
  ```python
  import uuid
  import time
  
  request_id = f"req_{int(time.time())}_{uuid.uuid4().hex[:12]}"
  # 示例结果: req_1696934400_a3f5d8c2b1e9
  ```

**响应2：缓存未命中**

```json
{
  "success": true,
  "cached": false,
  "message": "Cache not found, please upload the full image"
}
```

**优势**：
- ✅ 缓存命中时节省100%上传带宽
- ✅ 极快的响应速度（仅64字节哈希 vs 2MB图片）
- ✅ 对于重复图片（网络流行图、表情包），效果显著

---

### 3.2 图片分类接口

#### 3.2.1 单张图片分类

**请求**

```http
POST /api/v1/classify
Content-Type: multipart/form-data

Headers:
  X-User-ID: <可选，设备ID或用户ID>

Body:
  image: <File>  # 必需，图片文件（建议客户端压缩后上传）
  image_hash: <String>  # 可选，客户端已计算的SHA-256哈希（避免服务端重复计算）
```

**参数说明**：

| 参数 | 位置 | 必需 | 说明 |
|------|------|------|------|
| image | Body | ✅ 必需 | 图片文件（支持jpg/png/webp） |
| image_hash | Body | ❌ 可选 | SHA-256哈希值，如已计算可传入 |
| X-User-ID | Header | ❌ 可选 | 设备ID，用于统计分析 |

**注意**：
- `image_hash` 可选，传入可节省服务端计算时间
- `X-User-ID` 可选，用于请求日志和统计

**响应**

```json
{
  "success": true,
  "data": {
    "category": "foods",
    "confidence": 0.92,
    "description": "一盘精美的意大利面，色香味俱全"
  },
  "from_cache": false,
  "processing_time_ms": 1523,
  "request_id": "req_67890abcdef",
  "timestamp": "2025-10-10T12:00:00Z"
}
```

**状态码**

- `200 OK`: 分类成功
- `400 Bad Request`: 参数错误（文件格式、大小等）
- `413 Payload Too Large`: 文件过大
- `500 Internal Server Error`: 服务器错误

**字段说明**

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| category | string | 分类Key（8个类别之一） | `foods` |
| confidence | float | 置信度（0-1） | 0.92 |
| description | string | 图片描述（可选） | "一盘精美的..." |
| from_cache | boolean | 是否来自缓存 | false |
| processing_time_ms | integer | 处理耗时（毫秒） | 1523 |
| request_id | string | 请求唯一标识 | "req_67890..." |

**可能的 category 值**：
- `social_activities` - 社交活动
- `pets` - 宠物萌照
- `single_person` - 单人照片
- `foods` - 美食记录
- `travel_scenery` - 旅行风景
- `screenshot` - 手机截图
- `idcard` - 证件照
- `other` - 其它

---

### 3.3 统计接口

#### 3.3.1 今日统计

**请求**

```http
GET /api/v1/stats/today
```

**响应**

```json
{
  "success": true,
  "data": {
    "total_requests": 1523,
    "cache_hits": 456,
    "cache_misses": 1067,
    "cache_hit_rate": 29.94,
    "unique_users": 89,
    "unique_ips": 76,
    "avg_processing_time_ms": 1245,
    "estimated_cost": 10.67,
    "cost_saved": 4.56
  }
}
```

#### 3.3.2 缓存效率统计

**请求**

```http
GET /api/v1/stats/cache-efficiency
```

**响应**

```json
{
  "success": true,
  "data": {
    "total_cached_images": 3542,
    "total_hits": 8923,
    "times_saved": 5381,
    "cost_saved": 53.81,
    "avg_hit_per_image": 2.52,
    "max_hits": 156
  }
}
```

#### 3.3.3 分类分布统计

**请求**

```http
GET /api/v1/stats/category-distribution
```

**响应**

```json
{
  "success": true,
  "data": [
    {
      "category": "风景",
      "count": 4523,
      "percentage": 29.7,
      "avg_confidence": 0.92
    },
    {
      "category": "人物",
      "count": 3892,
      "percentage": 25.5,
      "avg_confidence": 0.89
    }
  ]
}
```

#### 3.3.4 用户请求统计

**请求**

```http
GET /api/v1/stats/users/top
Query Parameters:
  - limit: integer (默认20, 返回前N个用户)
```

**响应**

```json
{
  "success": true,
  "data": [
    {
      "user_id": "device_uuid_123",
      "request_count": 152,
      "cache_hits": 45,
      "cache_hit_rate": 29.6,
      "first_request": "2025-10-01T08:00:00Z",
      "last_request": "2025-10-10T12:00:00Z"
    }
  ]
}
```

---

### 3.4 健康检查接口

**请求**

```http
GET /api/v1/health
```

**响应**

```json
{
  "status": "healthy",
  "timestamp": "2025-10-10T12:00:00Z",
  "database": "connected",
  "model_api": "available"
}
```

---

## 4. 带宽优化方案

### 4.1 优化策略概述

通过**哈希预查询 + 客户端压缩**的组合策略，大幅降低上传带宽：

```
优化前：每次上传 2-5MB 原图
优化后：
  - 缓存命中(30%)：只传64字节哈希
  - 缓存未命中(70%)：上传400KB压缩图
节省效果：约90%带宽
```

### 4.2 完整客户端流程

#### 4.2.1 推荐流程图

```
用户选择图片
    │
    ▼
客户端压缩图片（2MB → 400KB）
    │
    ▼
计算SHA-256哈希（64字节）
    │
    ▼
步骤1: 调用 /check-cache 接口
（仅发送64字节哈希）
    │
    ├─► 缓存命中 ──────────────┐
    │   ✅ 直接返回结果          │
    │   ✅ 节省100%上传带宽      │
    │   ✅ 响应时间 < 1秒        │
    │                          │
    └─► 缓存未命中              │
         │                     │
         ▼                     │
    步骤2: 调用 /classify       │
    上传压缩图片（400KB）       │
         │                     │
         ▼                     │
    服务端调用大模型            │
         │                     │
         ▼                     │
    保存到MySQL缓存            │
         │                     │
         ▼                     │
    ✅ 返回分类结果             │
    ✅ 节省80%带宽（vs原图）    │
         │                     │
         └─────────────────────┘
                    │
                    ▼
            客户端显示结果
```

**流程说明**：
1. **步骤1（哈希查询）**：快速、轻量，仅64字节
2. **步骤2（上传图片）**：仅在缓存未命中时执行
3. **两步设计**：最大化节省带宽和时间

#### 4.2.2 客户端实现示例

**JavaScript/TypeScript (React Native / Web)**

```javascript
import CryptoJS from 'crypto-js';
import ImageResizer from 'react-native-image-resizer';

/**
 * 优化后的图片分类流程
 */
async function classifyImageOptimized(imageUri, userId) {
  try {
    // ========== 步骤1: 客户端压缩 ==========
    console.log('🔧 压缩图片...');
    const compressedImage = await ImageResizer.createResizedImage(
      imageUri,
      1024,        // 最大宽度
      1024,        // 最大高度
      'JPEG',      // 格式
      80,          // 质量(0-100)
      0,           // 旋转角度
      null,        // 输出路径
      false,       // 保持宽高比
      {
        mode: 'contain',
        onlyScaleDown: true  // 只缩小，不放大
      }
    );
    
    // ========== 步骤2: 读取压缩后的图片并计算哈希 ==========
    console.log('🔐 计算哈希...');
    const imageBytes = await readFileAsArrayBuffer(compressedImage.uri);
    const wordArray = CryptoJS.lib.WordArray.create(imageBytes);
    const imageHash = CryptoJS.SHA256(wordArray).toString();
    
    console.log(`📊 原图大小: ${originalSize / 1024 / 1024}MB`);
    console.log(`📊 压缩后大小: ${imageBytes.byteLength / 1024}KB`);
    console.log(`🔑 哈希: ${imageHash.substring(0, 16)}...`);
    
    // ========== 步骤3: 查询缓存 ==========
    console.log('🔍 查询缓存...');
    const cacheResponse = await fetch('https://api.yourapp.com/api/v1/classify/check-cache', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId,
      },
      body: JSON.stringify({
        image_hash: imageHash,
        user_id: userId
      })
    });
    
    const cacheResult = await cacheResponse.json();
    
    // ========== 步骤4: 缓存命中，直接返回 ==========
    if (cacheResult.cached) {
      console.log('✅ 缓存命中！节省上传带宽');
      return {
        ...cacheResult.data,
        from_cache: true,
        bandwidth_saved: true
      };
    }
    
    // ========== 步骤5: 缓存未命中，上传压缩图片 ==========
    console.log('⬆️  上传压缩图片...');
    const formData = new FormData();
    formData.append('image', {
      uri: compressedImage.uri,
      type: 'image/jpeg',
      name: 'image.jpg',
    });
    formData.append('image_hash', imageHash);  // 附带哈希，服务端无需重复计算
    
    const uploadResponse = await fetch('https://api.yourapp.com/api/v1/classify', {
      method: 'POST',
      headers: {
        'X-User-ID': userId,
      },
      body: formData
    });
    
    const result = await uploadResponse.json();
    console.log('✅ 分类完成');
    
    return result;
    
  } catch (error) {
    console.error('❌ 分类失败:', error);
    throw error;
  }
}

/**
 * 读取文件为ArrayBuffer
 */
async function readFileAsArrayBuffer(uri) {
  const response = await fetch(uri);
  const blob = await response.blob();
  return await blob.arrayBuffer();
}
```

**Flutter/Dart**

```dart
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

/// 优化后的图片分类
Future<Map<String, dynamic>> classifyImageOptimized(
  String imagePath,
  String userId,
) async {
  // ========== 步骤1: 压缩图片 ==========
  print('🔧 压缩图片...');
  final compressedBytes = await FlutterImageCompress.compressWithFile(
    imagePath,
    minWidth: 1024,
    minHeight: 1024,
    quality: 80,
    format: CompressFormat.jpeg,
  );
  
  if (compressedBytes == null) {
    throw Exception('图片压缩失败');
  }
  
  print('📊 压缩后大小: ${compressedBytes.length / 1024}KB');
  
  // ========== 步骤2: 计算哈希 ==========
  print('🔐 计算哈希...');
  final imageHash = sha256.convert(compressedBytes).toString();
  print('🔑 哈希: ${imageHash.substring(0, 16)}...');
  
  // ========== 步骤3: 查询缓存 ==========
  print('🔍 查询缓存...');
  final cacheResponse = await http.post(
    Uri.parse('https://api.yourapp.com/api/v1/classify/check-cache'),
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId,
    },
    body: jsonEncode({
      'image_hash': imageHash,
      'user_id': userId,
    }),
  );
  
  final cacheResult = jsonDecode(cacheResponse.body);
  
  // ========== 步骤4: 缓存命中 ==========
  if (cacheResult['cached'] == true) {
    print('✅ 缓存命中！节省上传带宽');
    return {
      ...cacheResult['data'],
      'from_cache': true,
      'bandwidth_saved': true,
    };
  }
  
  // ========== 步骤5: 上传压缩图片 ==========
  print('⬆️  上传压缩图片...');
  final request = http.MultipartRequest(
    'POST',
    Uri.parse('https://api.yourapp.com/api/v1/classify'),
  );
  
  request.headers['X-User-ID'] = userId;
  request.fields['image_hash'] = imageHash;
  request.files.add(
    http.MultipartFile.fromBytes(
      'image',
      compressedBytes,
      filename: 'image.jpg',
    ),
  );
  
  final streamedResponse = await request.send();
  final uploadResponse = await http.Response.fromStream(streamedResponse);
  final result = jsonDecode(uploadResponse.body);
  
  print('✅ 分类完成');
  return result;
}
```

### 4.3 压缩策略建议

#### 4.3.1 推荐参数

```
尺寸限制：
- 最大宽度：1024px
- 最大高度：1024px
- 保持宽高比

质量设置：
- JPEG质量：75-85%
- PNG转JPEG（更小）
- 支持WebP（可选，压缩率更高）

文件大小：
- 目标：200KB - 500KB
- 最大：1MB
```

#### 4.3.2 不同场景的压缩策略

```javascript
/**
 * 根据网络状况智能压缩
 */
async function adaptiveCompress(imageUri) {
  const networkInfo = await NetInfo.fetch();
  
  let quality, maxWidth;
  
  switch(networkInfo.type) {
    case 'wifi':
      quality = 85;
      maxWidth = 1024;
      break;
    case 'cellular':
      // 根据蜂窝网络类型调整
      if (networkInfo.effectiveType === '4g') {
        quality = 80;
        maxWidth = 1024;
      } else if (networkInfo.effectiveType === '3g') {
        quality = 70;
        maxWidth = 800;
      } else {
        quality = 60;
        maxWidth = 640;
      }
      break;
    default:
      quality = 75;
      maxWidth = 800;
  }
  
  return await compressImage(imageUri, { quality, maxWidth });
}
```

### 4.4 带宽节省效果分析

#### 4.4.1 实际测试数据

```
测试场景：1000次图片分类请求

原始方案（无优化）：
- 平均图片大小：3MB
- 总上传流量：3000MB (3GB)
- 用户等待时间：15秒/次 (4G网络)

优化后（哈希+压缩）：
- 缓存命中率：30%
  - 300次 × 64字节 = 0.02MB
- 缓存未命中：70%
  - 700次 × 400KB = 280MB
- 总上传流量：280MB
- 用户等待时间：
  - 缓存命中：0.5秒
  - 未命中：3秒

节省效果：
✅ 带宽节省：90.7%
✅ 时间节省：平均80%
✅ 成本节省：30%（缓存命中的API调用）
```

#### 4.4.2 成本对比表

| 指标 | 原始方案 | 优化方案 | 节省 |
|------|---------|---------|------|
| 月上传流量 | 90GB | 8.4GB | 90.7% |
| 用户平均等待 | 15秒 | 3.5秒 | 76.7% |
| 大模型API调用 | 30000次 | 21000次 | 30% |
| 月API成本 | 300元 | 210元 | 90元 |
| CDN流量成本 | 45元 | 4元 | 41元 |
| **总节省** | - | - | **131元/月** |

### 4.5 服务端优化配置

#### 4.5.1 接收压缩图片配置

```python
# config.py
MAX_IMAGE_SIZE_MB = 2              # 限制上传大小
RECOMMENDED_IMAGE_SIZE_KB = 500    # 推荐大小
ACCEPTED_FORMATS = ['jpeg', 'jpg', 'png', 'webp']
```

#### 4.5.2 可选：服务端再压缩

```python
from PIL import Image
import io

def optimize_image_if_needed(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
    """
    如果客户端上传的图片仍然过大，服务端再次优化
    """
    size_kb = len(image_bytes) / 1024
    
    if size_kb <= max_size_kb:
        return image_bytes  # 已经够小，不需要优化
    
    img = Image.open(io.BytesIO(image_bytes))
    
    # 调整尺寸
    if max(img.size) > 1024:
        ratio = 1024 / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.LANCZOS)
    
    # 压缩
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=80, optimize=True)
    
    return output.getvalue()
```

---

## 5. 服务设计

### 5.1 服务分层

```
ImageClassifierBackend/
├── app/
│   ├── api/                    # API层（路由、请求处理）
│   │   ├── classify.py         # 分类接口
│   │   ├── stats.py            # 统计接口
│   │   └── health.py           # 健康检查
│   │
│   ├── services/               # 服务层（业务逻辑）
│   │   ├── classifier.py       # 分类服务
│   │   ├── cache_service.py    # 缓存服务
│   │   ├── stats_service.py    # 统计服务
│   │   └── model_client.py     # 大模型客户端
│   │
│   ├── models/                 # 数据模型
│   │   ├── request.py          # 请求模型
│   │   └── response.py         # 响应模型
│   │
│   ├── utils/                  # 工具类
│   │   ├── hash_utils.py       # 哈希工具
│   │   ├── image_utils.py      # 图片工具
│   │   └── id_generator.py     # ID生成工具
│   │
│   ├── database.py             # 数据库连接
│   ├── config.py               # 配置管理
│   └── main.py                 # 应用入口
```

### 5.2 核心服务

#### 5.2.1 ClassifierService（分类服务）

**职责**：
- 接收图片数据
- 计算图片哈希
- 协调缓存查询和大模型调用
- 记录统计日志

**核心方法**：

```python
class ClassifierService:
    def classify(
        self, 
        image_bytes: bytes, 
        user_id: str = None, 
        ip_address: str = None
    ) -> ClassificationResult:
        """
        图片分类主流程
        
        Args:
            image_bytes: 图片二进制数据
            user_id: 用户ID（可选）
            ip_address: 客户端IP（可选）
            
        Returns:
            ClassificationResult: 分类结果
        """
        pass
```

#### 5.2.2 CacheService（缓存服务）

**职责**：
- 查询缓存
- 保存缓存
- 更新命中统计

**核心方法**：

```python
class CacheService:
    def get_cached_result(self, image_hash: str) -> Optional[dict]:
        """根据哈希查询缓存"""
        pass
    
    def save_result(self, image_hash: str, result: dict) -> None:
        """保存分类结果到缓存"""
        pass
    
    def increment_hit_count(self, image_hash: str) -> None:
        """增加缓存命中次数"""
        pass
```

#### 5.2.3 ModelClient（大模型客户端）

**职责**：
- 调用大模型API
- 处理API响应
- 错误处理和重试
- 确保分类结果符合预定义类别

**核心方法**：

```python
class ModelClient:
    # 预定义的分类类别
    CATEGORIES = [
        "social_activities",  # 社交活动
        "pets",               # 宠物萌照
        "single_person",      # 单人照片
        "foods",              # 美食记录
        "travel_scenery",     # 旅行风景
        "screenshot",         # 手机截图
        "idcard",             # 证件照
        "other"               # 其它
    ]
    
    def classify_image(self, image_bytes: bytes) -> dict:
        """
        调用大模型进行图片分类
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            dict: 分类结果
            {
                "category": str,        # 必须是8个类别之一
                "confidence": float,    # 置信度0-1
                "description": str      # 图片描述（可选）
            }
        """
        pass
    
    def _build_prompt(self) -> str:
        """
        构建大模型提示词
        
        要求：
        1. 从8个预定义类别中选择一个
        2. 返回置信度
        3. 可选：返回简短描述
        """
        return """
        请对这张图片进行分类。你必须从以下8个类别中选择一个：
        
        1. social_activities - 社交活动（聚会、合影、多人互动场景）
        2. pets - 宠物萌照（猫、狗等宠物照片）
        3. single_person - 单人照片（个人照、自拍、肖像）
        4. foods - 美食记录（食物、餐饮、烹饪相关）
        5. travel_scenery - 旅行风景（旅游景点、自然风光、城市风景）
        6. screenshot - 手机截图（手机屏幕截图、应用界面）
        7. idcard - 证件照（身份证、护照、驾照等证件）
        8. other - 其它（无法归类到上述类别）
        
        请以JSON格式返回结果：
        {
            "category": "类别key（必须是上述8个之一）",
            "confidence": 0.95,
            "description": "简短描述图片内容（可选）"
        }
        """
```

#### 5.2.4 StatsService（统计服务）

**职责**：
- 记录请求日志
- 查询统计数据
- 生成统计报告

**核心方法**：

```python
class StatsService:
    def log_request(self, log_data: dict) -> None:
        """记录请求日志"""
        pass
    
    def get_today_stats(self) -> dict:
        """获取今日统计"""
        pass
    
    def get_cache_efficiency(self) -> dict:
        """获取缓存效率统计"""
        pass
    
    def get_category_distribution(self) -> list:
        """获取分类分布"""
        pass
```

### 5.3 工具类

#### 5.3.1 ID生成器（id_generator.py）

**用途**：生成全局唯一的请求ID，用于追踪和日志关联

```python
import uuid
import time
from typing import Optional

class IDGenerator:
    """
    请求ID生成器
    
    生成格式：req_{timestamp}_{random_string}
    示例：req_1696934400_a3f5d8c2b1e9
    """
    
    @staticmethod
    def generate_request_id(prefix: str = "req") -> str:
        """
        生成请求ID
        
        Args:
            prefix: ID前缀，默认为"req"
            
        Returns:
            格式化的请求ID
        """
        timestamp = int(time.time())
        random_part = uuid.uuid4().hex[:12]
        return f"{prefix}_{timestamp}_{random_part}"
    
    @staticmethod
    def parse_request_id(request_id: str) -> Optional[dict]:
        """
        解析请求ID，提取时间戳
        
        Args:
            request_id: 请求ID
            
        Returns:
            包含前缀、时间戳、随机字符串的字典
        """
        try:
            parts = request_id.split('_')
            if len(parts) >= 3:
                return {
                    'prefix': parts[0],
                    'timestamp': int(parts[1]),
                    'random': parts[2]
                }
        except:
            pass
        return None

# 使用示例
request_id = IDGenerator.generate_request_id()
# 输出: req_1696934400_a3f5d8c2b1e9

# 解析
info = IDGenerator.parse_request_id(request_id)
# 输出: {'prefix': 'req', 'timestamp': 1696934400, 'random': 'a3f5d8c2b1e9'}
```

**request_id 设计说明**：

1. **唯一性保证**
   - 时间戳（秒级）：确保时间维度唯一
   - UUID随机部分：确保同一秒内唯一
   - 组合后全局唯一

2. **可读性**
   - 前缀`req_`：一眼识别为请求ID
   - 时间戳：方便按时间查询和排序
   - 长度适中：约30个字符

3. **用途**
   - ✅ 请求追踪：从前端到后端的完整链路
   - ✅ 日志关联：快速定位问题
   - ✅ 数据库索引：request_log表的唯一标识
   - ✅ 用户查询：用户可凭ID查看历史记录
   - ✅ 错误排查：问题复现和调试

4. **性能考虑**
   - 生成速度：< 1ms
   - 无需网络请求
   - 无需数据库查询
   - 线程安全（UUID保证）

5. **替代方案对比**

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| UUID4 | 完全随机 | 不可读、无时间信息 | ⭐⭐⭐ |
| 自增ID | 简单 | 分布式不友好、可预测 | ⭐⭐ |
| Snowflake | 高性能、有序 | 需要机器ID配置 | ⭐⭐⭐⭐ |
| 时间戳+UUID | 可读、唯一 | 长度稍长 | ⭐⭐⭐⭐⭐ |

**当前方案（时间戳+UUID）最适合本项目**，因为：
- 单机或小规模部署
- 需要可读性
- 需要时间排序
- 实现简单

---

## 6. 存储方案

### 6.1 数据库选型

**MySQL 8.0+**

**选择理由**：
- ✅ 成熟稳定，广泛使用
- ✅ 支持JSON字段（灵活存储分类结果）
- ✅ 事务支持
- ✅ 索引优化（哈希唯一索引）
- ✅ 简化架构（不需要Redis）
- ✅ 适合中小规模应用

### 6.2 数据存储策略

| 数据类型 | 存储方式 | 保留时长 | 说明 |
|---------|---------|---------|------|
| 原始图片 | ❌ 不存储 | - | 隐私保护 |
| 图片哈希 | MySQL | 永久 | 用于去重缓存 |
| 分类结果 | MySQL | 永久 | 全局共享缓存 |
| 请求日志 | MySQL | 可配置 | 统计分析用 |

### 6.3 缓存机制

**全局缓存策略**：
- 以图片SHA-256哈希为Key
- 所有用户共享缓存结果
- 避免对同一张图片重复调用大模型
- 大幅降低API调用成本

**缓存流程**：
```
1. 用户A上传图片X → 调用大模型 → 存入缓存
2. 用户B上传相同图片X → 命中缓存 → 直接返回（省钱！）
3. 用户C上传相同图片X → 命中缓存 → 直接返回（省钱！）
```

---

## 7. 表结构设计

### 7.1 表概览

| 表名 | 说明 | 核心功能 |
|------|------|---------|
| image_classification_cache | 分类结果缓存表 | 成本优化核心 |
| request_log | 请求日志表 | 统计分析 |

---

### 7.2 image_classification_cache（缓存表）

**用途**：存储图片分类结果，实现全局去重缓存，降低大模型调用成本

```sql
CREATE TABLE `image_classification_cache` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 图片标识（唯一键）
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希值',
  
  -- 分类结果
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个预定义类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度(0-1)',
  `description` TEXT DEFAULT NULL COMMENT '图片描述',
  
  -- 模型信息
  `model_used` VARCHAR(50) NOT NULL COMMENT '使用的模型',
  `model_response` JSON DEFAULT NULL COMMENT '完整模型响应',
  
  -- 统计信息
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_image_hash` (`image_hash`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`),
  KEY `idx_hit_count` (`hit_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='图片分类全局缓存表';
```

**字段说明**：

| 字段 | 类型 | 说明 | 备注 |
|------|------|------|------|
| id | BIGINT | 主键 | 自增 |
| image_hash | VARCHAR(64) | SHA-256哈希 | 唯一索引，去重核心 |
| category | VARCHAR(50) | 分类Key | 8个类别之一：social_activities/pets/single_person/foods/travel_scenery/screenshot/idcard/other |
| confidence | DECIMAL(5,4) | 置信度 | 0.0000 ~ 0.9999 |
| description | TEXT | 图片描述 | 大模型生成的描述（可选） |
| model_used | VARCHAR(50) | 模型名称 | 如：gpt-4-vision |
| model_response | JSON | 完整响应 | 可选，用于调试 |
| hit_count | INT | 命中次数 | 统计缓存效果 |
| created_at | DATETIME | 创建时间 | 首次分类时间 |
| last_hit_at | DATETIME | 最后命中 | 最近一次命中时间 |

**索引设计**：

| 索引名 | 类型 | 字段 | 用途 |
|--------|------|------|------|
| PRIMARY | 主键 | id | 主键 |
| uk_image_hash | 唯一索引 | image_hash | 快速查询缓存，防重复 |
| idx_created_at | 普通索引 | created_at | 按时间查询 |
| idx_category | 普通索引 | category | 分类统计 |
| idx_hit_count | 普通索引 | hit_count | 热门图片统计 |

**数据示例**：

```json
{
  "id": 1,
  "image_hash": "a3f5d8c2b1e9f7a6...",
  "category": "travel_scenery",
  "confidence": 0.9523,
  "description": "一张美丽的山景日落照片，橙红色的天空映衬着连绵的山脉",
  "model_used": "gpt-4-vision-preview",
  "model_response": {"category": "travel_scenery", "confidence": 0.9523, "description": "..."},
  "hit_count": 23,
  "created_at": "2025-10-01 08:30:00",
  "last_hit_at": "2025-10-10 15:45:00"
}
```

**预定义分类枚举**：
```sql
-- category 字段可能的值（8个固定类别）
-- 'social_activities' - 社交活动
-- 'pets' - 宠物萌照
-- 'single_person' - 单人照片
-- 'foods' - 美食记录
-- 'travel_scenery' - 旅行风景
-- 'screenshot' - 手机截图
-- 'idcard' - 证件照
-- 'other' - 其它
```

---

### 7.3 request_log（请求日志表）

**用途**：记录每次分类请求，用于统计分析

```sql
CREATE TABLE `request_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 请求标识
  `request_id` VARCHAR(64) NOT NULL COMMENT '请求唯一ID',
  
  -- 用户信息（用于统计）
  `user_id` VARCHAR(64) DEFAULT NULL COMMENT '用户ID/设备ID',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
  
  -- 图片信息
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希',
  `image_size` INT UNSIGNED DEFAULT NULL COMMENT '图片大小(字节)',
  
  -- 分类结果（冗余存储，便于查询）
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度',
  
  -- 统计字段
  `from_cache` TINYINT(1) DEFAULT 0 COMMENT '是否来自缓存(0-否 1-是)',
  `processing_time_ms` INT UNSIGNED DEFAULT NULL COMMENT '处理耗时(毫秒)',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` DATE GENERATED ALWAYS AS (DATE(`created_at`)) STORED COMMENT '日期(便于分区查询)',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_from_cache` (`from_cache`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='请求日志表-用于统计分析';
```

**字段说明**：

| 字段 | 类型 | 说明 | 备注 |
|------|------|------|------|
| id | BIGINT | 主键 | 自增 |
| request_id | VARCHAR(64) | 请求ID | 唯一标识每次请求 |
| user_id | VARCHAR(64) | 用户ID | 可选，客户端生成的设备ID |
| ip_address | VARCHAR(45) | IP地址 | IPv4或IPv6 |
| image_hash | VARCHAR(64) | 图片哈希 | 关联缓存表 |
| image_size | INT | 图片大小 | 字节数 |
| category | VARCHAR(50) | 分类Key | 8个类别之一，冗余存储便于统计 |
| confidence | DECIMAL(5,4) | 置信度 | 冗余存储 |
| from_cache | TINYINT(1) | 是否缓存 | 0-新调用 1-缓存命中 |
| processing_time_ms | INT | 处理耗时 | 毫秒 |
| created_at | DATETIME | 创建时间 | 请求时间 |
| created_date | DATE | 日期 | 虚拟列，便于按日统计 |

**索引设计**：

| 索引名 | 类型 | 字段 | 用途 |
|--------|------|------|------|
| PRIMARY | 主键 | id | 主键 |
| idx_user_id | 普通索引 | user_id | 按用户统计 |
| idx_ip_address | 普通索引 | ip_address | 按IP统计 |
| idx_created_date | 普通索引 | created_date | 按日期统计 |
| idx_from_cache | 普通索引 | from_cache | 缓存命中率统计 |
| idx_created_at | 普通索引 | created_at | 时间序列查询 |

**数据示例**：

```json
{
  "id": 12345,
  "request_id": "req_67890abcdef",
  "user_id": "device_uuid_abc123",
  "ip_address": "192.168.1.100",
  "image_hash": "a3f5d8c2b1e9f7a6...",
  "image_size": 412678,
  "category": "travel_scenery",
  "confidence": 0.9523,
  "from_cache": 1,
  "processing_time_ms": 45,
  "created_at": "2025-10-10 15:45:23",
  "created_date": "2025-10-10"
}
```

---

### 7.4 常用查询SQL

#### 7.4.1 今日统计

```sql
SELECT 
    COUNT(*) as total_requests,
    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as cache_hits,
    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) as cache_misses,
    ROUND(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as cache_hit_rate,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT ip_address) as unique_ips,
    AVG(processing_time_ms) as avg_processing_time,
    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) * 0.01 as estimated_cost,
    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * 0.01 as cost_saved
FROM request_log
WHERE created_date = CURDATE();
```

#### 7.4.2 缓存效率统计

```sql
SELECT 
    COUNT(*) as total_cached_images,
    SUM(hit_count) as total_hits,
    SUM(hit_count - 1) as times_saved,
    (SUM(hit_count - 1) * 0.01) as cost_saved,
    AVG(hit_count) as avg_hit_per_image,
    MAX(hit_count) as max_hits
FROM image_classification_cache;
```

#### 7.4.3 分类分布统计

```sql
SELECT 
    category,
    COUNT(*) as count,
    ROUND(AVG(confidence), 4) as avg_confidence,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM request_log WHERE created_date = CURDATE()), 2) as percentage
FROM request_log
WHERE created_date = CURDATE()
GROUP BY category
ORDER BY count DESC;
```

#### 7.4.4 热门图片Top10

```sql
SELECT 
    image_hash,
    category,
    confidence,
    hit_count,
    created_at,
    last_hit_at,
    TIMESTAMPDIFF(DAY, created_at, last_hit_at) as lifetime_days
FROM image_classification_cache
ORDER BY hit_count DESC
LIMIT 10;
```

#### 7.4.5 用户请求Top20

```sql
SELECT 
    user_id,
    COUNT(*) as request_count,
    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as cache_hits,
    ROUND(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as cache_hit_rate,
    MIN(created_at) as first_request,
    MAX(created_at) as last_request
FROM request_log
WHERE user_id IS NOT NULL
GROUP BY user_id
ORDER BY request_count DESC
LIMIT 20;
```

---

## 8. 核心业务流程

### 8.1 图片分类流程

```python
def classify_image_flow(image_bytes, user_id, ip_address):
    """
    完整的图片分类流程
    """
    # 步骤1: 生成请求ID
    request_id = generate_request_id()
    start_time = time.time()
    
    # 步骤2: 图片预处理
    # - 验证格式（jpg/png/webp等）
    # - 验证大小（最大10MB）
    # - 可选：压缩/调整尺寸
    validate_image(image_bytes)
    
    # 步骤3: 计算SHA-256哈希
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    image_size = len(image_bytes)
    
    # 步骤4: 查询缓存
    cached_result = query_cache_by_hash(image_hash)
    
    if cached_result:
        # 缓存命中分支
        # 4.1 更新缓存统计
        increment_cache_hit_count(image_hash)
        
        # 4.2 记录请求日志
        processing_time = int((time.time() - start_time) * 1000)
        log_request(
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            image_hash=image_hash,
            image_size=image_size,
            category=cached_result['category'],
            confidence=cached_result['confidence'],
            from_cache=True,
            processing_time_ms=processing_time
        )
        
        # 4.3 返回结果
        return build_response(cached_result, from_cache=True, request_id=request_id)
    
    # 步骤5: 缓存未命中，调用大模型
    try:
        model_result = call_llm_api(image_bytes)
    except Exception as e:
        # 错误处理：重试、降级等
        handle_llm_error(e)
        raise
    
    # 步骤6: 保存到缓存
    save_to_cache(image_hash, model_result)
    
    # 步骤7: 记录请求日志
    processing_time = int((time.time() - start_time) * 1000)
    log_request(
        request_id=request_id,
        user_id=user_id,
        ip_address=ip_address,
        image_hash=image_hash,
        image_size=image_size,
        category=model_result['category'],
        confidence=model_result['confidence'],
        from_cache=False,
        processing_time_ms=processing_time
    )
    
    # 步骤8: 返回结果
    return build_response(model_result, from_cache=False, request_id=request_id)
```

### 8.2 成本优化机制

**核心思想**：通过SHA-256哈希实现全局去重缓存

```
场景模拟：
- 1000个用户，每天共上传10000张图片
- 其中30%是重复图片（网络流行图片、表情包等）

无缓存：
- 大模型调用次数：10000次
- 成本：10000 × 0.01元 = 100元/天

有缓存：
- 首次调用：7000次（唯一图片）
- 缓存命中：3000次（重复图片）
- 成本：7000 × 0.01元 = 70元/天
- 节省：30元/天 = 900元/月 = 10800元/年
```

---

## 9. 技术栈

### 9.1 后端框架与Web容器

**核心技术栈**：
- **FastAPI**: 现代、高性能的Web框架
- **Python 3.10+**: 编程语言
- **Uvicorn**: ASGI服务器（开发环境）
- **Gunicorn + Uvicorn Workers**: 生产环境推荐

**Web容器架构**：

```
生产环境推荐方案：

┌─────────────────────────────────────┐
│     Nginx / Caddy (反向代理)         │
│  - HTTPS终止                        │
│  - 静态文件服务                      │
│  - 负载均衡                          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Gunicorn (进程管理器)              │
│  - 多进程管理                        │
│  - 自动重启                          │
│  - 优雅关闭                          │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┬──────┬──────┐
        ▼             ▼      ▼      ▼
    ┌───────┐    ┌───────┐  ...  ┌───────┐
    │Uvicorn│    │Uvicorn│       │Uvicorn│
    │Worker │    │Worker │       │Worker │
    │  #1   │    │  #2   │       │  #N   │
    └───┬───┘    └───┬───┘       └───┬───┘
        │            │               │
        └────────────┴───────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  FastAPI 应用   │
            └─────────────────┘
```

### 9.2 数据库
- **MySQL 8.0+**: 关系型数据库
- **PyMySQL / aiomysql**: MySQL驱动

### 9.3 图片处理
- **Pillow (PIL)**: 图片验证、格式转换
- **hashlib**: SHA-256哈希计算

### 9.4 大模型SDK
- **OpenAI SDK**: GPT-4 Vision
- **Anthropic SDK**: Claude Vision
- 或其他自定义模型API

### 9.5 其他工具
- **pydantic**: 数据验证
- **python-dotenv**: 环境变量管理
- **loguru**: 日志记录

---

## 10. 配置说明

### 10.1 环境变量配置

```ini
# .env

# ===== MySQL配置 =====
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=image_classifier
MYSQL_POOL_SIZE=10

# ===== 大模型配置 =====
LLM_PROVIDER=openai                    # openai / claude / custom
LLM_API_KEY=sk-xxxxxxxxxxxxx
LLM_MODEL=gpt-4-vision-preview
LLM_MAX_TOKENS=500
LLM_TIMEOUT=30

# ===== 应用配置 =====
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false
MAX_IMAGE_SIZE_MB=10
ALLOWED_IMAGE_FORMATS=jpg,jpeg,png,webp,gif

# ===== 统计配置 =====
ENABLE_REQUEST_LOG=true                # 是否记录请求日志
LOG_RETENTION_DAYS=90                  # 日志保留天数

# ===== 成本配置（用于统计） =====
COST_PER_API_CALL=0.01                 # 每次大模型调用成本（元）
```

### 10.2 数据库初始化

```bash
# 创建数据库和表
mysql -u root -p < sql/init.sql
```

---

## 11. 成本分析

### 11.1 成本构成

| 项目 | 说明 | 预估成本 |
|------|------|---------|
| 大模型API | 按调用次数计费 | 主要成本 |
| MySQL | 云数据库或自建 | 较低 |
| 服务器 | 2核4G起步 | 中等 |
| 带宽 | 图片上传流量 | 较低 |

### 11.2 缓存收益计算

```
假设参数：
- 日请求量：10,000次
- 重复率：30%
- API成本：0.01元/次

月度对比：
┌─────────────┬──────────┬──────────┬──────────┐
│   方案      │ API调用  │ 月成本   │ 节省     │
├─────────────┼──────────┼──────────┼──────────┤
│ 无缓存      │ 300,000  │ 3,000元  │ -        │
│ 缓存(30%)   │ 210,000  │ 2,100元  │ 900元    │
│ 缓存(50%)   │ 150,000  │ 1,500元  │ 1,500元  │
└─────────────┴──────────┴──────────┴──────────┘
```

### 11.3 优化建议

1. **提高缓存命中率**
   - 网络流行图片命中率高
   - 用户重复上传同一张照片

2. **优化图片大小**
   - 压缩后再调用API
   - 降低传输成本

3. **批量处理**
   - 支持批量上传
   - 减少网络开销

---

## 12. 扩展性设计

### 12.1 水平扩展

当前架构支持无缝扩展：

```
┌─────────────┐
│ Load Balancer│
└──────┬───────┘
       │
   ┌───┴────┬────────┬────────┐
   ▼        ▼        ▼        ▼
┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│ API │ │ API │ │ API │ │ API │  (无状态，可横向扩展)
│ 实例1│ │ 实例2│ │ 实例3│ │ 实例4│
└──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘
   └───────┴────────┴────────┘
            │
            ▼
      ┌──────────┐
      │  MySQL   │  (主从复制，读写分离)
      └──────────┘
```

### 12.2 性能优化

1. **数据库优化**
   - 读写分离（主库写，从库读）
   - 索引优化
   - 连接池管理

2. **引入Redis**（可选）
   - 热点数据缓存
   - 减轻MySQL压力

3. **CDN加速**（可选）
   - 静态资源分发
   - 图片上传加速

### 12.3 监控告警

建议监控指标：

- API响应时间
- 缓存命中率
- 数据库连接数
- 大模型API调用次数
- 错误率

---

## 13. 安全考虑

### 13.1 输入验证
- ✅ 文件格式白名单
- ✅ 文件大小限制
- ✅ 图片内容验证（防止恶意文件）

### 13.2 数据保护
- ✅ 不存储原始图片（隐私保护）
- ✅ 哈希不可逆（无法还原原图）
- ✅ HTTPS传输（可选）

### 13.3 API安全
- 可选：API Key认证
- 可选：IP白名单
- 可选：签名验证

---

## 14. Web容器实现与部署方案

### 14.1 Web容器方案对比

| 方案 | 适用场景 | 并发能力 | 配置复杂度 | 推荐度 |
|------|---------|---------|-----------|--------|
| Uvicorn单进程 | 开发环境 | 低 | 简单 | ⭐⭐⭐ (开发) |
| Gunicorn+Uvicorn | 生产环境 | 高 | 中等 | ⭐⭐⭐⭐⭐ |
| Docker | 容器化部署 | 可扩展 | 中等 | ⭐⭐⭐⭐⭐ |
| Kubernetes | 大规模集群 | 极高 | 复杂 | ⭐⭐⭐⭐ |

---

### 14.2 开发环境部署

#### 14.2.1 使用Uvicorn（开发调试）

**步骤**：

```bash
# 1. 激活conda环境
conda activate wechat-classifier

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置MySQL和大模型API

# 4. 初始化数据库
mysql -u root -p < sql/init.sql

# 5. 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Uvicorn参数说明**：

```bash
uvicorn app.main:app \
  --reload           # 代码变更自动重载（仅开发环境）
  --host 0.0.0.0     # 监听所有网络接口
  --port 8000        # 端口号
  --log-level info   # 日志级别：debug/info/warning/error
  --workers 1        # 工作进程数（开发环境建议1个）
```

**访问**：
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

---

### 14.3 生产环境部署

#### 14.3.1 方案1：Gunicorn + Uvicorn Workers（推荐）

**为什么使用Gunicorn？**
- ✅ 成熟的进程管理器
- ✅ 支持多worker进程（充分利用多核CPU）
- ✅ 自动重启崩溃的进程
- ✅ 优雅关闭和重启
- ✅ 与Uvicorn完美配合

**安装**：

```bash
pip install gunicorn uvicorn[standard]
```

**启动命令**：

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --access-logfile /var/log/image-classifier/access.log \
  --error-logfile /var/log/image-classifier/error.log \
  --log-level info
```

**配置文件方式（gunicorn_config.py）**：

```python
# gunicorn_config.py
import multiprocessing
import os

# 服务器配置
bind = "0.0.0.0:8000"
backlog = 2048

# Worker配置
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐公式
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # 处理N个请求后重启worker（防止内存泄漏）
max_requests_jitter = 50

# 超时配置
timeout = 120  # 请求超时（秒）
graceful_timeout = 30  # 优雅关闭超时
keepalive = 5  # Keep-Alive超时

# 日志配置
accesslog = "/var/log/image-classifier/access.log"
errorlog = "/var/log/image-classifier/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "image-classifier"

# 其他配置
daemon = False  # 是否后台运行（建议用systemd管理）
pidfile = "/var/run/image-classifier.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# 环境变量
raw_env = [
    f"ENV=production",
]
```

**使用配置文件启动**：

```bash
gunicorn -c gunicorn_config.py app.main:app
```

#### 14.3.2 Systemd服务配置

创建服务文件：`/etc/systemd/system/image-classifier.service`

```ini
[Unit]
Description=Image Classifier API Service
After=network.target mysql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/image-classifier
Environment="PATH=/home/user/miniconda3/envs/wechat-classifier/bin"
ExecStart=/home/user/miniconda3/envs/wechat-classifier/bin/gunicorn \
    -c gunicorn_config.py \
    app.main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**管理服务**：

```bash
# 启动服务
sudo systemctl start image-classifier

# 设置开机自启
sudo systemctl enable image-classifier

# 查看状态
sudo systemctl status image-classifier

# 重启服务
sudo systemctl restart image-classifier

# 查看日志
sudo journalctl -u image-classifier -f
```

#### 14.3.3 方案2：Docker容器化部署

**Dockerfile**：

```dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# 启动命令
CMD ["gunicorn", "-c", "gunicorn_config.py", "app.main:app"]
```

**docker-compose.yml**：

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: image-classifier-api
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=classifier
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - MYSQL_DATABASE=image_classifier
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - ./logs:/var/log/image-classifier
    restart: unless-stopped
    networks:
      - classifier-network

  mysql:
    image: mysql:8.0
    container_name: image-classifier-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=image_classifier
      - MYSQL_USER=classifier
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql-data:/var/lib/mysql
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - classifier-network

  nginx:
    image: nginx:alpine
    container_name: image-classifier-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - classifier-network

volumes:
  mysql-data:

networks:
  classifier-network:
    driver: bridge
```

**启动Docker服务**：

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down

# 重启单个服务
docker-compose restart api
```

#### 14.3.4 Nginx反向代理配置

**nginx.conf**：

```nginx
upstream image_classifier_backend {
    # 多个Gunicorn实例负载均衡
    server 127.0.0.1:8000 weight=1;
    # server 127.0.0.1:8001 weight=1;  # 如有多实例
    
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourapp.com;
    
    # 重定向到HTTPS（生产环境建议）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourapp.com;
    
    # SSL配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # 日志
    access_log /var/log/nginx/classifier_access.log;
    error_log /var/log/nginx/classifier_error.log;
    
    # 上传限制
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    
    # 超时配置
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;
    
    # 代理到后端
    location / {
        proxy_pass http://image_classifier_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 健康检查
    location /health {
        proxy_pass http://image_classifier_backend/api/v1/health;
        access_log off;
    }
    
    # 静态文件（如果有）
    location /static/ {
        alias /opt/image-classifier/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

### 14.4 性能优化建议

#### Worker数量配置

```python
# 推荐公式
workers = (CPU核心数 × 2) + 1

# 示例：
# 2核CPU: workers = 5
# 4核CPU: workers = 9
# 8核CPU: workers = 17

# 考虑内存限制：
# 每个worker约占用 100-200MB
# 4GB内存建议 8-10 workers
# 8GB内存建议 16-20 workers
```

#### 连接池配置

```python
# MySQL连接池（aiomysql）
MYSQL_POOL_SIZE = 10  # 每个worker的连接数
MYSQL_MAX_OVERFLOW = 5
MYSQL_POOL_RECYCLE = 3600
```

---

### 14.5 监控与健康检查

```bash
# 检查进程
ps aux | grep gunicorn

# 检查端口
netstat -tlnp | grep 8000

# 测试健康检查
curl http://localhost:8000/api/v1/health

# 查看实时日志
tail -f /var/log/image-classifier/error.log

# 性能监控
htop
```

---

### 14.6 Web容器选择建议

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 本地开发 | Uvicorn单进程 | 简单、支持热重载 |
| 测试环境 | Gunicorn + 2 workers | 接近生产环境 |
| 生产环境（单机） | Gunicorn + 多workers | 稳定、高性能 |
| 生产环境（容器） | Docker + Gunicorn | 标准化、易部署 |
| 生产环境（集群） | Kubernetes + Docker | 可扩展、高可用 |

---

## 15. 总结

### 15.1 核心优势
- ✅ **成本优化**：通过缓存大幅降低大模型调用成本（节省30%）
- ✅ **带宽优化**：哈希预查询+客户端压缩（节省90%上传带宽）
- ✅ **隐私保护**：不存储原始图片
- ✅ **简单高效**：单一MySQL数据库，架构清晰
- ✅ **易于扩展**：无状态设计，支持水平扩展
- ✅ **用户体验**：缓存命中快速响应，压缩减少等待时间
- ✅ **数据驱动**：完善的统计分析，了解使用情况

### 15.2 适用场景
- 多用户图片分类应用
- 成本敏感型AI应用
- 需要快速上线的MVP产品

### 15.3 后续优化方向
1. 引入Redis缓存热点数据
2. 实现用户认证系统
3. 支持批量分类
4. 增加更多统计维度
5. 实现实时监控大盘

---

## 附录A：完整SQL初始化脚本

```sql
-- ====================================
-- 图片分类系统数据库初始化脚本
-- ====================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS image_classifier 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE image_classifier;

-- ====================================
-- 表1: 图片分类缓存表
-- ====================================
CREATE TABLE `image_classification_cache` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 图片标识
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希值',
  
  -- 分类结果（8个固定类别）
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个预定义类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度(0-1)',
  `description` TEXT DEFAULT NULL COMMENT '图片描述',
  
  -- 模型信息
  `model_used` VARCHAR(50) NOT NULL COMMENT '使用的模型',
  `model_response` JSON DEFAULT NULL COMMENT '完整模型响应',
  
  -- 统计信息
  `hit_count` INT UNSIGNED DEFAULT 1 COMMENT '缓存命中次数',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
  `last_hit_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后命中时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_image_hash` (`image_hash`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`),
  KEY `idx_hit_count` (`hit_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='图片分类全局缓存表';

-- category 字段可能的值（8个固定类别）：
-- 'social_activities' - 社交活动
-- 'pets' - 宠物萌照  
-- 'single_person' - 单人照片
-- 'foods' - 美食记录
-- 'travel_scenery' - 旅行风景
-- 'screenshot' - 手机截图
-- 'idcard' - 证件照
-- 'other' - 其它

-- ====================================
-- 表2: 请求日志表
-- ====================================
CREATE TABLE `request_log` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  
  -- 请求标识
  `request_id` VARCHAR(64) NOT NULL COMMENT '请求唯一ID',
  
  -- 用户信息（可选）
  `user_id` VARCHAR(64) DEFAULT NULL COMMENT '用户ID/设备ID',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址',
  
  -- 图片信息
  `image_hash` VARCHAR(64) NOT NULL COMMENT 'SHA-256哈希',
  `image_size` INT UNSIGNED DEFAULT NULL COMMENT '图片大小(字节)',
  
  -- 分类结果（冗余存储）
  `category` VARCHAR(50) NOT NULL COMMENT '分类Key（8个类别之一）',
  `confidence` DECIMAL(5,4) NOT NULL COMMENT '置信度',
  
  -- 统计字段
  `from_cache` TINYINT(1) DEFAULT 0 COMMENT '是否来自缓存(0-否 1-是)',
  `processing_time_ms` INT UNSIGNED DEFAULT NULL COMMENT '处理耗时(毫秒)',
  
  -- 时间戳
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_date` DATE GENERATED ALWAYS AS (DATE(`created_at`)) STORED COMMENT '日期',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_created_date` (`created_date`),
  KEY `idx_from_cache` (`from_cache`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='请求日志表-用于统计分析';

-- ====================================
-- 初始化完成
-- ====================================
SELECT '数据库初始化完成！' AS message;
SELECT '共创建 2 张表：image_classification_cache, request_log' AS info;
```

---

## 附录B：分类映射配置（客户端）

客户端应维护以下分类映射表：

```json
{
  "categoryNameMap": {
    "social_activities": {
      "chinese": "社交活动",
      "english": "Social Activities"
    },
    "pets": {
      "chinese": "宠物萌照",
      "english": "Pet Photos"
    },
    "single_person": {
      "chinese": "单人照片",
      "english": "Single Person Photos"
    },
    "foods": {
      "chinese": "美食记录",
      "english": "Food Records"
    },
    "travel_scenery": {
      "chinese": "旅行风景",
      "english": "Travel Scenery"
    },
    "screenshot": {
      "chinese": "手机截图",
      "english": "Mobile Screenshots"
    },
    "idcard": {
      "chinese": "证件照",
      "english": "ID Card"
    },
    "other": {
      "chinese": "其它",
      "english": "Other Images"
    }
  }
}
```

**使用示例**：

```javascript
// 接收到服务器返回的category key
const categoryKey = response.data.category;  // "travel_scenery"

// 获取对应的显示名称
const displayName = categoryNameMap[categoryKey].chinese;  // "旅行风景"
```

---

**文档版本**: v1.1  
**最后更新**: 2025-10-10  
**维护者**: ImageClassifier Team

