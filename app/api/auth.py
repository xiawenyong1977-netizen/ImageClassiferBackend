#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证相关API路由
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel, Field
import requests
import logging
import aiomysql
import xml.etree.ElementTree as ET
import time
import json

from app.auth import authenticate_user, create_access_token, Token
from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


# ===== 管理员登录 =====

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


@router.post("/login", response_model=Token, summary="管理员登录")
async def login(request: LoginRequest):
    """
    管理员登录接口
    
    **参数:**
    - **username**: 用户名
    - **password**: 密码
    
    **返回:** JWT访问token
    """
    # 验证用户名和密码
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问token
    access_token_expires = timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds())
    )


@router.post("/logout", summary="登出")
async def logout():
    """登出接口（客户端删除token即可）"""
    return {"message": "登出成功"}


# ===== 微信认证 =====


# 已废弃的OAuth授权接口（保留但不使用）
class WeChatAuthRequest(BaseModel):
    code: str


class WeChatAuthResponse(BaseModel):
    success: bool
    openid: str
    access_token: str
    nickname: str = None
    avatar_url: str = None


@router.get("/wechat/verify", summary="微信服务器配置验证")
async def wechat_verify(
    signature: str,
    timestamp: str,
    nonce: str,
    echostr: str
):
    """
    微信服务器配置验证接口
    
    用于微信公众号后台配置服务器URL时的验证
    参数由微信服务器自动传入
    
    Args:
        signature: 微信加密签名
        timestamp: 时间戳
        nonce: 随机数
        echostr: 随机字符串（验证成功需原样返回）
    
    Returns:
        echostr: 验证成功返回随机字符串
    """
    import hashlib
    
    # 微信服务器验证逻辑
    token = settings.WECHAT_TOKEN
    
    # 1. 将token、timestamp、nonce三个参数进行字典序排序
    tmp_arr = sorted([token, timestamp, nonce])
    
    # 2. 将三个参数字符串拼接成一个字符串进行sha1加密
    tmp_str = ''.join(tmp_arr)
    sha1 = hashlib.sha1()
    sha1.update(tmp_str.encode('utf-8'))
    hashcode = sha1.hexdigest()
    
    # 3. 将获得加密后的字符串与signature对比
    if hashcode == signature:
        logger.info(f"微信服务器验证成功, echostr={echostr}")
        return PlainTextResponse(content=echostr)
    else:
        logger.warning(f"微信服务器验证失败: signature={signature}, hashcode={hashcode}")
        raise HTTPException(status_code=403, detail="验证失败")


