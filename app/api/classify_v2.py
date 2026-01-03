"""
分类接口路由（v2版本）
只提供批量接口，使用v2版本的llm_service和unified_llm_cache
/api/v2/classify/batch - 批量图片分类
/api/v2/classify/batch-check-cache - 批量查询缓存
"""

from fastapi import APIRouter, File, UploadFile, Form, Header, HTTPException, Request
from typing import Optional, List, Tuple
import time
import asyncio
import io

from app.models.schemas_v2 import (
    ImageMetadataItem,
    BatchClassifyV2Request,
    BatchClassifyResponseV2,
    BatchClassifyItemV2,
    BatchSummary,
    BatchCheckCacheV2Request,
    BatchCheckCacheV2Response,
    CacheItemV2,
    InternalErrorType
)
from app.services.llm import llm_service
from app.services.stats_service import stats_service
from app.services.user_photos_service import user_photos_service
from app.utils.image_utils import ImageUtils
from app.utils.hash_utils import HashUtils
from app.utils.id_generator import IDGenerator
from app.utils.request_logger import RequestLogger
from app.config import settings
from loguru import logger

router = APIRouter(prefix="/api/v2/classify", tags=["classify-v2"])


def _classify_internal_error(exception: Exception) -> Tuple[InternalErrorType, str]:
    """
    根据异常类型判断内部服务错误类型
    
    内部服务错误类型包括：
    - DATABASE_CONNECTION_FAILED: 数据库连接失败
    - DATABASE_OPERATION_FAILED: 数据库操作失败（查询/插入/更新）
    - CACHE_SERVICE_UNAVAILABLE: 缓存服务不可用
    - CACHE_QUERY_FAILED: 缓存查询失败
    - IMAGE_PROCESSING_FAILED: 图片处理服务异常（批量处理时的系统级错误）
    - UNKNOWN_INTERNAL_ERROR: 未知的内部错误
    
    Args:
        exception: 异常对象
        
    Returns:
        (错误类型, 错误消息)
    """
    error_msg = str(exception)
    error_type = InternalErrorType.UNKNOWN_INTERNAL_ERROR
    
    # 检查是否是数据库相关错误
    if "database" in error_msg.lower() or "mysql" in error_msg.lower() or "connection" in error_msg.lower():
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            error_type = InternalErrorType.DATABASE_CONNECTION_FAILED
        else:
            error_type = InternalErrorType.DATABASE_OPERATION_FAILED
    
    # 检查是否是缓存相关错误
    elif "cache" in error_msg.lower():
        if "unavailable" in error_msg.lower() or "timeout" in error_msg.lower():
            error_type = InternalErrorType.CACHE_SERVICE_UNAVAILABLE
        else:
            error_type = InternalErrorType.CACHE_QUERY_FAILED
    
    # 检查是否是图片处理相关错误（批量处理时的系统级错误）
    elif "image" in error_msg.lower() and ("processing" in error_msg.lower() or "format" in error_msg.lower()):
        error_type = InternalErrorType.IMAGE_PROCESSING_FAILED
    
    return error_type, error_msg


# 二维码检测相关导入
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    from PIL import Image
    QRCODE_DETECTION_AVAILABLE = True
except ImportError:
    QRCODE_DETECTION_AVAILABLE = False
    logger.warning("pyzbar 或 PIL 未安装，二维码检测功能不可用")


def _create_classify_result(
    index: int,
    image_uri: Optional[str] = None,
    error: Optional[str] = None,
    category: Optional[str] = None,
    confidence: Optional[float] = None,
    description: Optional[str] = None,
    background_color: Optional[str] = None,
    raw_content: Optional[str] = None,
    inference_method: Optional[str] = None,
    processing_time_ms: int = 0
) -> dict:
    """
    创建分类结果结构
    
    Args:
        index: 图片索引
        image_uri: 图片URI
        error: 错误信息
        category: 分类结果
        confidence: 置信度
        description: 描述
        background_color: 背景颜色
        raw_content: 原始响应内容
        inference_method: 推理方式
        processing_time_ms: 处理耗时(毫秒)
        
    Returns:
        分类结果字典
    """
    return {
        "index": index,
        "image_uri": image_uri,
        "error": error,
        "category": category,
        "confidence": confidence,
        "description": description,
        "background_color": background_color,
        "raw_content": raw_content,
        "inference_method": inference_method,
        "processing_time_ms": processing_time_ms
    }


