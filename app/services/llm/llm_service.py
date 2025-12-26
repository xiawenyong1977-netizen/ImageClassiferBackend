"""
统一LLM服务入口
提供统一的接口，自动选择对应的提供商适配器
"""

from typing import Dict, Any, Optional
from loguru import logger
from app.config import settings
from app.services.llm.providers import AliyunProvider, OpenAIProvider, ClaudeProvider
from app.services.llm.base_service import LLMError, LLMErrorType
from app.services.unified_llm_cache import unified_llm_cache
from app.utils.hash_utils import HashUtils


class LLMService:
    """统一LLM服务类"""
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[int] = None
    ):
        """
        初始化LLM服务
        
        Args:
            provider: 提供商名称（aliyun/openai/claude），None则使用配置值
            api_key: API密钥，None则使用配置值
            model: 模型名称，None则使用配置值
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒），None则使用配置值
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        # 创建对应的提供商适配器
        self._adapter = self._create_adapter()
    
    def _create_adapter(self):
        """创建对应的提供商适配器"""
        provider_lower = self.provider.lower()
        
        if provider_lower in ["aliyun", "qwen"]:
            return AliyunProvider(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                timeout=self.timeout
            )
        elif provider_lower == "openai":
            return OpenAIProvider(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                timeout=self.timeout
            )
        elif provider_lower == "claude":
            return ClaudeProvider(
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                timeout=self.timeout
            )
        else:
            raise ValueError(f"不支持的大模型提供商: {self.provider}")
    
    async def classify_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图片分类（带缓存和错误处理）
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 提示词，None则使用配置的分类提示词
            use_cache: 是否使用缓存（默认True）
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 响应内容（文本，成功时）
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
            - from_cache: 是否来自缓存
        """
        if prompt is None:
            prompt = settings.CLASSIFICATION_PROMPT
        
        # 计算image_hash
        image_hash = HashUtils.calculate_sha256(image_bytes)
        
        # 1. 如果启用缓存，先查缓存
        if use_cache:
            cached = await unified_llm_cache.get_cached_result(
                prompt=prompt,
                image_hash=image_hash,
                model_key=f"{self.provider}:{self.model}"
            )
            if cached:
                logger.info(f"缓存命中: image_hash={image_hash[:16]}...")
                # 检查是否是错误结果
                if cached.get('status') == 'error':
                    # 返回缓存的错误信息（error字典中已包含user_message）
                    error_info = cached.get('error', {})
                    # 确保user_message存在
                    if 'user_message' not in error_info:
                        error_info['user_message'] = '输入参数有误'
                    return {
                        "success": False,
                        "error": error_info,
                        "from_cache": True
                    }
                # 返回成功结果
                return {
                    "success": True,
                    "content": cached.get('result', {}).get('content') if isinstance(cached.get('result'), dict) else None,
                    "from_cache": True
                }
        
        # 2. 缓存未命中，调用API
        try:
            result = await self._adapter.call_with_retry(
                task_type="classification",
                image_bytes=image_bytes,
                prompt=prompt,
                **kwargs
            )
            
            # 3. 如果成功，保存到缓存
            if use_cache and result.get('success'):
                await unified_llm_cache.save_result(
                    prompt=prompt,
                    image_hash=image_hash,
                    provider=self.provider,
                    model_id=self.model,
                    result=result.get('content'),
                    service_type="classification"
                )
            
            return result
            
        except LLMError as e:
            # 4. 处理不同类型的错误
            if e.error_type == LLMErrorType.INPUT_ERROR:
                # 输入错误：缓存错误结果
                if use_cache:
                    await unified_llm_cache.save_error_result(
                        prompt=prompt,
                        image_hash=image_hash,
                        provider=self.provider,
                        model_id=self.model,
                        error=e,
                        service_type="classification"
                    )
                
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
            
            elif e.error_type == LLMErrorType.AUTH_ERROR:
                # 权限错误：记录详细日志，返回友好消息
                logger.error(
                    f"LLM权限错误 [{self.provider}:{self.model}]: "
                    f"status_code={e.status_code}, error_code={e.error_code}, "
                    f"message={e.message}"
                )
                
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
            
            else:
                # 其他错误（网络错误重试后仍失败、业务逻辑错误等）
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
    
    async def edit_image(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        model: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图像编辑（带缓存和错误处理）
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 编辑提示词
            edit_type: 编辑类型（可选）
            model: 模型名称（可选，用于覆盖默认模型）
            use_cache: 是否使用缓存（默认True）
            **kwargs: 其他参数（如negative_prompt, watermark等）
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - result_url: 结果图片URL（成功时）
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
            - from_cache: 是否来自缓存
        """
        # 计算image_hash
        image_hash = HashUtils.calculate_sha256(image_bytes)
        
        # 对于编辑服务，prompt需要包含edit_type
        full_prompt = f"{edit_type}:{prompt}" if edit_type else prompt
        
        # 确定使用的模型
        actual_model = model or self.model
        
        # 1. 如果启用缓存，先查缓存
        if use_cache:
            cached = await unified_llm_cache.get_cached_result(
                prompt=full_prompt,
                image_hash=image_hash,
                model_key=f"{self.provider}:{actual_model}"
            )
            if cached:
                logger.info(f"缓存命中: image_hash={image_hash[:16]}...")
                # 检查是否是错误结果
                if cached.get('status') == 'error':
                    # 返回缓存的错误信息（error字典中已包含user_message）
                    error_info = cached.get('error', {})
                    # 确保user_message存在
                    if 'user_message' not in error_info:
                        error_info['user_message'] = '输入参数有误'
                    return {
                        "success": False,
                        "error": error_info,
                        "from_cache": True
                    }
                # 返回成功结果
                return {
                    "success": True,
                    "result_url": cached.get('result') if isinstance(cached.get('result'), str) else None,
                    "from_cache": True
                }
        
        # 2. 如果指定了模型，创建临时适配器
        adapter = self._adapter
        if model and model != self.model:
            # 创建新的适配器实例（使用指定的模型）
            provider_lower = self.provider.lower()
            if provider_lower in ["aliyun", "qwen"]:
                adapter = AliyunProvider(
                    provider=self.provider,
                    api_key=self.api_key,
                    model=model,
                    max_retries=self.max_retries,
                    retry_delay=self.retry_delay,
                    timeout=self.timeout
                )
            else:
                logger.warning(f"提供商 {self.provider} 不支持动态指定模型，使用默认模型")
        
        # 3. 缓存未命中，调用API
        try:
            result = await adapter.call_with_retry(
                task_type="image_edit",
                image_bytes=image_bytes,
                prompt=prompt,
                edit_type=edit_type,
                **kwargs
            )
            
            # 4. 如果成功，保存到缓存
            if use_cache and result.get('success'):
                result_url = result.get('result_url')
                if result_url:
                    await unified_llm_cache.save_result(
                        prompt=full_prompt,
                        image_hash=image_hash,
                        provider=self.provider,
                        model_id=actual_model,
                        result=result_url,
                        service_type="image_edit",
                        edit_type=edit_type
                    )
            
            return result
            
        except LLMError as e:
            # 5. 处理不同类型的错误
            if e.error_type == LLMErrorType.INPUT_ERROR:
                # 输入错误：缓存错误结果
                if use_cache:
                    await unified_llm_cache.save_error_result(
                        prompt=full_prompt,
                        image_hash=image_hash,
                        provider=self.provider,
                        model_id=actual_model,
                        error=e,
                        service_type="image_edit",
                        edit_type=edit_type
                    )
                
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
            
            elif e.error_type == LLMErrorType.AUTH_ERROR:
                # 权限错误：记录详细日志，返回友好消息
                logger.error(
                    f"LLM权限错误 [{self.provider}:{actual_model}]: "
                    f"status_code={e.status_code}, error_code={e.error_code}, "
                    f"message={e.message}"
                )
                
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
            
            else:
                # 其他错误（网络错误重试后仍失败、业务逻辑错误等）
                return {
                    "success": False,
                    "error": {
                        "type": e.error_type.value,
                        "message": e.message,
                        "user_message": e.user_message,
                        "status_code": e.status_code,
                        "error_code": e.error_code
                    }
                }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        获取当前提供商信息
        
        Returns:
            提供商信息字典
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout
        }


# 全局LLM服务实例（使用配置的默认值）
llm_service = LLMService()

