# 通用大模型服务层

## 概述

这是一个通用的大模型服务层，提供统一的API调用、错误处理、重试机制、超时控制等功能。支持多个大模型提供商（阿里云、OpenAI、Claude），并可以轻松扩展新的提供商。

## 架构设计

```
┌─────────────────────────────────────┐
│  业务层（现有代码，不修改）            │
│  - ModelClient                      │
│  - ImageEditService                 │
└─────────────────────────────────────┘
           ↓ 可选使用
┌─────────────────────────────────────┐
│  统一服务入口（新增）                │
│  - LLMService                      │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  基础服务层（新增）                  │
│  - BaseLLMService                  │
│    - 统一错误处理                    │
│    - 重试机制                        │
│    - 超时控制                        │
│    - 日志记录                        │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  提供商适配层（新增）                 │
│  - AliyunProvider                  │
│  - OpenAIProvider                   │
│  - ClaudeProvider                   │
└─────────────────────────────────────┘
```

## 文件结构

```
app/services/llm/
├── __init__.py           # 模块导出
├── base_service.py       # 基础服务层（错误处理、重试等）
├── providers.py          # 提供商适配器
├── llm_service.py         # 统一服务入口
└── README.md             # 本文档
```

## 使用示例

### 1. 基本使用（使用默认配置）

```python
from app.services.llm import llm_service

# 图片分类
result = await llm_service.classify_image(image_bytes)
content = result['content']  # 获取响应文本

# 图像编辑
result = await llm_service.edit_image(
    image_bytes=image_bytes,
    prompt="将背景改为蓝色",
    edit_type="enhance"
)
result_url = result['result_url']  # 获取结果图片URL
```

### 2. 自定义配置

```python
from app.services.llm import LLMService

# 创建自定义服务实例
service = LLMService(
    provider="aliyun",
    api_key="your-api-key",
    model="qwen-vl-plus",
    max_retries=5,
    retry_delay=2.0,
    timeout=60
)

result = await service.classify_image(image_bytes, prompt="自定义提示词")
```

### 3. 直接使用提供商适配器

```python
from app.services.llm import AliyunProvider

provider = AliyunProvider(
    provider="aliyun",
    api_key="your-api-key",
    model="qwen-vl-plus"
)

# 分类任务
result = await provider.call_with_retry(
    task_type="classification",
    image_bytes=image_bytes,
    prompt="分类提示词"
)

# 编辑任务
result = await provider.call_with_retry(
    task_type="image_edit",
    image_bytes=image_bytes,
    prompt="编辑提示词",
    edit_type="enhance",
    negative_prompt="",
    watermark=False
)
```

## 功能特性

### 1. 统一错误处理
- 自动识别可重试的错误（网络超时、连接错误、限流等）
- 不可重试的错误直接抛出（认证失败、参数错误等）

### 2. 重试机制
- 支持配置最大重试次数（默认3次）
- 指数退避策略（延迟时间 = retry_delay * attempt）
- 可配置重试延迟（默认1.0秒）

### 3. 超时控制
- 支持配置超时时间（默认30秒）
- 不同任务类型可使用不同的超时设置

### 4. 日志记录
- 详细的调用日志（尝试次数、耗时、错误信息）
- 调用指标记录（可用于监控）

### 5. 多提供商支持
- 阿里云通义千问（分类 + 编辑）
- OpenAI（分类）
- Claude（分类）

## 配置项

在 `app/config.py` 中新增的配置项：

```python
LLM_MAX_RETRIES: int = 3      # 最大重试次数
LLM_RETRY_DELAY: float = 1.0  # 重试延迟(秒)
```

## 返回值格式

### 分类任务返回值

```python
{
    "success": True,
    "content": "JSON格式的分类结果文本",
    "raw_response": <原始响应对象>
}
```

### 图像编辑任务返回值

```python
{
    "success": True,
    "result_url": "https://...",  # 结果图片URL
    "raw_response": <原始响应对象>
}
```

## 扩展新提供商

要添加新的提供商，只需：

1. 在 `providers.py` 中创建新的Provider类
2. 继承 `LLMProvider` 基类
3. 实现 `_call_classification` 和 `_call_image_edit` 方法

示例：

```python
class NewProvider(LLMProvider):
    async def _call_classification(self, image_bytes: bytes, prompt: str) -> Dict[str, Any]:
        # 实现分类逻辑
        pass
    
    async def _call_image_edit(self, image_bytes: bytes, prompt: str, **kwargs) -> Dict[str, Any]:
        # 实现编辑逻辑
        pass
```

## 注意事项

1. **不修改现有业务代码**：新的服务层与现有代码并存，可以逐步迁移
2. **向后兼容**：现有的 `ModelClient` 和 `ImageEditService` 继续工作
3. **可选使用**：业务代码可以选择使用新服务层，也可以继续使用原有代码
4. **统一缓存**：建议与新创建的 `UnifiedLLMCacheService` 配合使用

## 后续计划

1. 集成到分类服务（`ModelClient`）
2. 集成到编辑服务（`ImageEditService`）
3. 添加更多监控指标
4. 支持更多提供商

