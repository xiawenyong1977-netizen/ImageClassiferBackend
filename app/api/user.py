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
    查询用户的图像编辑额度和会员状态
    
    返回用户的总额度、已使用额度、剩余额度和会员状态
    """
    try:
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT total_credits, used_credits, remaining_credits, 
                              is_member, member_expire_at, created_at, last_active_time
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


@router.get("/member-status", summary="查询会员状态")
async def get_member_status(x_wechat_openid: str = Header(..., description="微信openid")):
    """
    查询用户的会员状态
    
    返回用户是否是会员、会员到期时间等信息
    """
    try:
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT is_member, member_expire_at, created_at 
                       FROM wechat_users 
                       WHERE openid = %s""",
                    (x_wechat_openid,)
                )
                user = await cursor.fetchone()
                
                if not user:
                    raise HTTPException(status_code=404, detail="用户不存在")
                
                return {
                    "success": True,
                    "is_member": bool(user['is_member']),
                    "member_expire_at": str(user['member_expire_at']) if user['member_expire_at'] else None,
                    "data": user
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询会员状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")
