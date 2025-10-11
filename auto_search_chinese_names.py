#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动搜索并补充城市的中文名称
"""

import csv
import time

def read_unmatched_cities(csv_file, min_population=100000):
    """读取未匹配的城市"""
    cities = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == '✗' and int(row['population']) >= min_population:
                cities.append(row)
    return cities

def main():
    input_file = 'cities_chinese_supplement.csv'
    
    # 读取未匹配的城市（人口>10万）
    unmatched = read_unmatched_cities(input_file, min_population=100000)
    
    print(f'人口>10万的未匹配城市: {len(unmatched)}个')
    print('\n前30个需要搜索的城市：')
    print('-' * 80)
    print(f'{"序号":<6} {"英文名":<30} {"人口":<15} {"搜索关键词"}')
    print('-' * 80)
    
    for i, city in enumerate(unmatched[:30], 1):
        search_term = f"{city['name']} 中国 城市"
        print(f'{i:<6} {city["name"]:<30} {int(city["population"]):>12,}   "{search_term}"')
    
    print('\n' + '=' * 80)
    print('建议：将上述"搜索关键词"复制到百度搜索，获取中文名称后填入CSV文件')
    print('=' * 80)
    
    # 列出所有需要搜索的城市名称
    print(f'\n所有{len(unmatched)}个城市列表（可批量搜索）：')
    for city in unmatched:
        print(city['name'])


if __name__ == '__main__':
    main()

