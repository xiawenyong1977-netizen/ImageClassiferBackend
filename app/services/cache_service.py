"""
缓存服务
负责查询和更新image_classification_cache表
"""

from typing import Optional
from app.database import db
from loguru import logger


class CacheService:
    """缓存服务类"""
    
    async def get_cached_result(self, image_hash: str) -> Optional[dict]:
        """
        根据哈希查询缓存结果
        
        Args:
            image_hash: 图片SHA-256哈希
            
        Returns:
            缓存结果字典，未找到返回None
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT 
                    category,
                    confidence,
                    description,
                    model_used,
                    hit_count,
                    created_at
                FROM image_classification_cache
                WHERE image_hash = %s
                """
                await cursor.execute(sql, (image_hash,))
                result = await cursor.fetchone()
                
                if result:
                    logger.debug(f"缓存命中: {image_hash[:16]}... (命中次数: {result['hit_count']})")
                    return result
                
                logger.debug(f"缓存未命中: {image_hash[:16]}...")
                return None
                
        except Exception as e:
            logger.error(f"查询缓存失败: {e}")
            return None
    
    async def save_result(self, image_hash: str, category: str, confidence: float,
                         description: Optional[str], model_used: str) -> bool:
        """
        保存分类结果到缓存
        
        Args:
            image_hash: 图片哈希
            category: 分类类别
            confidence: 置信度
            description: 描述
            model_used: 使用的模型
            
        Returns:
            是否保存成功
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                INSERT INTO image_classification_cache 
                (image_hash, category, confidence, description, model_used, hit_count)
                VALUES (%s, %s, %s, %s, %s, 1)
                """
                await cursor.execute(sql, (
                    image_hash, category, confidence, description, model_used
                ))
                logger.info(f"缓存已保存: {image_hash[:16]}... -> {category}")
                return True
                
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False
    
    async def increment_hit_count(self, image_hash: str) -> bool:
        """
        增加缓存命中次数
        
        Args:
            image_hash: 图片哈希
            
        Returns:
            是否更新成功
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                UPDATE image_classification_cache
                SET 
                    hit_count = hit_count + 1,
                    last_hit_at = NOW()
                WHERE image_hash = %s
                """
                await cursor.execute(sql, (image_hash,))
                return True
                
        except Exception as e:
            logger.error(f"更新命中次数失败: {e}")
            return False


# 全局缓存服务实例
cache_service = CacheService()

