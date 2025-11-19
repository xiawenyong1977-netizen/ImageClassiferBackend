#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付相关API路由
"""

import logging
import hashlib
import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import aiomysql
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import time

from app.config import settings
from app.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payment", tags=["支付"])


# ===== 数据模型 =====

class CreateOrderRequest(BaseModel):
    """创建订单请求"""
    order_type: str = Field(..., description="订单类型：member-会员开通，credits-额度购买")
    credits_amount: int = Field(None, description="额度数量（仅type=credits时必填）")


class PaymentOrderResponse(BaseModel):
    """支付订单响应"""
    success: bool
    order_no: str
    payment_params: dict = None


# ===== 工具函数 =====

def generate_order_no() -> str:
    """生成唯一订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


def generate_nonce_str() -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def generate_sign(params: dict) -> str:
    """生成微信支付签名"""
    filtered_params = {k: v for k, v in params.items() if v and k != 'sign'}
    sorted_params = sorted(filtered_params.items())
    string_sign_temp = '&'.join([f"{k}={v}" for k, v in sorted_params])
    string_sign_temp += f"&key={settings.WECHAT_PAY_API_KEY}"
    return hashlib.md5(string_sign_temp.encode('utf-8')).hexdigest().upper()


def dict_to_xml(d: dict) -> str:
    """将字典转换为XML字符串"""
    xml = '<xml>'
    for k, v in d.items():
        xml += f'<{k}><![CDATA[{v}]]></{k}>'
    xml += '</xml>'
    return xml


def xml_to_dict(xml_str: str) -> dict:
    """将XML字符串转换为字典"""
    root = ET.fromstring(xml_str)
    result = {}
    for child in root:
        result[child.tag] = child.text
    return result


def call_wechat_pay_unifiedorder(order_no: str, openid: str, amount: float, description: str) -> dict:
    """调用微信支付统一下单接口"""
    notify_url = settings.WECHAT_PAY_NOTIFY_URL
    logger.info(f"支付回调URL配置: {notify_url}")
    
    params = {
        'appid': settings.WECHAT_APPID,
        'mch_id': settings.WECHAT_PAY_MCHID,
        'nonce_str': generate_nonce_str(),
        'body': description,
        'out_trade_no': order_no,
        'total_fee': int(amount * 100),
        'spbill_create_ip': '127.0.0.1',
        'notify_url': notify_url,
        'trade_type': 'JSAPI',
        'openid': openid
    }
    params['sign'] = generate_sign(params)
    url = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
    xml_data = dict_to_xml(params)
    logger.info(f"调用微信支付统一下单: order_no={order_no}, amount={amount}, notify_url={notify_url}, openid={openid[:16]}...")
    response = requests.post(url, data=xml_data.encode('utf-8'), timeout=10)
    response.raise_for_status()
    result = xml_to_dict(response.text)
    if result.get('return_code') != 'SUCCESS':
        logger.error(f"微信支付统一下单失败: {result}")
        raise HTTPException(status_code=400, detail=f"支付下单失败: {result.get('return_msg')}")
    if result.get('result_code') != 'SUCCESS':
        logger.error(f"微信支付统一下单失败: {result}")
        raise HTTPException(status_code=400, detail=f"支付下单失败: {result.get('err_code_des')}")
    prepay_id = result.get('prepay_id')
    payment_params = {
        'appId': settings.WECHAT_APPID,
        'timeStamp': str(int(time.time())),
        'nonceStr': generate_nonce_str(),
        'package': f'prepay_id={prepay_id}',
        'signType': 'MD5'
    }
    payment_params['paySign'] = generate_sign(payment_params)
    logger.info(f"统一下单成功: order_no={order_no}, prepay_id={prepay_id}")
    return payment_params


# ===== 微信支付接口 =====

