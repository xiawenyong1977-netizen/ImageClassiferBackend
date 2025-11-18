#!/usr/bin/env python3
"""
直接删除指定图片哈希的缓存数据
"""

import asyncio
import sys
from app.database import db
from loguru import logger

async def delete_cache_by_hash(image_hash: str):
    """根据图片哈希删除缓存"""
    try:
        await db.connect()
        
        async with db.get_cursor() as cursor:
            # 先查看缓存记录
            await cursor.execute('''
                SELECT image_hash, category, confidence, hit_count, created_at, last_hit_at
                FROM image_classification_cache 
                WHERE image_hash = %s
            ''', (image_hash,))
            record = await cursor.fetchone()
            
            if record:
                print(f"找到缓存记录:")
                print(f"  哈希: {record['image_hash']}")
                print(f"  分类: {record['category']}")
                print(f"  置信度: {record['confidence']}")
                print(f"  命中次数: {record['hit_count']}")
                print(f"  创建时间: {record['created_at']}")
                print(f"  最后命中: {record['last_hit_at']}")
                
                # 确认删除
                print(f"\n确认删除这条缓存记录吗？")
                response = input("输入 'YES' 确认删除: ").strip()
                
                if response == 'YES':
                    # 删除记录
                    await cursor.execute('''
                        DELETE FROM image_classification_cache 
                        WHERE image_hash = %s
                    ''', (image_hash,))
                    
                    if cursor.rowcount > 0:
                        print(f"✅ 成功删除缓存记录")
                        return True
                    else:
                        print(f"❌ 删除失败")
                        return False
                else:
                    print("❌ 操作已取消")
                    return False
            else:
                print(f"❌ 未找到哈希为 {image_hash} 的缓存记录")
                return False
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"删除缓存失败: {e}")
        print(f"错误: {e}")
        return False

async def search_cache_by_category(category: str = None):
    """搜索缓存记录"""
    try:
        await db.connect()
        
        async with db.get_cursor() as cursor:
            if category:
                sql = "SELECT image_hash, category, hit_count, created_at FROM image_classification_cache WHERE category = %s ORDER BY created_at DESC LIMIT 20"
                await cursor.execute(sql, (category,))
            else:
                sql = "SELECT image_hash, category, hit_count, created_at FROM image_classification_cache ORDER BY created_at DESC LIMIT 20"
                await cursor.execute(sql)
            
            records = await cursor.fetchall()
            
            if records:
                print(f"找到 {len(records)} 条缓存记录:")
                for i, record in enumerate(records, 1):
                    print(f"{i:2d}. 哈希: {record['image_hash'][:16]}..., 分类: {record['category']}, 命中: {record['hit_count']}, 时间: {record['created_at']}")
            else:
                print("没有找到缓存记录")
        
        await db.disconnect()
        
    except Exception as e:
        logger.error(f"搜索缓存失败: {e}")
        print(f"错误: {e}")

async def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python delete_cache_by_hash.py <image_hash>  # 删除指定哈希的缓存")
        print("  python delete_cache_by_hash.py --search [category]  # 搜索缓存记录")
        sys.exit(1)
    
    if sys.argv[1] == "--search":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        await search_cache_by_category(category)
    else:
        image_hash = sys.argv[1]
        print(f"删除哈希为 {image_hash} 的缓存记录...")
        success = await delete_cache_by_hash(image_hash)
        if success:
            print("🎉 删除操作完成！")
        else:
            print("💥 删除操作失败！")

if __name__ == "__main__":
    asyncio.run(main())
