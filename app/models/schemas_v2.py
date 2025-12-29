"""
API请求和响应数据模型（v2版本）
用于v2版本的分类接口
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class InternalErrorType(str, Enum):
    """内部服务错误类型（SUCCESS表示成功，其他值表示内部服务异常）"""
    SUCCESS = "success"  # 成功（无内部服务异常）
    DATABASE_CONNECTION_FAILED = "database_connection_failed"  # 数据库连接失败
    DATABASE_OPERATION_FAILED = "database_operation_failed"  # 数据库操作失败（查询/插入/更新）
    CACHE_SERVICE_UNAVAILABLE = "cache_service_unavailable"  # 缓存服务不可用
    CACHE_QUERY_FAILED = "cache_query_failed"  # 缓存查询失败
    IMAGE_PROCESSING_FAILED = "image_processing_failed"  # 图片处理服务异常（批量处理时）
    UNKNOWN_INTERNAL_ERROR = "unknown_internal_error"  # 未知的内部错误


class TaskStatus(str, Enum):
    """异步任务状态"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


# ===== 请求模型 =====

class ImageMetadataItem(BaseModel):
    """单张图片的元数据"""
    index: int = Field(..., description="图片索引（对应images数组中的位置）")
    image_uri: str = Field(..., description="图片URI（客户端传入）")
    image_hash: Optional[str] = Field(None, description="图片哈希（可选，客户端预计算）")


class BatchClassifyV2Request(BaseModel):
    """批量分类请求（用于multipart/form-data请求中的image_metadata字段）"""
    items: List[ImageMetadataItem] = Field(..., description="图片元数据数组")
    prompt: Optional[str] = Field(None, description="自定义分类提示词")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")


class BatchCheckCacheV2Request(BaseModel):
    """批量查询缓存请求（v2版本）"""
    items: List[ImageMetadataItem] = Field(..., description="图片元数据数组", min_length=1, max_length=200)
    prompt: Optional[str] = Field(None, description="提示词（用于查询对应prompt的缓存）")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")


# ===== 响应模型 =====

class BatchClassifyItemV2(BaseModel):
    """批量分类单个结果项（v2版本）"""
    index: int = Field(..., description="图片索引")
    image_uri: Optional[str] = Field(None, description="图片URI（客户端传入的）")
    error: Optional[str] = Field(None, description="错误信息（失败时才有）")
    
    # 分类结果字段（成功时才有）
    category: Optional[str] = Field(None, description="分类结果（LLM返回的原始内容或解析后的类别）")
    confidence: Optional[float] = Field(None, description="置信度（如果有）", ge=0, le=1)
    description: Optional[str] = Field(None, description="描述（如果有）")
    background_color: Optional[str] = Field(None, description="背景颜色（如果有）")
    raw_content: Optional[str] = Field(None, description="LLM返回的原始响应内容（用于自定义prompt的解析）")
    
    # 元数据字段
    inference_method: Optional[str] = Field(None, description="推理方式：cache|llm|qrcode_detection（None表示未进行推理，如验证失败、格式错误等）")
    processing_time_ms: int = Field(..., description="处理耗时(毫秒)")


class BatchSummary(BaseModel):
    """批量处理汇总统计"""
    total_count: int = Field(..., description="总数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
    cached_count: int = Field(..., description="缓存命中数")
    llm_count: int = Field(..., description="LLM处理数")
    total_time_ms: int = Field(..., description="总处理耗时(毫秒)")


class BatchClassifyResponseV2(BaseModel):
    """批量分类响应（v2版本）"""
    error_type: InternalErrorType = Field(InternalErrorType.SUCCESS, description="内部服务错误类型（SUCCESS表示成功，其他值表示内部服务异常）")
    error: Optional[str] = Field(None, description="内部服务错误信息（仅在error_type不为SUCCESS时存在）")
    results: List[BatchClassifyItemV2] = Field(..., description="分类结果列表")
    summary: BatchSummary = Field(..., description="汇总统计")
    request_id: str = Field(..., description="请求ID")


class CacheItemV2(BaseModel):
    """单个缓存项（v2版本）"""
    index: int = Field(..., description="图片索引")
    image_uri: Optional[str] = Field(None, description="图片URI（客户端传入的）")
    image_hash: str = Field(..., description="图片哈希")
    cached: bool = Field(..., description="是否有缓存")
    # 分类结果字段（缓存命中时才有）
    category: Optional[str] = Field(None, description="分类结果（LLM返回的原始内容或解析后的类别）")
    confidence: Optional[float] = Field(None, description="置信度（如果有）", ge=0, le=1)
    description: Optional[str] = Field(None, description="描述（如果有）")
    background_color: Optional[str] = Field(None, description="背景颜色（如果有）")
    raw_content: Optional[str] = Field(None, description="LLM返回的原始响应内容（用于自定义prompt的解析）")


class BatchCheckCacheV2Response(BaseModel):
    """批量检查缓存响应（v2版本）"""
    error_type: InternalErrorType = Field(InternalErrorType.SUCCESS, description="内部服务错误类型（SUCCESS表示成功，其他值表示内部服务异常）")
    error: Optional[str] = Field(None, description="内部服务错误信息（仅在error_type不为SUCCESS时存在）")
    results: List[CacheItemV2] = Field(..., description="缓存项列表")
    summary: dict = Field(..., description="汇总统计：total, cached_count, miss_count")
    request_id: str = Field(..., description="请求ID")


# ===== 图像编辑 v2 版本模型 =====

class ImageEditItem(BaseModel):
    """单张图片的编辑元数据"""
    index: int = Field(..., description="图片索引（对应images数组中的位置）")
    image_uri: str = Field(..., description="图片URI（客户端传入）")
    image_hash: Optional[str] = Field(None, description="图片哈希（可选，客户端预计算）")


class BatchImageEditV2Request(BaseModel):
    """批量图像编辑请求（用于multipart/form-data请求中的image_metadata字段）"""
    items: List[ImageEditItem] = Field(..., description="图片元数据数组")
    prompt: str = Field(..., description="编辑提示词")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")


class BatchImageEditSubmitResponseV2(BaseModel):
    """批量编辑提交响应（v2版本）"""
    error_type: InternalErrorType = Field(InternalErrorType.SUCCESS, description="内部服务错误类型（SUCCESS表示成功，其他值表示内部服务异常）")
    error: Optional[str] = Field(None, description="内部服务错误信息（仅在error_type不为SUCCESS时存在）")
    task_id: str = Field(..., description="任务ID（用于查询任务状态）")
    total_images: int = Field(..., description="总图片数")
    request_id: str = Field(..., description="请求ID")


class ImageEditResultItem(BaseModel):
    """图像编辑单个结果项"""
    index: int = Field(..., description="图片索引")
    image_uri: Optional[str] = Field(None, description="图片URI（客户端传入的，用于对应）")
    status: str = Field(..., description="状态：completed|failed|processing")
    result_url: Optional[str] = Field(None, description="编辑后的图片URL（成功时才有）")
    error: Optional[str] = Field(None, description="错误信息（失败时才有）")
    from_cache: Optional[bool] = Field(None, description="是否来自缓存（成功时才有）")


class TaskStatusResponseV2(BaseModel):
    """任务状态响应（v2版本，简化版）"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态：pending|processing|completed|failed")
    total_images: int = Field(..., description="总图片数")
    completed_images: int = Field(..., description="已完成数")
    results: List[ImageEditResultItem] = Field(..., description="结果列表")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

