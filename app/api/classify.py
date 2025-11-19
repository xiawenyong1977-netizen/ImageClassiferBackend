"""
分类接口路由
/api/v1/classify/check-cache - 查询缓存
/api/v1/classify - 图片分类
"""

from fastapi import APIRouter, File, UploadFile, Form, Header, HTTPException, Request
from typing import Optional, List
from datetime import datetime
import time
import json

from app.models.schemas import (
    CheckCacheRequest,
    CheckCacheResponse,
    BatchCheckCacheRequest,
    BatchCheckCacheResponse,
    CacheItem,
    ClassificationResponse,
    ClassificationData,
    BatchClassifyItem,
    BatchClassifyResponse,
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
        
        # 记录统一日志（单个缓存查询）
        from app.services.stats_service import stats_service
        cached_count = 1 if from_cache else 0
        await stats_service.log_unified_request(
            request_id=request_id,
            request_type='single_cache',  # 单个缓存查询
            ip_address=ip_address,
            client_id=user_id,
            openid=None,
            total_images=1,
            cached_count=cached_count,
            llm_count=0,
            local_count=0
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


@router.post("/classify/batch-check-cache", response_model=BatchCheckCacheResponse)
async def batch_check_cache(
    request_body: BatchCheckCacheRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    批量检查缓存接口
    
    一次性检查多个图片哈希的缓存状态
    最多支持100个哈希
    """
    try:
        # 获取user_id（优先使用Header）
        user_id = x_user_id or request_body.user_id
        
        # 获取IP地址
        ip_address = request.client.host if request else None
        
        # 批量查询缓存
        results, request_id = await classifier.batch_check_cache(
            image_hashes=request_body.image_hashes,
            user_id=user_id,
            ip_address=ip_address
        )
        
        # 统计缓存命中数
        cached_count = sum(1 for item in results if item['cached'])
        miss_count = len(results) - cached_count
        
        # 记录统一日志（批量缓存查询）
        from app.services.stats_service import stats_service
        await stats_service.log_unified_request(
            request_id=request_id,
            request_type='batch_cache',
            ip_address=ip_address,
            client_id=user_id,
            openid=None,
            total_images=len(results),
            cached_count=cached_count,
            llm_count=0,
            local_count=0
        )
        
        # 保留旧的批量缓存查询统计（兼容性）
        await stats_service.log_batch_cache_query(
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            total_count=len(results),
            cached_count=cached_count,
            miss_count=miss_count
        )
        
        # 构造响应
        cache_items = [
            CacheItem(
                image_hash=item['image_hash'],
                cached=item['cached'],
                data=ClassificationData(**item['data']) if item['data'] else None
            )
            for item in results
        ]
        
        return BatchCheckCacheResponse(
            success=True,
            total=len(results),
            cached_count=cached_count,
            items=cache_items,
            request_id=request_id,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"批量检查缓存失败: {e}")
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
    注意：图片分类不扣减额度，只有图像增强（image-edit）才扣减额度
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
        result, from_cache, request_id, processing_time, inference_method = await classifier.classify_image(
            image_bytes=image_bytes,
            image_hash=image_hash,
            user_id=user_id,
            ip_address=ip_address
        )
        
        # 记录统一日志（单个分类请求）
        from app.services.stats_service import stats_service
        cached_count = 1 if from_cache else 0
        llm_count = 1 if not from_cache and inference_method in ('llm', 'llm_fallback') else 0
        local_count = 1 if not from_cache and inference_method in ('local', 'local_fallback', 'local_test') else 0
        
        await stats_service.log_unified_request(
            request_id=request_id,
            request_type='single_classify',
            ip_address=ip_address,
            client_id=user_id,
            openid=None,
            total_images=1,
            cached_count=cached_count,
            llm_count=llm_count,
            local_count=local_count
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


@router.post("/classify/batch", response_model=BatchClassifyResponse)
async def batch_classify(
    images: List[UploadFile] = File(..., description="图片文件列表"),
    image_hashes: Optional[str] = Form(None, description="图片哈希列表JSON字符串"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    批量图片分类接口
    
    一次性上传多张图片进行分类
    最多支持20张图片
    """
    try:
        # 限制最大数量
        max_images = 20
        if len(images) > max_images:
            raise HTTPException(
                status_code=400,
                detail=f"一次最多上传{max_images}张图片，当前: {len(images)}"
            )
        
        # 解析image_hashes
        hashes_list = []
        if image_hashes:
            try:
                hashes_list = json.loads(image_hashes)
                if not isinstance(hashes_list, list):
                    hashes_list = []
            except:
                hashes_list = []
        
        # 获取user_id
        user_id = x_user_id
        ip_address = request.client.host if request else None
        
        # 生成批量请求ID
        from app.utils.id_generator import IDGenerator
        batch_request_id = IDGenerator.generate_request_id()
        
        # 记录开始时间
        batch_start_time = time.time()
        
        # 处理每张图片
        results = []
        success_count = 0
        fail_count = 0
        cached_count = 0
        llm_count = 0
        local_count = 0
        
        for index, image in enumerate(images):
            item_start_time = time.time()
            
            try:
                # 读取图片
                image_bytes = await image.read()
                
                # 验证图片
                is_valid, error_msg = ImageUtils.validate_image(image_bytes)
                if not is_valid:
                    raise Exception(error_msg)
                
                # 获取对应的hash（如果有）
                image_hash = hashes_list[index] if index < len(hashes_list) else None
                
                # 调用分类服务
                result, from_cache, request_id, processing_time, inference_method = await classifier.classify_image(
                    image_bytes=image_bytes,
                    image_hash=image_hash,
                    user_id=user_id,
                    ip_address=ip_address
                )
                
                # 统计处理方式
                if from_cache:
                    cached_count += 1
                elif inference_method in ('llm', 'llm_fallback'):
                    llm_count += 1
                elif inference_method in ('local', 'local_fallback', 'local_test'):
                    local_count += 1
                
                item_processing_time = int((time.time() - item_start_time) * 1000)
                
                # 成功结果
                results.append(BatchClassifyItem(
                    index=index,
                    filename=image.filename or f"image_{index}",
                    success=True,
                    data=ClassificationData(**result),
                    error=None,
                    from_cache=from_cache,
                    processing_time_ms=item_processing_time
                ))
                success_count += 1
                
            except Exception as e:
                item_processing_time = int((time.time() - item_start_time) * 1000)
                logger.error(f"批量分类-图片{index}失败: {e}")
                
                # 失败结果
                results.append(BatchClassifyItem(
                    index=index,
                    filename=image.filename or f"image_{index}",
                    success=False,
                    data=None,
                    error=str(e),
                    from_cache=False,
                    processing_time_ms=item_processing_time
                ))
                fail_count += 1
        
        # 计算总耗时
        total_processing_time = int((time.time() - batch_start_time) * 1000)
        
        # 记录统一日志（批量分类）
        from app.services.stats_service import stats_service
        await stats_service.log_unified_request(
            request_id=batch_request_id,
            request_type='batch_classify',
            ip_address=ip_address,
            client_id=user_id,
            openid=None,
            total_images=len(images),
            cached_count=cached_count,
            llm_count=llm_count,
            local_count=local_count
        )
        
        # 保留旧的批量分类统计（兼容性）
        await stats_service.log_batch_classify(
            request_id=batch_request_id,
            user_id=user_id,
            ip_address=ip_address,
            total_count=len(images),
            success_count=success_count,
            fail_count=fail_count,
            total_processing_time_ms=total_processing_time
        )
        
        return BatchClassifyResponse(
            success=True,
            total=len(images),
            success_count=success_count,
            fail_count=fail_count,
            items=results,
            request_id=batch_request_id,
            total_processing_time_ms=total_processing_time,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

