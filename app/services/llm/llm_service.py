"""
统一LLM服务入口
提供统一的接口，自动选择对应的提供商适配器
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
from app.config import settings
from app.services.llm.providers import AliyunProvider, OpenAIProvider, ClaudeProvider, DeepseekProvider
from app.services.llm.base_service import LLMError, LLMErrorType
from app.services.unified_llm_cache import unified_llm_cache
from app.utils.hash_utils import HashUtils


class LLMService:
    """统一LLM服务类"""
    
    @staticmethod
    def _parse_classification_response(content: str, try_parse_json: bool = True) -> dict:
        """
        解析分类任务的LLM返回内容
        
        Args:
            content: LLM返回的文本内容（可能是JSON格式或纯文本），必须是字符串
            try_parse_json: 是否尝试解析JSON格式（默认True，如果使用自定义prompt应设为False）
            
        Returns:
            解析后的分类结果字典：
            {
                "category": str,
                "confidence": float (可选),
                "description": str (可选),
                "background_color": str (可选),
                "raw_content": str (原始响应内容)
            }
        """
        # 确保content是字符串
        if not isinstance(content, str):
            logger.warning(f"_parse_classification_response收到非字符串类型: {type(content)}")
            return {
                "category": "other",
                "confidence": None,
                "description": None,
                "background_color": None,
                "raw_content": str(content) if content else None
            }
        
        if not content:
            return {
                "category": "other",
                "confidence": None,
                "description": None,
                "background_color": None,
                "raw_content": None
            }
        
        # 如果不尝试解析JSON，直接返回原始内容（自定义prompt的情况）
        if not try_parse_json:
            return {
                "category": None,  # 自定义prompt时，category设为None，客户端应使用raw_content
                "confidence": None,
                "description": None,
                "background_color": None,
                "raw_content": content  # 保存完整的原始响应内容，供客户端自行解析
            }
        
        # 尝试解析JSON格式
        try:
            # 移除可能的markdown代码块标记
            content_clean = content.strip()
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            if content_clean.startswith("```"):
                content_clean = content_clean[3:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()
            
            parsed = json.loads(content_clean)
            
            # 提取字段
            result = {
                "category": parsed.get("category", "other"),
                "confidence": float(parsed.get("confidence", 0.5)) if parsed.get("confidence") is not None else None,
                "description": parsed.get("description"),
                "background_color": parsed.get("background_color"),
                "raw_content": content  # 保存原始响应内容
            }
            
            return result
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # JSON解析失败，将整个content作为category
            logger.warning(f"LLM返回内容不是JSON格式，使用原始内容作为category: {e}")
            return {
                "category": content.strip()[:100],  # 限制长度
                "confidence": None,  # 无法解析时confidence为None
                "description": None,
                "background_color": None,
                "raw_content": content  # 保存原始响应内容，让客户端自己解析
            }
    
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
        elif provider_lower == "deepseek":
            return DeepseekProvider(
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
            - parsed_result: 解析后的分类结果（成功时，仅当使用默认prompt时才有）
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
        
        # 判断是否使用默认prompt（默认prompt要求返回JSON格式）
        is_default_prompt = prompt == settings.CLASSIFICATION_PROMPT
        
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
                # 返回成功结果（缓存中存储的是原始内容字符串）
                # 处理result字段：可能是字符串（新格式）或dict（旧格式兼容）
                cached_result_data = cached.get('result', {})
                if isinstance(cached_result_data, dict):
                    # 旧格式兼容：dict中包含content字段
                    content = cached_result_data.get('content')
                else:
                    # 新格式：result就是原始内容字符串
                    content = cached_result_data
                
                result = {
                    "success": True,
                    "content": content,
                    "from_cache": True
                }
                # 如果使用默认prompt，自动解析JSON
                if is_default_prompt and content:
                    result["parsed_result"] = self._parse_classification_response(content, try_parse_json=True)
                return result
        
        # 2. 缓存未命中，调用API
        try:
            result = await self._adapter.call_with_retry(
                task_type="classification",
                image_bytes=image_bytes,
                prompt=prompt,
                **kwargs
            )
            
            # 3. 如果成功，保存到缓存（只保存原始内容，不解析）
            if use_cache and result.get('success'):
                content = result.get('content')
                
                # 保存原始内容到缓存（不解析，解析在check_cache时进行）
                await unified_llm_cache.save_result(
                    prompt=prompt,
                    image_hash=image_hash,
                    provider=self.provider,
                    model_id=self.model,
                    result=content,  # 只保存原始内容（字符串）
                    service_type="classification",
                    is_default_prompt=is_default_prompt  # 保存是否使用默认prompt的标记
                )
                
                # 如果使用默认prompt，解析响应并添加到返回结果中
                if is_default_prompt and content:
                    result["parsed_result"] = self._parse_classification_response(content, try_parse_json=True)
            
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
    
    async def classify_color(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图片颜色分类（只识别背景颜色）
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 提示词，None则使用配置的颜色分类提示词
            use_cache: 是否使用缓存（默认True）
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 响应内容（JSON文本，成功时），包含background_color和confidence
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
            - from_cache: 是否来自缓存
        """
        if prompt is None:
            prompt = settings.COLOR_CLASSIFICATION_PROMPT
        
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
                logger.info(f"颜色分类缓存命中: image_hash={image_hash[:16]}...")
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
                # 返回成功结果（统一格式：result是字符串）
                raw_content = cached.get('result')
                if isinstance(raw_content, dict):
                    # 兼容旧格式：dict中包含content字段
                    raw_content = raw_content.get('content')
                
                return {
                    "success": True,
                    "content": raw_content,
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
                # 判断是否使用默认prompt
                is_default_prompt = prompt == settings.COLOR_CLASSIFICATION_PROMPT
                
                await unified_llm_cache.save_result(
                    prompt=prompt,
                    image_hash=image_hash,
                    provider=self.provider,
                    model_id=self.model,
                    result=result.get('content'),
                    service_type="color_classification",
                    is_default_prompt=is_default_prompt
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
                        service_type="color_classification"
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
    
    async def analyze_composition(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行照片构图分析（识别构图方式并给出专业点评）
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 提示词，None则使用配置的构图分析提示词
            use_cache: 是否使用缓存（默认True）
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 响应内容（JSON文本，成功时），包含构图分析结果
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
            - from_cache: 是否来自缓存
        """
        if prompt is None:
            prompt = settings.COMPOSITION_ANALYSIS_PROMPT
        
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
                logger.info(f"构图分析缓存命中: image_hash={image_hash[:16]}...")
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
                # 返回成功结果（统一格式：result是字符串）
                raw_content = cached.get('result')
                if isinstance(raw_content, dict):
                    # 兼容旧格式：dict中包含content字段
                    raw_content = raw_content.get('content')
                
                return {
                    "success": True,
                    "content": raw_content,
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
                # 判断是否使用默认prompt
                is_default_prompt = prompt == settings.COMPOSITION_ANALYSIS_PROMPT
                
                await unified_llm_cache.save_result(
                    prompt=prompt,
                    image_hash=image_hash,
                    provider=self.provider,
                    model_id=self.model,
                    result=result.get('content'),
                    service_type="composition_analysis",
                    is_default_prompt=is_default_prompt
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
                        service_type="composition_analysis"
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
    
    async def predict_face_fortune(
        self,
        image_bytes: bytes,
        event: str,
        time: Optional[str] = None,
        prompt: Optional[str] = None,
        use_cache: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行面相预测（基于面相特征预测事件的吉凶）
        
        注意：此接口默认不使用缓存，因为prompt包含动态的time和event，每次调用prompt都不同，缓存命中率极低
        
        Args:
            image_bytes: 图片二进制数据（需包含清晰的人脸）
            event: 用户描述的事件（如："我要去参加一个重要的面试"）
            time: 当前时间字符串（如："2024年1月15日 14:30"），None则自动生成
            prompt: 提示词，None则使用配置的面相预测提示词
            use_cache: 是否使用缓存（默认False，因为prompt包含动态内容，缓存意义不大）
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 响应内容（JSON文本，成功时），包含面相分析结果
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
            - from_cache: 是否来自缓存
        """
        # 如果没有提供时间，自动生成
        if time is None:
            time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        
        # 构建完整的提示词（替换占位符）
        if prompt is None:
            prompt_template = settings.FACE_FORTUNE_PROMPT
            # 使用 replace 而不是 format，避免 JSON 中的花括号转义问题
            prompt = prompt_template.replace("{time}", time).replace("{event}", event)
        else:
            # 如果提供了自定义提示词，也需要替换占位符
            prompt = prompt.replace("{time}", time).replace("{event}", event)
        
        # 计算image_hash
        image_hash = HashUtils.calculate_sha256(image_bytes)
        
        # 1. 如果启用缓存，先查缓存
        # 注意：由于面相预测涉及事件和时间，prompt已经包含了这些信息，所以缓存key会自动区分
        if use_cache:
            # 注意：由于面相预测涉及事件和时间，缓存key需要包含这些信息
            # 这里使用prompt作为缓存key的一部分，因为prompt已经包含了event和time
            cached = await unified_llm_cache.get_cached_result(
                prompt=prompt,
                image_hash=image_hash,
                model_key=f"{self.provider}:{self.model}"
            )
            if cached:
                logger.info(f"面相预测缓存命中: image_hash={image_hash[:16]}...")
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
                # 返回成功结果（统一格式：result是字符串）
                raw_content = cached.get('result')
                if isinstance(raw_content, dict):
                    # 兼容旧格式：dict中包含content字段
                    raw_content = raw_content.get('content')
                
                return {
                    "success": True,
                    "content": raw_content,
                    "from_cache": True
                }
        
        # 2. 缓存未命中或未启用缓存，调用API
        # 注意：由于prompt包含动态的time和event，缓存命中率极低，默认不使用缓存
        try:
            result = await self._adapter.call_with_retry(
                task_type="classification",
                image_bytes=image_bytes,
                prompt=prompt,
                **kwargs
            )
            
            # 3. 如果启用缓存且成功，保存到缓存（但通常不会命中，因为prompt包含动态内容）
            if use_cache and result.get('success'):
                # 判断是否使用默认prompt（检查prompt是否基于默认模板）
                is_default_prompt = (
                    prompt is not None and 
                    (prompt.startswith(settings.FACE_FORTUNE_PROMPT.split("{")[0]) or
                     "【当前时间】" in prompt or "【事件】" in prompt)
                ) if prompt else False
                
                await unified_llm_cache.save_result(
                    prompt=prompt,
                    image_hash=image_hash,
                    provider=self.provider,
                    model_id=self.model,
                    result=result.get('content'),
                    service_type="face_fortune",
                    is_default_prompt=is_default_prompt
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
                        service_type="face_fortune"
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
                # 返回成功结果（统一格式：result是字符串）
                raw_content = cached.get('result')
                if isinstance(raw_content, dict):
                    # 兼容旧格式：dict中包含content字段
                    raw_content = raw_content.get('content')
                
                return {
                    "success": True,
                    "result_url": raw_content if isinstance(raw_content, str) else None,
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
                        edit_type=edit_type,
                        is_default_prompt=None  # 图像编辑不使用默认prompt
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
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行文本生成（使用Deepseek）
        
        注意：文本生成不使用缓存，每次调用都会直接请求API
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            max_tokens: 最大token数，None则使用配置值
            temperature: 温度参数（0-2），默认0.7
            **kwargs: 其他参数（如api_key、model等）
            
        Returns:
            API响应结果字典，包含：
            - success: 是否成功
            - content: 生成的文本内容（成功时）
            - error: 错误信息字典（失败时），包含：
              - type: 错误类型
              - message: 技术错误消息
              - user_message: 用户友好消息
              - status_code: HTTP状态码
              - error_code: 错误代码
        """
        # 文本生成默认使用Deepseek
        # 如果当前provider不是deepseek，创建临时的Deepseek适配器
        if self.provider.lower() != "deepseek":
            # 优先使用用户提供的API Key，其次使用DEEPSEEK_API_KEY配置，最后回退到LLM_API_KEY
            deepseek_api_key = kwargs.get('api_key') or settings.DEEPSEEK_API_KEY or self.api_key
            if not deepseek_api_key:
                # 如果没有提供API Key，记录错误日志并返回
                logger.error("文本生成失败：未提供Deepseek API Key")
                return {
                    "success": False,
                    "error": {
                        "type": LLMErrorType.AUTH_ERROR.value,
                        "message": "未提供Deepseek API Key",
                        "user_message": "服务暂时不可用，请稍后重试",
                        "status_code": None,
                        "error_code": None
                    }
                }
            
            adapter = DeepseekProvider(
                provider="deepseek",
                api_key=deepseek_api_key,
                model=kwargs.get('model', 'deepseek-chat'),
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                timeout=self.timeout
            )
        else:
            adapter = self._adapter
        
        # 调用文本生成（带重试机制）
        try:
            # 手动实现重试逻辑（因为文本生成不需要image_bytes）
            last_error = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        f"[{adapter.provider}] 调用文本生成 "
                        f"(尝试 {attempt}/{self.max_retries}, model={adapter.model})"
                    )
                    
                    result = await adapter._call_text_generation(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
                        temperature=temperature,
                        **kwargs
                    )
                    
                    logger.info(
                        f"[{adapter.provider}] 文本生成成功 "
                        f"(model={adapter.model})"
                    )
                    
                    return result
                    
                except LLMError as e:
                    last_error = e
                    # 判断是否应该重试
                    should_retry = e.should_retry and attempt < self.max_retries
                    
                    if should_retry:
                        logger.warning(
                            f"[{adapter.provider}] 文本生成失败 "
                            f"(尝试 {attempt}/{self.max_retries}, "
                            f"错误类型: {e.error_type.value}): {e.message}，"
                            f"{self.retry_delay * attempt}秒后重试..."
                        )
                        await asyncio.sleep(self.retry_delay * attempt)
                    else:
                        # 不可重试的错误，直接处理
                        logger.error(
                            f"[{adapter.provider}] 文本生成失败 "
                            f"(尝试 {attempt}/{self.max_retries}, "
                            f"错误类型: {e.error_type.value}): {e.message}"
                        )
                        break
                except Exception as e:
                    # 非LLMError异常，转换为LLMError
                    from app.services.llm.base_service import LLMError, LLMErrorType
                    last_error = LLMError(
                        message=str(e),
                        error_type=LLMErrorType.NETWORK_ERROR,
                        should_retry=True
                    )
                    if attempt < self.max_retries:
                        logger.warning(
                            f"[{adapter.provider}] 文本生成失败 "
                            f"(尝试 {attempt}/{self.max_retries}): {str(e)}，"
                            f"{self.retry_delay * attempt}秒后重试..."
                        )
                        await asyncio.sleep(self.retry_delay * attempt)
                    else:
                        break
            
            # 所有重试都失败
            if isinstance(last_error, LLMError):
                return {
                    "success": False,
                    "error": {
                        "type": last_error.error_type.value,
                        "message": last_error.message,
                        "user_message": last_error.user_message,
                        "status_code": last_error.status_code,
                        "error_code": last_error.error_code
                    }
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "type": "network_error",
                        "message": str(last_error) if last_error else "未知错误",
                        "user_message": "文本生成失败，请稍后重试",
                        "status_code": None,
                        "error_code": None
                    }
                }
                
        except Exception as e:
            logger.error(f"文本生成异常: {e}")
            return {
                "success": False,
                "error": {
                    "type": "business_error",
                    "message": str(e),
                    "user_message": "文本生成失败，请稍后重试",
                    "status_code": None,
                    "error_code": None
                }
            }
    
    async def check_cache(
        self,
        prompt: str,
        image_hash: str
    ) -> Optional[dict]:
        """
        查询单张图片的缓存结果（仅查询，不调用LLM）
        根据service_type进行相应的解析
        
        Args:
            prompt: 提示词
            image_hash: 图片哈希
            
        Returns:
            解析后的缓存结果字典，如果未命中返回None
            格式：
            {
                "cached": True,
                "content": "原始内容",
                "parsed_result": {...},  # 根据service_type解析的结果（可选）
                "service_type": "classification" | "image_edit" | ...
            }
        """
        model_key = f"{self.provider}:{self.model}"
        cached = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key=model_key
        )
        
        if not cached:
            return None
        
        # 检查是否是错误结果
        if cached.get('status') == 'error':
            return {
                "cached": True,
                "success": False,
                "error": cached.get('error', {}),
                "service_type": cached.get('service_type')
            }
        
        # 获取service_type和原始内容
        service_type = cached.get('service_type', 'classification')
        # 处理result字段：可能是字符串（新格式）或dict（旧格式兼容）
        cached_result_data = cached.get('result', {})
        if isinstance(cached_result_data, dict):
            # 旧格式兼容：dict中包含content字段
            raw_content = cached_result_data.get('content')
        else:
            # 新格式：result就是原始内容字符串
            raw_content = cached_result_data
        
        result = {
            "cached": True,
            "content": raw_content,
            "service_type": service_type
        }
        
        # 根据service_type进行不同的解析
        # 优先使用缓存中保存的is_default_prompt标记，如果没有则回退到字符串比较
        cached_is_default_prompt = cached.get('is_default_prompt')
        
        if service_type == "classification":
            # 分类服务：使用缓存中的标记，如果没有则回退到字符串比较
            is_default_prompt = cached_is_default_prompt if cached_is_default_prompt is not None else (prompt == settings.CLASSIFICATION_PROMPT)
            if is_default_prompt and raw_content:
                # 默认prompt：解析JSON
                result["parsed_result"] = self._parse_classification_response(raw_content, try_parse_json=True)
            # 自定义prompt：不解析，返回原始内容（parsed_result为None）
        elif service_type == "image_edit":
            # 图像编辑服务：result就是URL字符串，不需要解析
            result["result_url"] = raw_content
        elif service_type == "color_classification":
            # 颜色分类服务：使用缓存中的标记，如果没有则回退到字符串比较
            is_default_prompt = cached_is_default_prompt if cached_is_default_prompt is not None else (prompt == settings.COLOR_CLASSIFICATION_PROMPT)
            if is_default_prompt and raw_content:
                # 默认prompt：解析JSON（颜色分类返回的是JSON格式）
                result["parsed_result"] = self._parse_classification_response(raw_content, try_parse_json=True)
            # 自定义prompt：不解析，返回原始内容
        elif service_type == "composition_analysis":
            # 构图分析服务：使用缓存中的标记，如果没有则回退到字符串比较
            is_default_prompt = cached_is_default_prompt if cached_is_default_prompt is not None else (prompt == settings.COMPOSITION_ANALYSIS_PROMPT)
            if is_default_prompt and raw_content:
                # 默认prompt：解析JSON（构图分析返回的是JSON格式）
                result["parsed_result"] = self._parse_classification_response(raw_content, try_parse_json=True)
            # 自定义prompt：不解析，返回原始内容
        elif service_type == "face_fortune":
            # 面相预测服务：使用缓存中的标记，如果没有则回退到模式匹配
            if cached_is_default_prompt is not None:
                is_default_prompt = cached_is_default_prompt
            else:
                # 回退到模式匹配判断
                default_prompt_template = settings.FACE_FORTUNE_PROMPT
                default_prompt_pattern = re.sub(r'\{time\}', r'.*?', re.escape(default_prompt_template))
                default_prompt_pattern = re.sub(r'\{event\}', r'.*?', default_prompt_pattern)
                is_default_prompt = (
                    "【当前时间】" in prompt or 
                    "【事件】" in prompt or
                    re.match(default_prompt_pattern, prompt) is not None
                )
            if is_default_prompt and raw_content:
                # 默认prompt：解析JSON（面相预测返回的是JSON格式）
                result["parsed_result"] = self._parse_classification_response(raw_content, try_parse_json=True)
            # 自定义prompt：不解析，返回原始内容
        
        return result
    
    def get_model_key(self) -> str:
        """
        获取当前模型的key（用于缓存查询）
        
        Returns:
            模型key（格式: "provider:model"）
        """
        return f"{self.provider}:{self.model}"
    
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

