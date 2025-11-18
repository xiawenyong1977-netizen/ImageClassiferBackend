#!/usr/bin/env python3
"""
检查request_log表中的用户ID
"""

import asyncio
import sys
from app.database import db
from loguru import logger

async def check_user_ids():
    """检查request_log表中的用户ID"""
    try:
        await db.connect()
        
        async with db.get_cursor() as cursor:
            # 查看request_log表中所有的user_id
            await cursor.execute('SELECT DISTINCT user_id FROM request_log WHERE user_id IS NOT NULL ORDER BY user_id')
            user_ids = await cursor.fetchall()
            
            print('request_log表中所有的user_id:')
            for i, record in enumerate(user_ids, 1):
                print(f'{i:2d}. {record["user_id"]}')
            
            # 查看包含f57742ff的记录
            await cursor.execute('SELECT user_id, image_hash, created_at FROM request_log WHERE user_id LIKE %s', ('%f57742ff%',))
            matching_records = await cursor.fetchall()
            
            if matching_records:
                print(f'\n包含f57742ff的记录:')
                for record in matching_records:
                    print(f'  user_id: {record["user_id"]}, 哈希: {record["image_hash"][:16]}..., 时间: {record["created_at"]}')
            else:
                print('\n没有找到包含f57742ff的记录')
            
            # 查看最近的记录
            await cursor.execute('SELECT user_id, image_hash, created_at FROM request_log ORDER BY created_at DESC LIMIT 10')
            recent_records = await cursor.fetchall()
            
            print(f'\n最近的10条记录:')
            for record in recent_records:
                print(f'  user_id: {record["user_id"]}, 哈希: {record["image_hash"][:16]}..., 时间: {record["created_at"]}')
            
            # 查看总记录数
            await cursor.execute('SELECT COUNT(*) as total FROM request_log')
            total_count = await cursor.fetchone()
            print(f'\nrequest_log表总记录数: {total_count["total"]}')
            
            # 查看有user_id的记录数
            await cursor.execute('SELECT COUNT(*) as count FROM request_log WHERE user_id IS NOT NULL')
            with_user_id_count = await cursor.fetchone()
            print(f'有user_id的记录数: {with_user_id_count["count"]}')
            
            # 查看没有user_id的记录数
            await cursor.execute('SELECT COUNT(*) as count FROM request_log WHERE user_id IS NULL')
            without_user_id_count = await cursor.fetchone()
            print(f'没有user_id的记录数: {without_user_id_count["count"]}')
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"检查用户ID失败: {e}")
        print(f"错误: {e}")

async def main():
    print("检查request_log表中的用户ID...")
    await check_user_ids()

if __name__ == "__main__":
    asyncio.run(main())
