#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查并修复 global_cities_v2 表的 data_source 字段
添加 'llm' 选项以支持 V3 接口
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.database import db
from app.config import settings
import asyncio

async def check_and_fix_data_source():
    """检查并修复 data_source 字段"""
    try:
        await db.connect()
        
        # 检查当前字段定义
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'global_cities_v2' 
                AND COLUMN_NAME = 'data_source'
            """, (settings.MYSQL_DATABASE,))
            
            result = await cursor.fetchone()
            if result:
                current_type = result['COLUMN_TYPE']
                print(f"当前 data_source 字段类型: {current_type}")
                
                if 'llm' not in current_type:
                    print("需要添加 'llm' 选项...")
                    # 修改字段，添加 'llm' 选项
                    await cursor.execute("""
                        ALTER TABLE global_cities_v2 
                        MODIFY COLUMN data_source ENUM('local', 'gaode', 'nominatim', 'llm') 
                        DEFAULT 'local' 
                        COMMENT '数据来源'
                    """)
                    print("✅ 已成功添加 'llm' 选项到 data_source 字段")
                    
                    # 再次检查
                    await cursor.execute("""
                        SELECT COLUMN_TYPE 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = 'global_cities_v2' 
                        AND COLUMN_NAME = 'data_source'
                    """, (settings.MYSQL_DATABASE,))
                    
                    result = await cursor.fetchone()
                    if result:
                        print(f"更新后的 data_source 字段类型: {result['COLUMN_TYPE']}")
                else:
                    print("✅ data_source 字段已包含 'llm' 选项")
            else:
                print("❌ 未找到 data_source 字段")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_and_fix_data_source())
