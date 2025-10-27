"""
用户管理相关API
"""

from fastapi import APIRouter, Header, HTTPException
import logging
import aiomysql

from app.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user", tags=["用户"])


@router.get("/credits", summary="查询用户额度")
async def get_user_credits(x_wechat_openid: str = Header(..., description="微信openid")):
    """
    查询用户的图像编辑额度
    
    返回用户的总额度、已使用额度和剩余额度
    """
    try:
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT total_credits, used_credits, remaining_credits 
                       FROM wechat_users 
                       WHERE openid = %s""",
                    (x_wechat_openid,)
                )
                user = await cursor.fetchone()
                
                if not user:
                    raise HTTPException(status_code=404, detail="用户不存在")
                
                return {
                    "success": True,
                    "data": user
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询用户额度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")
