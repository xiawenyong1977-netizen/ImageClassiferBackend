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
        self.timeout = timeout or settings.LLM_TIMEOUT
    
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
                logger.info(
                    f"[{self.provider}] 调用大模型 [{task_type}] "
                    f"(尝试 {attempt}/{self.max_retries}, model={self.model})"
                )
                
                # 调用具体的API方法
                result = await self._call_api(task_type, image_bytes, prompt, **kwargs)
                
                elapsed_time = time.time() - attempt_start_time
                logger.info(
                    f"[{self.provider}] 大模型调用成功 [{task_type}] "
                    f"(耗时: {elapsed_time:.2f}s, model={self.model})"
                )
                
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
        
        # 判断错误类型
        if status_code == 400:
            # 400错误需要进一步判断是输入错误还是业务逻辑错误
            if any(keyword in error_str for keyword in [
                'invalidparameter', 'invalidimage', 'imagetoolarge',
                'contentviolation', 'prompttoolong', 'invalid format',
                'image length and width', 'image size'
            ]):
                return LLMError(
                    message=error_message,
                    error_type=LLMErrorType.INPUT_ERROR,
                    status_code=status_code,
                    error_code=error_code,
                    should_retry=False  # 输入错误不重试
                )
            else:
                return LLMError(
                    message=error_message,
                    error_type=LLMErrorType.BUSINESS_ERROR,
                    status_code=status_code,
                    error_code=error_code,
                    should_retry=False
                )
        
        elif status_code in [401, 403]:
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.AUTH_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=False
            )
        
        elif status_code == 429:
            return LLMError(
                message=error_message,
                error_type=LLMErrorType.RATE_LIMIT_ERROR,
                status_code=status_code,
                error_code=error_code,
                should_retry=True  # 限流错误可重试
            )
        
        elif status_code and status_code >= 500:
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

