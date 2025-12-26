"""
统一LLM服务入口
提供统一的接口，自动选择对应的提供商适配器
"""

from typing import Dict, Any, Optional
from loguru import logger
from app.config import settings
from app.services.llm.providers import AliyunProvider, OpenAIProvider, ClaudeProvider


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
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图片分类
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 提示词，None则使用配置的分类提示词
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 响应内容（文本）
            - raw_response: 原始响应对象
        """
        if prompt is None:
            prompt = settings.CLASSIFICATION_PROMPT
        
        return await self._adapter.call_with_retry(
            task_type="classification",
            image_bytes=image_bytes,
            prompt=prompt,
            **kwargs
        )
    
    async def edit_image(
        self,
        image_bytes: bytes,
        prompt: str,
        edit_type: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图像编辑
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 编辑提示词
            edit_type: 编辑类型（可选）
            model: 模型名称（可选，用于覆盖默认模型）
            **kwargs: 其他参数（如negative_prompt, watermark等）
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - result_url: 结果图片URL
            - raw_response: 原始响应对象
        """
        # 如果指定了模型，创建临时适配器
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
        
        return await adapter.call_with_retry(
            task_type="image_edit",
            image_bytes=image_bytes,
            prompt=prompt,
            edit_type=edit_type,
            **kwargs
        )
    
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

