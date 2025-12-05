#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将检查完成的中文名称导入到数据库
使用方法：python import_chinese_names.py cities_chinese_supplement.csv
"""

import csv
import sys
import pymysql
from dotenv import load_dotenv
import os

def main():
    if len(sys.argv) < 2:
        print("使用方法: python import_chinese_names.py cities_chinese_supplement.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # 读取CSV文件
    print(f'读取文件: {input_file}')
    updates = []
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            geoname_id = row['geoname_id']
            name_zh = row['name_zh'].strip()
            
            # 只处理有中文名称的记录
            if name_zh:
                updates.append((name_zh, int(geoname_id)))
    
    print(f'共有 {len(updates)} 条记录需要更新')
    
    if len(updates) == 0:
        print('没有需要更新的记录')
        sys.exit(0)
    
    # 连接数据库（需要在服务器上运行）
    # 如果在本地运行，需要修改host
    print('\n连接数据库...')
    conn = pymysql.connect(
        host='localhost',  # 如果在服务器上运行用localhost，本地运行需要改为服务器IP
        user='classifier',
        password='Classifier@2024',
        database='image_classifier',
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # 批量更新
    print('开始批量更新...')
    batch_size = 1000
    total_updated = 0
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        cursor.executemany(
            'UPDATE global_cities SET name_zh = %s WHERE geoname_id = %s',
            batch
        )
        conn.commit()
        total_updated += len(batch)
        print(f'  已更新 {total_updated}/{len(updates)} 条记录...')
    
    print(f'\n✓ 更新完成！共更新 {total_updated} 条记录')
    
    # 统计结果
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN name_zh IS NOT NULL THEN 1 ELSE 0 END) as has_chinese,
            ROUND(SUM(CASE WHEN name_zh IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as percentage
        FROM global_cities 
        WHERE country_code = 'CN'
    ''')
    result = cursor.fetchone()
    print(f'\n当前统计（中国地区）：')
    print(f'  总城市数: {result[0]}')
    print(f'  有中文名: {result[1]}')
    print(f'  覆盖率: {result[2]}%')
    
    # 显示示例
    print(f'\n更新后的示例（人口最多的10个有中文名的城市）：')
    cursor.execute('''
        SELECT name, name_zh, population 
        FROM global_cities 
        WHERE country_code = 'CN' AND name_zh IS NOT NULL
        ORDER BY population DESC 
        LIMIT 10
    ''')
    for row in cursor.fetchall():
        print(f'  {row[0]:20s} -> {row[1]:15s} (人口: {row[2]:,})')
    
    cursor.close()
    conn.close()
    
    print('\n✓ 所有操作完成！')


if __name__ == '__main__':
    main()

