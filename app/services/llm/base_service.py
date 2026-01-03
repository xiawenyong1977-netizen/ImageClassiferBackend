"""
基础LLM服务层
提供统一的错误处理、重试机制、超时控制、日志记录等
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from enum import Enum
from loguru import logger
from app.config import settings


class LLMErrorType(str, Enum):
    """LLM错误类型枚举"""
    # 可重试的错误（在base_service层处理）
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    FORMAT_ERROR = "format_error"
    
    # 不可重试的错误（在llm_service层处理）
    INPUT_ERROR = "input_error"
    AUTH_ERROR = "auth_error"
    BUSINESS_ERROR = "business_error"


class LLMError(Exception):
    """LLM调用错误基类"""
    def __init__(
        self,
        message: str,
        error_type: LLMErrorType,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        should_retry: bool = False,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.error_code = error_code
        self.should_retry = should_retry
        self.user_message = user_message or self._get_default_user_message()
        super().__init__(self.message)
    
    def _get_default_user_message(self) -> str:
        """获取默认用户友好消息"""
        messages = {
            LLMErrorType.NETWORK_ERROR: "网络连接异常，请稍后重试",
            LLMErrorType.SERVER_ERROR: "服务暂时不可用，请稍后重试",
            LLMErrorType.RATE_LIMIT_ERROR: "请求过于频繁，请稍后重试",
            LLMErrorType.FORMAT_ERROR: "服务响应异常，请稍后重试",
            LLMErrorType.INPUT_ERROR: "输入参数有误，请检查图片格式和内容",
            LLMErrorType.AUTH_ERROR: "服务暂时不可用，请稍后重试",
            LLMErrorType.BUSINESS_ERROR: "当前功能暂不可用",
        }
        return messages.get(self.error_type, "服务暂时不可用，请稍后重试")


class BaseLLMService(ABC):
    """基础LLM服务抽象类"""
    
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[int] = None
    ):
        """
        初始化基础LLM服务
        
        Args:
            provider: 提供商名称（aliyun/openai/claude）
            api_key: API密钥
            model: 模型名称
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒），None则使用配置值
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # timeout 应该由调用方根据任务类型传入，这里使用传入的值或默认值
        # 如果没有传入，使用分类任务的默认超时时间（30秒）
        self.timeout = timeout or settings.LLM_TIMEOUT_CLASSIFICATION or 30
    
    async def call_with_retry(
        self,
        task_type: str,
        image_bytes: bytes,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        带重试机制的API调用
        
        Args:
            task_type: 任务类型（classification/image_edit等）
            image_bytes: 图片二进制数据
            prompt: 提示词
            **kwargs: 其他参数（如edit_type, edit_params等）
            
        Returns:
            API响应结果字典
            
        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        last_error = None
        start_time = time.time()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                attempt_start_time = time.time()
                # 不记录成功日志，只记录失败日志
                
                # 调用具体的API方法
                result = await self._call_api(task_type, image_bytes, prompt, **kwargs)
                
                # 成功时不记录日志，减少日志噪音
                return result
                
            except Exception as e:
                last_error = e
                elapsed_time = time.time() - attempt_start_time
                
                # 解析错误
                llm_error = self._parse_error(e) if not isinstance(e, LLMError) else e
                
                # 判断是否应该重试
                should_retry = llm_error.should_retry and attempt < self.max_retries
                
                if should_retry:
                    logger.warning(
                        f"[{self.provider}] 大模型调用失败 [{task_type}] "
                        f"(尝试 {attempt}/{self.max_retries}, 耗时: {elapsed_time:.2f}s, "
                        f"错误类型: {llm_error.error_type.value}): {llm_error.message}，"
                        f"{self.retry_delay * attempt}秒后重试..."
                    )
                    await asyncio.sleep(self.retry_delay * attempt)  # 指数退避
                else:
                    # 不可重试的错误，直接抛出（让llm_service层处理）
                    logger.error(
                        f"[{self.provider}] 大模型调用失败 [{task_type}] "
                        f"(尝试 {attempt}/{self.max_retries}, 耗时: {elapsed_time:.2f}s, "
                        f"错误类型: {llm_error.error_type.value}): {llm_error.message}"
                    )
                    raise llm_error  # 抛出LLMError，让上层处理
        
        # 所有重试都失败（可重试的错误最终也失败了）
        if isinstance(last_error, LLMError):
            raise last_error
        else:
            llm_error = self._parse_error(last_error)
            raise llm_error
    
    def _parse_error(self, error: Exception, status_code: Optional[int] = None) -> LLMError:
        """
        解析错误并转换为LLMError
        
        Args:
            error: 原始异常
            status_code: HTTP状态码（如果有）
        
        Returns:
            LLMError对象
        """
        error_str = str(error).lower()
        error_message = str(error)
        
        # 从异常中提取状态码和错误码
        status_code = status_code or getattr(error, 'status_code', None)
        error_code = getattr(error, 'error_code', None) or getattr(error, 'code', None)
        
        # 如果已经是LLMError，直接返回
        if isinstance(error, LLMError):
            return error
        
        # 判断错误类型（根据阿里云DashScope API文档）
        if status_code == 400:
            # 400 - InvalidParameter：参数错误或格式错误
            # 根据阿里云DashScope API文档，400错误都是参数/输入错误，不应重试
            # 识别常见的400错误关键词（扩展版，覆盖所有文档中的错误类型）
            input_error_keywords = [
                # 参数相关
                'invalidparameter', 'invalid parameter', 'parameter', 'required parameter',
                'enable_thinking', 'thinking_budget', 'stream mode', 'enable_search',
                'incremental_output', 'source_lang', 'target_lang',
                'field required', 'missing required', 'missing parameter',
                # 输入长度相关
                'range of input length', 'range of max_tokens', 'token length exceed',
                'input length', 'max_tokens', 'too many files', 'exceeds size limit',
                'exceeds page limits', 'exceeded limit', 'too short', 'too large',
                'too long', 'too small', 'exceed', 'beyond limit',
                # 参数值范围相关
                'temperature should be', 'temperature must be', 'range of top_p',
                'top_p must be', 'top_k be greater', 'repetition_penalty',
                'presence_penalty', 'range of n', 'range of seed',
                'must be', 'should be', 'must be between', 'should be in',
                # 格式相关
                'invalid format', 'invalid file', 'format is not supported',
                'format is illegal', 'cannot be opened', 'failed to decode',
                'read image error', 'read video error', 'decode error',
                'file format', 'image format', 'audio format', 'video format',
                # 图像相关
                'invalidimage', 'imagetoolarge', 'image length and width',
                'image size', 'multimodal file size', 'sequence images',
                'video modality', 'data-uri item', 'image resolution',
                'image size is not supported', 'image resolution is invalid',
                'image content does not comply', 'image has no human',
                # 内容相关
                'contentviolation', 'prompttoolong', 'content must be',
                'content field is required', 'input content must be',
                'messages with role', 'input must contain', 'input should be',
                'content length', 'messages length', 'no messages found',
                'lack of image or text', 'input messages do not contain',
                # 模型相关
                'model not exist', 'model only support', 'model does not support',
                'model cannot be set', 'model restrictions', 'model not found',
                'unsupported model', 'model unavailable',
                # 文件相关
                'file parsing', 'file format', 'file cannot be found',
                'file content blank', 'file_urls', 'invalid file',
                'file size', 'file duration', 'file ratio', 'file sample rate',
                'file download', 'download failed', 'download timeout',
                'file not found', 'file too large', 'file too small',
                # URL相关
                'url error', 'invalid url', 'url does not appear',
                'connection refused', 'download timeout', 'connection timeout',
                # 音频相关
                'audio is empty', 'audio format', 'voice', 'audio length',
                'audio duration', 'audio rate', 'audio silent', 'audio short',
                'audio preprocess', 'audio decoder', 'audio file',
                # 视频相关
                'video file', 'video resolution', 'video fps', 'video duration',
                'video modality', 'video format',
                # 其他参数错误
                'request method', 'required body invalid', 'body format',
                'messages must contain', 'tool names', 'tool call',
                'result_format', 'stop parameter', 'batch size',
                'download', 'media resource', 'data inspection',
                'input json error', 'json error', 'invalid json',
                'check input data', 'invalid value', 'invalid schema',
                'invalid garment', 'invalid bbox', 'invalid style',
                'driven not exist', 'missing training files',
                # 内容合规相关
                'inappropriate content', 'green network', 'ip infringement',
                'faq rule blocked', 'custom role blocked',
                # 配额相关
                'quota exceeded', 'allocation quota', 'free tier',
                # 其他
                'request parameter is invalid', 'parameter is invalid',
                'parameter missing', 'parameter out of range',
                'unsupported operation', 'client disconnect',
                'service unavailable error', 'bad request'
            ]
            
            # 检查是否是输入/参数错误
            # 根据阿里云文档，所有400错误都是参数/输入错误，不应重试
            if any(keyword in error_str for keyword in input_error_keywords):
                return LLMError(
                    message=error_message,
                    error_type=LLMErrorType.INPUT_ERROR,
                    status_code=status_code,
                    error_code=error_code,
                    should_retry=False  # 400错误都是参数/输入错误，不重试
                )
            else:
                # 其他400错误也归类为输入错误（根据阿里云文档，400都是参数错误）
                return LLMError(
                    message=error_message,
                    error_type=LLMErrorType.INPUT_ERROR,
                    status_code=status_code,
                    error_code=error_code,
                    should_retry=False  # 400错误不重试
                )
        
        elif status_code == 401:
            # 401 - 认证失败：API key 错误，认证失败
            # 包括：InvalidApiKey, invalid_api_key, NOT AUTHORIZED
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.AUTH_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 认证错误不重试
            )
        
        elif status_code == 403:
            # 403 - 访问被拒绝：无权限访问资源
            # 包括：AccessDenied, access_denied, Model.AccessDenied, App.AccessDenied等
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.AUTH_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 权限错误不重试
            )
        
        elif status_code == 402:
            # 402 - 余额不足：账号余额不足（如果支持）
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.BUSINESS_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 余额不足不重试
            )
        
        elif status_code == 404:
            # 404 - 资源不存在：模型不存在、工作空间不存在等
            # 包括：ModelNotFound, model_not_found, WorkSpaceNotFound, NotFound
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.BUSINESS_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 资源不存在不重试
            )
        
        elif status_code == 409:
            # 409 - 冲突：资源已存在等
            # 包括：Conflict（模型实例已存在）
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.BUSINESS_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 冲突错误不重试
            )
        
        elif status_code == 422:
            # 422 - 参数错误：请求体参数错误
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.INPUT_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False  # 参数错误不重试
            )
        
        elif status_code == 429:
            # 429 - 请求速率达到上限：TPM 或 RPM 达到上限
            # 包括：Throttling, RateQuota, BurstRate, AllocationQuota等
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.RATE_LIMIT_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True  # 限流错误可重试
            )
        
        elif status_code == 500:
            # 500 - 服务器内部错误：内部算法错误、服务异常等
            # 包括：InternalError, internal_error, SystemError, ModelServiceFailed等
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.SERVER_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True  # 服务器内部错误可重试
            )
        
        elif status_code == 503:
            # 503 - 服务不可用：服务器繁忙、模型不可用等
            # 包括：ModelServingError, ModelUnavailable
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.SERVER_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True  # 服务器繁忙可重试
            )
        
        elif status_code and status_code >= 500:
            # 其他5xx错误：服务器故障
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.SERVER_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True  # 服务端错误可重试
            )
        
        # 网络相关错误
        elif any(keyword in error_str for keyword in [
            'timeout', 'connection', 'network', 'temporarily unavailable',
            'connection refused', 'connection reset'
        ]):
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.NETWORK_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True
            )
        
        # 格式错误（可能是临时问题）
        elif any(keyword in error_str for keyword in [
            'json', 'parse', 'format', 'decode', 'invalid json'
        ]):
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.FORMAT_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True
            )
        
        # 默认作为网络错误（可重试）
        return LLMError(
            message=error_message,
            error_type=LLMErrorType.NETWORK_ERROR,
            status_code=status_code,
            error_code=error_code,
            should_retry=True
        )
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 异常对象
            attempt: 当前尝试次数
            
        Returns:
            是否应该重试
        """
        # 如果是LLMError，直接使用其should_retry属性
        if isinstance(error, LLMError):
            return error.should_retry
        
        # 否则解析错误
        llm_error = self._parse_error(error)
        return llm_error.should_retry
    
    @abstractmethod
    async def _call_api(
        self,
        task_type: str,
        image_bytes: bytes,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        具体的API调用实现（由子类实现）
        
        Args:
            task_type: 任务类型
            image_bytes: 图片二进制数据
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            API响应结果字典
        """
        pass
    
    def _log_call_metrics(
        self,
        task_type: str,
        success: bool,
        elapsed_time: float,
        error: Optional[Exception] = None
    ):
        """
        记录调用指标（可用于后续监控）
        
        Args:
            task_type: 任务类型
            success: 是否成功
            elapsed_time: 耗时（秒）
            error: 错误对象（如果有）
        """
        # 这里可以扩展为发送到监控系统
        logger.debug(
            f"[{self.provider}] 调用指标 [{task_type}]: "
            f"success={success}, time={elapsed_time:.2f}s, model={self.model}"
        )

