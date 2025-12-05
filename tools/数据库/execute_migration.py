#!/usr/bin/env python3
"""
执行数据库迁移脚本
用于添加 ip_address 字段到 image_edit_tasks 表
"""

import sys
import os
import asyncio
import aiomysql

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from app.config import settings


async def execute_migration():
    """执行迁移脚本"""
    try:
        # 连接数据库
        conn = await aiomysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            charset='utf8mb4'
        )
        
        print(f"✅ 已连接到数据库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        
        async with conn.cursor() as cursor:
            # 检查字段是否已存在
            await cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'image_edit_tasks'
                  AND COLUMN_NAME = 'ip_address'
            """, (settings.MYSQL_DATABASE,))
            
            result = await cursor.fetchone()
            if result and result[0] > 0:
                print("⚠️  字段 ip_address 已存在，跳过添加")
            else:
                # 添加 ip_address 字段
                print("📝 正在添加 ip_address 字段...")
                await cursor.execute("""
                    ALTER TABLE `image_edit_tasks` 
                    ADD COLUMN `ip_address` VARCHAR(45) DEFAULT NULL COMMENT '客户端IP地址' AFTER `user_id`
                """)
                print("✅ ip_address 字段已添加")
                
                # 检查索引是否已存在
                await cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = 'image_edit_tasks'
                      AND INDEX_NAME = 'idx_ip_address'
                """, (settings.MYSQL_DATABASE,))
                
                index_result = await cursor.fetchone()
                if index_result and index_result[0] > 0:
                    print("⚠️  索引 idx_ip_address 已存在，跳过添加")
                else:
                    # 添加索引
                    print("📝 正在添加索引 idx_ip_address...")
                    await cursor.execute("""
                        ALTER TABLE `image_edit_tasks` 
                        ADD KEY `idx_ip_address` (`ip_address`)
                    """)
                    print("✅ 索引 idx_ip_address 已添加")
            
            # 验证表结构
            await cursor.execute("DESC image_edit_tasks")
            columns = await cursor.fetchall()
            print("\n📋 当前表结构:")
            for col in columns:
                if col[0] == 'ip_address':
                    print(f"  ✅ {col[0]}: {col[1]} (索引: idx_ip_address)")
                    break
            else:
                print("  ❌ ip_address 字段未找到")
        
        await conn.commit()
        conn.close()
        print("\n✅ 迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(execute_migration())