def _create_cache_item(
    index: int,
    image_hash: str,
    image_uri: Optional[str] = None,
    cached: bool = False,
    category: Optional[str] = None,
    confidence: Optional[float] = None,
    description: Optional[str] = None,
    background_color: Optional[str] = None,
    raw_content: Optional[str] = None
) -> dict:
    """
    创建缓存查询结果结构
    
    Args:
        index: 图片索引
        image_hash: 图片哈希
        image_uri: 图片URI
        cached: 是否有缓存
        category: 分类结果
        confidence: 置信度
        description: 描述
        background_color: 背景颜色
        raw_content: 原始响应内容
        
    Returns:
        缓存项字典
    """
    return {
        "index": index,
        "image_uri": image_uri,
        "image_hash": image_hash,
        "cached": cached,
        "category": category,
        "confidence": confidence,
        "description": description,
        "background_color": background_color,
        "raw_content": raw_content
    }


def _detect_qrcode(image_bytes: bytes) -> bool:
    """
    检测图片是否包含二维码（优化：对大图进行缩放以提升性能）
    
    Args:
        image_bytes: 图片二进制数据
        
    Returns:
        是否包含二维码
    """
    if not QRCODE_DETECTION_AVAILABLE:
        return False
        
    try:
        # 使用PIL加载图片
        img = Image.open(io.BytesIO(image_bytes))
        
        # 转换为RGB模式（pyzbar需要）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 对大图进行缩放以提升检测性能（二维码检测不需要高分辨率）
        # 如果图片最大边超过1024px，缩放到1024px
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            logger.debug(f"二维码检测-图片已缩放: {img.size[0]}x{img.size[1]}")
        
        # 检测二维码
        decoded_objects = pyzbar_decode(img)
        if len(decoded_objects) > 0:
            logger.info(f"✅ 检测到二维码: {len(decoded_objects)} 个")
            return True
        
        return False
        
    except Exception as e:
        logger.debug(f"二维码检测异常: {e}")
        return False


