"""
图像编辑API路由
"""

from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException
from typing import List, Optional
import json
import aiomysql
from loguru import logger

from app.services.image_editor import image_editor
from app.database import db

router = APIRouter(prefix="/api/v1/image-edit", tags=["image-edit"])


@router.post("/submit")
async def submit_edit(
    images: List[UploadFile] = File(...),
    edit_type: str = Form(...),
    edit_params: str = Form(...),
    client_id: Optional[str] = Form(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_wechat_openid: Optional[str] = Header(None, alias="X-WeChat-OpenID")
):
    """
    提交编辑任务（支持单张或多张）
    
    Args:
        images: 图片文件数组（1-9张）
        edit_type: 编辑类型（如 "remove"）
        edit_params: 编辑参数（JSON字符串）
        client_id: 客户端ID（用于额度管理，扫码场景）
        x_user_id: 用户ID（可选）
        x_wechat_openid: 微信openid（用于额度管理，网页授权场景）
    
    Returns:
        task_id: 任务ID
        total_images: 总图片数
        estimated_time_ms: 预估时间（毫秒）
    """
    try:
        # 检查数量
        if len(images) == 0:
            raise HTTPException(status_code=400, detail="至少需要1张图片")
        if len(images) > 9:
            raise HTTPException(status_code=400, detail="最多9张图片")
        
        # 1. 确定openid（支持client_id或x_wechat_openid）
        openid = x_wechat_openid
        
        if not openid and client_id:
            # 通过client_id查询openid
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """SELECT openid FROM wechat_qrcode_bindings 
                           WHERE client_id = %s AND status = 'completed'""",
                        (client_id,)
                    )
                    binding = await cursor.fetchone()
                    if binding and binding['openid']:
                        openid = binding['openid']
                        logger.info(f"通过client_id获取openid: {openid[:16]}...")
        
        # 2. 检查额度（如果有openid）
        if openid:
            # 先查询用户剩余额度
            from app.services.credit_service import credit_service
            async with db.get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT remaining_credits FROM wechat_users WHERE openid = %s",
                        (openid,)
                    )
                    user = await cursor.fetchone()
                    if user:
                        remaining = user['remaining_credits'] or 0
                        if remaining < len(images):
                            raise HTTPException(
                                status_code=400, 
                                detail=f"额度不足：剩余{remaining}张，需要{len(images)}张"
                            )
        
        # 3. 读取图片
        image_data = []
        for img in images:
            bytes = await img.read()
            image_data.append({
                'filename': img.filename,
                'bytes': bytes
            })
        
        # 4. 解析参数
        try:
            params = json.loads(edit_params)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="编辑参数格式错误")
        
        # 5. 提交任务（异步处理，立即返回）
        task_id = await image_editor.submit_task_async(
            image_data, edit_type, params, x_user_id, openid
        )
        
        # 6. 预估时间（使用原图，约18秒/张）
        batch_count = (len(images) + 2) // 3  # 向上取整
        estimated_time = batch_count * 54000  # 每批约54秒（3张×18秒）
        
        logger.info(f"任务提交成功: {task_id}, 图片数: {len(images)}, openid: {openid[:16] if openid else 'None'}...")
        
        return {
            "success": True,
            "task_id": task_id,
            "total_images": len(images),
            "estimated_time_ms": estimated_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务状态信息
    """
    try:
        status = await image_editor.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