@router.get("/wechat", summary="微信网页授权获取openid")
async def wechat_auth(code: str):
    """
    微信网页授权，通过code获取openid
    
    这是网页授权流程的一部分，用户点击公众号菜单后：
    1. 跳转到微信授权页面
    2. 授权后返回code
    3. 调用此接口换取openid
    """
    try:
        logger.info(f"微信网页授权请求: code={code[:20]}...")
        
        # 1. 调用微信API获取access_token
        token_response = requests.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            },
            timeout=10
        ).json()
        
        if 'errcode' in token_response:
            logger.error(f"微信授权失败: {token_response}")
            raise HTTPException(status_code=400, detail=token_response.get('errmsg', '授权失败'))
        
        openid = token_response['openid']
        access_token = token_response['access_token']
        logger.info(f"获取openid成功: {openid[:16]}...")
        
        # 2. 创建或更新用户（使用snsapi_base时，不需要获取用户详情信息）
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT id FROM wechat_users WHERE openid = %s""",
                    (openid,)
                )
                exists = await cursor.fetchone()
                
                if not exists:
                    # 创建新用户（首次授权，给予10张额度）
                    await cursor.execute(
                        """INSERT INTO wechat_users 
                           (openid, total_credits, remaining_credits, used_credits)
                           VALUES (%s, 10, 10, 0)""",
                        (openid,)
                    )
                    logger.info(f"创建新用户: openid={openid[:16]}..., 额度=10")
                else:
                    # 更新活跃时间
                    await cursor.execute(
                        """UPDATE wechat_users SET last_active_time = NOW() WHERE openid = %s""",
                        (openid,)
                    )
                
                await conn.commit()
        
        return {
            "success": True,
            "openid": openid
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"微信授权异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="授权失败")


class GenerateQRCodeRequest(BaseModel):
    """生成二维码请求"""
    client_id: str = Field(..., description="客户端ID")


# 生成带参数的二维码（关注公众号获取openid）
@router.post("/wechat/qrcode", summary="生成带参数二维码")
async def generate_qrcode(request: GenerateQRCodeRequest):
    """
    生成带参数的二维码
    用户扫描后关注公众号，后端通过事件通知获取openid
    
    流程：
    1. 客户端提供client_id，后端生成带参数的二维码
    2. 用户扫码关注公众号，微信推送关注事件（包含scene_id和openid）
    3. 后端建立client_id -> scene_id -> openid 的映射
    4. 客户端通过client_id查询openid，判断是否关注
    """
    try:
        client_id = request.client_id
        logger.info(f"生成二维码请求: client_id={client_id}")
        
        # 获取access_token
        token_response = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                'grant_type': 'client_credential',
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET
            },
            timeout=10
        ).json()
        
        if 'errcode' in token_response:
            logger.error(f"获取access_token失败: {token_response}")
            raise HTTPException(status_code=400, detail="获取access_token失败")
        
        access_token = token_response['access_token']
        
        # 先插入或更新数据库获取自增ID作为scene_id
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # 尝试插入新记录，如果已存在则更新
                await cursor.execute(
                    """INSERT INTO wechat_qrcode_bindings 
                       (client_id, scene_id, status, created_at)
                       VALUES (%s, 0, 'pending', NOW())
                       ON DUPLICATE KEY UPDATE 
                           created_at = NOW()""",
                    (client_id,)
                )
                
                # 查询刚插入的记录，获取自增ID
                await cursor.execute(
                    "SELECT id FROM wechat_qrcode_bindings WHERE client_id = %s",
                    (client_id,)
                )
                result = await cursor.fetchone()
                scene_id = result[0]
                
                # 更新scene_id
                await cursor.execute(
                    "UPDATE wechat_qrcode_bindings SET scene_id = %s WHERE client_id = %s",
                    (scene_id, client_id)
                )
                
                await conn.commit()
        
        logger.info(f"使用自增ID作为scene_id: client_id={client_id}, scene_id={scene_id}")
        
        qrcode_response = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={access_token}",
            json={
                "action_name": "QR_LIMIT_SCENE",
                "action_info": {
                    "scene": {
                        "scene_id": scene_id
                    }
                }
            },
            timeout=10
        ).json()
        
        if 'errcode' in qrcode_response:
            logger.error(f"生成二维码失败: {qrcode_response}")
            raise HTTPException(status_code=400, detail="生成二维码失败")
        
        ticket = qrcode_response['ticket']
        expire_seconds = qrcode_response.get('expire_seconds', 2592000)
        qrcode_url = f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={ticket}"
        
        logger.info(f"二维码生成成功: client_id={client_id}, scene_id={scene_id}")
        
        return {
            "success": True,
            "qrcode_url": qrcode_url,
            "ticket": ticket,
            "client_id": client_id,
            "scene_id": scene_id,
            "expire_seconds": expire_seconds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成二维码异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="生成二维码失败")


# ===== 已废弃：OAuth授权回调接口 =====
# 注意：这个接口已被废弃，不再使用，仅保留代码
async def wechat_callback_function(code: str, state: str = None):
    """
    【已废弃】微信授权回调页面
    
    已废弃，不再使用，请使用扫码关注流程
    """
    try:
        logger.info(f"微信授权回调: code={code[:20]}...")
        
        # 1. 调用微信API获取openid
        token_response = requests.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET,
                'code': code,
                'grant_type': 'authorization_code'
            },
            timeout=10
        ).json()
        
        if 'errcode' in token_response:
            logger.error(f"微信授权失败: {token_response}")
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>授权失败</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #e74c3c; }}
                </style>
            </head>
            <body>
                <h1 class="error">授权失败</h1>
                <p>{token_response.get('errmsg', '未知错误')}</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html)
        
        openid = token_response['openid']
        logger.info(f"获取openid成功: {openid[:16]}...")
        
        # 2. 保存用户到数据库
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT id FROM wechat_users WHERE openid = %s""",
                    (openid,)
                )
                exists = await cursor.fetchone()
                
                if not exists:
                    # 创建新用户，首次关注给予10张额度
                    await cursor.execute(
                        """INSERT INTO wechat_users 
                           (openid, total_credits, remaining_credits, used_credits)
                           VALUES (%s, 10, 10, 0)""",
                        (openid,)
                    )
                    logger.info(f"创建新用户: openid={openid[:16]}..., 额度=10")
                else:
                    logger.info(f"用户已存在: openid={openid[:16]}...")
                
                await conn.commit()
        
        # 3. 返回HTML页面，将openid传给客户端
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>授权成功</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    max-width: 400px;
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ margin-top: 0; }}
                .spinner {{
                    border: 3px solid rgba(255, 255, 255, 0.3);
                    border-radius: 50%;
                    border-top: 3px solid white;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✓ 授权成功！</h1>
                <p>正在跳转...</p>
                <div class="spinner"></div>
            </div>
            <script>
                // 将openid存储到localStorage
                localStorage.setItem('wechat_openid', '{openid}');
                console.log('openid已保存:', '{openid.substring(0, 16)}...');
                
                // 跳转到主页面
                setTimeout(function() {{
                    window.location.href = '/';
                }}, 1500);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
        
    except Exception as e:
        logger.error(f"微信授权回调异常: {e}", exc_info=True)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>错误</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h1 class="error">授权失败</h1>
            <p>{str(e)}</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html)


# 微信公众号消息推送接收接口
async def wechat_message_handler(request: Request):
    """
    接收微信服务器推送的消息
    包括：关注/取消关注事件、扫码事件等
    """
    try:
        # 解析XML消息
        body = await request.body()
        logger.info(f"收到微信POST请求，body长度: {len(body)}")
        if body:
            try:
                logger.info(f"收到微信消息body: {body.decode('utf-8')[:500]}")
                root = ET.fromstring(body)
            except ET.ParseError as e:
                logger.error(f"XML解析失败: {e}")
                return PlainTextResponse(content="")
        else:
            logger.warning("收到空的body")
            return PlainTextResponse(content="")
        
        # 提取基础信息
        to_user = root.find('ToUserName').text
        from_user = root.find('FromUserName').text  # 这就是openid
        msg_type = root.find('MsgType').text
        event = root.find('Event').text if root.find('Event') is not None else None
        
        logger.info(f"收到微信消息: msg_type={msg_type}, event={event}, openid={from_user[:16]}...")
        
        # 检查扫码参数
        event_key = root.find('EventKey').text if root.find('EventKey') is not None else None
        
        # 处理关注事件（新用户关注）
        if msg_type == 'event' and event == 'subscribe':
            logger.info(f"用户关注公众号: openid={from_user[:16]}...")
            
            # 检查是否通过扫码关注
            scene_id = None
            if event_key and event_key.startswith('qrscene_'):
                scene_id_str = event_key.replace('qrscene_', '')
                try:
                    scene_id = int(scene_id_str)  # 转换为整数
                    logger.info(f"扫码关注: scene_id={scene_id} (从'{scene_id_str}'转换)")
                except ValueError:
                    logger.error(f"scene_id转换失败: '{scene_id_str}'")
                    scene_id = None
            
            # 保存用户到数据库
            async with db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """SELECT id FROM wechat_users WHERE openid = %s""",
                        (from_user,)
                    )
                    exists = await cursor.fetchone()
                    
                    if not exists:
                        # 创建新用户，首次关注给予10张额度
                        await cursor.execute(
                            """INSERT INTO wechat_users 
                               (openid, total_credits, remaining_credits, used_credits)
                               VALUES (%s, 10, 10, 0)""",
                            (from_user,)
                        )
                        logger.info(f"创建新用户: openid={from_user[:16]}..., 额度=10")
                    else:
                        # 更新最后活跃时间
                        await cursor.execute(
                            """UPDATE wechat_users SET last_active_time = NOW() WHERE openid = %s""",
                            (from_user,)
                        )
                        logger.info(f"用户已存在，更新活跃时间: openid={from_user[:16]}...")
                    
                    # 如果通过扫码关注，更新 scene_id -> openid 映射
                    if scene_id:
                        await cursor.execute(
                            """UPDATE wechat_qrcode_bindings 
                               SET openid = %s, status = 'completed', completed_at = NOW()
                               WHERE scene_id = %s""",
                            (from_user, scene_id)
                        )
                        logger.info(f"更新二维码绑定: scene_id={scene_id} -> openid={from_user[:16]}...")
                    
                    await conn.commit()
            
            # 返回欢迎消息
            reply = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[欢迎关注！您已获得10张图片编辑额度。]]></Content>
