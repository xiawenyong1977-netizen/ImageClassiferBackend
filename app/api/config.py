"""
运行时配置管理接口
支持动态修改配置，无需重启服务
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from app.config import settings
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/config", tags=["config"])


class InferenceConfigUpdate(BaseModel):
    """推理配置更新"""
    use_local_inference: Optional[bool] = Field(None, description="是否使用本地推理")
    local_inference_fallback: Optional[bool] = Field(None, description="大模型失败时是否降级")


class InferenceConfigResponse(BaseModel):
    """推理配置响应"""
    use_local_inference: bool = Field(..., description="是否使用本地推理")
    local_inference_fallback: bool = Field(..., description="大模型失败时是否降级")


@router.get("/inference", response_model=InferenceConfigResponse, summary="获取推理配置")
async def get_inference_config(current_user: str = Depends(get_current_user)):
    """
    获取当前推理配置（需要认证）
    """
    return {
        "use_local_inference": settings.USE_LOCAL_INFERENCE,
        "local_inference_fallback": settings.LOCAL_INFERENCE_FALLBACK
    }


@router.put("/inference", response_model=InferenceConfigResponse, summary="更新推理配置")
async def update_inference_config(
    config: InferenceConfigUpdate,
    current_user: str = Depends(get_current_user)
):
    """
    更新推理配置（需要认证）
    
    运行时动态修改配置，立即生效，无需重启服务
    注意：修改后只在运行时生效，重启后会恢复.env文件中的配置
    """
    try:
        # 动态更新配置
        if config.use_local_inference is not None:
            settings.USE_LOCAL_INFERENCE = config.use_local_inference
            logger.info(f"配置已更新: USE_LOCAL_INFERENCE = {config.use_local_inference} (by {current_user})")
        
        if config.local_inference_fallback is not None:
            settings.LOCAL_INFERENCE_FALLBACK = config.local_inference_fallback
            logger.info(f"配置已更新: LOCAL_INFERENCE_FALLBACK = {config.local_inference_fallback} (by {current_user})")
        
        # 返回当前配置
        return {
            "use_local_inference": settings.USE_LOCAL_INFERENCE,
            "local_inference_fallback": settings.LOCAL_INFERENCE_FALLBACK
        }
        
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inference/reset", summary="重置推理配置")
async def reset_inference_config(current_user: str = Depends(get_current_user)):
    """
    重置推理配置为默认值（需要认证）
    """
    try:
        # 重置为默认值
        settings.USE_LOCAL_INFERENCE = False
        settings.LOCAL_INFERENCE_FALLBACK = True
        
        logger.info(f"配置已重置为默认值 (by {current_user})")
        
        return {
            "success": True,
            "message": "配置已重置",
            "use_local_inference": settings.USE_LOCAL_INFERENCE,
            "local_inference_fallback": settings.LOCAL_INFERENCE_FALLBACK
        }
        
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

