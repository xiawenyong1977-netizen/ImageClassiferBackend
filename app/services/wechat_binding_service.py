"""
微信二维码绑定服务
用于管理 wechat_qrcode_bindings 表的操作
"""

from typing import Optional
from app.database import db
from loguru import logger


class WeChatBindingService:
    """微信二维码绑定服务类"""
    
    async def get_openid_by_client_id(self, client_id: str) -> Optional[str]:
        """
        根据 client_id 查询 openid
        
        Args:
            client_id: 客户端ID（user_id）
            
        Returns:
            openid，如果未找到或查询失败则返回 None
        """
        if not client_id:
            return None
        
        try:
            async with db.get_cursor() as cursor:
                await cursor.execute("""
                    SELECT openid FROM wechat_qrcode_bindings 
                    WHERE client_id = %s AND openid IS NOT NULL 
                    ORDER BY completed_at DESC, id DESC
                    LIMIT 1
                """, (client_id,))
                binding = await cursor.fetchone()
                if binding:
                    openid = binding.get('openid')
                    logger.debug(f"通过 client_id={client_id} 查询到 openid={openid[:16] if openid else None}...")
                    return openid
                return None
        except Exception as e:
            logger.warning(f"查询 openid 失败 (client_id={client_id}): {e}")
            return None
    
    async def resolve_openid(self, openid: Optional[str] = None, client_id: Optional[str] = None) -> Optional[str]:
        """
        解析 openid，如果提供了 openid 则直接返回，否则根据 client_id 查询
        
        Args:
            openid: 直接提供的 openid（优先使用）
            client_id: 客户端ID（如果 openid 为空则使用此参数查询）
            
        Returns:
            openid，如果都未找到则返回 None
        """
        # 如果已经提供了 openid，直接返回
        if openid:
            return openid
        
        # 如果提供了 client_id，尝试查询
        if client_id:
            return await self.get_openid_by_client_id(client_id)
        
        return None


# 全局实例
wechat_binding_service = WeChatBindingService()