async def _classify_single_image(
    image_bytes: bytes,
    image_hash: Optional[str],
    image_uri: Optional[str],
    prompt: str,
    user_id: Optional[str],
    openid: Optional[str],
    ip_address: Optional[str],
    index: int
) -> dict:
    """
    处理单张图片的分类（内部函数）
    
    Returns:
        包含分类结果和元数据的字典
    """
    item_start_time = time.time()
    
    try:
        # 使用客户端提供的hash（基于原图计算）
        # 注意：服务器收到的图片是压缩后的，所以应该使用客户端提供的原图hash来查询缓存
        # 如果客户端没有提供hash，则基于压缩后的图片计算（向后兼容）
        if not image_hash:
            image_hash = HashUtils.calculate_sha256(image_bytes)
        
        # 1. 先检测二维码（在调用LLM之前快速检测）
        has_qrcode = _detect_qrcode(image_bytes)
        if has_qrcode:
            processing_time = int((time.time() - item_start_time) * 1000)
            return _create_classify_result(
                index=index,
                image_uri=image_uri,
                category="qrcode",
                confidence=1.0,
                description="检测到二维码",
                inference_method="qrcode_detection",
                processing_time_ms=processing_time
            )
        
        # 2. 调用LLM（内部会处理缓存查询和响应解析）
        # 传入客户端提供的hash（基于原图），用于查询缓存
        llm_result = await llm_service.classify_image(
            image_bytes=image_bytes,
            prompt=prompt,
            use_cache=True,  # llm_service内部会处理缓存
            image_hash=image_hash  # 使用客户端提供的原图hash
        )
        
        processing_time = int((time.time() - item_start_time) * 1000)
        
        if not llm_result.get('success'):
            # LLM调用失败
            error_info = llm_result.get('error', {})
            return _create_classify_result(
                index=index,
                image_uri=image_uri,
                error=error_info.get('user_message', 'LLM调用失败'),
                inference_method="llm",
                processing_time_ms=processing_time
            )
        
        # 3. 记录用户照片关系（分类成功时）
        # user_photos_service内部会自动查询openid（如果未提供）
        if user_id and image_hash:
            try:
                await user_photos_service.upsert_user_photo(
                    user_id=user_id,
                    openid=openid,  # 如果为None，service内部会从wechat_qrcode_bindings表查询
                    image_hash=image_hash,
                    image_uri=image_uri
                )
            except Exception as e:
                # 记录失败不影响分类结果返回，只记录异常（汇总日志在batch_classify_v2中）
                logger.warning(f"更新user_photos异常 [{index}]: {e}")
        
        # 4. 获取解析后的结果（llm_service已自动解析）
        # 如果使用默认prompt，llm_service会返回parsed_result
        # 如果使用自定义prompt，直接构造结果结构（category=None，使用raw_content）
        parsed_result = llm_result.get('parsed_result')
        if not parsed_result:
            # 自定义prompt，直接构造结果结构
            content = llm_result.get('content', '')
            parsed_result = {
                "category": None,
                "confidence": None,
                "description": None,
                "background_color": None,
                "raw_content": content
            }
        
        # 判断是否来自缓存
        from_cache = llm_result.get('from_cache', False)
        
        return _create_classify_result(
            index=index,
            image_uri=image_uri,
            category=parsed_result.get("category"),
            confidence=parsed_result.get("confidence"),
            description=parsed_result.get("description"),
            background_color=parsed_result.get("background_color"),
            raw_content=parsed_result.get("raw_content"),
            inference_method="cache" if from_cache else "llm",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        processing_time = int((time.time() - item_start_time) * 1000)
        logger.error(f"处理图片失败 [{index}]: {e}", exc_info=True)
        return _create_classify_result(
            index=index,
            image_uri=image_uri,
            error=str(e),
            inference_method="error",
            processing_time_ms=processing_time
        )


@router.post("/batch", response_model=BatchClassifyResponseV2)
async def batch_classify_v2(
    images: List[UploadFile] = File(..., description="图片文件列表"),
    image_metadata: str = Form(..., description="图片元数据JSON字符串"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_openid: Optional[str] = Header(None, alias="X-OpenID"),
    request: Request = None
):
    """
    批量图片分类接口（v2版本）
    
    特点：
    - 只提供批量接口，不提供单张接口
    - 使用v2版本的llm_service和unified_llm_cache
    - 支持自定义分类提示词
    - 统计用户分类图片张数（不统计类别分布）
    - 最多支持50张图片
    
    请求格式：
    - images: 图片文件列表
    - image_metadata: JSON字符串，格式：
      {
        "items": [
          {"index": 0, "image_uri": "uri1", "image_hash": "hash1"},
          {"index": 1, "image_uri": "uri2", "image_hash": null}
        ],
        "prompt": "optional",
        "user_id": "optional"
      }
    """
    batch_request_id = IDGenerator.generate_request_id("batch_classify")
    batch_start_time = time.time()
    user_id = None
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=batch_request_id,
            endpoint="/api/v2/classify/batch",
            method="POST",
            user_id=None,  # 稍后获取
            ip_address=ip_address,
            params={"image_count": len(images)}
        )
        
        # 1. 参数验证
        max_images = 20
        if len(images) > max_images:
            RequestLogger.log_error(
                batch_request_id,
                Exception(f"图片数量超限: {len(images)}"),
                "/api/v2/classify/batch",
                None,
                "image_count_exceeded",
                image_count=len(images),
                max_images=max_images
            )
            raise HTTPException(
                status_code=400,
                detail=f"一次最多上传{max_images}张图片，当前: {len(images)}"
            )
        
        # 2. 解析image_metadata
        try:
            request_obj = BatchClassifyV2Request.model_validate_json(image_metadata)
        except Exception as e:
            # 记录详细的错误信息，包括原始JSON内容（截取前500字符）
            error_detail = str(e)
            json_preview = image_metadata[:500] if len(image_metadata) > 500 else image_metadata
            RequestLogger.log_error(
                batch_request_id, 
                e, 
                "/api/v2/classify/batch", 
                None, 
                "metadata_parse_failed",
                error_detail=error_detail,
                json_preview=json_preview
            )
            # 如果是Pydantic验证错误，提供更友好的错误信息
            if hasattr(e, 'errors'):
                # Pydantic ValidationError
                error_messages = []
                for err in e.errors():
                    field_path = ' -> '.join(str(loc) for loc in err['loc'])
                    error_messages.append(f"{field_path}: {err['msg']}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"image_metadata格式错误: {'; '.join(error_messages)}"
                )
            else:
                raise HTTPException(status_code=400, detail=f"image_metadata格式错误: {error_detail}")
        
        items = request_obj.items
        prompt = request_obj.prompt
        
        # 验证items数组
        if len(items) != len(images):
            RequestLogger.log_error(
                batch_request_id,
                Exception(f"图片数量与元数据数量不匹配"),
                "/api/v2/classify/batch",
                None,
                "items_count_mismatch",
                image_count=len(images),
                items_count=len(items)
            )
            raise HTTPException(
                status_code=400,
                detail=f"图片数量({len(images)})与元数据数量({len(items)})不匹配"
            )
        
        # 3. 处理prompt（如果未提供则使用默认prompt）
        classification_prompt = prompt or settings.CLASSIFICATION_PROMPT
        
        # 4. 获取用户信息（优先使用请求体中的user_id，否则使用Header）
        # 注意：不使用客户端提供的openid（安全考虑），由user_photos_service从数据库查询
        user_id = request_obj.user_id or x_user_id
        
        # 合并日志：参数验证、元数据解析、prompt处理、用户信息获取、开始处理
        RequestLogger.log_step(
            batch_request_id,
            "batch_classify_init",
            f"批量分类初始化: 图片数量={len(images)}, 提示词={'自定义' if prompt else '默认'}, 开始并行处理 {len(items)} 张图片",
            user_id=user_id
        )
        
        # 6. 处理每张图片
        tasks = []
        for index, image in enumerate(images):
            # 读取图片数据
            image_bytes = await image.read()
            
            # 验证图片
            is_valid, error_msg = ImageUtils.validate_image(image_bytes)
            if not is_valid:
                # 验证失败，直接返回错误结果
                item_meta = items[index] if index < len(items) else None
                tasks.append(_create_classify_result(
                    index=index,
                    image_uri=item_meta.image_uri if item_meta else None,
                    error=error_msg,
                    inference_method=None,  # 验证失败，未进行推理
                    processing_time_ms=0
                ))
                continue
            
            # 标准化图片格式
            try:
                image_bytes = ImageUtils.normalize_image_format(image_bytes)
            except Exception as e:
                item_meta = items[index] if index < len(items) else None
                tasks.append(_create_classify_result(
                    index=index,
                    image_uri=item_meta.image_uri if item_meta else None,
                    error=f"图片格式标准化失败: {str(e)}",
                    inference_method="format_error",
                    processing_time_ms=0
                ))
                continue
            
            # 获取对应的元数据
            item_meta = items[index]
            
            # 使用客户端提供的hash（基于原图计算）
            # 注意：服务器收到的图片是压缩后的，所以应该使用客户端提供的原图hash来查询缓存
            # 如果客户端没有提供hash，则基于压缩后的图片计算（向后兼容）
            image_hash = item_meta.image_hash if item_meta.image_hash else HashUtils.calculate_sha256(image_bytes)
            
            image_uri = item_meta.image_uri
            
            # 创建分类任务（llm_service会自动判断是否解析JSON）
            task = _classify_single_image(
                image_bytes=image_bytes,
                image_hash=image_hash,
                image_uri=image_uri,
                prompt=classification_prompt,
                user_id=user_id,
                openid=None,  # 不使用客户端提供的openid，由user_photos_service从数据库查询
                ip_address=ip_address,
                index=index
            )
            
            tasks.append(task)
        
        # 7. 执行任务（并行处理）
        # 日志已在初始化阶段输出，这里不再重复
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # 处理异常
        processed_results = []
        exception_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                exception_count += 1
                RequestLogger.log_error(
                    batch_request_id,
                    result,
                    "/api/v2/classify/batch",
                    user_id,
                    "image_processing_exception",
                    image_index=i
                )
                item_meta = items[i] if i < len(items) else None
                processed_results.append(_create_classify_result(
                    index=i,
                    image_uri=item_meta.image_uri if item_meta else None,
                    error=str(result),
                    inference_method="error",
                    processing_time_ms=0
                ))
            else:
                processed_results.append(result)
        results = processed_results
        
        if exception_count > 0:
            RequestLogger.log_step(batch_request_id, "process_images", f"处理完成，发现 {exception_count} 个异常", user_id=user_id)
        
        # 8. 汇总统计
        # 注意：user_photos记录已在_classify_single_image函数中完成（分类成功时自动记录）
        total_count = len(images)
        success_count = sum(1 for r in results if not r.get('error'))
        failed_count = total_count - success_count
        cached_count = sum(1 for r in results if r.get('inference_method') == 'cache')
        llm_count = sum(1 for r in results if not r.get('error') and r.get('inference_method') == 'llm')
        total_time_ms = int((time.time() - batch_start_time) * 1000)
        
        RequestLogger.log_step(
            batch_request_id,
            "summary",
            f"统计完成: 总数={total_count}, 成功={success_count}, 失败={failed_count}, 缓存={cached_count}, LLM={llm_count}",
            user_id=user_id
        )
        
        # 10. 记录统一日志（统计用户分类图片张数）
        RequestLogger.log_step(batch_request_id, "log_stats", "记录统计日志", user_id=user_id)
        try:
            await stats_service.log_unified_request(
                request_id=batch_request_id,
                request_type='batch_classify_v2',
                ip_address=ip_address,
                client_id=user_id,
                openid=None,  # 不使用客户端提供的openid
                total_images=success_count,  # 用户实际成功分类的图片张数
                cached_count=cached_count,
                llm_count=llm_count,
                local_count=0  # v2版本不使用本地推理
            )
        except Exception as e:
            RequestLogger.log_error(batch_request_id, e, "/api/v2/classify/batch", user_id, "stats_log_failed")
        
        # 11. 构造响应
        response_items = [
            BatchClassifyItemV2(**result) for result in results
        ]
        
        response = BatchClassifyResponseV2(
            error_type=InternalErrorType.SUCCESS,
            error=None,
            results=response_items,
            summary=BatchSummary(
                total_count=total_count,
                success_count=success_count,
                failed_count=failed_count,
                cached_count=cached_count,
                llm_count=llm_count,
                total_time_ms=total_time_ms
            ),
            request_id=batch_request_id
        )
        
        # 记录响应
        RequestLogger.log_response(
            request_id=batch_request_id,
            endpoint="/api/v2/classify/batch",
            status_code=200,
            user_id=user_id,
            response_time_ms=total_time_ms,
            total_count=total_count,
            success_count=success_count,
            cached_count=cached_count,
            llm_count=llm_count
        )
        
        return response
        
    except HTTPException as e:
        # 参数验证错误等客户端错误，继续抛出
        RequestLogger.log_error(
            batch_request_id,
            e,
            "/api/v2/classify/batch",
            user_id,
            "http_exception",
            status_code=e.status_code,
            detail=e.detail
        )
        response_time_ms = int((time.time() - batch_start_time) * 1000)
        RequestLogger.log_response(
            request_id=batch_request_id,
            endpoint="/api/v2/classify/batch",
            status_code=e.status_code,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        raise
    except Exception as e:
        # 内部服务异常（如数据库连接失败），返回error_type为具体错误类型
        error_type, error_msg = _classify_internal_error(e)
        RequestLogger.log_error(
            batch_request_id,
            e,
            "/api/v2/classify/batch",
            user_id,
            error_type.value
        )
        return BatchClassifyResponseV2(
            error_type=error_type,
            error=f"内部服务异常: {error_msg}",
            results=[],
            summary=BatchSummary(
                total_count=0,
                success_count=0,
                failed_count=0,
                cached_count=0,
                llm_count=0,
                total_time_ms=0
            ),
            request_id=batch_request_id
        )


@router.post("/batch-check-cache", response_model=BatchCheckCacheV2Response)
async def batch_check_cache_v2(
    request_body: BatchCheckCacheV2Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_openid: Optional[str] = Header(None, alias="X-OpenID"),
    request: Request = None
):
    """
    批量查询缓存接口（v2版本）
    
    一次性检查多个图片哈希的缓存状态
    最多支持200个哈希
    """
    request_id = IDGenerator.generate_request_id("batch_cache")
    start_time = time.time()
    user_id = None
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint="/api/v2/classify/batch-check-cache",
            method="POST",
            user_id=None,  # 稍后获取
            ip_address=ip_address,
            params={"items_count": len(request_body.items) if request_body.items else 0}
        )
        
        # 1. 参数验证
        items_count = len(request_body.items) if request_body.items else 0
        if not request_body.items:
            RequestLogger.log_error(
                request_id,
                Exception("items不能为空"),
                "/api/v2/classify/batch-check-cache",
                None,
                "empty_items"
            )
            raise HTTPException(status_code=400, detail="items不能为空")
        
        if len(request_body.items) > 200:
            RequestLogger.log_error(
                request_id,
                Exception(f"items数量超限: {len(request_body.items)}"),
                "/api/v2/classify/batch-check-cache",
                None,
                "items_count_exceeded",
                items_count=len(request_body.items)
            )
            raise HTTPException(status_code=400, detail="最多支持200个哈希")
        
        # 验证每个item都有image_hash
        for item in request_body.items:
            if not item.image_hash:
                RequestLogger.log_error(
                    request_id,
                    Exception("item缺少image_hash"),
                    "/api/v2/classify/batch-check-cache",
                    None,
                    "missing_image_hash",
                    item_index=item.index
                )
                raise HTTPException(status_code=400, detail="每个item必须包含image_hash")
        
        # 2. 处理prompt
        prompt = request_body.prompt or settings.CLASSIFICATION_PROMPT
        
        # 3. 获取用户信息
        # 注意：不使用客户端提供的openid（安全考虑）
        user_id = x_user_id or request_body.user_id
        
        # 合并日志：参数验证、prompt处理、用户信息获取、缓存查询开始
        RequestLogger.log_step(
            request_id, 
            "batch_cache_init", 
            f"批量缓存查询初始化: items数量={items_count}, 提示词={'自定义' if request_body.prompt else '默认'}, 开始查询 {items_count} 个哈希",
            user_id=user_id
        )
        # 批量查询缓存的逻辑保留在这里，循环调用llm_service的单张图片缓存查询接口
        # 数据库连接池大小为10，最大溢出5，总共15个连接，限制并发为10个
        max_concurrent_cache_queries = 10
        semaphore = asyncio.Semaphore(max_concurrent_cache_queries)
        
        async def check_cache_with_limit(item: ImageMetadataItem):
            """带并发限制的缓存查询"""
            async with semaphore:
                # 注意：这里使用客户端提供的 image_hash
                # 如果客户端 hash 不正确，会导致缓存查询失败
                # 而 batch 接口使用服务端计算的 hash，所以可能命中缓存
                return await llm_service.check_cache(prompt=prompt, image_hash=item.image_hash)
        
        cache_tasks = [
            check_cache_with_limit(item) for item in request_body.items
        ]
        
        cached_results_list = await asyncio.gather(*cache_tasks, return_exceptions=True)
        
        # 5. 构造结果列表并批量更新 user_photos（缓存命中时）
        results = []
        exception_count = 0
        user_photos_tasks = []  # 收集需要更新 user_photos 的任务
        
        for i, item in enumerate(request_body.items):
            cached_result = cached_results_list[i] if i < len(cached_results_list) else None
            
            # 处理异常情况
            if isinstance(cached_result, Exception):
                exception_count += 1
                RequestLogger.log_error(
                    request_id,
                    cached_result,
                    "/api/v2/classify/batch-check-cache",
                    user_id,
                    "cache_query_exception",
                    image_hash=item.image_hash[:16] if item.image_hash else None,
                    item_index=item.index
                )
                cached_result = None
            
            if cached_result:
                # check_cache已经根据service_type做了解析
                cached_content = cached_result.get('content')
                parsed_result = cached_result.get('parsed_result', {})
                
                # 缓存命中时，如果 user_id 存在，收集更新 user_photos 的任务（批量处理）
                # 如果记录不存在，插入新记录（first_seen_at 会自动设置）
                # 如果记录存在，更新 classify_count 和 last_seen_at（first_seen_at 保持不变）
                if user_id and item.image_hash:
                    user_photos_tasks.append(
                        user_photos_service.upsert_user_photo(
                            user_id=user_id,
                            openid=None,  # 不使用客户端提供的openid，由service内部从数据库查询
                            image_hash=item.image_hash,
                            image_uri=item.image_uri
                        )
                    )
                    logger.debug(f"收集user_photos更新任务 [{i}]: user_id={user_id}, image_hash={item.image_hash[:16] if item.image_hash else 'None'}...")
                else:
                    logger.debug(f"跳过user_photos更新任务 [{i}]: user_id={user_id or 'None'}, image_hash={item.image_hash[:16] if item.image_hash else 'None'}...")
                
                results.append(_create_cache_item(
                    index=item.index,
                    image_hash=item.image_hash,
                    image_uri=item.image_uri,
                    cached=True,
                    category=parsed_result.get('category'),  # 如果解析了就有，否则None
                    confidence=parsed_result.get('confidence'),
                    description=parsed_result.get('description'),
                    background_color=parsed_result.get('background_color'),
                    raw_content=parsed_result.get('raw_content', cached_content)  # 优先使用parsed_result中的raw_content
                ))
            else:
                results.append(_create_cache_item(
                    index=item.index,
                    image_hash=item.image_hash,
                    image_uri=item.image_uri,
                    cached=False
                ))
        
        if exception_count > 0:
            RequestLogger.log_step(request_id, "check_cache", f"缓存查询完成，发现 {exception_count} 个异常", user_id=user_id)
        
        # 6. 汇总统计（先统计，再输出日志）
        cached_count = sum(1 for r in results if r['cached'])
        miss_count = len(results) - cached_count
        
        # 输出关键信息：缓存命中数量（在更新user_photos之前）
        logger.info(f"缓存查询完成: 总数={len(results)}, 命中={cached_count}, 未命中={miss_count}")
        RequestLogger.log_step(
            request_id,
            "summary",
            f"统计完成: 总数={len(results)}, 命中={cached_count}, 未命中={miss_count}",
            user_id=user_id
        )
        
        # 7. 批量更新 user_photos（针对缓存命中的记录，并发执行，失败不影响结果返回）
        if user_photos_tasks:
            try:
                logger.info(f"开始批量更新 user_photos: {len(user_photos_tasks)} 条记录（缓存命中）")
                results_list = await asyncio.gather(*user_photos_tasks, return_exceptions=True)
                
                # 检查每个任务的结果
                success_count = 0
                fail_count = 0
                for idx, result in enumerate(results_list):
                    if isinstance(result, Exception):
                        fail_count += 1
                        logger.warning(f"user_photos更新任务 [{idx}] 失败: {result}")
                    elif result is False:
                        fail_count += 1
                        logger.warning(f"user_photos更新任务 [{idx}] 返回False")
                    else:
                        success_count += 1
                
                logger.info(f"批量更新 user_photos 完成: 成功={success_count}, 失败={fail_count}, 总数={len(user_photos_tasks)}")
            except Exception as e:
                logger.warning(f"批量更新 user_photos 异常: {e}")
        else:
            logger.debug(f"没有user_photos更新任务（user_photos_tasks为空）")
        
        # 8. 记录统一日志
        RequestLogger.log_step(request_id, "log_stats", "记录统计日志", user_id=user_id)
        try:
            await stats_service.log_unified_request(
                request_id=request_id,
                request_type='batch_cache_v2',
                ip_address=ip_address,
                client_id=user_id,
                openid=None,  # 不使用客户端提供的openid
                total_images=len(request_body.items),
                cached_count=cached_count,
                llm_count=0,
                local_count=0
            )
        except Exception as e:
            RequestLogger.log_error(request_id, e, "/api/v2/classify/batch-check-cache", user_id, "stats_log_failed")
        
        # 9. 构造响应
        cache_items = [CacheItemV2(**r) for r in results]
        response_time_ms = int((time.time() - start_time) * 1000)
        
        response = BatchCheckCacheV2Response(
            error_type=InternalErrorType.SUCCESS,
            error=None,
            results=cache_items,
            summary={
                "total": len(results),
                "cached_count": cached_count,
                "miss_count": miss_count
            },
            request_id=request_id
        )
        
        # 记录响应
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/classify/batch-check-cache",
            status_code=200,
            user_id=user_id,
            response_time_ms=response_time_ms,
            total=len(results),
            cached_count=cached_count,
            miss_count=miss_count
        )
        
        return response
        
    except HTTPException as e:
        # 参数验证错误等客户端错误，继续抛出
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/classify/batch-check-cache",
            user_id,
            "http_exception",
            status_code=e.status_code,
            detail=e.detail
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/classify/batch-check-cache",
            status_code=e.status_code,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        raise
    except Exception as e:
        # 内部服务异常（如数据库连接失败），返回error_type为具体错误类型
        error_type, error_msg = _classify_internal_error(e)
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/classify/batch-check-cache",
            user_id,
            error_type.value
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/classify/batch-check-cache",
            status_code=500,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        return BatchCheckCacheV2Response(
            error_type=error_type,
            error=f"内部服务异常: {error_msg}",
            results=[],
            summary={
                "total": 0,
                "cached_count": 0,
                "miss_count": 0
            },
            request_id=request_id
        )

