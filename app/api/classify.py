"""
分类接口路由
/api/v1/classify/check-cache - 查询缓存
/api/v1/classify - 图片分类
"""

from fastapi import APIRouter, File, UploadFile, Form, Header, HTTPException, Request
from typing import Optional
from datetime import datetime

from app.models.schemas import (
    CheckCacheRequest,
    CheckCacheResponse,
    ClassificationResponse,
    ClassificationData,
    ErrorResponse
)
from app.services.classifier import classifier
from app.utils.image_utils import ImageUtils
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["classify"])


@router.post("/classify/check-cache", response_model=CheckCacheResponse)
async def check_cache(
    request_body: CheckCacheRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    检查缓存接口
    
    客户端先发送图片哈希，如果有缓存直接返回结果
    """
    try:
        # 获取user_id（优先使用Header）
        user_id = x_user_id or request_body.user_id
        
        # 获取IP地址
        ip_address = request.client.host if request else None
        
        # 查询缓存
        result, from_cache, request_id = await classifier.classify_by_hash(
            image_hash=request_body.image_hash,
            user_id=user_id,
            ip_address=ip_address
        )
        
        if result:
            # 缓存命中
            return CheckCacheResponse(
                success=True,
                cached=True,
                data=ClassificationData(**result),
                from_cache=True,
                request_id=request_id,
                timestamp=datetime.now()
            )
        else:
            # 缓存未命中
            return CheckCacheResponse(
                success=True,
                cached=False,
                data=None,
                from_cache=False,
                request_id=request_id,
                timestamp=datetime.now()
            )
            
    except Exception as e:
        logger.error(f"检查缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify", response_model=ClassificationResponse)
async def classify_image(
    image: UploadFile = File(..., description="图片文件"),
    image_hash: Optional[str] = Form(None, description="客户端计算的SHA-256哈希"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    图片分类接口
    
    上传图片进行分类，如果缓存未命中则调用大模型
    """
    try:
        # 读取图片数据
        image_bytes = await image.read()
        
        # 验证图片
        is_valid, error_msg = ImageUtils.validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 获取user_id和IP
        user_id = x_user_id
        ip_address = request.client.host if request else None
        
        # 分类
        result, from_cache, request_id, processing_time = await classifier.classify_image(
            image_bytes=image_bytes,
            image_hash=image_hash,
            user_id=user_id,
            ip_address=ip_address
        )
        
        return ClassificationResponse(
            success=True,
            data=ClassificationData(**result),
            from_cache=from_cache,
            processing_time_ms=processing_time,
            request_id=request_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图片分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

