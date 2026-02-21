"""
统一LLM服务入口
提供统一的接口，自动选择对应的提供商适配器
"""

import asyncio
import json
import re
import math
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
from app.config import settings
from app.services.llm.providers import AliyunProvider, OpenAIProvider, ClaudeProvider, DeepseekProvider
from app.services.llm.base_service import LLMError, LLMErrorType
from app.services.llm.model_config import (
    TaskType, Provider, get_default_model, is_model_supported, validate_model_for_task,
    get_model_default_params
)
from app.services.unified_llm_cache import unified_llm_cache
from app.utils.hash_utils import HashUtils

# 尝试导入scikit-learn（用于聚类）
try:
    import numpy as np
    from sklearn.cluster import DBSCAN
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    np = None
    DBSCAN = None

# 导入Coordinate类型和haversine_distance函数（用于类型提示和距离计算）
try:
    from app.api.location_v2 import Coordinate, haversine_distance
except ImportError:
    # 如果导入失败，定义一个简单的Coordinate类用于类型提示
    from pydantic import BaseModel
    class Coordinate(BaseModel):
        id: Optional[str] = None
        latitude: float
        longitude: float
    # 如果导入失败，定义一个简单的haversine_distance函数
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两个经纬度点之间的距离（公里）"""
        R = 6371.0  # 地球半径（公里）
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


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
        
        # 验证 provider 是否有效
        try:
            Provider(self.provider.lower())
        except ValueError:
            raise ValueError(f"不支持的大模型提供商: {self.provider}")
        
        # 🔥 使用分类任务的默认模型
        # 优先级：1. 传入的model参数 2. LLM_MODEL_CLASSIFICATION配置 3. 提供商默认模型
        if model:
            self.model = model
        elif settings.LLM_MODEL_CLASSIFICATION:
            self.model = settings.LLM_MODEL_CLASSIFICATION
        else:
            # 使用提供商默认的分类模型
            default_model = get_default_model(self.provider, TaskType.CLASSIFICATION)
            if not default_model:
                raise ValueError(f"提供商 {self.provider} 不支持图像分类任务")
            self.model = default_model
        # 🔥 根据任务类型和模型获取默认参数
        # 优先级：1. 传入的参数 2. 任务类型对应的配置 3. 模型默认值
        default_params = get_model_default_params(self.provider, TaskType.CLASSIFICATION, self.model)
        
        # 分类任务的参数配置
        self.max_retries = max_retries or (
            settings.LLM_MAX_RETRIES_CLASSIFICATION or 
            default_params["max_retries"]
        )
        self.retry_delay = retry_delay or (
            settings.LLM_RETRY_DELAY_CLASSIFICATION or 
            default_params["retry_delay"]
        )
        self.timeout = timeout or (
            settings.LLM_TIMEOUT_CLASSIFICATION or 
            default_params["timeout"]
        )
        # max_tokens 在调用时根据任务类型动态获取
        
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
        image_hash: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用大模型进行图片分类（带缓存和错误处理）
        
        Args:
            image_bytes: 图片二进制数据（可能是压缩后的）
            prompt: 提示词，None则使用配置的分类提示词
            use_cache: 是否使用缓存（默认True）
            image_hash: 客户端提供的图片hash（基于原图计算），如果提供则使用，否则基于image_bytes计算
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
        
        # 使用客户端提供的hash（基于原图），如果没有提供则基于压缩后的图片计算
        # 注意：由于服务器收到的图片是压缩后的，应该使用客户端提供的原图hash来查询缓存
        if image_hash is None:
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
        
        # 2. 获取分类任务的 max_tokens 参数
        classification_default_params = get_model_default_params(self.provider, TaskType.CLASSIFICATION, self.model)
        max_tokens = (
            settings.LLM_MAX_TOKENS_CLASSIFICATION or 
            classification_default_params["max_tokens"]
        )
        
        # 3. 缓存未命中，调用API
        try:
            result = await self._adapter.call_with_retry(
                task_type="classification",
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=max_tokens,
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
        logger.info(f"[edit_image] 方法开始执行: image_bytes_size={len(image_bytes)}, prompt={prompt[:50] if prompt else None}...")
        
        # 计算image_hash
        logger.info(f"[edit_image] 开始计算image_hash...")
        image_hash = HashUtils.calculate_sha256(image_bytes)
        logger.info(f"[edit_image] image_hash计算完成: {image_hash[:16]}...")
        
        # 对于编辑服务，prompt需要包含edit_type
        full_prompt = f"{edit_type}:{prompt}" if edit_type else prompt
        logger.info(f"[edit_image] full_prompt准备完成: {full_prompt[:50]}...")
        
        # 确定使用的模型
        # 🔥 根据任务类型自动选择模型
        # 1. 如果明确指定了模型，使用指定的模型
        if model:
            actual_model = model
            # 验证模型是否支持图像编辑任务
            try:
                validate_model_for_task(self.provider, TaskType.IMAGE_EDIT, actual_model)
            except ValueError as e:
                logger.warning(f"[edit_image] 模型验证警告: {e}")
                # 如果模型验证失败，且提供商不支持动态指定模型，使用默认模型
                provider_lower = self.provider.lower()
                if provider_lower not in ["aliyun", "qwen"]:
                    logger.warning(f"提供商 {self.provider} 不支持动态指定模型，使用默认模型")
                    actual_model = get_default_model(self.provider, TaskType.IMAGE_EDIT)
                    if not actual_model:
                        raise ValueError(
                            f"提供商 {self.provider} 不支持图像编辑任务。"
                            f"支持的提供商: aliyun"
                        )
        else:
            # 2. 使用配置的模型（如果配置了LLM_MODEL_IMAGE_EDIT）
            if settings.LLM_MODEL_IMAGE_EDIT:
                actual_model = settings.LLM_MODEL_IMAGE_EDIT
                logger.info(f"[edit_image] 使用配置的图像编辑模型: {actual_model}")
            else:
                # 3. 使用提供商默认的图像编辑模型
                actual_model = get_default_model(self.provider, TaskType.IMAGE_EDIT)
                if not actual_model:
                    raise ValueError(
                        f"提供商 {self.provider} 不支持图像编辑任务。"
                        f"支持的提供商: aliyun"
                    )
                logger.info(f"[edit_image] 使用提供商默认图像编辑模型: {actual_model}")
        
        logger.info(f"[edit_image] 最终使用模型: {actual_model} (提供商: {self.provider})")
        
        # 1. 如果启用缓存，先查缓存
        if use_cache:
            logger.info(f"[edit_image] 开始查询缓存: prompt_hash={full_prompt[:20]}..., image_hash={image_hash[:16]}...")
            cached = await unified_llm_cache.get_cached_result(
                prompt=full_prompt,
                image_hash=image_hash,
                model_key=f"{self.provider}:{actual_model}"
            )
            logger.info(f"[edit_image] 缓存查询完成: cached={'命中' if cached else '未命中'}")
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
        
        # 2. 获取图像编辑任务的参数配置
        edit_default_params = get_model_default_params(self.provider, TaskType.IMAGE_EDIT, actual_model)
        edit_max_retries = (
            settings.LLM_MAX_RETRIES_IMAGE_EDIT or 
            edit_default_params["max_retries"]
        )
        edit_retry_delay = (
            settings.LLM_RETRY_DELAY_IMAGE_EDIT or 
            edit_default_params["retry_delay"]
        )
        edit_timeout = (
            settings.LLM_TIMEOUT_IMAGE_EDIT or 
            edit_default_params["timeout"]
        )
        
        # 3. 确保使用正确的模型创建适配器（图像编辑必须使用 qwen-image-edit）
        adapter = self._adapter
        # 🔥 如果实际模型与默认模型不同，或者参数不同，需要创建新的适配器
        provider_lower = self.provider.lower()
        if provider_lower in ["aliyun", "qwen"]:
            if actual_model != self.model or edit_timeout != self.timeout or edit_max_retries != self.max_retries:
                logger.info(f"[edit_image] 创建新的适配器，使用模型: {actual_model}, timeout={edit_timeout}s, max_retries={edit_max_retries}")
                adapter = AliyunProvider(
                    provider=self.provider,
                    api_key=self.api_key,
                    model=actual_model,  # 使用计算出的实际模型
                    max_retries=edit_max_retries,
                    retry_delay=edit_retry_delay,
                    timeout=edit_timeout
                )
        # 对于非阿里云提供商，如果模型验证失败，已经在上面处理了，这里不需要再次警告
        
        # 4. 获取图像编辑任务的 max_tokens 参数
        edit_max_tokens = (
            settings.LLM_MAX_TOKENS_IMAGE_EDIT or 
            edit_default_params["max_tokens"]
        )
        
        # 5. 缓存未命中，调用API
        logger.info(f"[edit_image] 缓存未命中，开始调用LLM API: provider={self.provider}, model={actual_model}, timeout={edit_timeout}s")
        try:
            result = await adapter.call_with_retry(
                task_type="image_edit",
                image_bytes=image_bytes,
                prompt=prompt,
                edit_type=edit_type,
                max_tokens=edit_max_tokens,
                **kwargs
            )
            logger.info(f"[edit_image] LLM API调用完成: success={result.get('success') if isinstance(result, dict) else 'unknown'}")
            
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
                    
                    # 文本生成任务的默认 max_tokens（2000）
                    text_gen_max_tokens = max_tokens or 2000
                    result = await adapter._call_text_generation(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        max_tokens=text_gen_max_tokens,
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
        # 临时调试：这3张图片的 image_hash
        DEBUG_IMAGE_HASHES = {
            '5a3e8f23af6c9e214e6dcf56aca55da74a8332679446fc1cee77046b1bd9f81f',
            'dafbb388bacb41cd9c24ce6381f79d8d6cc195a83c42367b3317691150d42536',
            '5d12eec8e838ab831f45e897cfea5d743c0446c8ada39fe6df9d5f0c2bd54406'
        }
        is_debug = image_hash in DEBUG_IMAGE_HASHES
        
        model_key = f"{self.provider}:{self.model}"
        if is_debug:
            logger.info(f"[DEBUG] check_cache开始: image_hash={image_hash[:16]}..., model_key={model_key}, prompt长度={len(prompt)}")
        
        cached = await unified_llm_cache.get_cached_result(
            prompt=prompt,
            image_hash=image_hash,
            model_key=model_key
        )
        
        if not cached:
            if is_debug:
                logger.warning(f"[DEBUG] 缓存未命中: image_hash={image_hash[:16]}..., model_key={model_key}")
            return None
        
        if is_debug:
            logger.info(f"[DEBUG] 缓存命中: image_hash={image_hash[:16]}..., cached类型={type(cached).__name__}, cached.keys()={list(cached.keys()) if isinstance(cached, dict) else 'N/A'}")
        
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
        
        if is_debug:
            logger.info(f"[DEBUG] cached_result_data: 类型={type(cached_result_data).__name__}, 值={cached_result_data}")
            if isinstance(cached_result_data, dict):
                logger.info(f"[DEBUG] cached_result_data.keys()={list(cached_result_data.keys())}")
        
        # 检查result是否已经是解析好的分类结果字典（包含category, confidence等字段）
        is_already_parsed = (
            isinstance(cached_result_data, dict) and 
            'category' in cached_result_data and 
            'confidence' in cached_result_data
        )
        
        if is_debug:
            logger.info(f"[DEBUG] is_already_parsed={is_already_parsed}, isinstance={isinstance(cached_result_data, dict)}, has_category={'category' in cached_result_data if isinstance(cached_result_data, dict) else False}, has_confidence={'confidence' in cached_result_data if isinstance(cached_result_data, dict) else False}")
        
        if isinstance(cached_result_data, dict):
            if is_already_parsed:
                # result已经是解析好的分类结果，直接使用
                raw_content = None  # 不需要原始内容
            else:
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
            
            if is_debug:
                logger.info(f"[DEBUG] classification处理: cached_is_default_prompt={cached_is_default_prompt}, is_default_prompt={is_default_prompt}, prompt匹配={prompt == settings.CLASSIFICATION_PROMPT}")
                logger.info(f"[DEBUG] 执行分支: is_already_parsed={is_already_parsed}, is_default_prompt={is_default_prompt}, raw_content={raw_content is not None if raw_content else False}")
            
            if is_already_parsed:
                # result已经是解析好的分类结果，直接使用
                result["parsed_result"] = cached_result_data
                if is_debug:
                    logger.info(f"[DEBUG] 使用已解析结果: parsed_result={cached_result_data}")
            elif is_default_prompt and raw_content:
                # 默认prompt：解析JSON
                result["parsed_result"] = self._parse_classification_response(raw_content, try_parse_json=True)
                if is_debug:
                    logger.info(f"[DEBUG] 解析JSON结果: parsed_result={result.get('parsed_result')}")
            else:
                # 自定义prompt：不解析，返回原始内容（parsed_result为None）
                if is_debug:
                    logger.warning(f"[DEBUG] parsed_result未设置: is_already_parsed={is_already_parsed}, is_default_prompt={is_default_prompt}, raw_content={raw_content is not None if raw_content else False}")
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
        
        if is_debug:
            logger.info(f"[DEBUG] check_cache返回: result.keys()={list(result.keys())}, parsed_result存在={'parsed_result' in result}, parsed_result={result.get('parsed_result')}")
        
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
    
    @staticmethod
    def _calculate_cluster_center(
        points: List[Coordinate],
        radius_km: float = 3.0
    ) -> Tuple[float, float]:
        """
        计算聚类中心点（自适应方案）
        
        根据照片分布选择最密集的点或质心：
        - 密度差异大（景区场景）→ 使用最密集的点
        - 密度差异小（非景区场景）→ 使用质心
        
        Args:
            points: 聚类内的坐标点列表
            radius_km: 半径（公里），用于计算密度
        
        Returns:
            (center_lat, center_lon) 圆心坐标
        """
        if len(points) == 0:
            raise ValueError("点列表不能为空")
        
        if len(points) == 1:
            return points[0].latitude, points[0].longitude
        
        # 步骤1：计算每个点的密度（周围点数）
        densities = []
        for point in points:
            density = sum(1 for p in points 
                         if haversine_distance(
                             point.latitude, point.longitude, 
                             p.latitude, p.longitude
                         ) <= radius_km)
            densities.append((point, density))
        
        # 步骤2：判断是否存在明显的密集点
        density_values = [d for _, d in densities]
        max_density = max(density_values)
        avg_density = sum(density_values) / len(density_values)
        density_variance = sum((d - avg_density) ** 2 for d in density_values) / len(density_values)
        
        # 步骤3：根据密度分布选择圆心
        if density_variance > avg_density * 0.5:
            # 密度差异大，存在明显的密集点（景区场景）
            # 使用最密集的点作为圆心
            center_point = max(densities, key=lambda x: x[1])[0]
            return center_point.latitude, center_point.longitude
        else:
            # 密度差异小，照片分布均匀（非景区场景）
            # 使用质心（坐标平均值）
            center_lat = sum(p.latitude for p in points) / len(points)
            center_lon = sum(p.longitude for p in points) / len(points)
            return center_lat, center_lon
    
    @staticmethod
    def _cluster_coordinates_dbscan(
        coordinates: List[Coordinate], 
        radius_km: float = 3.0,
        min_samples: int = 1
    ) -> List[Tuple[float, float, List[Coordinate]]]:
        """
        使用DBSCAN算法将坐标点聚类成3公里圆
        
        Args:
            coordinates: 坐标点列表
            radius_km: 聚类半径（公里），默认3km
            min_samples: 最小样本数，默认1（所有点都形成聚类）
        
        Returns:
            聚类结果列表，格式：[(center_lat, center_lon, [该聚类内的坐标点列表]), ...]
        """
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn未安装，无法使用DBSCAN聚类算法")
        
        if len(coordinates) == 0:
            return []
        
        if len(coordinates) == 1:
            # 单个点，直接返回
            coord = coordinates[0]
            return [(coord.latitude, coord.longitude, [coord])]
        
        # 转换为numpy数组
        coords_array = np.array([[c.latitude, c.longitude] for c in coordinates])
        
        # 将3公里转换为度（粗略估算：1度 ≈ 111公里）
        eps_degrees = radius_km / 111.0
        
        # DBSCAN聚类
        # 注意：使用haversine距离需要将坐标转换为弧度
        clustering = DBSCAN(
            eps=eps_degrees,
            min_samples=min_samples,
            metric='haversine',
            algorithm='ball_tree'
        )
        labels = clustering.fit_predict(np.radians(coords_array))  # 转换为弧度
        
        # 构建聚类结果
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(coordinates[i])
        
        # 计算每个聚类的圆心（自适应方案）
        result = []
        for label, points in clusters.items():
            if len(points) == 1:
                # 单点聚类，直接使用该点坐标
                center_lat = points[0].latitude
                center_lon = points[0].longitude
            else:
                # 多点聚类，使用自适应方案计算圆心
                center_lat, center_lon = LLMService._calculate_cluster_center(points, radius_km)
            
            result.append((center_lat, center_lon, points))
        
        return result
    
    async def _query_locations_by_llm_single_batch(
        self,
        center_coordinates: List[Tuple[float, float]]
    ) -> List[dict]:
        """
        使用大模型查询单个批次的位置信息（最多30个圆心）
        
        Args:
            center_coordinates: 圆心坐标列表，格式：[(lat, lon), ...]
        
        Returns:
            位置信息列表，每个元素包含位置信息字典
        """
        # 构建坐标列表（包含index，便于匹配）
        coords_list = [
            {"index": i, "latitude": lat, "longitude": lon}
            for i, (lat, lon) in enumerate(center_coordinates)
        ]
        coords_json = json.dumps(coords_list, indent=2, ensure_ascii=False)
        
        # 从配置文件读取提示词模板，并替换坐标列表
        prompt_template = settings.REVERSE_GEOCODING_PROMPT
        prompt = prompt_template.format(coords_json=coords_json)
        
        # 调用大模型API
        # 根据坐标数量动态调整max_tokens
        estimated_tokens = len(center_coordinates) * 200 + 1000  # 每个坐标200 tokens + 基础1000 tokens
        max_tokens = min(estimated_tokens, 16000)  # 限制最大16k，避免超出API限制
        
        result = await self.generate_text(
            prompt=prompt,
            system_prompt="你是一个专业的地理信息专家，能够准确地将坐标转换为地址信息。",
            max_tokens=max_tokens,
            temperature=0.3,  # 降低温度，提高准确性
        )
        
        if not result.get("success"):
            error_info = result.get("error", {})
            raise Exception(f"大模型调用失败: {error_info.get('message', '未知错误')}")
        
        content = result.get("content", "")
        
        # 解析JSON响应
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
            
            location_data_list = json.loads(content_clean)
            
            if not isinstance(location_data_list, list):
                raise ValueError(f"大模型返回结果不是数组格式: {type(location_data_list)}")
            
            # 验证：检查是否所有坐标都有对应的结果
            input_indices = set(range(len(center_coordinates)))
            result_indices = set(item.get('index') for item in location_data_list if 'index' in item)
            
            if input_indices != result_indices:
                logger.warning(f"大模型返回结果不完整: 输入={len(center_coordinates)}个, 返回={len(location_data_list)}个")
                # 补充缺失的结果（返回None标记，由调用方处理）
                missing_indices = input_indices - result_indices
                for idx in missing_indices:
                    location_data_list.append({
                        "index": idx,
                        "query_latitude": center_coordinates[idx][0],
                        "query_longitude": center_coordinates[idx][1],
                        "error": "大模型未返回该坐标的结果"
                    })
            
            return location_data_list
        except json.JSONDecodeError as e:
            logger.error(f"大模型返回JSON解析失败: {e}")
            logger.error(f"原始内容: {content[:500]}")  # 只记录前500字符
            raise
    
    async def reverse_geocode_batch(
        self,
        coordinates: List[Coordinate],
        use_clustering: bool = True,
        radius_km: float = 3.0,
        min_samples: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量逆地址编码（坐标转地址）
        
        接收未命中本地数据库的坐标，进行聚类、LLM查询等处理。
        
        Args:
            coordinates: 坐标列表（未命中本地数据库的坐标）
            use_clustering: 是否使用聚类优化（默认True）
            radius_km: 聚类半径（默认3km）
            min_samples: DBSCAN最小样本数（默认1）
            **kwargs: 其他参数
        
        Returns:
            结果字典，包含：
            - success: 是否成功
            - results: 位置信息列表，格式：
              [
                  {
                      "coordinate": Coordinate,  # 原始坐标
                      "location_info": dict,      # LLM返回的位置信息
                      "cluster_center": Tuple[float, float]  # 所属聚类的中心（如果使用聚类）
                  },
                  ...
              ]
            - clusters: 聚类信息（如果使用聚类），格式：
              [(center_lat, center_lon, [坐标点列表]), ...]
            - error: 错误信息（失败时）
        """
        if len(coordinates) == 0:
            return {
                "success": True,
                "results": [],
                "clusters": []
            }
        
        try:
            # 步骤1：聚类（如果启用）
            if use_clustering:
                if not HAS_SKLEARN:
                    logger.warning("scikit-learn未安装，无法使用聚类，将逐个查询")
                    use_clustering = False
                else:
                    clusters = self._cluster_coordinates_dbscan(
                        coordinates, 
                        radius_km=radius_km, 
                        min_samples=min_samples
                    )
                    logger.info(f"聚类完成: {len(coordinates)}个坐标 → {len(clusters)}个聚类")
            else:
                # 不使用聚类，每个坐标单独形成一个"聚类"
                clusters = [(coord.latitude, coord.longitude, [coord]) for coord in coordinates]
            
            # 步骤2：提取聚类中心坐标
            center_coordinates = [(center_lat, center_lon) for center_lat, center_lon, _ in clusters]
            
            # 步骤3：分批查询（30个/批次）
            BATCH_SIZE = 30
            all_results = []
            
            for i in range(0, len(center_coordinates), BATCH_SIZE):
                batch = center_coordinates[i:i + BATCH_SIZE]
                logger.info(f"处理批次 {i//BATCH_SIZE + 1}/{(len(center_coordinates)-1)//BATCH_SIZE + 1}, "
                           f"圆心数量: {len(batch)}")
                
                try:
                    # 调用大模型查询当前批次
                    batch_results = await self._query_locations_by_llm_single_batch(batch)
                    all_results.extend(batch_results)
                except Exception as e:
                    logger.error(f"批次处理失败: {e}", exc_info=True)
                    # 为失败的批次创建错误标记
                    for idx, (lat, lon) in enumerate(batch):
                        batch_idx = i + idx
                        all_results.append({
                            "index": batch_idx,
                            "query_latitude": lat,
                            "query_longitude": lon,
                            "error": f"大模型查询失败: {str(e)}"
                        })
                
                # 避免API限流
                if i + BATCH_SIZE < len(center_coordinates):
                    await asyncio.sleep(1)  # 批次间等待1秒
            
            # 步骤4：构建结果映射（圆心结果 → 原始坐标点）
            # 建立圆心坐标到结果的映射
            center_to_result = {}
            for llm_result in all_results:
                query_lat = llm_result.get('query_latitude')
                query_lon = llm_result.get('query_longitude')
                if query_lat is not None and query_lon is not None:
                    # 使用精确匹配（允许小误差）
                    center_to_result[(query_lat, query_lon)] = llm_result
            
            # 为每个原始坐标点分配结果
            results = []
            for center_lat, center_lon, points in clusters:
                # 查找该聚类中心对应的LLM结果
                llm_result = None
                # 先尝试精确匹配
                if (center_lat, center_lon) in center_to_result:
                    llm_result = center_to_result[(center_lat, center_lon)]
                else:
                    # 如果精确匹配失败，尝试模糊匹配（允许小误差）
                    for (clat, clon), result in center_to_result.items():
                        if abs(clat - center_lat) < 0.0001 and abs(clon - center_lon) < 0.0001:
                            llm_result = result
                            break
                
                # 为聚类内的每个坐标点分配结果
                for coord in points:
                    results.append({
                        "coordinate": coord,
                        "location_info": llm_result if llm_result else {
                            "error": "未找到对应的LLM查询结果"
                        },
                        "cluster_center": (center_lat, center_lon)
                    })
            
            return {
                "success": True,
                "results": results,
                "clusters": clusters
            }
            
        except Exception as e:
            logger.error(f"批量逆地址编码失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "type": "business_error",
                    "message": str(e),
                    "user_message": "逆地址编码失败，请稍后重试"
                },
                "results": [],
                "clusters": []
            }


# 全局LLM服务实例（使用配置的默认值）
llm_service = LLMService()

