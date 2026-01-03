"""
健康检查接口 v2版本
相比 v1 版本增加了 user_id、设备类型和客户端提交时间字段
"""

from fastapi import APIRouter, Query, Request
from datetime import datetime
from typing import Optional
import time
from app.models.schemas_v2 import HealthCheckResponseV2
from app.database import db
from app.config import settings
from app.utils.id_generator import IDGenerator
from app.utils.request_logger import RequestLogger
from loguru import logger

router = APIRouter(prefix="/api/v2", tags=["health-v2"])


@router.get("/health", response_model=HealthCheckResponseV2)
async def health_check_v2(
    user_id: Optional[str] = Query(None, description="用户ID/设备ID"),
    device_type: Optional[str] = Query(None, description="设备类型（如：iOS、Android、Web等）"),
    client_timestamp: Optional[str] = Query(None, description="客户端提交的时间（ISO 8601格式）"),
    request: Request = None
):
    """
    健康检查 v2版本
    
    相比 v1 版本增加了以下字段：
    - user_id: 用户ID/设备ID
    - device_type: 设备类型
    - client_timestamp: 客户端提交的时间
    
    参数:
    - user_id: 用户ID/设备ID（可选）
    - device_type: 设备类型（可选）
    - client_timestamp: 客户端提交的时间，ISO 8601格式（可选）
    """
    request_id = IDGenerator.generate_request_id("health")
    start_time = time.time()
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint="/api/v2/health",
            method="GET",
            user_id=user_id,
            device_type=device_type,
            ip_address=ip_address,
            params={
                "user_id": user_id,
                "device_type": device_type,
                "client_timestamp": client_timestamp
            }
        )
        
        # 检查数据库
        db_status = "unknown"
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("SELECT 1")
                db_status = "connected"
        except Exception as e:
            RequestLogger.log_error(request_id, e, "/api/v2/health", user_id, "database_check_failed")
            db_status = "disconnected"
        
        # 检查模型API（简单检查配置）
        model_status = "available" if settings.LLM_API_KEY else "not_configured"
        
        # 确定整体状态
        # 在测试环境中，只要数据库连接正常就认为健康
        # 在生产环境中，需要数据库和模型API都可用
        is_test_env = settings.APP_ENV.lower() in ["test", "testing", "ci"]
        if is_test_env:
            status = "healthy" if db_status == "connected" else "unhealthy"
        else:
            status = "healthy" if db_status == "connected" and model_status == "available" else "unhealthy"
        
        # 解析客户端时间戳
        parsed_client_timestamp = None
        timestamp_parse_status = "not_provided"
        if client_timestamp:
            try:
                # 支持 ISO 8601 格式，包括带 Z 的 UTC 时间
                parsed_client_timestamp = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                timestamp_parse_status = f"parsed: {parsed_client_timestamp}"
            except (ValueError, AttributeError) as e:
                RequestLogger.log_error(request_id, e, "/api/v2/health", user_id, "timestamp_parse_failed", client_timestamp=client_timestamp)
                timestamp_parse_status = "parse_failed"
        
        # 合并所有检查结果到一条日志
        RequestLogger.log_step(
            request_id, 
            "health_check", 
            f"健康检查完成: 状态={status}, 数据库={db_status}, 模型API={model_status}, 时间戳={timestamp_parse_status}", 
            user_id=user_id
        )
        
        response = HealthCheckResponseV2(
            status=status,
            timestamp=datetime.now(),
            database=db_status,
            model_api=model_status,
            user_id=user_id,
            device_type=device_type,
            client_timestamp=parsed_client_timestamp
        )
        
        # 记录响应
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/health",
            status_code=200,
            user_id=user_id,
            response_time_ms=response_time_ms,
            status=status,
            database=db_status,
            model_api=model_status
        )
        
        return response
        
    except Exception as e:
        # 记录未预期的错误
        RequestLogger.log_error(request_id, e, "/api/v2/health", user_id, "unexpected_error")
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/health",
            status_code=500,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        raise

