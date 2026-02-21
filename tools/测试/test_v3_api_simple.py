#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的V3接口测试脚本（用于服务器端测试）
"""
import requests
import json

url = 'http://localhost:8000/api/v3/location/nearest-cities'

# 测试1: 单个坐标点
print('=' * 60)
print('测试1: 单个坐标点查询')
print('=' * 60)
payload1 = {
    'coordinates': [
        {'id': 'test1', 'latitude': 39.9042, 'longitude': 116.4074}
    ]
}

try:
    response = requests.post(url, json=payload1, timeout=60)
    print('状态码:', response.status_code)
    if response.status_code == 200:
        result = response.json()
        print('✅ 测试1通过')
        print('  城市:', result['results'][0]['city']['name_zh'])
        print('  数据来源:', result['results'][0]['data_source'])
    else:
        print('❌ 测试1失败:', response.text[:200])
except Exception as e:
    print('❌ 测试1异常:', str(e))

print()

# 测试2: 批量查询（5个坐标）
print('=' * 60)
print('测试2: 批量坐标点查询（5个坐标）')
print('=' * 60)
payload2 = {
    'coordinates': [
        {'id': 'test1', 'latitude': 39.9042, 'longitude': 116.4074},  # 北京
        {'id': 'test2', 'latitude': 31.2304, 'longitude': 121.4737},  # 上海
        {'id': 'test3', 'latitude': 23.1064, 'longitude': 113.3245},  # 广州
        {'id': 'test4', 'latitude': 40.7580, 'longitude': -73.9855},  # 纽约
        {'id': 'test5', 'latitude': 48.8584, 'longitude': 2.2945},  # 巴黎
    ]
}

try:
    response = requests.post(url, json=payload2, timeout=120)
    print('状态码:', response.status_code)
    if response.status_code == 200:
        result = response.json()
        print('✅ 测试2通过')
        print('  总查询数:', result.get('total_count'))
        print('  成功数:', result.get('success_count'))
        print('  总耗时:', result.get('total_time_ms'), 'ms')
        
        # 数据来源分布
        data_sources = {}
        for city_result in result.get('results', []):
            ds = city_result.get('data_source', 'unknown')
            data_sources[ds] = data_sources.get(ds, 0) + 1
        print('  数据来源分布:', data_sources)
    else:
        print('❌ 测试2失败:', response.text[:200])
except Exception as e:
    print('❌ 测试2异常:', str(e))

print()

# 测试3: 聚类功能测试（3个相近坐标）
print('=' * 60)
print('测试3: 聚类功能测试（3个相近坐标）')
print('=' * 60)
payload3 = {
    'coordinates': [
        {'id': 'cluster1', 'latitude': 39.9042, 'longitude': 116.4074},  # 北京天安门
        {'id': 'cluster2', 'latitude': 39.9050, 'longitude': 116.4080},  # 距离约100米
        {'id': 'cluster3', 'latitude': 39.9060, 'longitude': 116.4090},  # 距离约200米
    ]
}

print('这些坐标点距离很近（<3km），应该被聚类成一个圆心')
print()

try:
    response = requests.post(url, json=payload3, timeout=120)
    print('状态码:', response.status_code)
    if response.status_code == 200:
        result = response.json()
        print('✅ 测试3通过')
        print('  总查询数:', result.get('total_count'))
        print('  成功数:', result.get('success_count'))
        print('  总耗时:', result.get('total_time_ms'), 'ms')
        
        # 数据来源分布
        data_sources = {}
        for city_result in result.get('results', []):
            ds = city_result.get('data_source', 'unknown')
            data_sources[ds] = data_sources.get(ds, 0) + 1
        print('  数据来源分布:', data_sources)
        
        print('\n  各坐标点结果:')
        for i, city_result in enumerate(result.get('results', []), 1):
            city = city_result.get('city')
            if city:
                print(f'    {i}. {city_result.get("location_id")}: {city.get("name_zh")} / {city.get("name_en")} (来源: {city_result.get("data_source")})')
    else:
        print('❌ 测试3失败:', response.text[:200])
except Exception as e:
    print('❌ 测试3异常:', str(e))
    import traceback
    traceback.print_exc()

print()
print('=' * 60)
print('测试完成')
print('=' * 60)
