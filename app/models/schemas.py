"""
API请求和响应数据模型
使用Pydantic进行数据验证
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===== 请求模型 =====

class CheckCacheRequest(BaseModel):
    """检查缓存请求"""
    image_hash: str = Field(..., description="图片SHA-256哈希值", min_length=64, max_length=64)
    user_id: Optional[str] = Field(None, description="用户ID/设备ID")


# ===== 响应模型 =====

class ClassificationData(BaseModel):
    """分类结果数据"""
    category: str = Field(..., description="分类类别Key（使用本地推理时为空，需客户端映射）")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    description: Optional[str] = Field(None, description="图片描述")
    local_inference_result: Optional[dict] = Field(None, description="本地推理原始结果（如果使用本地推理）")


class ClassificationResponse(BaseModel):
    """分类响应"""
    success: bool = Field(True, description="是否成功")
    data: ClassificationData = Field(..., description="分类数据")
    from_cache: bool = Field(..., description="是否来自缓存")
    processing_time_ms: int = Field(..., description="处理耗时(毫秒)")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class CheckCacheResponse(BaseModel):
    """检查缓存响应"""
    success: bool = Field(True, description="是否成功")
    cached: bool = Field(..., description="是否有缓存")
    data: Optional[ClassificationData] = Field(None, description="分类数据")
    from_cache: bool = Field(True, description="来自缓存")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    request_id: Optional[str] = Field(None, description="请求ID")


# ===== 统计模型 =====

class TodayStatsResponse(BaseModel):
    """今日统计响应"""
    success: bool = Field(True)
    data: dict = Field(..., description="统计数据")


class CacheEfficiencyResponse(BaseModel):
    """缓存效率响应"""
    success: bool = Field(True)
    data: dict = Field(..., description="缓存效率数据")


class CategoryDistributionResponse(BaseModel):
    """分类分布响应"""
    success: bool = Field(True)
    data: List[dict] = Field(..., description="分类分布数据")


# ===== 健康检查模型 =====

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态")
    timestamp: datetime = Field(default_factory=datetime.now)
    database: str = Field(..., description="数据库状态")
    model_api: str = Field(..., description="模型API状态")

