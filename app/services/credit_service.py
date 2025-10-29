"""
用户额度服务
负责检查、扣减用户额度
"""

import aiomysql
from typing import Optional, Tuple
from app.database import db
from loguru import logger


class CreditService:
    """额度服务类"""
    
    async def check_and_deduct_credit(self, openid: str, deduct_on_success: bool = True) -> Tuple[bool, Optional[str]]:
        """
        检查并扣减用户额度
        
        Args:
            openid: 微信openid
            deduct_on_success: 是否成功后才扣减（默认True）
            
        Returns:
            (是否有足够额度, 错误消息)
        """
        if not openid:
            return False, "需要openid参数"
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 查询用户额度
                    await cursor.execute(
                        """SELECT remaining_credits, is_member, member_expire_at 
                           FROM wechat_users 
                           WHERE openid = %s""",
                        (openid,)
                    )
                    user = await cursor.fetchone()
                    
                    if not user:
                        return False, "用户不存在"
                    
                    # 检查用户额度（会员和非会员都需要检查和扣减）
                    remaining_credits = user['remaining_credits'] or 0
                    if remaining_credits <= 0:
                        return False, f"额度不足，剩余额度: {remaining_credits}"
                    
                    # 如果需要扣减，扣除1个额度（会员和非会员都扣减）
                    if deduct_on_success:
                        await cursor.execute(
                            """UPDATE wechat_users 
                               SET remaining_credits = remaining_credits - 1,
                                   used_credits = used_credits + 1
                               WHERE openid = %s AND remaining_credits > 0""",
                            (openid,)
                        )
                        await conn.commit()
                        logger.info(f"扣减额度成功: {openid[:16]}... 剩余额度: {remaining_credits - 1}")
                    
                    return True, None
                    
        except Exception as e:
            logger.error(f"检查额度失败: {e}")
            return False, str(e)
    
    async def refund_credit(self, openid: str) -> bool:
        """
        退还用户额度（处理失败时使用）
        
        Args:
            openid: 微信openid
            
        Returns:
            是否退还成功
        """
        if not openid:
            return False
        
        try:
            async with db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """UPDATE wechat_users 
                           SET remaining_credits = remaining_credits + 1,
                               used_credits = used_credits - 1
                           WHERE openid = %s""",
                        (openid,)
                    )
                    await conn.commit()
                    logger.info(f"退还额度成功: {openid[:16]}...")
                    return True
                    
        except Exception as e:
            logger.error(f"退还额度失败: {e}")
            return False


# 全局额度服务实例
credit_service = CreditService()

