"""
健康检查接口
"""

from fastapi import APIRouter
from datetime import datetime
from app.models.schemas import HealthCheckResponse
from app.database import db
from app.config import settings
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查"""
    
    # 检查数据库
    db_status = "unknown"
    try:
        async with db.get_cursor() as cursor:
            await cursor.execute("SELECT 1")
            db_status = "connected"
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        db_status = "disconnected"
    
    # 检查模型API（简单检查配置）
    model_status = "available" if settings.LLM_API_KEY else "not_configured"
    
    # 确定整体状态
    status = "healthy" if db_status == "connected" and model_status == "available" else "unhealthy"
    
    return HealthCheckResponse(
        status=status,
        timestamp=datetime.now(),
        database=db_status,
        model_api=model_status
    )

