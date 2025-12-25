#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证城市名称映射表数据质量"""

import pymysql
import re

def main():
    conn = pymysql.connect(
        host='localhost',
        user='classifier',
        password='Classifier@2024',
        database='image_classifier',
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    # 总记录数
    cursor.execute('SELECT COUNT(*) FROM city_name_mapping')
    total = cursor.fetchone()[0]
    print(f'总记录数: {total}')

    # 检查是否有日文假名（使用Python正则）
    cursor.execute('SELECT name_zh FROM city_name_mapping')
    all_names = [r[0] for r in cursor.fetchall()]
    japanese_names = [name for name in all_names if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', name)]
    if japanese_names:
        print(f'⚠️ 发现日文数据: {japanese_names[:5]}')
    else:
        print('✓ 没有日文数据')

    # 检查一些常见城市
    test_cities = ['北京', '北京市', '上海', '上海市', '广州', '广州市', '深圳', '深圳市']
    print('\n常见城市查询:')
    for city in test_cities:
        cursor.execute('SELECT name_zh, name_en FROM city_name_mapping WHERE name_zh = %s', (city,))
        result = cursor.fetchone()
        if result:
            print(f'  {result[0]:10} -> {result[1]}')
        else:
            print(f'  {city:10} -> 未找到')

    # 检查规范化后的名称
    print('\n规范化名称检查:')
    cursor.execute('SELECT name_zh, name_en FROM city_name_mapping WHERE name_zh LIKE "%市" LIMIT 5')
    with_suffix = cursor.fetchall()
    print('带"市"后缀的名称:')
    for r in with_suffix:
        print(f'  {r[0]:15} -> {r[1]}')
        normalized = r[0].rstrip('市')
        cursor.execute('SELECT name_zh, name_en FROM city_name_mapping WHERE name_zh = %s', (normalized,))
        norm_result = cursor.fetchone()
        if norm_result:
            print(f'    规范化: {norm_result[0]:15} -> {norm_result[1]}')

    # 统计信息
    cursor.execute('SELECT COUNT(DISTINCT name_en) FROM city_name_mapping')
    unique_cities = cursor.fetchone()[0]
    print(f'\n统计信息:')
    print(f'  唯一城市数: {unique_cities}')

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()

