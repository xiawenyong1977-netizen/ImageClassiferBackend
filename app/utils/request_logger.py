"""
请求日志辅助工具
提供统一的日志记录格式，包含 request_id、user_id 等关键信息
"""

from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime
import json


class RequestLogger:
    """请求日志记录器"""
    
    @staticmethod
    def log_request(
        request_id: str,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
        device_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        记录请求开始日志
        
        Args:
            request_id: 请求ID
            endpoint: 接口路径
            method: HTTP方法
            user_id: 用户ID
            device_type: 设备类型
            ip_address: IP地址
            params: 请求参数（字典）
            **kwargs: 其他额外信息
        """
        log_data = {
            "request_id": request_id,
            "endpoint": endpoint,
            "method": method,
            "user_id": user_id,
            "device_type": device_type,
            "ip_address": ip_address,
            "timestamp": datetime.now().isoformat(),
        }
        
        if params:
            log_data["params"] = params
        
        if kwargs:
            log_data.update(kwargs)
        
        logger.info(f"[REQUEST] {method} {endpoint} | request_id={request_id} | user_id={user_id} | device_type={device_type} | params={json.dumps(params, ensure_ascii=False) if params else None}")
    
    @staticmethod
    def log_step(
        request_id: str,
        step: str,
        message: str,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """
        记录关键步骤日志
        
        Args:
            request_id: 请求ID
            step: 步骤名称
            message: 日志消息
            user_id: 用户ID
            **kwargs: 其他额外信息
        """
        log_data = {
            "request_id": request_id,
            "step": step,
            "message": message,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        if kwargs:
            log_data.update(kwargs)
        
        logger.info(f"[STEP] {step} | request_id={request_id} | user_id={user_id} | {message}")
    
    @staticmethod
    def log_error(
        request_id: str,
        error: Exception,
        endpoint: Optional[str] = None,
        user_id: Optional[str] = None,
        error_type: Optional[str] = None,
        **kwargs
    ):
        """
        记录错误日志
        
        Args:
            request_id: 请求ID
            error: 异常对象
            endpoint: 接口路径
            user_id: 用户ID
            error_type: 错误类型
            **kwargs: 其他额外信息
        """
        log_data = {
            "request_id": request_id,
            "error_type": error_type or type(error).__name__,
            "error_message": str(error),
            "endpoint": endpoint,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        if kwargs:
            log_data.update(kwargs)
        
        logger.error(f"[ERROR] {error_type or type(error).__name__} | request_id={request_id} | user_id={user_id} | endpoint={endpoint} | error={str(error)}", exc_info=error)
    
    @staticmethod
    def log_response(
        request_id: str,
        endpoint: str,
        status_code: int,
        user_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        response_size: Optional[int] = None,
        **kwargs
    ):
        """
        记录响应日志
        
        Args:
            request_id: 请求ID
            endpoint: 接口路径
            status_code: HTTP状态码
            user_id: 用户ID
            response_time_ms: 响应时间（毫秒）
            response_size: 响应大小（字节）
            **kwargs: 其他额外信息
        """
        log_data = {
            "request_id": request_id,
            "endpoint": endpoint,
            "status_code": status_code,
            "user_id": user_id,
            "response_time_ms": response_time_ms,
            "response_size": response_size,
            "timestamp": datetime.now().isoformat(),
        }
        
        if kwargs:
            log_data.update(kwargs)
        
        logger.info(f"[RESPONSE] {endpoint} | request_id={request_id} | user_id={user_id} | status_code={status_code} | response_time_ms={response_time_ms}ms")
    
    @staticmethod
    def log_info(
        request_id: str,
        message: str,
        user_id: Optional[str] = None,
        **kwargs
    ):
        """
        记录一般信息日志
        
        Args:
            request_id: 请求ID
            message: 日志消息
            user_id: 用户ID
            **kwargs: 其他额外信息
        """
        log_data = {
            "request_id": request_id,
            "message": message,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
        
        if kwargs:
            log_data.update(kwargs)
        
        logger.info(f"[INFO] request_id={request_id} | user_id={user_id} | {message}")

