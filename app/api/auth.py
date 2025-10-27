#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证相关API路由
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import requests
import logging
import aiomysql

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
        logger.info("微信服务器验证成功")
        return echostr
    else:
        logger.warning(f"微信服务器验证失败: signature={signature}, hashcode={hashcode}")
        raise HTTPException(status_code=403, detail="验证失败")


@router.post("/wechat", summary="微信授权登录")
async def wechat_auth(request: WeChatAuthRequest):
    """
    微信授权登录，获取openid
    
    1. 接收客户端传来的code
    2. 调用微信API获取openid和access_token
    3. 获取用户信息
    4. 创建或更新用户记录
    5. 返回openid和用户信息
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

