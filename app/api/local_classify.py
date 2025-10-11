"""
本地模型分类接口路由
/api/v1/local-classify - 使用本地ONNX模型进行图片分类
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Header
from typing import Optional
from datetime import datetime
import time

from app.models.schemas import ClassificationResponse, ClassificationData, ErrorResponse
from app.services.local_model_inference import local_model_inference
from app.services.stats_service import stats_service
from app.utils.image_utils import ImageUtils
from app.utils.hash_utils import HashUtils
from app.utils.id_generator import IDGenerator
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["local-classify"])


@router.post("/local-classify")
async def classify_image_local(
    image: UploadFile = File(..., description="图片文件"),
    request: Request = None
):
    """
    本地模型图片分类接口（简化版）
    
    使用本地ONNX模型进行推理，返回原始检测结果
    支持三个模型：ID卡识别、YOLO8s通用检测、MobileNetV3图像分类
    
    注意：
    - 只返回原始检测结果，不包含categoryId（由客户端映射）
    - 推荐使用 /local-classify/detailed 接口获取完整信息
    """
    try:
        # 读取图片数据
        image_bytes = await image.read()
        
        # 验证图片
        is_valid, error_msg = ImageUtils.validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 确保模型已初始化
        if not local_model_inference.is_initialized:
            logger.info("🚀 首次调用，初始化本地模型...")
            await local_model_inference.initialize()
        
        # 使用本地模型进行推理
        result = await local_model_inference.classify_image(image_bytes)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        # 返回简化结果
        return {
            "success": True,
            "message": result['message'],
            "idCardDetections": result['idCardDetections'],
            "generalDetections": result['generalDetections'],
            "mobileNetV3Detections": result['mobileNetV3Detections'],
            "timestamp": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"本地模型分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/local-classify/detailed", summary="本地模型分类（详细结果）")
async def classify_image_local_detailed(
    image: UploadFile = File(..., description="图片文件"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    request: Request = None
):
    """
    本地模型图片分类接口（返回详细检测结果）
    
    返回所有模型的检测结果，包括：
    - ID卡检测结果
    - YOLO8s通用检测结果
    - MobileNetV3分类结果
    
    注意：
    - 不返回 categoryId（由客户端根据检测结果映射）
    - 不返回 imageDimensions（客户端提供原始尺寸）
    - 会记录统计数据（推理方式为 'local_test'）
    """
    try:
        # 读取图片数据
        image_bytes = await image.read()
        
        # 验证图片
        is_valid, error_msg = ImageUtils.validate_image(image_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 生成请求ID和计算哈希
        request_id = IDGenerator.generate_request_id()
        image_hash = HashUtils.calculate_sha256(image_bytes)
        image_size = len(image_bytes)
        user_id = x_user_id or "admin_test"
        ip_address = request.client.host if request else None
        
        start_time = time.time()
        
        # 确保模型已初始化
        if not local_model_inference.is_initialized:
            logger.info("🚀 首次调用，初始化本地模型...")
            await local_model_inference.initialize()
        
        # 使用本地模型进行推理
        result = await local_model_inference.classify_image(image_bytes)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        # 记录统计数据
        await stats_service.log_request(
            request_id=request_id,
            user_id=user_id,
            ip_address=ip_address,
            image_hash=image_hash,
            image_size=image_size,
            category="local_test",  # 标记为测试
            confidence=0.8,
            from_cache=False,
            processing_time_ms=processing_time,
            inference_method="local_test"  # 管理后台测试
        )
        
        logger.info(f"本地模型测试完成 [{request_id}]: {processing_time}ms")
        
        # 返回原始检测结果
        return {
            "success": True,
            "message": result['message'],
            "details": {
                "idCardDetections": result['idCardDetections'],
                "generalDetections": result['generalDetections'],
                "mobileNetV3Detections": result['mobileNetV3Detections']
            },
            "processing_time_ms": processing_time,
            "request_id": request_id,
            "timestamp": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"本地模型分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local-classify/models", summary="获取本地模型状态")
async def get_local_models_status():
    """
    获取本地模型加载状态
    """
    try:
        return {
            "initialized": local_model_inference.is_initialized,
            "models": {
                name: {
                    "loaded": name in local_model_inference.models,
                    "path": path
                }
                for name, path in local_model_inference.model_paths.items()
            },
            "total_models": len(local_model_inference.model_paths),
            "loaded_models": len(local_model_inference.models)
        }
    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

