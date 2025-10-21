#!/usr/bin/env python3
"""
检查用户数据的脚本
"""

import asyncio
import sys
from app.database import db
from loguru import logger

async def check_user_data(user_id: str):
    """检查用户数据"""
    try:
        await db.connect()
        
        async with db.get_cursor() as cursor:
            # 检查request_log表中的数据
            await cursor.execute('SELECT COUNT(*) as count FROM request_log WHERE user_id = %s', (user_id,))
            request_log_count = await cursor.fetchone()
            print(f'request_log表中该用户记录数: {request_log_count["count"]}')
            
            if request_log_count["count"] > 0:
                # 查看具体的记录
                await cursor.execute('''
                    SELECT image_hash, category, created_at, from_cache 
                    FROM request_log 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 10
                ''', (user_id,))
                records = await cursor.fetchall()
                print(f'该用户的请求记录:')
                for record in records:
                    print(f'  哈希: {record["image_hash"][:16]}..., 分类: {record["category"]}, 缓存: {record["from_cache"]}, 时间: {record["created_at"]}')
            
            # 检查image_classification_cache表中的数据
            await cursor.execute('SELECT COUNT(*) as count FROM image_classification_cache')
            cache_count = await cursor.fetchone()
            print(f'image_classification_cache表总记录数: {cache_count["count"]}')
            
            # 查看最近的几条记录
            await cursor.execute('''
                SELECT image_hash, category, created_at, hit_count 
                FROM image_classification_cache 
                ORDER BY created_at DESC 
                LIMIT 5
            ''')
            recent_records = await cursor.fetchall()
            print('最近的缓存记录:')
            for record in recent_records:
                print(f'  哈希: {record["image_hash"][:16]}..., 分类: {record["category"]}, 命中: {record["hit_count"]}, 时间: {record["created_at"]}')
            
            # 如果用户有记录，检查这些哈希是否在缓存表中
            if request_log_count["count"] > 0:
                await cursor.execute('''
                    SELECT DISTINCT image_hash 
                    FROM request_log 
                    WHERE user_id = %s
                ''', (user_id,))
                user_hashes = await cursor.fetchall()
                
                if user_hashes:
                    hash_list = [h['image_hash'] for h in user_hashes]
                    placeholders = ','.join(['%s'] * len(hash_list))
                    
                    await cursor.execute(f'''
                        SELECT image_hash, category, hit_count, created_at 
                        FROM image_classification_cache 
                        WHERE image_hash IN ({placeholders})
                    ''', hash_list)
                    cached_records = await cursor.fetchall()
                    
                    print(f'该用户使用过的图片在缓存表中的记录数: {len(cached_records)}')
                    for record in cached_records:
                        print(f'  哈希: {record["image_hash"][:16]}..., 分类: {record["category"]}, 命中: {record["hit_count"]}, 时间: {record["created_at"]}')
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"检查用户数据失败: {e}")
        print(f"错误: {e}")

async def main():
    user_id = "f57742ff-6278-453b-8410-ae6b4466b627userid"
    print(f"检查用户 {user_id} 的数据...")
    await check_user_data(user_id)

if __name__ == "__main__":
    asyncio.run(main())
