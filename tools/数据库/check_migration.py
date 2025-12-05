#!/usr/bin/env python3
"""
检查迁移结果：验证 ip_address 字段是否已添加到 image_edit_tasks 表
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

try:
    import aiomysql
    from app.config import settings
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装依赖: pip install aiomysql")
    sys.exit(1)


async def check_master():
    """检查主库表结构"""
    try:
        conn = await aiomysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            charset='utf8mb4'
        )
        
        print(f"📊 检查主库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
        print("=" * 60)
        
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 检查字段是否存在
            await cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'image_edit_tasks'
                  AND COLUMN_NAME = 'ip_address'
            """, (settings.MYSQL_DATABASE,))
            
            column = await cursor.fetchone()
            
            if column:
                print("✅ ip_address 字段已存在")
                print(f"   类型: {column['COLUMN_TYPE']}")
                print(f"   允许NULL: {column['IS_NULLABLE']}")
                print(f"   默认值: {column['COLUMN_DEFAULT']}")
                print(f"   注释: {column['COLUMN_COMMENT']}")
            else:
                print("❌ ip_address 字段不存在")
            
            # 检查索引是否存在
            await cursor.execute("""
                SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'image_edit_tasks'
                  AND INDEX_NAME = 'idx_ip_address'
            """, (settings.MYSQL_DATABASE,))
            
            index = await cursor.fetchone()
            
            if index:
                print("✅ idx_ip_address 索引已存在")
                print(f"   列名: {index['COLUMN_NAME']}")
                print(f"   非唯一: {index['NON_UNIQUE']}")
            else:
                print("❌ idx_ip_address 索引不存在")
            
            # 显示完整的表结构（只显示相关字段）
            await cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY, EXTRA
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = 'image_edit_tasks'
                  AND COLUMN_NAME IN ('id', 'task_id', 'user_id', 'ip_address', 'openid', 'edit_type')
                ORDER BY ORDINAL_POSITION
            """, (settings.MYSQL_DATABASE,))
            
            columns = await cursor.fetchall()
            print("\n📋 相关字段列表:")
            for col in columns:
                key_info = f" [{col['COLUMN_KEY']}]" if col['COLUMN_KEY'] else ""
                print(f"   {col['COLUMN_NAME']}: {col['COLUMN_TYPE']}{key_info}")
        
        conn.close()
        return column is not None and index is not None
        
    except Exception as e:
        print(f"❌ 检查主库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🔍 开始检查迁移结果...\n")
    
    master_ok = await check_master()
    
    print("\n" + "=" * 60)
    if master_ok:
        print("✅ 主库迁移检查通过！")
        print("\n💡 提示：")
        print("   1. 主库表结构已更新")
        print("   2. 如果配置了主从复制，从库会自动同步")
        print("   3. 可以通过以下命令检查从库：")
        print("      ssh root@web \"mysql -u root -p image_classifier -e 'SHOW COLUMNS FROM image_edit_tasks LIKE \\\"ip_address\\\";'\"")
    else:
        print("❌ 主库迁移检查未通过，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

