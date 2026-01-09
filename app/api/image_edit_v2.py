"""
图像编辑接口路由（v2版本）
使用 llm_service 和 unified_llm_cache
/api/v2/image-edit/batch - 批量图像编辑（异步任务模式）
/api/v2/image-edit/task/{task_id} - 查询任务状态
"""

from fastapi import APIRouter, File, UploadFile, Form, Header, HTTPException, Request
from typing import Optional, List, Tuple, Dict
import json
import asyncio
import time
from datetime import datetime
import aiomysql

from app.models.schemas_v2 import (
    BatchImageEditV2Request,
    BatchImageEditSubmitResponseV2,
    TaskStatusResponseV2,
    ImageEditResultItem,
    InternalErrorType,
    TaskStatus
)
from app.services.stats_service import stats_service
from app.services.llm import llm_service
from app.services.credit_service import credit_service
from app.services.async_task_service import async_task_service
from app.services.wechat_binding_service import wechat_binding_service
from app.services.credits_usage_service import credits_usage_service
from app.services.unified_llm_cache import unified_llm_cache
from app.utils.hash_utils import HashUtils
from app.utils.image_utils import ImageUtils
from app.utils.id_generator import IDGenerator
from app.utils.request_logger import RequestLogger
from loguru import logger

# 七牛云服务（可选，如果未安装qiniu包则跳过）
try:
    from app.services.qiniu_service import qiniu_service
except ImportError as e:
    logger.warning(f"七牛云服务导入失败，图片上传功能将不可用: {e}")
    qiniu_service = None

router = APIRouter(prefix="/api/v2/image-edit", tags=["image-edit-v2"])


# ========== v2版本任务处理逻辑 ==========

async def _submit_task_async_v2(
    images: List[Dict],
    prompt: str,
    user_id: Optional[str] = None,
    openid: Optional[str] = None,
    request_id: Optional[str] = None
) -> str:
    """
    提交编辑任务（v2版本，使用 llm_service 和 unified_llm_cache）
    
    改进点：
    1. 使用 llm_service.edit_image 统一接口
    2. 缓存由 llm_service 自动处理（使用 unified_llm_cache）
    3. 任务处理过程中会内部批量查询缓存（与分类API不同，图像编辑不提供独立的批量查询缓存接口）
    """
    total_images = len(images)
    
    # 记录请求信息（request_id 在调用时已存在）
    RequestLogger.log_step(
        request_id, 
        "submit_task_start", 
        f"开始提交编辑任务: 图片数={total_images}, prompt={'已提供' if prompt else '未提供'}, user_id={user_id}",
        user_id=user_id
    )
    
    # 参数校验（prompt已在API层校验，这里只做防御性检查）
    if not prompt:
        error_msg = "prompt参数缺失"
        RequestLogger.log_error(request_id, ValueError(error_msg), "_submit_task_async_v2", user_id, "missing_prompt")
        raise ValueError(error_msg)
    
    RequestLogger.log_step(request_id, "validate_params", "参数校验通过", user_id=user_id)
    
    # 生成任务ID
    task_id = IDGenerator.generate_request_id("task")
    RequestLogger.log_step(request_id, "generate_task_id", f"生成任务ID: {task_id}", user_id=user_id)
    
    # 保存任务到数据库（使用通用异步任务服务）
    try:
        await async_task_service.create_task(
            task_id=task_id,
            task_type='image_edit',
            total_items=total_images,
            task_params={'prompt': prompt},
            user_id=user_id,
            openid=openid
        )
        RequestLogger.log_step(request_id, "save_task_to_db", f"任务已保存到数据库: task_id={task_id}", user_id=user_id)
    except Exception as e:
        RequestLogger.log_error(request_id, e, "_submit_task_async_v2", user_id, "save_task_failed")
        raise
    
    # 记录响应信息（任务创建成功）
    RequestLogger.log_step(
        request_id, 
        "task_created", 
        f"任务创建成功(v2): task_id={task_id}, 图片数={total_images}, 已启动后台处理",
        user_id=user_id
    )
    
    # 异步处理任务（不阻塞）
    # 包装一个带超时的任务，避免后台任务无限期卡住
    async def _process_with_timeout():
        """带超时的后台任务包装器"""
        # 动态计算超时时间：基础30秒 + 每张图片20秒（考虑网络延迟和重试）
        # 最多支持9张图片，最大超时时间 = 30 + 9*20 = 210秒（3.5分钟）
        base_timeout = 30.0  # 基础超时时间（秒）
        per_image_timeout = 20.0  # 每张图片的超时时间（秒）
        dynamic_timeout = base_timeout + (total_images * per_image_timeout)
        max_timeout = 300.0  # 最大超时时间（5分钟），防止异常情况
        timeout = min(dynamic_timeout, max_timeout)
        
        logger.info(f"[后台任务] _process_with_timeout开始: task_id={task_id}, 图片数={total_images}, 超时时间={timeout:.1f}秒")
        try:
            import asyncio
            logger.info(f"[后台任务] 准备调用_process_task_async_v2: task_id={task_id}, 超时时间={timeout:.1f}秒")
            await asyncio.wait_for(
                _process_task_async_v2(task_id, images, prompt, openid, request_id),
                timeout=timeout
            )
            logger.info(f"[后台任务] _process_task_async_v2完成: task_id={task_id}")
        except asyncio.TimeoutError:
            logger.error(f"后台任务超时(v2): task_id={task_id}, 图片数={total_images}, 已超过{timeout:.1f}秒")
            # 更新任务状态为失败
            try:
                await async_task_service.update_status(task_id, TaskStatus.FAILED)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"后台任务执行异常(v2): task_id={task_id}, 错误: {e}", exc_info=True)
    
    logger.info(f"[后台任务] 准备创建后台任务: task_id={task_id}")
    asyncio.create_task(_process_with_timeout())
    logger.info(f"[后台任务] 后台任务已创建: task_id={task_id}")
    
    return task_id


