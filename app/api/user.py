"""
用户管理相关API
"""

from fastapi import APIRouter, Header, HTTPException, Response, Query
from fastapi.responses import JSONResponse
import logging
import aiomysql

from app.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/user", tags=["用户"])


@router.get("/credits", summary="查询用户额度")
async def get_user_credits(
    client_id: str = Query(None, description="客户端ID（用于扫码关注场景）"),
    x_wechat_openid: str = Header(None, description="微信openid")
):
    """
    查询用户的图像编辑额度和会员状态
    
    支持两种调用方式：
    1. 通过client_id查询（客户端扫码场景）
    2. 通过openid查询（网页授权场景）
    
    返回用户的总额度、已使用额度、剩余额度和会员状态
    """
    try:
        openid = None
        
        # 方式1：使用openid（网页授权）
        if x_wechat_openid:
            openid = x_wechat_openid
            logger.info(f"查询用户额度: openid={openid[:16]}...")
        
        # 方式2：使用client_id（扫码关注）
        elif client_id:
            client_id = client_id.strip()
            logger.info(f"查询用户额度: client_id={client_id}")
            
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 先查询所有状态，用于调试
                    await cursor.execute(
                        """SELECT openid, status FROM wechat_qrcode_bindings 
                           WHERE client_id = %s""",
                        (client_id,)
                    )
                    all_bindings = await cursor.fetchall()
                    logger.info(f"查询到绑定记录数: {len(all_bindings)}, client_id={client_id}")
                    
                    # 以是否存在openid为完成判定（保留status但不作为门槛）
                    await cursor.execute(
                        """SELECT openid, status FROM wechat_qrcode_bindings 
                               WHERE client_id = %s AND openid IS NOT NULL 
                               ORDER BY completed_at DESC, id DESC LIMIT 1""",
                        (client_id,)
                    )
                    binding = await cursor.fetchone()
                    
                    if not binding or not binding['openid']:
                        logger.warning(f"未找到有效绑定(openid为空): client_id={client_id}, 所有记录={all_bindings}")
                        raise HTTPException(status_code=404, detail="用户未关注公众号")
                    
                    openid = binding['openid']
                    logger.info(f"找到openid: {openid[:16]}...")
        else:
            raise HTTPException(status_code=400, detail="缺少client_id或openid参数")
        
        # 查询用户额度信息
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT total_credits, used_credits, remaining_credits, 
                              is_member, member_expire_at, created_at, last_active_time
                       FROM wechat_users 
                       WHERE openid = %s""",
                    (openid,)
                )
                user = await cursor.fetchone()
                
                if not user:
                    raise HTTPException(status_code=404, detail="用户不存在")
                
                # 设置防缓存响应头
                response_data = {
                    "success": True,
                    "total_credits": user['total_credits'],
                    "used_credits": user['used_credits'],
                    "remaining_credits": user['remaining_credits'],
                    "is_member": bool(user['is_member']),
                    "member_expire_at": str(user['member_expire_at']) if user['member_expire_at'] else None
                }
                response = JSONResponse(content=response_data)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询用户额度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.get("/member-status", summary="查询会员状态")
async def get_member_status(
    client_id: str = Query(None, description="客户端ID（用于扫码关注场景）"),
    x_wechat_openid: str = Header(None, description="微信openid")
):
    """
    查询用户的会员状态
    
    支持两种调用方式：
    1. 通过client_id查询（客户端扫码场景）
    2. 通过openid查询（网页授权场景）
    
    返回用户是否是会员、会员到期时间等信息
    """
    try:
        openid = None
        
        # 方式1：使用openid（网页授权）
        if x_wechat_openid:
            openid = x_wechat_openid
            logger.info(f"查询会员状态: openid={openid[:16]}...")
        
        # 方式2：使用client_id（扫码关注）
        elif client_id:
            client_id = client_id.strip()
            logger.info(f"查询会员状态: client_id={client_id}")
            
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 以是否存在openid为完成判定（保留status但不作为门槛）
                    await cursor.execute(
                        """SELECT openid, status FROM wechat_qrcode_bindings 
                               WHERE client_id = %s AND openid IS NOT NULL 
                               ORDER BY completed_at DESC, id DESC LIMIT 1""",
                        (client_id,)
                    )
                    binding = await cursor.fetchone()
                    
                    if not binding or not binding.get('openid'):
                        raise HTTPException(status_code=404, detail="用户未关注公众号")
                    
                    openid = binding['openid']
        else:
            raise HTTPException(status_code=400, detail="缺少client_id或openid参数")
        
        # 查询会员状态
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT is_member, member_expire_at, created_at 
                       FROM wechat_users 
                       WHERE openid = %s""",
                    (openid,)
                )
                user = await cursor.fetchone()
                
                if not user:
                    raise HTTPException(status_code=404, detail="用户不存在")
                
                return {
                    "success": True,
                    "is_member": bool(user['is_member']),
                    "member_expire_at": str(user['member_expire_at']) if user['member_expire_at'] else None
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
                
                # 设置防缓存响应头
                response_data = {
                    "success": True,
                    "data": result,
                    "count": len(result)
                }
                response = JSONResponse(content=response_data)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                return response
                
    except Exception as e:
        logger.error(f"查询额度消费记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")
