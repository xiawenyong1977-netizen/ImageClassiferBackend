# LLM Provider 错误码说明文档

本文档说明不同 LLM Provider 的错误码定义和处理方式。

## 错误处理架构

### 两层错误处理机制

1. **BaseService 层** (`base_service.py`)
   - `_parse_error()`: 通用错误解析，处理所有provider的通用HTTP状态码
   - 提供统一的重试逻辑和错误分类

2. **Provider 层** (`providers.py`)
   - 每个provider可以有自己的特定错误处理
   - 处理provider特定的错误码和错误消息格式

---

## 阿里云 (Aliyun/DashScope)

### 使用的模型
- **qwen-vl-plus**: 图像分类（多模态理解）
- **qwen-image-edit**: 图像编辑

### 错误码定义

| HTTP状态码 | 错误类型 | 是否重试 | 说明 | 示例错误码 |
|-----------|---------|---------|------|-----------|
| 400 | INPUT_ERROR | ❌ 否 | 参数错误 | InvalidParameter, url error, invalid format等 |
| 401 | AUTH_ERROR | ❌ 否 | API key 错误 | InvalidApiKey, invalid_api_key |
| 402 | BUSINESS_ERROR | ❌ 否 | 余额不足 | Arrearage |
| 403 | AUTH_ERROR | ❌ 否 | 访问被拒绝 | AccessDenied, Model.AccessDenied |
| 404 | BUSINESS_ERROR | ❌ 否 | 资源不存在 | ModelNotFound, WorkSpaceNotFound |
| 409 | BUSINESS_ERROR | ❌ 否 | 资源冲突 | Conflict |
| 422 | INPUT_ERROR | ❌ 否 | 参数错误 | 参数验证失败 |
| 429 | RATE_LIMIT_ERROR | ✅ 是 | 请求速率达到上限 | Throttling, RateQuota |
| 500 | SERVER_ERROR | ✅ 是 | 服务器内部错误 | InternalError, SystemError |
| 503 | SERVER_ERROR | ✅ 是 | 服务不可用 | ModelServingError, ModelUnavailable |

### 特殊错误类型

- **400错误**：包含大量子类型，如：
  - `InvalidParameter`: 参数错误
  - `url error`: URL错误
  - `InvalidFile.*`: 文件相关错误（格式、大小、分辨率等）
  - `DataInspectionFailed`: 内容合规检查失败
  - `Arrearage`: 账号欠费

### 文档链接
- 官方文档：https://help.aliyun.com/zh/dashscope/developer-reference/error-codes
- API文档：https://help.aliyun.com/zh/dashscope/developer-reference/api-details

---

## OpenAI

### 使用的模型
- **gpt-4-vision-preview**: 图像分类（Vision API）

### 错误码定义

| HTTP状态码 | 错误类型 | 是否重试 | 说明 |
|-----------|---------|---------|------|
| 400 | INPUT_ERROR | ❌ 否 | 请求体格式错误 |
| 401 | AUTH_ERROR | ❌ 否 | API key 错误 |
| 402 | BUSINESS_ERROR | ❌ 否 | 余额不足 |
| 422 | INPUT_ERROR | ❌ 否 | 参数错误 |
| 429 | RATE_LIMIT_ERROR | ✅ 是 | 请求速率达到上限 |
| 500 | SERVER_ERROR | ✅ 是 | 服务器内部错误 |
| 503 | SERVER_ERROR | ✅ 是 | 服务器繁忙 |

### 特殊说明
- 使用 OpenAI SDK，错误通过异常对象传递
- 错误消息可能包含英文描述
- 通过 `status_code` 和错误消息关键词识别错误类型

### 文档链接
- 官方文档：https://platform.openai.com/docs/guides/error-codes

---

## Claude (Anthropic)

### 使用的模型
- **claude-3-opus**: 图像分类（Vision API）

### 错误码定义

| HTTP状态码 | 错误类型 | 是否重试 | 说明 |
|-----------|---------|---------|------|
| 400 | INPUT_ERROR | ❌ 否 | 请求体格式错误 |
| 401 | AUTH_ERROR | ❌ 否 | API key 错误 |
| 402 | BUSINESS_ERROR | ❌ 否 | 余额不足 |
| 422 | INPUT_ERROR | ❌ 否 | 参数错误 |
| 429 | RATE_LIMIT_ERROR | ✅ 是 | 请求速率达到上限 |
| 500 | SERVER_ERROR | ✅ 是 | 服务器内部错误 |
| 503 | SERVER_ERROR | ✅ 是 | 服务器繁忙 |

### 特殊说明
- 使用 Anthropic SDK，错误通过异常对象传递
- 错误处理逻辑与 OpenAI 类似

### 文档链接
- 官方文档：https://docs.anthropic.com/claude/reference/errors

---

## Deepseek

### 使用的模型
- **deepseek-chat**: 文本生成（兼容OpenAI API格式）

### 错误码定义

| HTTP状态码 | 错误类型 | 是否重试 | 说明 |
|-----------|---------|---------|------|
| 400 | INPUT_ERROR | ❌ 否 | 格式错误：请求体格式错误 |
| 401 | AUTH_ERROR | ❌ 否 | 认证失败：API key 错误 |
| 402 | BUSINESS_ERROR | ❌ 否 | 余额不足：账号余额不足 |
| 422 | INPUT_ERROR | ❌ 否 | 参数错误：请求体参数错误 |
| 429 | RATE_LIMIT_ERROR | ✅ 是 | 请求速率达到上限：TPM 或 RPM 达到上限 |
| 500 | SERVER_ERROR | ✅ 是 | 服务器故障：服务器内部故障 |
| 503 | SERVER_ERROR | ✅ 是 | 服务器繁忙：服务器负载过高 |

### 特殊说明
- 使用 OpenAI 兼容的 API 格式
- API 基础 URL: `https://api.deepseek.com`
- 错误处理逻辑与 OpenAI 类似

### 文档链接
- 官方文档：https://platform.deepseek.com/docs

---

## 错误处理流程

```
API调用失败
    ↓
Provider层捕获异常
    ↓
调用 base_service._parse_error() 或 Provider特定处理
    ↓
转换为 LLMError
    ↓
根据 should_retry 决定是否重试
    ↓
返回错误信息给 llm_service 层
```

## 统一错误类型映射

所有provider的错误最终都会映射到以下统一错误类型：

- **INPUT_ERROR**: 输入/参数错误（不重试）
- **AUTH_ERROR**: 认证/权限错误（不重试）
- **BUSINESS_ERROR**: 业务逻辑错误（不重试）
- **RATE_LIMIT_ERROR**: 限流错误（可重试）
- **SERVER_ERROR**: 服务器错误（可重试）
- **NETWORK_ERROR**: 网络错误（可重试）
- **FORMAT_ERROR**: 格式错误（可重试）

## 最佳实践

1. **优先使用 base_service._parse_error()**: 对于通用HTTP状态码，使用统一的错误解析
2. **Provider特定处理**: 对于provider特有的错误码或错误格式，在provider层单独处理
3. **错误消息保留**: 保留原始错误消息，便于调试和问题定位
4. **错误码提取**: 尽可能提取provider特定的错误码（error_code），便于问题追踪

