"""
额度消耗记录服务
用于管理 credits_usage 表的操作
"""

from typing import Optional, List, Dict
import aiomysql
from app.database import db
from loguru import logger


class CreditsUsageService:
    """额度消耗记录服务类"""
    
    async def log_usage(
        self,
        openid: str,
        task_id: str,
        task_type: str,
        credits_used: int,
        request_image_count: int,
        success_image_count: int
    ) -> bool:
        """
        记录额度消耗
        
        Args:
            openid: 用户openid
            task_id: 任务ID
            task_type: 任务类型（如 'image_edit', 'batch_classify'）
            credits_used: 消耗的额度
            request_image_count: 请求的图片张数
            success_image_count: 成功处理的图片张数
            
        Returns:
            是否记录成功
        """
        if not openid or not task_id:
            logger.warning("记录额度消耗失败: openid 或 task_id 为空")
            return False
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """INSERT INTO credits_usage 
                           (openid, task_id, task_type, credits_used, request_image_count, success_image_count)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (openid, task_id, task_type, credits_used, request_image_count, success_image_count)
                    )
                    await conn.commit()
                    logger.debug(f"记录额度消耗成功: openid={openid[:16]}..., task_id={task_id}, credits_used={credits_used}")
                    return True
        except Exception as e:
            logger.error(f"记录额度消耗失败: {e}")
            return False
    
    async def get_usage_by_openid(
        self,
        openid: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """
        根据 openid 查询额度消耗记录
        
        Args:
            openid: 用户openid
            limit: 返回记录数限制（默认20）
            offset: 偏移量（默认0）
            
        Returns:
            额度消耗记录列表
        """
        if not openid:
            return []
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT id, task_id, task_type, credits_used, 
                                  request_image_count, success_image_count, created_at
                           FROM credits_usage 
                           WHERE openid = %s
                           ORDER BY created_at DESC, id DESC
                           LIMIT %s OFFSET %s""",
                        (openid, limit, offset)
                    )
                    records = await cursor.fetchall()
                    return list(records) if records else []
        except Exception as e:
            logger.error(f"查询额度消耗记录失败: {e}")
            return []
    
    async def get_usage_by_task_id(
        self,
        task_id: str
    ) -> Optional[Dict]:
        """
        根据 task_id 查询额度消耗记录
        
        Args:
            task_id: 任务ID
            
        Returns:
            额度消耗记录（如果找到），否则返回 None
        """
        if not task_id:
            return None
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT id, openid, task_id, task_type, credits_used, 
                                  request_image_count, success_image_count, created_at
                           FROM credits_usage 
                           WHERE task_id = %s
                           LIMIT 1""",
                        (task_id,)
                    )
                    record = await cursor.fetchone()
                    return dict(record) if record else None
        except Exception as e:
            logger.error(f"查询额度消耗记录失败: {e}")
            return None
    
    async def get_total_credits_used(
        self,
        openid: str
    ) -> int:
        """
        查询用户累计消耗的额度总数
        
        Args:
            openid: 用户openid
            
        Returns:
            累计消耗的额度总数
        """
        if not openid:
            return 0
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """SELECT SUM(credits_used) as total
                           FROM credits_usage 
                           WHERE openid = %s""",
                        (openid,)
                    )
                    result = await cursor.fetchone()
                    return int(result[0]) if result and result[0] else 0
        except Exception as e:
            logger.error(f"查询累计额度消耗失败: {e}")
            return 0


# 全局实例
credits_usage_service = CreditsUsageService()

