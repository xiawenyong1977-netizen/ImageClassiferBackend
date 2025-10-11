"""
统计接口路由
"""

from fastapi import APIRouter, HTTPException, Depends
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