</xml>"""
            return PlainTextResponse(content=reply)
        
        # 处理扫码事件（已关注的用户扫描带参数二维码）
        elif msg_type == 'event' and event == 'SCAN':
            logger.info(f"已关注用户扫码: openid={from_user[:16]}...")
            
            # EventKey 直接是场景值（不包含qrscene_前缀）
            scene_id = None
            if event_key:
                try:
                    scene_id = int(event_key)  # 转换为整数
                    logger.info(f"扫码事件: scene_id={scene_id} (从'{event_key}'转换)")
                except ValueError:
                    logger.error(f"scene_id转换失败: '{event_key}'")
                    scene_id = None
            
            if scene_id:
                # 更新 scene_id -> openid 映射（仅在状态为pending时更新）
                async with db.get_connection() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """UPDATE wechat_qrcode_bindings 
                               SET openid = %s, status = 'completed', completed_at = NOW()
                               WHERE scene_id = %s AND status = 'pending'""",
                            (from_user, scene_id)
                        )
                        await conn.commit()
                        logger.info(f"更新二维码绑定: scene_id={scene_id} -> openid={from_user[:16]}...")
            
            return PlainTextResponse(content="")
        
        # 处理取消关注事件
        elif msg_type == 'event' and event == 'unsubscribe':
            logger.info(f"用户取消关注: openid={from_user[:16]}...")
            return PlainTextResponse(content="")
        
        # 其他事件或消息，返回空响应
        else:
            return PlainTextResponse(content="")
            
    except Exception as e:
        logger.error(f"处理微信消息异常: {e}", exc_info=True)
        return PlainTextResponse(content="")


@router.get("/wechat/check-follow", summary="检查用户是否已关注公众号")
async def check_follow(client_id: str):
    """
    通过client_id查询用户是否已关注公众号
    
    返回：
    - subscribed: True表示已关注，False表示未关注
    - completed_at: 如果已关注，返回关注完成时间
    """
    try:
        client_id = client_id.strip()  # 去除前后空格
        logger.info(f"检查关注状态: client_id='{client_id}'")
        
        # 查询client_id -> openid映射
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 查询特定client_id（必须status=completed才有openid）
                await cursor.execute(
                    """SELECT openid, status, completed_at
                       FROM wechat_qrcode_bindings
                       WHERE client_id = %s AND status = 'completed'""",
                    (client_id,)
                )
                binding = await cursor.fetchone()
                
                if binding and binding['openid']:
                    logger.info(f"用户已关注: client_id={client_id}")
                    return {
                        "subscribed": True,
                        "completed_at": str(binding['completed_at'])
                    }
                else:
                    logger.info(f"用户未关注: client_id={client_id}")
                    return {
                        "subscribed": False
                    }
                    
    except Exception as e:
        logger.error(f"检查关注状态异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="检查失败")


# ===== 微信公众号菜单管理 =====

@router.get("/wechat/get-menu", summary="查询当前微信公众号菜单")
async def get_wechat_menu():
    """
    查询当前微信公众号菜单
    """
    try:
        logger.info("开始查询微信公众号菜单...")
        
        # 获取access_token
        token_response = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                'grant_type': 'client_credential',
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET
            },
            timeout=10
        ).json()
        
        if 'errcode' in token_response:
            logger.error(f"获取access_token失败: {token_response}")
            raise HTTPException(status_code=400, detail="获取access_token失败")
        
        access_token = token_response['access_token']
        
        # 查询菜单
        get_response = requests.get(
            f"https://api.weixin.qq.com/cgi-bin/menu/get?access_token={access_token}",
            timeout=10
        ).json()
        
        if 'menu' in get_response:
            logger.info("菜单查询成功")
            return {
                "success": True,
                "menu": get_response.get('menu'),
                "conditionalmenu": get_response.get('conditionalmenu')
            }
        else:
            logger.warning(f"菜单查询结果: {get_response}")
            return {
                "success": True,
                "message": "当前没有菜单或查询失败",
                "response": get_response
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询菜单异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询菜单失败")


@router.post("/wechat/create-menu", summary="创建微信公众号菜单")
async def create_wechat_menu():
    """
    创建微信公众号菜单
    一级菜单：芯图相册、会员服务
    会员服务二级菜单：开通会员、购买额度、额度查询
    """
    try:
        logger.info("开始创建微信公众号菜单...")
        
        # 检查微信配置
        if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
            error_msg = f"微信配置缺失: APPID={bool(settings.WECHAT_APPID)}, SECRET={bool(settings.WECHAT_SECRET)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 获取access_token
        logger.info(f"正在获取access_token, APPID: {settings.WECHAT_APPID[:8]}...")
        token_response = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                'grant_type': 'client_credential',
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET
            },
            timeout=10
        ).json()
        
        if 'errcode' in token_response:
            error_msg = f"获取access_token失败: {token_response.get('errmsg', '未知错误')} (错误码: {token_response.get('errcode')})"
            logger.error(f"微信API返回错误: {token_response}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        access_token = token_response['access_token']
        logger.info(f"成功获取access_token: {access_token[:20]}...")
        
        # 先删除旧菜单
        logger.info("正在删除旧菜单...")
        delete_response = requests.get(
            f"https://api.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}",
            timeout=10
        ).json()
        if delete_response.get('errcode') == 0:
            logger.info("旧菜单删除成功")
        else:
            logger.warning(f"删除旧菜单失败（可能不存在）: {delete_response}")
        
        # 定义菜单结构（使用网页授权URL）
        # 注意：微信网页授权需要跳转到授权页面获取code，然后回调到目标页面
        from urllib.parse import quote
        
        auth_base_url = "https://open.weixin.qq.com/connect/oauth2/authorize"
        appid = settings.WECHAT_APPID
        
        # 构建授权URL（redirect_uri需要URL编码）
        member_url = f"{auth_base_url}?appid={appid}&redirect_uri={quote('https://www.xintuxiangce.top/wechat/member.html')}&response_type=code&scope=snsapi_base&state=member#wechat_redirect"
        credits_url = f"{auth_base_url}?appid={appid}&redirect_uri={quote('https://www.xintuxiangce.top/wechat/credits.html')}&response_type=code&scope=snsapi_base&state=credits#wechat_redirect"
        credits_info_url = f"{auth_base_url}?appid={appid}&redirect_uri={quote('https://www.xintuxiangce.top/wechat/credits_info.html')}&response_type=code&scope=snsapi_base&state=credits_info#wechat_redirect"
        
        # 芯图相册直接跳转URL（不需要授权）
        xintu_url = "https://www.xintuxiangce.top"
        
        menu_data = {
            "button": [
                {
                    "type": "view",
                    "name": "芯图相册",
                    "url": xintu_url
                },
                {
                    "name": "会员服务",
                    "sub_button": [
                        {
                            "type": "view",
                            "name": "开通会员",
                            "url": member_url
                        },
                        {
                            "type": "view",
                            "name": "购买额度",
                            "url": credits_url
                        },
                        {
                            "type": "view",
                            "name": "额度查询",
                            "url": credits_info_url
                        }
                    ]
                }
            ]
        }
        
        # 打印菜单结构（用于调试）
        logger.info("菜单结构:")
        logger.info(json.dumps(menu_data, indent=2, ensure_ascii=False))
        
        # 调用微信菜单创建接口（使用data参数确保UTF-8编码）
        menu_json = json.dumps(menu_data, ensure_ascii=False).encode('utf-8')
        
        logger.info("正在创建新菜单...")
        create_response = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}",
            data=menu_json,
            headers={'Content-Type': 'application/json'},
            timeout=10
        ).json()
        
        logger.info(f"微信API响应: {json.dumps(create_response, ensure_ascii=False)}")
        
        if create_response.get('errcode') == 0:
            logger.info("公众号菜单创建成功")
            return {
                "success": True,
                "message": "菜单创建成功",
                "menu_structure": menu_data,
                "wechat_response": create_response
            }
        else:
            logger.error(f"菜单创建失败: {create_response}")
            raise HTTPException(status_code=400, detail=f"菜单创建失败: {create_response.get('errmsg', '未知错误')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建菜单异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建菜单失败")
