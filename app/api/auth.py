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


@router.post("/wechat", summary="微信授权登录（已废弃）")
async def wechat_auth(request: WeChatAuthRequest):
    """
    【已废弃】微信授权登录，获取openid
    
    这个接口已经不再使用，请使用扫码关注流程：
    1. POST /api/v1/auth/wechat/qrcode - 生成二维码
    2. GET /api/v1/auth/wechat/check-follow - 检查关注状态
    """
    try:
        logger.info(f"微信授权请求: code={request.code[:20]}...")
        
        # 1. 调用微信API获取access_token
        token_response = requests.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                'appid': settings.WECHAT_APPID,
                'secret': settings.WECHAT_SECRET,
                'code': request.code,
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
        
        # 2. 获取用户信息
        user_info_response = requests.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN'
            },
            timeout=10
        ).json()
        
        if 'errcode' in user_info_response:
            logger.warning(f"获取用户信息失败: {user_info_response}")
            # 如果获取用户信息失败，使用默认值
            nickname = None
            avatar_url = None
        else:
            nickname = user_info_response.get('nickname')
            avatar_url = user_info_response.get('headimgurl')
        
        # 3. 创建或更新用户
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT id FROM wechat_users WHERE openid = %s""",
                    (openid,)
                )
                exists = await cursor.fetchone()
                
                if exists:
                    # 更新用户信息
                    await cursor.execute(
                        """UPDATE wechat_users 
                           SET nickname = %s, avatar_url = %s, last_active_time = NOW()
                           WHERE openid = %s""",
                        (nickname, avatar_url, openid)
                    )
                    logger.info(f"更新用户信息: openid={openid[:16]}...")
                else:
                    # 创建新用户（首次关注，给予100张额度）
                    await cursor.execute(
                        """INSERT INTO wechat_users 
                           (openid, nickname, avatar_url, total_credits, remaining_credits, used_credits)
                           VALUES (%s, %s, %s, 100, 100, 0)""",
                        (openid, nickname, avatar_url)
                    )
                    logger.info(f"创建新用户: openid={openid[:16]}..., 额度=100")
                
                await conn.commit()
        
        return WeChatAuthResponse(
            success=True,
            openid=openid,
            access_token=access_token,
            nickname=nickname,
            avatar_url=avatar_url
        )
        
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
                       ON DUPLICATE KEY UPDATE status = 'pending', created_at = NOW()""",
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
                # 更新 scene_id -> openid 映射
                async with db.get_connection() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(
                            """UPDATE wechat_qrcode_bindings 
                               SET openid = %s, status = 'completed', completed_at = NOW()
                               WHERE scene_id = %s""",
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
    - openid: 如果已关注，返回openid
    """
    try:
        client_id = client_id.strip()  # 去除前后空格
        logger.info(f"检查关注状态: client_id='{client_id}' (length={len(client_id)})")
        
        # 查询client_id -> openid映射
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 先查询数据库中有哪些client_id
                await cursor.execute("SELECT client_id, status FROM wechat_qrcode_bindings")
                all_bindings = await cursor.fetchall()
                logger.info(f"数据库中的所有绑定: {[b['client_id'] for b in all_bindings]}")
                
                # 查询特定client_id（必须status=completed才有openid）
                await cursor.execute(
                    """SELECT b.openid, b.status, b.completed_at
                       FROM wechat_qrcode_bindings b
                       WHERE b.client_id = %s AND b.status = 'completed'""",
                    (client_id,)
                )
                binding = await cursor.fetchone()
                
                logger.info(f"查询结果: binding={binding}, type={type(binding)}")
                if binding:
                    logger.info(f"binding['openid']={binding.get('openid')}, type={type(binding.get('openid'))}")
                    logger.info(f"bool binding={bool(binding)}, bool openid={bool(binding.get('openid'))}")
                
                if binding and binding['openid']:
                    logger.info(f"用户已关注: client_id={client_id}, openid={binding['openid'][:16]}...")
                    return {
                        "subscribed": True,
                        "openid": binding['openid'],
                        "completed_at": str(binding['completed_at'])
                    }
                else:
                    logger.info(f"用户未关注: client_id={client_id}")
                    return {
                        "subscribed": False,
                        "openid": None
                    }
                    
    except Exception as e:
        logger.error(f"检查关注状态异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="检查失败")

