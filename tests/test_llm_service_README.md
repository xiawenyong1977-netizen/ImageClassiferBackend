# LLM服务层测试说明

## 测试文件

`tests/test_llm_service.py` - LLM服务层的完整测试套件

## 测试分类

### 1. Mock测试（17个测试用例）

这些测试使用Mock来模拟API调用，不依赖真实的API密钥，可以快速运行。

#### TestBaseLLMService（4个测试）
- `test_successful_call` - 测试成功调用
- `test_retry_on_retryable_error` - 测试可重试错误的重试机制
- `test_no_retry_on_non_retryable_error` - 测试不可重试错误不重试
- `test_max_retries_exceeded` - 测试超过最大重试次数

#### TestLLMService（7个测试）
- `test_create_aliyun_provider` - 测试创建阿里云提供商
- `test_create_openai_provider` - 测试创建OpenAI提供商
- `test_create_claude_provider` - 测试创建Claude提供商
- `test_invalid_provider` - 测试无效的提供商
- `test_classify_image_with_default_prompt` - 测试使用默认提示词
- `test_classify_image_with_custom_prompt` - 测试使用自定义提示词
- `test_get_provider_info` - 测试获取提供商信息

#### TestProviderAdapters（6个测试）
- `test_aliyun_classification` - 测试阿里云分类适配器
- `test_aliyun_image_edit` - 测试阿里云图像编辑适配器
- `test_openai_classification` - 测试OpenAI分类适配器
- `test_claude_classification` - 测试Claude分类适配器
- `test_openai_image_edit_not_supported` - 测试OpenAI不支持图像编辑
- `test_claude_image_edit_not_supported` - 测试Claude不支持图像编辑

### 2. 真实API调用测试（3个测试用例）

这些测试会进行真实的API调用，需要设置相应的环境变量。

#### TestAliyunProviderReal
- `test_real_classification` - 真实阿里云分类API调用

**环境变量**: `TEST_ALIYUN_API_KEY`

#### TestOpenAIProviderReal
- `test_real_classification` - 真实OpenAI分类API调用

**环境变量**: `TEST_OPENAI_API_KEY`

#### TestClaudeProviderReal
- `test_real_classification` - 真实Claude分类API调用

**环境变量**: `TEST_CLAUDE_API_KEY`

## 运行测试

### 运行所有Mock测试（推荐）

```bash
# 运行所有Mock测试（排除真实API调用测试）
pytest tests/test_llm_service.py -v -k "not Real"

# 或者运行所有测试（真实API调用测试会被跳过）
pytest tests/test_llm_service.py -v
```

### 运行特定测试类

```bash
# 运行基础服务层测试
pytest tests/test_llm_service.py::TestBaseLLMService -v

# 运行统一服务入口测试
pytest tests/test_llm_service.py::TestLLMService -v

# 运行提供商适配器测试
pytest tests/test_llm_service.py::TestProviderAdapters -v
```

### 运行真实API调用测试

**注意**: 这些测试会消耗API配额，请谨慎使用。

```bash
# 设置环境变量（Windows PowerShell）
$env:TEST_ALIYUN_API_KEY="your-api-key"

# 运行阿里云真实API测试
pytest tests/test_llm_service.py::TestAliyunProviderReal -v

# 设置OpenAI API密钥
$env:TEST_OPENAI_API_KEY="your-api-key"

# 运行OpenAI真实API测试
pytest tests/test_llm_service.py::TestOpenAIProviderReal -v

# 设置Claude API密钥
$env:TEST_CLAUDE_API_KEY="your-api-key"

# 运行Claude真实API测试
pytest tests/test_llm_service.py::TestClaudeProviderReal -v
```

## 测试覆盖率

运行测试并生成覆盖率报告：

```bash
# 运行测试并生成覆盖率报告
pytest tests/test_llm_service.py --cov=app.services.llm --cov-report=html

# 查看HTML报告
# 打开 htmlcov/index.html
```

## 测试数据

测试使用最小的有效PNG图片（1x1像素）来减少API调用成本。

## 注意事项

1. **Mock测试**: 所有Mock测试不依赖外部服务，可以安全运行
2. **真实API测试**: 需要设置环境变量，会消耗API配额
3. **跳过逻辑**: 如果没有设置相应的API密钥，真实API测试会自动跳过
4. **测试隔离**: 每个测试都是独立的，不会相互影响

## 持续集成

在CI/CD环境中，建议：
- 只运行Mock测试（`-k "not Real"`）
- 真实API测试可以在需要时手动运行或使用专用的测试环境

