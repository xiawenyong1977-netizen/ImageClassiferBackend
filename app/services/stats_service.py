"""
统计服务
负责记录请求日志和查询统计数据
"""

from typing import Optional
from app.database import db
from loguru import logger
from app.config import settings


class StatsService:
    """统计服务类"""
    
    async def log_request(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        image_hash: str,
        image_size: int,
        category: str,
        confidence: float,
        from_cache: bool,
        processing_time_ms: int
    ) -> bool:
        """
        记录请求日志
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            image_hash: 图片哈希
            image_size: 图片大小
            category: 分类类别
            confidence: 置信度
            from_cache: 是否来自缓存
            processing_time_ms: 处理耗时
            
        Returns:
            是否记录成功
        """
        if not settings.ENABLE_REQUEST_LOG:
            return True
        
        try:
            async with db.get_cursor() as cursor:
                sql = """
                INSERT INTO request_log (
                    request_id, user_id, ip_address, image_hash, image_size,
                    category, confidence, from_cache, processing_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(sql, (
                    request_id, user_id, ip_address, image_hash, image_size,
                    category, confidence, 1 if from_cache else 0, processing_time_ms
                ))
                logger.debug(f"请求日志已记录: {request_id}")
                return True
                
        except Exception as e:
            logger.error(f"记录请求日志失败: {e}")
            return False
    
    async def get_today_stats(self) -> dict:
        """
        获取今日统计
        
        Returns:
            今日统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as cache_hits,
                    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) as cache_misses,
                    ROUND(SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as cache_hit_rate,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT ip_address) as unique_ips,
                    ROUND(AVG(processing_time_ms), 2) as avg_processing_time,
                    SUM(CASE WHEN from_cache = 0 THEN 1 ELSE 0 END) * %s as estimated_cost,
                    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) * %s as cost_saved
                FROM request_log
                WHERE created_date = CURDATE()
                """
                await cursor.execute(sql, (settings.COST_PER_API_CALL, settings.COST_PER_API_CALL))
                result = await cursor.fetchone()
                return result or {}
                
        except Exception as e:
            logger.error(f"查询今日统计失败: {e}")
            return {}
    
    async def get_cache_efficiency(self) -> dict:
        """
        获取缓存效率统计
        
        Returns:
            缓存效率数据
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_cached_images,
                    SUM(hit_count) as total_hits,
                    SUM(hit_count - 1) as times_saved,
                    ROUND((SUM(hit_count - 1) * %s), 2) as cost_saved,
                    ROUND(AVG(hit_count), 2) as avg_hit_per_image,
                    MAX(hit_count) as max_hits
                FROM image_classification_cache
                """
                await cursor.execute(sql, (settings.COST_PER_API_CALL,))
                result = await cursor.fetchone()
                return result or {}
                
        except Exception as e:
            logger.error(f"查询缓存效率失败: {e}")
            return {}
    
    async def get_category_distribution(self) -> list:
        """
        获取分类分布统计
        
        Returns:
            分类分布列表
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    category,
                    COUNT(*) as count,
                    ROUND(AVG(confidence), 4) as avg_confidence,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM request_log WHERE created_date = CURDATE()), 2) as percentage
                FROM request_log
                WHERE created_date = CURDATE()
                GROUP BY category
                ORDER BY count DESC
                """
                await cursor.execute(sql)
                results = await cursor.fetchall()
                return results or []
                
        except Exception as e:
            logger.error(f"查询分类分布失败: {e}")
            return []


# 全局统计服务实例
stats_service = StatsService()

