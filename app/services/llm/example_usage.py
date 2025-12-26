"""
新LLM服务层使用示例
此文件仅作为示例，不修改现有业务代码
"""

# 示例1: 使用默认配置的分类服务
async def example_classification_default():
    """使用默认配置进行分类"""
    from app.services.llm import llm_service
    
    # 假设有图片数据
    image_bytes = b"..."  # 图片二进制数据
    
    try:
        result = await llm_service.classify_image(image_bytes)
        print(f"分类结果: {result['content']}")
    except Exception as e:
        print(f"分类失败: {e}")


# 示例2: 使用自定义配置的分类服务
async def example_classification_custom():
    """使用自定义配置进行分类"""
    from app.services.llm import LLMService
    
    service = LLMService(
        provider="aliyun",
        api_key="your-api-key",
        model="qwen-vl-plus",
        max_retries=5,
        retry_delay=2.0,
        timeout=60
    )
    
    image_bytes = b"..."  # 图片二进制数据
    custom_prompt = "请对这张图片进行分类..."
    
    try:
        result = await service.classify_image(image_bytes, prompt=custom_prompt)
        print(f"分类结果: {result['content']}")
    except Exception as e:
        print(f"分类失败: {e}")


# 示例3: 图像编辑服务
async def example_image_edit():
    """使用图像编辑服务"""
    from app.services.llm import llm_service
    
    image_bytes = b"..."  # 图片二进制数据
    prompt = "将背景改为蓝色"
    
    try:
        result = await llm_service.edit_image(
            image_bytes=image_bytes,
            prompt=prompt,
            edit_type="enhance",
            negative_prompt="",
            watermark=False
        )
        print(f"编辑结果URL: {result['result_url']}")
    except Exception as e:
        print(f"编辑失败: {e}")


# 示例4: 直接使用提供商适配器
async def example_direct_provider():
    """直接使用提供商适配器"""
    from app.services.llm import AliyunProvider
    
    provider = AliyunProvider(
        provider="aliyun",
        api_key="your-api-key",
        model="qwen-vl-plus",
        max_retries=3,
        retry_delay=1.0,
        timeout=30
    )
    
    image_bytes = b"..."  # 图片二进制数据
    prompt = "分类提示词"
    
    try:
        # 分类任务
        result = await provider.call_with_retry(
            task_type="classification",
            image_bytes=image_bytes,
            prompt=prompt
        )
        print(f"分类结果: {result['content']}")
        
        # 编辑任务
        edit_result = await provider.call_with_retry(
            task_type="image_edit",
            image_bytes=image_bytes,
            prompt="编辑提示词",
            edit_type="enhance"
        )
        print(f"编辑结果URL: {edit_result['result_url']}")
    except Exception as e:
        print(f"调用失败: {e}")


# 示例5: 与统一缓存服务配合使用
async def example_with_cache():
    """与统一缓存服务配合使用"""
    from app.services.llm import llm_service
    from app.services.unified_llm_cache import unified_llm_cache
    from app.utils.hash_utils import calculate_hash
    import hashlib
    
    image_bytes = b"..."  # 图片二进制数据
    prompt = "分类提示词"
    
    # 计算哈希
    image_hash = calculate_hash(image_bytes)
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    # 先查缓存
    cached = await unified_llm_cache.get_cached_result(
        prompt=prompt,
        image_hash=image_hash,
        model_key="aliyun:qwen-vl-plus"
    )
    
    if cached:
        print("缓存命中，使用缓存结果")
        return cached['result']
    
    # 缓存未命中，调用大模型
    try:
        result = await llm_service.classify_image(image_bytes, prompt=prompt)
        
        # 保存到缓存
        await unified_llm_cache.save_result(
            prompt=prompt,
            image_hash=image_hash,
            provider="aliyun",
            model_id="qwen-vl-plus",
            result=result['content'],
            service_type="classification"
        )
        
        print("大模型调用成功，结果已缓存")
        return result['content']
    except Exception as e:
        print(f"大模型调用失败: {e}")
        raise

