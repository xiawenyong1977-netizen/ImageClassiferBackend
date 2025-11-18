#!/usr/bin/env python3
"""
删除指定用户的图片分类缓存数据
通过request_log表找到用户使用过的图片哈希，然后删除image_classification_cache中对应的记录
"""

import asyncio
import sys
from typing import List, Optional
from app.database import db
from app.config import settings
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

class UserCacheDeleter:
    """用户缓存删除器"""
    
    def __init__(self):
        self.user_id = None
        
    async def delete_user_cache(self, user_id: str, confirm: bool = False) -> bool:
        """
        删除指定用户的所有缓存数据
        
        Args:
            user_id: 用户ID
            confirm: 是否确认删除（安全机制）
            
        Returns:
            是否删除成功
        """
        self.user_id = user_id
        
        if not confirm:
            print(f"⚠️  警告：即将删除用户 {user_id} 的所有缓存数据！")
            print("此操作不可逆，请确认是否继续？")
            response = input("请输入 'YES' 确认删除，或按任意键取消: ").strip()
            if response != 'YES':
                print("❌ 操作已取消")
                return False
        
        try:
            # 连接数据库
            await db.connect()
            
            # 1. 查找该用户使用过的所有图片哈希
            image_hashes = await self._get_user_image_hashes()
            if not image_hashes:
                print(f"✅ 用户 {user_id} 没有找到任何缓存数据")
                return True
            
            print(f"📋 找到用户 {user_id} 使用过的 {len(image_hashes)} 个图片哈希")
            
            # 2. 显示将要删除的缓存记录信息
            await self._show_cache_info(image_hashes)
            
            # 3. 删除缓存记录
            deleted_count = await self._delete_cache_records(image_hashes)
            
            print(f"✅ 成功删除 {deleted_count} 条缓存记录")
            print(f"🎯 用户 {user_id} 的缓存数据清理完成")
            
            return True
            
        except Exception as e:
            logger.error(f"删除用户缓存失败: {e}")
            print(f"❌ 删除失败: {e}")
            return False
        finally:
            await db.disconnect()
    
    async def _get_user_image_hashes(self) -> List[str]:
        """获取用户使用过的所有图片哈希"""
        try:
            async with db.get_cursor() as cursor:
                sql = """
                SELECT DISTINCT image_hash 
                FROM request_log 
                WHERE user_id = %s
                """
                await cursor.execute(sql, (self.user_id,))
                results = await cursor.fetchall()
                
                return [row['image_hash'] for row in results]
                
        except Exception as e:
            logger.error(f"查询用户图片哈希失败: {e}")
            raise
    
    async def _show_cache_info(self, image_hashes: List[str]) -> None:
        """显示将要删除的缓存信息"""
        try:
            async with db.get_cursor() as cursor:
                # 查询这些哈希对应的缓存记录
                placeholders = ','.join(['%s'] * len(image_hashes))
                sql = f"""
                SELECT 
                    image_hash,
                    category,
                    confidence,
                    hit_count,
                    created_at,
                    last_hit_at
                FROM image_classification_cache 
                WHERE image_hash IN ({placeholders})
                ORDER BY created_at DESC
                """
                await cursor.execute(sql, image_hashes)
                results = await cursor.fetchall()
                
                if results:
                    print(f"\n📊 将要删除的缓存记录详情:")
                    print("-" * 80)
                    for i, record in enumerate(results, 1):
                        print(f"{i:2d}. 哈希: {record['image_hash'][:16]}...")
                        print(f"    分类: {record['category']}")
                        print(f"    置信度: {record['confidence']:.4f}")
                        print(f"    命中次数: {record['hit_count']}")
                        print(f"    创建时间: {record['created_at']}")
                        print(f"    最后命中: {record['last_hit_at']}")
                        print()
                else:
                    print("⚠️  警告：这些图片哈希在缓存表中没有找到对应记录")
                    print("可能是缓存数据已经被清理或从未被缓存")
                
        except Exception as e:
            logger.error(f"查询缓存信息失败: {e}")
            raise
    
    async def _delete_cache_records(self, image_hashes: List[str]) -> int:
        """删除缓存记录"""
        if not image_hashes:
            return 0
            
        try:
            async with db.get_cursor() as cursor:
                placeholders = ','.join(['%s'] * len(image_hashes))
                sql = f"""
                DELETE FROM image_classification_cache 
                WHERE image_hash IN ({placeholders})
                """
                await cursor.execute(sql, image_hashes)
                deleted_count = cursor.rowcount
                
                logger.info(f"删除了 {deleted_count} 条缓存记录")
                return deleted_count
                
        except Exception as e:
            logger.error(f"删除缓存记录失败: {e}")
            raise

async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python delete_user_cache.py <user_id> [--confirm]")
        print("示例: python delete_user_cache.py f57742ff-6278-453b-8410-ae6b4466b627userid")
        print("示例: python delete_user_cache.py f57742ff-6278-453b-8410-ae6b4466b627userid --confirm")
        sys.exit(1)
    
    user_id = sys.argv[1]
    confirm = "--confirm" in sys.argv
    
    print(f"🚀 开始删除用户 {user_id} 的缓存数据...")
    print(f"📅 时间: {asyncio.get_event_loop().time()}")
    print(f"🔧 配置: 数据库={settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    print()
    
    deleter = UserCacheDeleter()
    success = await deleter.delete_user_cache(user_id, confirm)
    
    if success:
        print("\n🎉 删除操作完成！")
        sys.exit(0)
    else:
        print("\n💥 删除操作失败！")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
