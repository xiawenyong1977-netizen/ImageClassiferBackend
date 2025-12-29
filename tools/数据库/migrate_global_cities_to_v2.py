#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 global_cities 迁移数据到 global_cities_v2
"""

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
import os

def main():
    # 加载环境变量
    load_dotenv()
    
    # 数据库连接配置
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'classifier'),
        'password': os.getenv('MYSQL_PASSWORD', 'Classifier@2024'),
        'database': os.getenv('MYSQL_DATABASE', 'image_classifier'),
        'charset': 'utf8mb4'
    }
    
    print("=" * 60)
    print("global_cities 数据迁移到 global_cities_v2")
    print("=" * 60)
    print()
    
    try:
        # 连接数据库
        print("连接数据库...")
        conn = pymysql.connect(**db_config, cursorclass=DictCursor)
        cursor = conn.cursor()
        
        # 检查v1表是否存在
        cursor.execute("SHOW TABLES LIKE 'global_cities'")
        if not cursor.fetchone():
            print("错误: global_cities 表不存在")
            return
        
        # 检查v2表是否存在
        cursor.execute("SHOW TABLES LIKE 'global_cities_v2'")
        if not cursor.fetchone():
            print("错误: global_cities_v2 表不存在，请先执行 create_global_cities_v2.sql")
            return
        
        # 统计v1表数据
        cursor.execute("SELECT COUNT(*) AS count FROM global_cities")
        v1_count = cursor.fetchone()['count']
        print(f"v1表记录数: {v1_count}")
        
        # 统计v2表现有数据
        cursor.execute("SELECT COUNT(*) AS count FROM global_cities_v2")
        v2_count_before = cursor.fetchone()['count']
        print(f"v2表迁移前记录数: {v2_count_before}")
        print()
        
        # 开始迁移
        print("开始迁移数据...")
        
        # 批量迁移（每次1000条）
        batch_size = 1000
        offset = 0
        total_migrated = 0
        total_updated = 0
        
        while True:
            # 查询一批数据（不包含name_zh，中文名通过映射表获取）
            cursor.execute("""
                SELECT 
                    geoname_id,
                    COALESCE(ascii_name, name) AS name_en,
                    latitude,
                    longitude,
                    country_code,
                    admin1_code,
                    admin2_code,
                    feature_code,
                    population,
                    created_at,
                    updated_at
                FROM global_cities
                WHERE geoname_id IS NOT NULL
                ORDER BY id
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            rows = cursor.fetchall()
            if not rows:
                break
            
            # 批量插入/更新（不包含name_zh，中文名通过映射表获取）
            insert_sql = """
                INSERT INTO global_cities_v2 (
                    name_en, latitude, longitude,
                    country_code, admin1_code, admin2_code,
                    geoname_id, feature_code, population,
                    data_source, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, 'local', %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    name_en = VALUES(name_en),
                    latitude = VALUES(latitude),
                    longitude = VALUES(longitude),
                    country_code = VALUES(country_code),
                    admin1_code = VALUES(admin1_code),
                    admin2_code = VALUES(admin2_code),
                    feature_code = VALUES(feature_code),
                    population = VALUES(population),
                    updated_at = CURRENT_TIMESTAMP
            """
            
            batch_data = []
            for row in rows:
                batch_data.append((
                    row['name_en'],
                    row['latitude'],
                    row['longitude'],
                    row['country_code'],
                    row['admin1_code'],
                    row['admin2_code'],
                    row['geoname_id'],
                    row['feature_code'],
                    row['population'],
                    row['created_at'],
                    row['updated_at']
                ))
            
            # 执行批量插入
            cursor.executemany(insert_sql, batch_data)
            conn.commit()
            
            total_migrated += len(batch_data)
            print(f"  已迁移 {total_migrated}/{v1_count} 条记录...")
            
            if len(rows) < batch_size:
                break
            
            offset += batch_size
        
        print()
        print(f"✓ 迁移完成！共处理 {total_migrated} 条记录")
        
        # 统计迁移后数据
        cursor.execute("SELECT COUNT(*) AS count FROM global_cities_v2")
        v2_count_after = cursor.fetchone()['count']
        print(f"v2表迁移后记录数: {v2_count_after}")
        print(f"新增记录数: {v2_count_after - v2_count_before}")
        print()
        
        # 数据完整性检查
        print("数据完整性检查:")
        cursor.execute("""
            SELECT 
                COUNT(*) AS total,
                COUNT(DISTINCT geoname_id) AS unique_geoname_id,
                COUNT(DISTINCT name_en) AS unique_name_en,
                SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) AS has_coordinates
            FROM global_cities_v2
        """)
        stats = cursor.fetchone()
        print(f"  总记录数: {stats['total']}")
        print(f"  唯一geoname_id数: {stats['unique_geoname_id']}")
        print(f"  唯一英文名数: {stats['unique_name_en']}")
        print(f"  有坐标记录数: {stats['has_coordinates']}")
        
        # 检查可以通过映射表获取中文名的记录数
        cursor.execute("""
            SELECT COUNT(DISTINCT gc.name_en) AS mappable_count
            FROM global_cities_v2 gc
            INNER JOIN city_name_mapping cnm ON gc.name_en = cnm.name_en COLLATE utf8mb4_unicode_ci
        """)
        mappable = cursor.fetchone()
        print(f"  可通过映射表获取中文名的记录数: {mappable['mappable_count']}")
        print()
        
        # 按国家统计
        print("按国家统计（前10个）:")
        cursor.execute("""
            SELECT country_code, COUNT(*) AS count
            FROM global_cities_v2
            GROUP BY country_code
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  {row['country_code']}: {row['count']} 条")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 60)
        print("✓ 所有操作完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

