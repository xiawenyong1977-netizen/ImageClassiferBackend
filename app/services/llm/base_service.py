"""
基础LLM服务层
提供统一的错误处理、重试机制、超时控制、日志记录等
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from loguru import logger
from app.config import settings


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
                
                # 判断是否应该重试
                should_retry = self._should_retry(e, attempt)
                
                if should_retry and attempt < self.max_retries:
                    logger.warning(
                        f"[{self.provider}] 大模型调用失败 [{task_type}] "
                        f"(尝试 {attempt}/{self.max_retries}, 耗时: {elapsed_time:.2f}s): {e}，"
                        f"{self.retry_delay}秒后重试..."
                    )
                    await asyncio.sleep(self.retry_delay * attempt)  # 指数退避
                else:
                    logger.error(
                        f"[{self.provider}] 大模型调用失败 [{task_type}] "
                        f"(尝试 {attempt}/{self.max_retries}, 耗时: {elapsed_time:.2f}s): {e}"
                    )
                    if not should_retry:
                        # 不可重试的错误，直接抛出
                        raise
                    # 最后一次重试也失败
                    break
        
        # 所有重试都失败
        raise Exception(
            f"[{self.provider}] 大模型调用失败 [{task_type}]，"
            f"已重试 {self.max_retries} 次: {last_error}"
        ) from last_error
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 异常对象
            attempt: 当前尝试次数
            
        Returns:
            是否应该重试
        """
        error_str = str(error).lower()
        
        # 网络相关错误，可以重试
        retryable_errors = [
            "timeout",
            "connection",
            "network",
            "temporarily unavailable",
            "rate limit",
            "too many requests",
            "503",
            "502",
            "500",
        ]
        
        if any(keyword in error_str for keyword in retryable_errors):
            return True
        
        # 其他错误不重试（如认证失败、参数错误等）
        return False
    
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

