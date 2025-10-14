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
        processing_time_ms: int,
        inference_method: str = "llm"
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
            inference_method: 推理方式(llm/local/llm_fallback/local_fallback)
            
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
                    category, confidence, from_cache, processing_time_ms, inference_method
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(sql, (
                    request_id, user_id, ip_address, image_hash, image_size,
                    category, confidence, 1 if from_cache else 0, processing_time_ms, inference_method
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
    
    async def get_inference_method_stats(self) -> dict:
        """
        获取推理方式统计
        
        Returns:
            推理方式统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN from_cache = 1 THEN 1 ELSE 0 END) as from_cache,
                    SUM(CASE WHEN inference_method = 'llm' THEN 1 ELSE 0 END) as llm_success,
                    SUM(CASE WHEN inference_method = 'local' THEN 1 ELSE 0 END) as local_direct,
                    SUM(CASE WHEN inference_method = 'llm_fallback' THEN 1 ELSE 0 END) as llm_fallback,
                    SUM(CASE WHEN inference_method = 'local_fallback' THEN 1 ELSE 0 END) as local_fallback_success,
                    SUM(CASE WHEN inference_method = 'local_test' THEN 1 ELSE 0 END) as local_test,
                    SUM(CASE WHEN inference_method IN ('llm_fallback', 'local_fallback') THEN 1 ELSE 0 END) as total_fallback
                FROM request_log
                WHERE created_date = CURDATE()
                """
                await cursor.execute(sql)
                result = await cursor.fetchone()
                
                if result:
                    # 计算百分比
                    total = result['total_requests'] or 0
                    return {
                        'total_requests': total,
                        'from_cache': result['from_cache'] or 0,
                        'llm_success': result['llm_success'] or 0,
                        'local_direct': result['local_direct'] or 0,
                        'llm_fallback': result['llm_fallback'] or 0,
                        'local_fallback_success': result['local_fallback_success'] or 0,
                        'local_test': result['local_test'] or 0,
                        'total_fallback': result['total_fallback'] or 0,
                        'llm_fail_count': result['local_fallback_success'] or 0,  # 大模型失败次数 = 降级到本地推理的次数
                        'local_total': (result['local_direct'] or 0) + (result['local_fallback_success'] or 0) + (result['local_test'] or 0)  # 本地推理总次数（包含测试）
                    }
                
                return {}
                
        except Exception as e:
            logger.error(f"查询推理方式统计失败: {e}")
            return {}
    async def log_batch_cache_query(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        total_count: int,
        cached_count: int,
        miss_count: int
    ) -> bool:
        """
        记录批量缓存查询统计
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            total_count: 查询总数
            cached_count: 缓存命中数
            miss_count: 缓存未命中数
            
        Returns:
            是否记录成功
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO batch_cache_stats 
                    (request_id, user_id, ip_address, total_count, cached_count, miss_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (request_id, user_id, ip_address, total_count, cached_count, miss_count))
                
            return True
        except Exception as e:
            logger.error(f"记录批量缓存查询统计失败: {e}")
            return False
    
    async def get_batch_cache_stats(self, days: int = 7) -> dict:
        """
        获取批量缓存查询统计
        
        Args:
            days: 查询最近几天的数据
            
        Returns:
            统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                # 总体统计
                await cursor.execute("""
                    SELECT 
                        COUNT(*) as total_queries,
                        SUM(total_count) as total_hashes,
                        SUM(cached_count) as total_cached,
                        SUM(miss_count) as total_miss,
                        ROUND(AVG(total_count), 2) as avg_batch_size,
                        ROUND(SUM(cached_count) * 100.0 / NULLIF(SUM(total_count), 0), 2) as hit_rate
                    FROM batch_cache_stats
                    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """, (days,))
                
                overall = await cursor.fetchone()
                
                # 每日统计
                await cursor.execute("""
                    SELECT 
                        created_date,
                        COUNT(*) as queries,
                        SUM(total_count) as hashes,
                        SUM(cached_count) as cached,
                        SUM(miss_count) as miss,
                        ROUND(SUM(cached_count) * 100.0 / NULLIF(SUM(total_count), 0), 2) as hit_rate
                    FROM batch_cache_stats
                    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    GROUP BY created_date
                    ORDER BY created_date DESC
                """, (days,))
                
                daily = await cursor.fetchall()
                
                return {
                    "overall": {
                        "total_queries": overall['total_queries'] or 0,
                        "total_hashes": overall['total_hashes'] or 0,
                        "total_cached": overall['total_cached'] or 0,
                        "total_miss": overall['total_miss'] or 0,
                        "avg_batch_size": float(overall['avg_batch_size'] or 0),
                        "hit_rate": float(overall['hit_rate'] or 0)
                    },
                    "daily": [
                        {
                            "date": str(row['created_date']),
                            "queries": row['queries'],
                            "hashes": row['hashes'],
                            "cached": row['cached'],
                            "miss": row['miss'],
                            "hit_rate": float(row['hit_rate'] or 0)
                        }
                        for row in daily
                    ]
                }
        except Exception as e:
            logger.error(f"获取批量缓存统计失败: {e}")
            return {
                "overall": {
                    "total_queries": 0,
                    "total_hashes": 0,
                    "total_cached": 0,
                    "total_miss": 0,
                    "avg_batch_size": 0,
                    "hit_rate": 0
                },
                "daily": []
            }
    
    async def log_batch_classify(
        self,
        request_id: str,
        user_id: Optional[str],
        ip_address: Optional[str],
        total_count: int,
        success_count: int,
        fail_count: int,
        total_processing_time_ms: int
    ) -> bool:
        """
        记录批量分类统计
        
        Args:
            request_id: 请求ID
            user_id: 用户ID
            ip_address: IP地址
            total_count: 图片总数
            success_count: 成功数
            fail_count: 失败数
            total_processing_time_ms: 总处理耗时
            
        Returns:
            是否记录成功
        """
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO batch_classify_stats 
                    (request_id, user_id, ip_address, total_count, success_count, fail_count, total_processing_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (request_id, user_id, ip_address, total_count, success_count, fail_count, total_processing_time_ms))
                
            return True
        except Exception as e:
            logger.error(f"记录批量分类统计失败: {e}")
            return False
    
    async def get_batch_classify_stats(self, days: int = 7) -> dict:
        """
        获取批量分类统计
        
        Args:
            days: 查询最近几天的数据
            
        Returns:
            统计数据
        """
        try:
            async with db.get_cursor() as cursor:
                # 总体统计
                await cursor.execute("""
                    SELECT 
                        COUNT(*) as total_batches,
                        SUM(total_count) as total_images,
                        SUM(success_count) as total_success,
                        SUM(fail_count) as total_fail,
                        ROUND(AVG(total_count), 2) as avg_batch_size,
                        ROUND(AVG(avg_processing_time_ms), 2) as avg_time_per_image,
                        ROUND(SUM(success_count) * 100.0 / NULLIF(SUM(total_count), 0), 2) as success_rate
                    FROM batch_classify_stats
                    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                """, (days,))
                
                overall = await cursor.fetchone()
                
                # 每日统计
                await cursor.execute("""
                    SELECT 
                        created_date,
                        COUNT(*) as batches,
                        SUM(total_count) as images,
                        SUM(success_count) as success,
                        SUM(fail_count) as fail,
                        ROUND(AVG(avg_processing_time_ms), 2) as avg_time,
                        ROUND(SUM(success_count) * 100.0 / NULLIF(SUM(total_count), 0), 2) as success_rate
                    FROM batch_classify_stats
                    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    GROUP BY created_date
                    ORDER BY created_date DESC
                """, (days,))
                
                daily = await cursor.fetchall()
                
                return {
                    "overall": {
                        "total_batches": overall['total_batches'] or 0,
                        "total_images": overall['total_images'] or 0,
                        "total_success": overall['total_success'] or 0,
                        "total_fail": overall['total_fail'] or 0,
                        "avg_batch_size": float(overall['avg_batch_size'] or 0),
                        "avg_time_per_image": float(overall['avg_time_per_image'] or 0),
                        "success_rate": float(overall['success_rate'] or 0)
                    },
                    "daily": [
                        {
                            "date": str(row['created_date']),
                            "batches": row['batches'],
                            "images": row['images'],
                            "success": row['success'],
                            "fail": row['fail'],
                            "avg_time": float(row['avg_time'] or 0),
                            "success_rate": float(row['success_rate'] or 0)
                        }
                        for row in daily
                    ]
                }
        except Exception as e:
            logger.error(f"获取批量分类统计失败: {e}")
            return {
                "overall": {
                    "total_batches": 0,
                    "total_images": 0,
                    "total_success": 0,
                    "total_fail": 0,
                    "avg_batch_size": 0,
                    "avg_time_per_image": 0,
                    "success_rate": 0
                },
                "daily": []
            }


# 全局统计服务实例
stats_service = StatsService()

