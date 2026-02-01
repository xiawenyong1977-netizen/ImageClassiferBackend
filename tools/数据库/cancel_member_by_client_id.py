#!/usr/bin/env python3
"""
根据 client_id 查询 openid 并取消会员状态
使用方法：python cancel_member_by_client_id.py <client_id>
"""

import sys
import asyncio
import aiomysql
from app.database import db
from loguru import logger


async def cancel_member_by_client_id(client_id: str):
    """
    根据 client_id 查询 openid 并取消会员状态
    
    Args:
        client_id: 客户端ID
    """
    if not client_id:
        print("错误：请提供 client_id")
        return
    
    try:
        async with db.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. 查询该 client_id 对应的 openid
                await cursor.execute("""
                    SELECT 
                        b.client_id,
                        b.openid,
                        b.status,
                        b.completed_at,
                        u.is_member,
                        u.member_expire_at,
                        u.total_credits,
                        u.remaining_credits,
                        u.nickname
                    FROM wechat_qrcode_bindings b
                    LEFT JOIN wechat_users u ON b.openid = u.openid
                    WHERE b.client_id = %s 
                      AND b.openid IS NOT NULL
                    ORDER BY b.completed_at DESC, b.id DESC
                    LIMIT 1
                """, (client_id,))
                
                binding = await cursor.fetchone()
                
                if not binding:
                    print(f"❌ 未找到 client_id={client_id} 对应的 openid")
                    return
                
                if not binding['openid']:
                    print(f"❌ client_id={client_id} 对应的 openid 为空")
                    return
                
                openid = binding['openid']
                print(f"\n📋 查询结果：")
                print(f"  client_id: {binding['client_id']}")
                print(f"  openid: {openid}")
                print(f"  当前会员状态: {'是会员' if binding['is_member'] else '非会员'}")
                print(f"  会员到期时间: {binding['member_expire_at'] or '无'}")
                print(f"  总额度: {binding['total_credits']}")
                print(f"  剩余额度: {binding['remaining_credits']}")
                print(f"  昵称: {binding['nickname'] or '无'}")
                
                # 2. 取消会员状态
                await cursor.execute("""
                    UPDATE wechat_users 
                    SET 
                        is_member = 0,
                        member_expire_at = NULL,
                        updated_at = NOW()
                    WHERE openid = %s
                """, (openid,))
                
                affected_rows = cursor.rowcount
                
                if affected_rows > 0:
                    await conn.commit()
                    print(f"\n✅ 成功取消会员状态！")
                    print(f"  受影响行数: {affected_rows}")
                    
                    # 3. 验证更新结果
                    await cursor.execute("""
                        SELECT 
                            openid,
                            is_member,
                            member_expire_at,
                            total_credits,
                            remaining_credits,
                            updated_at,
                            nickname
                        FROM wechat_users
                        WHERE openid = %s
                    """, (openid,))
                    
                    user = await cursor.fetchone()
                    if user:
                        print(f"\n📊 更新后的状态：")
                        print(f"  openid: {user['openid']}")
                        print(f"  会员状态: {'是会员' if user['is_member'] else '非会员'}")
                        print(f"  会员到期时间: {user['member_expire_at'] or '无'}")
                        print(f"  总额度: {user['total_credits']}")
                        print(f"  剩余额度: {user['remaining_credits']}")
                        print(f"  更新时间: {user['updated_at']}")
                else:
                    print(f"\n⚠️  未找到对应的用户记录，可能用户不存在")
                    
    except Exception as e:
        logger.error(f"取消会员状态失败: {e}", exc_info=True)
        print(f"\n❌ 操作失败: {e}")
        raise


async def main():
    if len(sys.argv) < 2:
        print("使用方法: python cancel_member_by_client_id.py <client_id>")
        print("示例: python cancel_member_by_client_id.py d2dca4de-8de1-496f-84c7-1710a0e7263a")
        sys.exit(1)
    
    client_id = sys.argv[1].strip()
    await cancel_member_by_client_id(client_id)


if __name__ == "__main__":
    asyncio.run(main())
