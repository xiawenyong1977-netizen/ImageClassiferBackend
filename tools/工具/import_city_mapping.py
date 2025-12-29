#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入城市名称映射关系到数据库
"""
import csv
import sys
import pymysql
from dotenv import load_dotenv
import os

def load_db_config():
    """从环境变量加载数据库配置"""
    load_dotenv()
    
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'image_classifier'),
        'charset': 'utf8mb4'
    }

def import_mapping(csv_file, db_config, batch_size=1000):
    """
    导入映射关系到数据库
    
    Args:
        csv_file: CSV文件路径
        db_config: 数据库配置
        batch_size: 批量插入大小
    """
    print("=" * 50)
    print("城市名称映射表导入工具")
    print("=" * 50)
    print()
    
    # 连接数据库
    print("正在连接数据库...")
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        print(f"✓ 数据库连接成功: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        sys.exit(1)
    
    print()
    
    # 检查表是否存在
    cursor.execute("""
        SELECT COUNT(*) as cnt 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = 'city_name_mapping'
    """, (db_config['database'],))
    
    if cursor.fetchone()[0] == 0:
        print("错误: city_name_mapping 表不存在，请先执行 create_city_name_mapping.sql")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    # 读取CSV文件
    print(f"正在读取文件: {csv_file}")
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"✓ 读取完成，共 {len(rows)} 条记录")
    except FileNotFoundError:
        print(f"✗ 文件不存在: {csv_file}")
        cursor.close()
        conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"✗ 读取文件失败: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    print()
    
    # 准备SQL
    sql = """
        INSERT INTO city_name_mapping (name_zh, name_en, country_code)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name_en = VALUES(name_en),
            country_code = VALUES(country_code),
            updated_at = CURRENT_TIMESTAMP
    """
    
    # 批量导入
    print("正在导入数据...")
    total_imported = 0
    total_updated = 0
    errors = []
    
    # 先查询现有记录数
    cursor.execute("SELECT COUNT(*) FROM city_name_mapping")
    before_count = cursor.fetchone()[0]
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        batch_data = []
        
        for row in batch:
            name_zh = row.get('name_zh', '').strip()
            name_en = row.get('name_en', '').strip()
            country_code = row.get('country_code', '').strip() or None
            
            if not name_zh or not name_en:
                errors.append(f"跳过无效记录: name_zh={name_zh}, name_en={name_en}")
                continue
            
            batch_data.append((name_zh, name_en, country_code))
        
        if batch_data:
            try:
                # 检查哪些是新记录，哪些是更新
                for data in batch_data:
                    cursor.execute("SELECT id FROM city_name_mapping WHERE name_zh = %s", (data[0],))
                    if cursor.fetchone():
                        total_updated += 1
                    else:
                        total_imported += 1
                
                # 批量插入
                cursor.executemany(sql, batch_data)
                conn.commit()
                
                processed = min(i + batch_size, len(rows))
                print(f"  已处理 {processed}/{len(rows)} 条记录... (新增: {total_imported}, 更新: {total_updated})")
                
            except Exception as e:
                errors.append(f"批量插入失败 (行 {i}-{i+len(batch_data)}): {e}")
                conn.rollback()
    
    # 查询最终记录数
    cursor.execute("SELECT COUNT(*) FROM city_name_mapping")
    after_count = cursor.fetchone()[0]
    
    print()
    print("=" * 50)
    print("导入完成！")
    print("=" * 50)
    print(f"导入前记录数: {before_count}")
    print(f"导入后记录数: {after_count}")
    print(f"新增记录: {total_imported}")
    print(f"更新记录: {total_updated}")
    print(f"总处理记录: {len(rows)}")
    
    if errors:
        print()
        print(f"警告: 有 {len(errors)} 个错误")
        if len(errors) <= 10:
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"  前10个错误:")
            for error in errors[:10]:
                print(f"  - {error}")
    
    # 统计信息
    print()
    print("统计信息:")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT country_code) as country_count,
            SUM(CASE WHEN country_code = 'CN' THEN 1 ELSE 0 END) as china_count
        FROM city_name_mapping
    """)
    stats = cursor.fetchone()
    print(f"  总映射数: {stats[0]}")
    print(f"  国家数: {stats[1]}")
    print(f"  中国城市: {stats[2]}")
    
    # 显示示例
    print()
    print("示例数据（前10条）:")
    cursor.execute("""
        SELECT name_zh, name_en, country_code 
        FROM city_name_mapping 
        ORDER BY id 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:15s} -> {row[1]:20s} ({row[2]})")
    
    cursor.close()
    conn.close()
    print()
    print("✓ 所有操作完成！")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python import_city_mapping.py <CSV文件>")
        print("")
        print("示例:")
        print("  python import_city_mapping.py city_mapping.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # 加载数据库配置
    db_config = load_db_config()
    
    # 导入数据
    import_mapping(csv_file, db_config)

if __name__ == '__main__':
    main()

