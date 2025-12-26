"""
用户照片关系服务
用于管理user_photos表的操作
"""

from typing import Optional
from app.database import db
from loguru import logger


class UserPhotosService:
    """用户照片关系服务类"""
    
    async def upsert_user_photo(
        self,
        user_id: str,
        image_hash: str,
        image_uri: Optional[str] = None,
        openid: Optional[str] = None
    ) -> bool:
        """
        插入或更新用户照片记录
        
        Args:
            user_id: 用户ID
            image_hash: 图片哈希
            image_uri: 图片URI（可选）
            openid: 微信openid（可选）
            
        Returns:
            是否操作成功
        """
        try:
            async with db.get_cursor() as cursor:
                # 如果openid为空但user_id不为空，尝试从绑定表查询openid
                resolved_openid = openid
                if not resolved_openid and user_id:
                    try:
                        await cursor.execute("""
                            SELECT openid FROM wechat_qrcode_bindings 
                            WHERE client_id = %s AND openid IS NOT NULL 
                            LIMIT 1
                        """, (user_id,))
                        binding_result = await cursor.fetchone()
                        if binding_result:
                            resolved_openid = binding_result.get('openid')
                            logger.debug(f"通过 user_id={user_id} 查询到 openid={resolved_openid}")
                    except Exception as e:
                        logger.warning(f"查询 openid 失败 (user_id={user_id}): {e}")
                
                # 使用INSERT ... ON DUPLICATE KEY UPDATE（使用别名语法避免VALUES()函数弃用警告）
                sql = """
                INSERT INTO user_photos (user_id, openid, image_hash, image_uri, classify_count, first_seen_at, last_seen_at)
                VALUES (%s, %s, %s, %s, 1, NOW(), NOW()) AS new_values
                ON DUPLICATE KEY UPDATE
                    classify_count = user_photos.classify_count + 1,
                    last_seen_at = NOW(),
                    image_uri = COALESCE(new_values.image_uri, user_photos.image_uri),
                    openid = COALESCE(new_values.openid, user_photos.openid)
                """
                await cursor.execute(sql, (user_id, resolved_openid, image_hash, image_uri))
                logger.debug(f"用户照片记录已更新: user_id={user_id}, openid={resolved_openid}, image_hash={image_hash[:16]}...")
                return True
                
        except Exception as e:
            logger.error(f"更新用户照片记录失败: {e}")
            return False
    
    async def get_user_photos(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """
        获取用户的照片列表
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            照片列表
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT image_hash, image_uri, classify_count, first_seen_at, last_seen_at
                FROM user_photos
                WHERE user_id = %s
                ORDER BY last_seen_at DESC
                LIMIT %s OFFSET %s
                """
                await cursor.execute(sql, (user_id, limit, offset))
                results = await cursor.fetchall()
                return results
                
        except Exception as e:
            logger.error(f"查询用户照片列表失败: {e}")
            return []
    
    async def get_user_photo_count(self, user_id: str) -> int:
        """
        获取用户的照片数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            照片数量
        """
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT COUNT(*) as count
                FROM user_photos
                WHERE user_id = %s
                """
                await cursor.execute(sql, (user_id,))
                result = await cursor.fetchone()
                return result['count'] if result else 0
                
        except Exception as e:
            logger.error(f"查询用户照片数量失败: {e}")
            return 0


# 全局服务实例
user_photos_service = UserPhotosService()

