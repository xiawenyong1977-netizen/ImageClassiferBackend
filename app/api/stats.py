"""
统计接口路由
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from app.models.schemas import (
    TodayStatsResponse,
    CacheEfficiencyResponse,
    CategoryDistributionResponse
)
from app.services.stats_service import stats_service
from app.auth import get_current_user
from loguru import logger

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/today", response_model=TodayStatsResponse)
async def get_today_stats(current_user: str = Depends(get_current_user)):
    """获取今日统计（需要认证）"""
    try:
        stats = await stats_service.get_today_stats()
        return TodayStatsResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取今日统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-efficiency", response_model=CacheEfficiencyResponse)
async def get_cache_efficiency(current_user: str = Depends(get_current_user)):
    """获取缓存效率统计（需要认证）"""
    try:
        stats = await stats_service.get_cache_efficiency()
        return CacheEfficiencyResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"获取缓存效率失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category-distribution", response_model=CategoryDistributionResponse)
async def get_category_distribution(current_user: str = Depends(get_current_user)):
    """获取分类分布（需要认证）"""
    try:
        distribution = await stats_service.get_category_distribution()
        return CategoryDistributionResponse(success=True, data=distribution)
    except Exception as e:
        logger.error(f"获取分类分布失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inference-method", summary="获取推理方式统计")
async def get_inference_method_stats(current_user: str = Depends(get_current_user)):
    """获取推理方式统计（需要认证）"""
    try:
        stats = await stats_service.get_inference_method_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取推理方式统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-cache", summary="获取批量缓存查询统计")
async def get_batch_cache_stats(
    days: int = 7,
    current_user: str = Depends(get_current_user)
):
    """
    获取批量缓存查询统计（需要认证）
    
    Args:
        days: 查询最近几天的数据，默认7天
    """
    try:
        stats = await stats_service.get_batch_cache_stats(days=days)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取批量缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-classify", summary="获取批量分类统计")
async def get_batch_classify_stats(
    days: int = 7,
    current_user: str = Depends(get_current_user)
):
    """
    获取批量分类统计（需要认证）
    
    Args:
        days: 查询最近几天的数据，默认7天
    """
    try:
        stats = await stats_service.get_batch_classify_stats(days=days)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取批量分类统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image-edit", summary="获取图片编辑统计")
async def get_image_edit_stats(
    days: int = 7,
    current_user: str = Depends(get_current_user)
):
    """
    获取图片编辑统计（需要认证）
    
    Args:
        days: 查询最近几天的数据，默认7天
    """
    try:
        stats = await stats_service.get_image_edit_stats(days=days)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取图片编辑统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-count", summary="获取下载量统计")
async def get_download_count(
    download_type: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """
    获取下载量统计（需要认证）
    
    Args:
        download_type: 下载类型（android、windows），如果为空则返回所有类型的统计
    """
    try:
        stats = await stats_service.get_download_count(download_type)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"获取下载量统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-count/increment", summary="增加下载量")
async def increment_download_count(
    download_type: str,
    current_user: str = Depends(get_current_user)
):
    """
    增加下载量（+1）（需要认证）
    
    Args:
        download_type: 下载类型（android、windows）
    """
    try:
        if download_type not in ['android', 'windows']:
            raise HTTPException(status_code=400, detail="download_type必须是android或windows")
        
        success = await stats_service.increment_download_count(download_type)
        if success:
            stats = await stats_service.get_download_count()
            return {"success": True, "data": stats}
        else:
            raise HTTPException(status_code=500, detail="增加下载量失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"增加下载量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-count/increment/public", summary="增加下载量（公开接口）")
async def increment_download_count_public(
    download_type: str,
    request: Request = None
):
    """
    增加下载量（+1）（公开接口，无需认证，供官网调用）
    
    Args:
        download_type: 下载类型（android、windows）
    """
    try:
        if download_type not in ['android', 'windows']:
            raise HTTPException(status_code=400, detail="download_type必须是android或windows")
        
        # 可选：添加简单的频率限制或IP验证
        # 这里暂时不做限制，如果后续需要可以添加
        
        success = await stats_service.increment_download_count(download_type)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="增加下载量失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"增加下载量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bound-users-count", summary="获取已绑定用户数统计")
async def get_bound_users_count(current_user: str = Depends(get_current_user)):
    """获取已绑定用户数统计（按openid去重）（需要认证）"""
    try:
        count = await stats_service.get_bound_users_count()
        return {"success": True, "data": {"bound_users_count": count}}
    except Exception as e:
        logger.error(f"获取已绑定用户数统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/member-count", summary="获取会员数量统计")
async def get_member_count(current_user: str = Depends(get_current_user)):
    """获取会员数量统计（支付了开通会员的openid数量）（需要认证）"""
    try:
        count = await stats_service.get_member_count()
        return {"success": True, "data": {"member_count": count}}
    except Exception as e:
        logger.error(f"获取会员数量统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))