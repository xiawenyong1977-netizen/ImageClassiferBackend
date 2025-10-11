#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证相关API路由
"""

from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import authenticate_user, create_access_token, Token
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
    
    **示例:**
    ```json
    {
      "username": "zywl",
      "password": "zywl@123"
    }
    ```
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
    """
    登出接口（客户端删除token即可）
    """
    return {"message": "登出成功"}