async def _process_task_async_v2(
    task_id: str,
    images: List[Dict],
    prompt: str,
    openid: Optional[str] = None,
    request_id: Optional[str] = None
):
    """
    异步处理任务（v2版本，使用 llm_service）
    
    特点：
    1. 使用 llm_service.edit_image（自动处理缓存，无需外部批量查询）
    2. 逐张处理图片，实时更新进度
    """
    logger.info(f"[_process_task_async_v2] 方法开始执行: task_id={task_id}, images_count={len(images)}")
    try:
        logger.info(f"[_process_task_async_v2] 准备更新任务状态为PROCESSING: task_id={task_id}")
        await async_task_service.update_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"[_process_task_async_v2] 任务状态已更新为PROCESSING: task_id={task_id}")
        
        # 1. 初始化结果数组
        all_results = [None] * len(images)
        cache_hit_count = 0
        api_count = 0
        
        # 2. 处理所有图片（llm_service.edit_image 内部会自动处理缓存）
        for index, image_data in enumerate(images):
            logger.info(f"处理第 {index + 1}/{len(images)} 张图片（LLM调用v2）")
            
            try:
                # 使用 llm_service.edit_image（自动处理缓存和错误）
                llm_result = await llm_service.edit_image(
                    image_bytes=image_data['bytes'],
                    prompt=prompt,
                    use_cache=True  # 启用缓存，llm_service 内部会自动查询
                )
                
                if llm_result.get('success'):
                    result_url = llm_result.get('result_url')
                    from_cache = llm_result.get('from_cache', False)
                    
                    # 🔥 v2版本：下载图片并上传到七牛云CDN（生成永久URL）
                    # 如果七牛云服务未启用，则使用原始URL（24小时有效）
                    permanent_url = result_url
                    if result_url and not from_cache and qiniu_service is not None:
                        # 只有非缓存结果才需要上传（缓存的结果已经是永久URL）
                        try:
                            cdn_url = await qiniu_service.upload_image_from_url(
                                image_url=result_url,
                                key_prefix="image-edit",
                                filename=None
                            )
                            if cdn_url:
                                permanent_url = cdn_url
                                logger.info(f"✅ 图片已上传到七牛云CDN: {cdn_url}")
                                
                                # 🔥 更新缓存中的URL为永久URL
                                try:
                                    image_hash = HashUtils.calculate_sha256(image_data['bytes'])
                                    # 构建完整的prompt（包含edit_type，如果有的话）
                                    full_prompt = prompt  # llm_service内部已经处理了edit_type
                                    model_key = f"{llm_service.provider}:{llm_service.model}"
                                    
                                    await unified_llm_cache.save_result(
                                        prompt=full_prompt,
                                        image_hash=image_hash,
                                        provider=llm_service.provider,
                                        model_id=llm_service.model,
                                        result=cdn_url,  # 保存永久URL
                                        service_type="image_edit",
                                        edit_type=None,  # edit_type已包含在prompt中
                                        is_default_prompt=None
                                    )
                                    logger.info(f"✅ 缓存已更新为永久URL: {cdn_url}")
                                except Exception as cache_error:
                                    logger.warning(f"⚠️ 更新缓存失败: {cache_error}")
                                    # 缓存更新失败不影响任务结果
                            else:
                                logger.warning(f"⚠️ 七牛云上传失败，使用原始URL: {result_url[:50]}...")
                        except Exception as e:
                            logger.error(f"❌ 上传图片到七牛云异常: {e}", exc_info=True)
                            # 上传失败时仍使用原始URL，不阻塞任务
                    
                    # 统计缓存命中数
                    if from_cache:
                        cache_hit_count += 1
                    else:
                        api_count += 1
                    
                    all_results[index] = {
                        'index': index,
                        'image_uri': image_data.get('image_uri'),
                        'status': 'completed',
                        'result_url': permanent_url,  # 使用永久URL（七牛云CDN或原始URL）
                        'from_cache': from_cache
                    }
                else:
                    api_count += 1  # 失败也算作API调用（因为可能已经尝试调用）
                    error_info = llm_result.get('error', {})
                    all_results[index] = {
                        'index': index,
                        'image_uri': image_data.get('image_uri'),
                        'status': 'failed',
                        'error': error_info.get('user_message', '编辑失败')
                    }
            except Exception as e:
                api_count += 1  # 异常也算作API调用
                logger.error(f"图片 {index} 处理失败(v2): {e}")
                all_results[index] = {
                    'index': index,
                    'image_uri': image_data.get('image_uri'),
                    'status': 'failed',
                    'error': str(e)
                }
            
            # 同时更新进度和结果（一次数据库调用）
            processed = sum(1 for r in all_results if r and r.get('status') in ('completed', 'failed'))
            await async_task_service.update_task(
                task_id,
                completed_items=processed,
                results=all_results
            )
        
        logger.info(f"处理完成(v2): 缓存命中={cache_hit_count}张, API调用={api_count}张")
        
        # 6. 保存最终结果（数据库操作）
        # 处理完成后，所有图片都应该是 completed 或 failed，所以 processed_count = len(all_results)
        await async_task_service.save_results(task_id, all_results, len(all_results))
        
        # 7. 处理业务逻辑（额度扣减）- 业务层处理
        if openid:
            success_count = len([r for r in all_results if r and r.get('status') == 'completed'])
            cache_count = cache_hit_count  # 使用循环中统计的缓存命中数
            # api_count 已经在循环中统计完成（包括成功和失败的API调用）
            
            if api_count > 0:
                # 使用 credit_service 扣减额度
                for _ in range(api_count):
                    success, msg = await credit_service.check_and_deduct_credit(openid, deduct_on_success=True)
                    if not success:
                        logger.warning(f"扣减额度失败: {msg}")
                
                # 记录额度消耗
                await credits_usage_service.log_usage(
                    openid=openid,
                    task_id=task_id,
                    task_type='image_edit',
                    credits_used=api_count,
                    request_image_count=len(all_results),
                    success_image_count=success_count
                )
                
                logger.info(f"已扣除额度: openid={openid[:16]}..., 扣除={api_count}张(总请求={len(all_results)}张, 成功={success_count}, 缓存={cache_count}, API={api_count})")
            elif cache_count > 0:
                logger.info(f"缓存命中，不扣减额度: openid={openid[:16]}..., 成功={success_count}张全部来自缓存")
        
        # 8. 记录统一日志（图像编辑）
        try:
            task_info = await async_task_service.get_task_status(task_id)
            if task_info:
                await stats_service.log_unified_request(
                    request_id=task_id,
                    request_type='image_edit',
                    ip_address=None,  # 统一任务表不存储ip_address
                    client_id=task_info.get('user_id'),
                    openid=openid,
                    total_images=len(images),
                    cached_count=cache_hit_count,
                    llm_count=api_count,
                    local_count=0
                )
        except Exception as e:
            logger.error(f"记录图像编辑统一日志失败(v2): {e}")
        
    except Exception as e:
        logger.error(f"任务处理失败(v2): {task_id}, 错误: {e}")
        await async_task_service.update_status(task_id, TaskStatus.FAILED)


