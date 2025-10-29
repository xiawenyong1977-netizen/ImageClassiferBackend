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


@router.get("/credits-usage", summary="查询额度消费记录")
async def get_credits_usage(
    x_wechat_openid: str = Header(..., description="微信openid"),
    limit: int = 20
):
    """
    查询用户的额度消费记录
    
    返回最近的额度消费历史记录
    """
    try:
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT id, task_id, task_type, credits_used, 
                              request_image_count, success_image_count, created_at
                       FROM credits_usage 
                       WHERE openid = %s
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (x_wechat_openid, limit)
                )
                records = await cursor.fetchall()
                
                # 转换为可序列化的格式
                result = []
                for record in records:
                    result.append({
                        "id": record['id'],
                        "task_id": record['task_id'],
                        "task_type": record['task_type'],
                        "credits_used": record['credits_used'],
                        "request_image_count": record.get('request_image_count', record['credits_used']),
                        "success_image_count": record.get('success_image_count', record['credits_used']),
                        "created_at": str(record['created_at']) if record['created_at'] else None
                    })
                
                return {
                    "success": True,
                    "data": result,
                    "count": len(result)
                }
                
    except Exception as e:
        logger.error(f"查询额度消费记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")