@router.post("/create-order", summary="创建支付订单")
async def create_order(
    request: CreateOrderRequest,
    x_wechat_openid: str = Header(None, alias="X-WeChat-OpenID")
):
    """
    创建支付订单
    
    订单类型：
    - member: 会员开通（固定价格，例如29.9元/月）
    - credits: 购买额度（需要指定数量，例如10张）
    """
    try:
        if not x_wechat_openid:
            raise HTTPException(status_code=401, detail="请先关注公众号并扫码")
        
        openid = x_wechat_openid
        
        # 验证订单类型
        if request.order_type not in ['member', 'credits']:
            raise HTTPException(status_code=400, detail="无效的订单类型")
        
        # 校验会员开通订单
        if request.order_type == 'member':
            async with db.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT is_member, member_expire_at FROM wechat_users WHERE openid = %s",
                        (openid,)
                    )
                    user = await cursor.fetchone()
                    
                    if user and user[0] and user[1] and user[1] > datetime.now():
                        raise HTTPException(status_code=400, detail="您已经是会员，无需重复开通")
        
        # 计算额度数量和订单金额
        if request.order_type == 'credits':
            # 额度订单：使用前端传入的数量，或配置的默认数量
            credits_amount = request.credits_amount if request.credits_amount else (settings.CREDITS_AMOUNT_TEST if settings.USE_TEST_PRICE else settings.CREDITS_AMOUNT_PROD)
            # 价格 = 数量 × 单价
            if settings.USE_TEST_PRICE:
                amount = credits_amount * settings.CREDITS_PRICE_TEST
            else:
                amount = credits_amount * settings.CREDITS_PRICE_PROD
        else:
            # 会员订单
            credits_amount = request.credits_amount
            amount = settings.MEMBER_PRICE_TEST if settings.USE_TEST_PRICE else settings.MEMBER_PRICE_PROD
        
        # 生成订单号
        order_no = generate_order_no()
        
        # 保存订单到数据库
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """INSERT INTO payment_orders 
                       (order_no, openid, order_type, amount, credits_amount, status, expire_at)
                       VALUES (%s, %s, %s, %s, %s, 'pending', DATE_ADD(NOW(), INTERVAL 30 MINUTE))""",
                    (order_no, openid, request.order_type, amount, credits_amount)
                )
                await conn.commit()
        
        logger.info(f"创建订单成功: order_no={order_no}, openid={openid[:16]}..., type={request.order_type}, amount={amount}")
        
        # 调用微信支付统一下单接口
        description = "会员开通" if request.order_type == 'member' else f"购买{request.credits_amount}张图片编辑额度"
        logger.info(f"准备调用微信支付接口，描述={description}")
        payment_params = call_wechat_pay_unifiedorder(order_no, openid, amount, description)
        logger.info(f"微信支付接口调用成功，返回prepay_id")
        
        return {
            "success": True,
            "order_no": order_no,
            "amount": amount,
            "payment_params": payment_params,
            "message": "订单创建成功，正在调起支付..."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建订单异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建订单失败")


@router.post("/notify", summary="微信支付回调通知")
async def payment_notify(request: Request):
    """
    微信支付回调通知接口
    
    接收微信支付的异步通知，更新订单状态
    """
    try:
        # 获取回调数据
        body = await request.body()
        logger.info(f"收到支付回调，数据长度: {len(body)}")
        
        # 解析XML
        root = ET.fromstring(body)
        
        # 提取关键信息
        return_code = root.find('return_code').text
        result_code = root.find('result_code').text if root.find('result_code') is not None else None
        
        if return_code != 'SUCCESS' or result_code != 'SUCCESS':
            logger.warning(f"支付回调失败: return_code={return_code}, result_code={result_code}")
            return PlainTextResponse(content="<xml><return_code><![CDATA[FAIL]]></return_code></xml>")
        
        # 提取订单信息
        transaction_id = root.find('transaction_id').text
        out_trade_no = root.find('out_trade_no').text  # 我们的订单号
        total_fee = int(root.find('total_fee').text) / 100  # 转换为元
        openid = root.find('openid').text
        time_end = root.find('time_end').text
        
        logger.info(f"支付成功: order_no={out_trade_no}, transaction_id={transaction_id}, amount={total_fee}")
        
        # TODO: 验证签名
        # if not verify_signature(...):
        #     return PlainTextResponse(content="<xml><return_code><![CDATA[FAIL]]></return_code></xml>")
        
        # 查询订单
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """SELECT id, order_type, credits_amount, status 
                       FROM payment_orders 
                       WHERE order_no = %s""",
                    (out_trade_no,)
                )
                order = await cursor.fetchone()
                
                if not order:
                    logger.error(f"订单不存在: order_no={out_trade_no}")
                    return PlainTextResponse(content="<xml><return_code><![CDATA[FAIL]]></return_code></xml>")
                
                # 防止重复处理
                if order[3] == 'paid':
                    logger.info(f"订单已处理: order_no={out_trade_no}")
                    return PlainTextResponse(content="<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>")
                
                order_id, order_type, credits_amount, status = order
                
                # 更新订单状态
                await cursor.execute(
                    """UPDATE payment_orders 
                       SET status = 'paid', 
                           wx_payment_no = %s,
                           wx_transaction_id = %s,
                           paid_at = NOW()
                       WHERE id = %s""",
                    (transaction_id, transaction_id, order_id)
                )
                
                # 处理会员开通
                if order_type == 'member':
                    # 更新会员状态（有效期30天），并赠送10个免费额度
                    expire_at = datetime.now() + timedelta(days=30)
                    free_credits = 10  # 会员赠送额度
                    await cursor.execute(
                        """UPDATE wechat_users 
                           SET is_member = 1, 
                               member_expire_at = %s,
                               remaining_credits = remaining_credits + %s,
                               total_credits = total_credits + %s,
                               total_paid_amount = total_paid_amount + %s
                           WHERE openid = %s""",
                        (expire_at, free_credits, free_credits, total_fee, openid)
                    )
                    logger.info(f"会员开通成功: openid={openid[:16]}..., expire_at={expire_at}, 赠送额度={free_credits}")
                
                # 处理额度购买
                elif order_type == 'credits':
                    # 增加用户额度
                    await cursor.execute(
                        """UPDATE wechat_users 
                           SET remaining_credits = remaining_credits + %s,
                               total_credits = total_credits + %s,
                               total_paid_amount = total_paid_amount + %s
                           WHERE openid = %s""",
                        (credits_amount, credits_amount, total_fee, openid)
                    )
                    logger.info(f"额度购买成功: openid={openid[:16]}..., credits={credits_amount}")
                
                # 保存支付记录
                await cursor.execute(
                    """INSERT INTO payment_records 
                       (order_no, openid, transaction_id, amount, payment_time, notify_data)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (out_trade_no, openid, transaction_id, total_fee, datetime.now(), body.decode('utf-8'))
                )
                
                await conn.commit()
        
        # 返回成功响应
        return PlainTextResponse(content="<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>")
        
    except Exception as e:
        logger.error(f"支付回调处理异常: {e}", exc_info=True)
        return PlainTextResponse(content="<xml><return_code><![CDATA[FAIL]]></return_code></xml>")


@router.get("/prices", summary="获取价格配置")
async def get_prices():
    """
    获取价格配置（公开接口，无需认证）
    返回会员价格和额度价格配置
    """
    try:
        # 解析套餐数量列表（用分号分隔）
        if settings.USE_TEST_PRICE:
            credits_amounts_str = settings.CREDITS_AMOUNTS_TEST
            credits_price = settings.CREDITS_PRICE_TEST
        else:
            credits_amounts_str = settings.CREDITS_AMOUNTS_PROD
            credits_price = settings.CREDITS_PRICE_PROD
        
        # 解析套餐数量列表
        credits_amounts = []
        if credits_amounts_str:
            for amount_str in credits_amounts_str.split(';'):
                amount_str = amount_str.strip()
                if amount_str:
                    try:
                        amount = int(amount_str)
                        if amount > 0:
                            credits_amounts.append(amount)
                    except ValueError:
                        continue
        
        # 如果没有配置，使用默认值
        if not credits_amounts:
            if settings.USE_TEST_PRICE:
                credits_amounts = [settings.CREDITS_AMOUNT_TEST]
            else:
                credits_amounts = [settings.CREDITS_AMOUNT_PROD]
        
        # 生成套餐列表
        packages = []
        for amount in credits_amounts:
            packages.append({
                "credits": amount,
                "price": amount * credits_price
            })
        
        return {
            "success": True,
            "data": {
                "member_price": settings.MEMBER_PRICE_TEST if settings.USE_TEST_PRICE else settings.MEMBER_PRICE_PROD,
                "credits_price": credits_price,
                "credits_amount": credits_amounts[0] if credits_amounts else 0,  # 保留兼容性
                "credits_packages": packages,  # 新增：套餐列表
                "is_test_price": settings.USE_TEST_PRICE
            }
        }
    except Exception as e:
        logger.error(f"获取价格配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", summary="查询订单列表")
async def get_orders(
    x_wechat_openid: str = Header(None, alias="X-WeChat-OpenID")
):
    """
    查询用户的订单列表
    """
    try:
        if not x_wechat_openid:
            raise HTTPException(status_code=401, detail="请先关注公众号并扫码")
        
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """SELECT order_no, order_type, amount, credits_amount, status, created_at, paid_at
                       FROM payment_orders 
                       WHERE openid = %s 
                       ORDER BY created_at DESC 
                       LIMIT 50""",
                    (x_wechat_openid,)
                )
                orders = await cursor.fetchall()
        
        return {
            "success": True,
            "orders": orders
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询订单异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")