# ========== API端点 ==========

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


@router.post("/batch", response_model=BatchImageEditSubmitResponseV2)
async def batch_edit_v2(
    images: List[UploadFile] = File(...),
    image_metadata: str = Form(...),  # JSON字符串
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    批量图像编辑（v2版本，异步任务模式）
    
    特点：
    1. 使用 unified_llm_cache（v2版本）进行缓存
    2. 使用 llm_service.edit_image 统一接口
    3. 异步处理，立即返回 task_id
    4. 客户端通过 /task/{task_id} 轮询查询状态
    """
    request_id = IDGenerator.generate_request_id("batch_edit")
    start_time = time.time()
    user_id = None
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint="/api/v2/image-edit/batch",
            method="POST",
            user_id=None,  # 稍后获取
            ip_address=ip_address,
            params={"image_count": len(images)}
        )
        
        # 1. 解析请求参数
        RequestLogger.log_step(request_id, "parse_metadata", "解析图片元数据")
        request_obj = BatchImageEditV2Request.model_validate_json(image_metadata)
        prompt = request_obj.prompt
        
        # 2. 验证参数
        RequestLogger.log_step(request_id, "validate_params", f"验证参数: prompt={'已提供' if prompt else '未提供'}, 图片数量={len(images)}")
        if not prompt:
            RequestLogger.log_error(
                request_id,
                Exception("prompt字段不能为空"),
                "/api/v2/image-edit/batch",
                None,
                "empty_prompt"
            )
            raise HTTPException(status_code=400, detail="prompt字段不能为空")
        
        # 3. 验证图片数量
        if len(images) == 0:
            RequestLogger.log_error(
                request_id,
                Exception("图片数量为0"),
                "/api/v2/image-edit/batch",
                None,
                "no_images"
            )
            raise HTTPException(status_code=400, detail="至少需要1张图片")
        if len(images) > 9:
            RequestLogger.log_error(
                request_id,
                Exception(f"图片数量超限: {len(images)}"),
                "/api/v2/image-edit/batch",
                None,
                "image_count_exceeded",
                image_count=len(images)
            )
            raise HTTPException(status_code=400, detail="最多9张图片")
        
        # 4. 解析 openid（类似 v1，但不强制要求）
        user_id = request_obj.user_id or x_user_id
        RequestLogger.log_step(request_id, "get_user_info", f"获取用户信息: user_id={user_id}")
        openid = await wechat_binding_service.get_openid_by_client_id(user_id) if user_id else None
        
        # 5. 检查额度（如果提供了 openid）
        if openid:
            RequestLogger.log_step(request_id, "check_credit", f"检查用户额度: openid={openid}", user_id=user_id)
            from app.services.credit_service import credit_service
            has_credit, error_msg = await credit_service.check_and_deduct_credit(
                openid, deduct_on_success=False
            )
            if not has_credit:
                RequestLogger.log_error(
                    request_id,
                    Exception(error_msg),
                    "/api/v2/image-edit/batch",
                    user_id,
                    "insufficient_credit",
                    openid=openid
                )
                raise HTTPException(status_code=400, detail=error_msg)
        
        # 6. 读取图片数据
        RequestLogger.log_step(request_id, "read_images", f"开始读取 {len(images)} 张图片", user_id=user_id)
        image_data_list = []
        for idx, img in enumerate(images):
            try:
                image_bytes = await img.read()
                # 验证图片格式和大小
                is_valid, error_msg = ImageUtils.validate_image(image_bytes)
                if not is_valid:
                    RequestLogger.log_error(
                        request_id,
                        Exception(f"图片{idx + 1}验证失败: {error_msg}"),
                        "/api/v2/image-edit/batch",
                        user_id,
                        "image_validation_failed",
                        image_index=idx
                    )
                    raise HTTPException(status_code=400, detail=f"图片{idx + 1}验证失败: {error_msg}")
                
                # 获取对应的 image_uri（从请求的 items 中）
                image_uri = None
                if idx < len(request_obj.items):
                    image_uri = request_obj.items[idx].image_uri
                
                image_data_list.append({
                    'index': idx,
                    'image_uri': image_uri,
                    'bytes': image_bytes
                })
            except HTTPException:
                raise
            except Exception as e:
                RequestLogger.log_error(
                    request_id,
                    e,
                    "/api/v2/image-edit/batch",
                    user_id,
                    "image_read_failed",
                    image_index=idx
                )
                raise HTTPException(status_code=400, detail=f"读取图片失败: {img.filename if img.filename else f'index_{idx}'}")
        
        RequestLogger.log_step(request_id, "read_images", f"图片读取完成: {len(image_data_list)} 张", user_id=user_id)
        
        # 7. 提交异步任务（使用 v2 版本的处理逻辑）
        RequestLogger.log_step(request_id, "submit_task", "提交异步任务", user_id=user_id)
        task_id = await _submit_task_async_v2(
            image_data_list, prompt, user_id, openid, request_id
        )
        RequestLogger.log_step(request_id, "submit_task", f"任务提交成功: task_id={task_id}", user_id=user_id)
        
        # 8. 注意：不在这里记录统计日志
        # 统计日志会在任务完成时记录（_process_task_async_v2函数中，request_type='image_edit'）
        # 这样可以避免重复记录，因为统计时只统计 image_edit（任务完成时的记录）
        
        response = BatchImageEditSubmitResponseV2(
            error_type=InternalErrorType.SUCCESS,
            task_id=task_id,
            total_images=len(image_data_list),
            request_id=request_id
        )
        
        # 记录响应
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/image-edit/batch",
            status_code=200,
            user_id=user_id,
            response_time_ms=response_time_ms,
            task_id=task_id,
            total_images=len(image_data_list)
        )
        
        return response
        
    except HTTPException as e:
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/image-edit/batch",
            user_id,
            "http_exception",
            status_code=e.status_code,
            detail=e.detail
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/image-edit/batch",
            status_code=e.status_code,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        raise
    except Exception as e:
        error_type, error_msg = _classify_internal_error(e)
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/image-edit/batch",
            user_id,
            error_type.value
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/image-edit/batch",
            status_code=500,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        return BatchImageEditSubmitResponseV2(
            error_type=error_type,
            error=error_msg,
            task_id="",
            total_images=0,
            request_id=request_id
        )


@router.get("/task/{task_id}", response_model=TaskStatusResponseV2)
async def get_task_status_v2(task_id: str, request: Request = None):
    """
    查询任务状态（v2版本）
    
    特点：
    1. 简化响应结构（移除 progress 字段，客户端可根据 completed_images/total_images 计算）
    2. 统一错误处理
    """
    request_id = IDGenerator.generate_request_id("task_status")
    start_time = time.time()
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint=f"/api/v2/image-edit/task/{task_id}",
            method="GET",
            user_id=None,
            ip_address=ip_address,
            params={"task_id": task_id}
        )
        
        RequestLogger.log_step(request_id, "get_task_status", f"查询任务状态: task_id={task_id}")
        status = await async_task_service.get_task_status(task_id)
        if not status:
            RequestLogger.log_error(
                request_id,
                Exception("任务不存在"),
                f"/api/v2/image-edit/task/{task_id}",
                None,
                "task_not_found",
                task_id=task_id
            )
            raise HTTPException(status_code=404, detail="任务不存在")
        
        RequestLogger.log_step(request_id, "format_response", f"格式化响应: status={status.get('status')}")
        
        # 格式化时间
        created_at = status['created_at']
        updated_at = status['updated_at']
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()
        
        # 转换 results 为 Pydantic 模型列表
        results_list = []
        results = status.get('results') or []  # 如果 results 为 None，使用空列表
        for result in results:
            if isinstance(result, dict):
                # 确保所有字段都存在（处理可能缺失的字段）
                # 兼容旧格式（可能有 filename），优先使用 image_uri
                result_dict = {
                    'index': result.get('index', 0),
                    'image_uri': result.get('image_uri'),  # v2版本使用 image_uri
                    'status': result.get('status', 'processing'),
                    'result_url': result.get('result_url'),
                    'error': result.get('error'),
                    'from_cache': result.get('from_cache')
                }
                results_list.append(ImageEditResultItem(**result_dict))
            else:
                # 如果已经是 Pydantic 模型，直接添加
                results_list.append(result)
        
        response = TaskStatusResponseV2(
            task_id=status['task_id'],
            status=status['status'],
            total_images=status['total_items'],  # 统一任务表使用 total_items
            completed_images=status['completed_items'],  # 统一任务表使用 completed_items
            results=results_list,
            created_at=created_at,
            updated_at=updated_at
        )
        
        # 记录响应
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint=f"/api/v2/image-edit/task/{task_id}",
            status_code=200,
            user_id=None,
            response_time_ms=response_time_ms,
            task_id=task_id,
            task_status=status['status'],
            total_images=status['total_items'],
            completed_images=status['completed_items']
        )
        
        return response
    except HTTPException as e:
        RequestLogger.log_error(
            request_id,
            e,
            f"/api/v2/image-edit/task/{task_id}",
            None,
            "http_exception",
            status_code=e.status_code,
            detail=e.detail
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint=f"/api/v2/image-edit/task/{task_id}",
            status_code=e.status_code,
            user_id=None,
            response_time_ms=response_time_ms
        )
        raise
    except Exception as e:
        RequestLogger.log_error(
            request_id,
            e,
            f"/api/v2/image-edit/task/{task_id}",
            None,
            "query_task_failed"
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint=f"/api/v2/image-edit/task/{task_id}",
            status_code=500,
            user_id=None,
            response_time_ms=response_time_ms
        )
        raise HTTPException(status_code=500, detail=str(e))

