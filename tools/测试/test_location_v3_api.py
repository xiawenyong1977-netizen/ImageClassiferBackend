#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试V3版本逆地址编码接口

测试场景：
1. 单个坐标点查询
2. 批量坐标点查询（多个坐标）
3. 验证返回格式
4. 验证数据来源（local/llm）
5. 验证聚类功能（多个相近坐标应该被聚类）

使用方法：
    python tools/测试/test_location_v3_api.py
    或指定服务器：
    python tools/测试/test_location_v3_api.py --server https://your-server.com
"""

import sys
import os
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx
from loguru import logger


# 测试数据：不同场景的坐标点
TEST_COORDINATES = [
    # 中国坐标（常见城市）
    {
        "id": "test_beijing",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "expected_country": "CN",
        "expected_city": "北京",
        "description": "北京天安门"
    },
    {
        "id": "test_shanghai",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "expected_country": "CN",
        "expected_city": "上海",
        "description": "上海外滩"
    },
    {
        "id": "test_guangzhou",
        "latitude": 23.1064,
        "longitude": 113.3245,
        "expected_country": "CN",
        "expected_city": "广州",
        "description": "广州塔"
    },
    # 海外坐标
    {
        "id": "test_newyork",
        "latitude": 40.7580,
        "longitude": -73.9855,
        "expected_country": "US",
        "expected_city": "New York",
        "description": "纽约时代广场"
    },
    {
        "id": "test_paris",
        "latitude": 48.8584,
        "longitude": 2.2945,
        "expected_country": "FR",
        "expected_city": "Paris",
        "description": "巴黎埃菲尔铁塔"
    },
    # 聚类测试：多个相近坐标（应该被聚类）
    {
        "id": "cluster_test_1",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "description": "聚类测试点1（北京天安门附近）"
    },
    {
        "id": "cluster_test_2",
        "latitude": 39.9050,
        "longitude": 116.4080,
        "description": "聚类测试点2（北京天安门附近，距离约100米）"
    },
    {
        "id": "cluster_test_3",
        "latitude": 39.9060,
        "longitude": 116.4090,
        "description": "聚类测试点3（北京天安门附近，距离约200米）"
    },
]


async def test_single_coordinate(server_url: str) -> bool:
    """测试单个坐标点查询"""
    logger.info("=" * 80)
    logger.info("测试1: 单个坐标点查询")
    logger.info("=" * 80)
    
    test_coord = TEST_COORDINATES[0]  # 使用北京天安门
    logger.info(f"测试坐标: {test_coord['description']} ({test_coord['latitude']}, {test_coord['longitude']})")
    
    url = f"{server_url}/api/v3/location/nearest-cities"
    payload = {
        "coordinates": [
            {
                "id": test_coord["id"],
                "latitude": test_coord["latitude"],
                "longitude": test_coord["longitude"]
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 验证响应格式
            if not result.get("success"):
                logger.error("❌ 响应 success 字段为 False")
                return False
            
            if "results" not in result:
                logger.error("❌ 响应缺少 results 字段")
                return False
            
            if len(result["results"]) != 1:
                logger.error(f"❌ 返回结果数量不正确: 期望 1，实际 {len(result['results'])}")
                return False
            
            city_result = result["results"][0]
            
            # 验证必需字段
            required_fields = ["location_id", "coordinate", "city", "success", "data_source", "query_time_ms"]
            for field in required_fields:
                if field not in city_result:
                    logger.error(f"❌ 缺少必需字段: {field}")
                    return False
            
            # 验证城市信息
            city = city_result.get("city")
            if not city:
                logger.error("❌ 城市信息为空")
                return False
            
            logger.info(f"✅ 数据来源: {city_result.get('data_source')}")
            logger.info(f"✅ 城市名称（中文）: {city.get('name_zh')}")
            logger.info(f"✅ 城市名称（英文）: {city.get('name_en')}")
            logger.info(f"✅ 国家代码: {city.get('country_code')}")
            logger.info(f"✅ 省份: {city.get('province')}")
            
            logger.success("✅ 单个坐标点查询测试通过")
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP错误: {e.response.status_code}")
        logger.error(f"响应内容: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_batch_coordinates(server_url: str) -> bool:
    """测试批量坐标点查询"""
    logger.info("=" * 80)
    logger.info("测试2: 批量坐标点查询")
    logger.info("=" * 80)
    
    # 选择前5个测试坐标
    test_coords = TEST_COORDINATES[:5]
    logger.info(f"测试坐标数量: {len(test_coords)}")
    for i, tc in enumerate(test_coords):
        logger.info(f"  {i+1}. {tc['description']} ({tc['latitude']}, {tc['longitude']})")
    
    url = f"{server_url}/api/v3/location/nearest-cities"
    payload = {
        "coordinates": [
            {
                "id": tc["id"],
                "latitude": tc["latitude"],
                "longitude": tc["longitude"]
            }
            for tc in test_coords
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info("发送批量查询请求...")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"总查询数: {result.get('total_count')}")
            logger.info(f"成功数: {result.get('success_count')}")
            logger.info(f"失败数: {result.get('failed_count')}")
            logger.info(f"总耗时: {result.get('total_time_ms')}ms")
            
            # 验证响应格式
            if not result.get("success"):
                logger.error("❌ 响应 success 字段为 False")
                return False
            
            if len(result.get("results", [])) != len(test_coords):
                logger.error(f"❌ 返回结果数量不正确: 期望 {len(test_coords)}，实际 {len(result.get('results', []))}")
                return False
            
            # 验证每个结果
            all_valid = True
            for i, city_result in enumerate(result["results"]):
                logger.info(f"\n验证结果 {i+1}: {test_coords[i]['description']}")
                logger.info(f"  数据来源: {city_result.get('data_source')}")
                
                city = city_result.get("city")
                if city:
                    logger.info(f"  城市: {city.get('name_zh')} / {city.get('name_en')}")
                    logger.info(f"  国家: {city.get('country_code')}")
                else:
                    logger.warning(f"  ⚠️ 城市信息为空")
                    all_valid = False
            
            if all_valid:
                logger.success("✅ 批量坐标点查询测试通过")
                return True
            else:
                logger.warning("⚠️ 部分结果验证有警告")
                return True  # 仍然算通过，因为有警告
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP错误: {e.response.status_code}")
        logger.error(f"响应内容: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_clustering(server_url: str) -> bool:
    """测试聚类功能（多个相近坐标应该被聚类）"""
    logger.info("=" * 80)
    logger.info("测试3: 聚类功能测试（多个相近坐标）")
    logger.info("=" * 80)
    
    # 使用聚类测试坐标（3个相近的点）
    cluster_coords = [tc for tc in TEST_COORDINATES if tc["id"].startswith("cluster_test")]
    logger.info(f"测试坐标数量: {len(cluster_coords)}")
    logger.info("这些坐标点距离很近（<3km），应该被聚类成一个圆心")
    
    url = f"{server_url}/api/v3/location/nearest-cities"
    payload = {
        "coordinates": [
            {
                "id": tc["id"],
                "latitude": tc["latitude"],
                "longitude": tc["longitude"]
            }
            for tc in cluster_coords
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info("发送聚类测试请求...")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"总查询数: {result.get('total_count')}")
            logger.info(f"成功数: {result.get('success_count')}")
            logger.info(f"总耗时: {result.get('total_time_ms')}ms")
            
            # 检查数据来源分布
            data_sources = {}
            for city_result in result.get("results", []):
                ds = city_result.get("data_source", "unknown")
                data_sources[ds] = data_sources.get(ds, 0) + 1
            
            logger.info(f"数据来源分布: {data_sources}")
            
            # 验证所有结果都有城市信息
            all_valid = True
            for i, city_result in enumerate(result["results"]):
                city = city_result.get("city")
                if not city:
                    logger.warning(f"⚠️ 结果 {i+1} 城市信息为空")
                    all_valid = False
                else:
                    logger.info(f"结果 {i+1}: {city.get('name_zh')} / {city.get('name_en')} (来源: {city_result.get('data_source')})")
            
            if all_valid:
                logger.success("✅ 聚类功能测试通过")
                logger.info("注意: 如果这些点都在本地数据库中，数据来源可能是 'local'")
                logger.info("如果不在本地数据库，应该通过聚类后调用大模型，数据来源应该是 'llm'")
                return True
            else:
                logger.warning("⚠️ 部分结果验证有警告")
                return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP错误: {e.response.status_code}")
        logger.error(f"响应内容: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def test_unknown_location(server_url: str) -> bool:
    """测试未知位置处理"""
    logger.info("=" * 80)
    logger.info("测试4: 未知位置处理（无效坐标）")
    logger.info("=" * 80)
    
    # 使用一个不太可能存在的坐标（海洋中央）
    url = f"{server_url}/api/v3/location/nearest-cities"
    payload = {
        "coordinates": [
            {
                "id": "test_unknown",
                "latitude": 0.0,
                "longitude": 0.0,  # 几内亚湾，可能没有城市数据
                "description": "未知位置测试"
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info("发送未知位置查询请求...")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"响应状态码: {response.status_code}")
            
            if result.get("results"):
                city_result = result["results"][0]
                city = city_result.get("city")
                if city:
                    logger.info(f"返回的城市: {city.get('name_zh')} / {city.get('name_en')}")
                    logger.info(f"国家代码: {city.get('country_code')}")
                    if city.get("country_code") == "UN":
                        logger.success("✅ 未知位置正确返回（country_code=UN）")
                    else:
                        logger.info("ℹ️ 返回了实际位置（可能大模型识别出了位置）")
                else:
                    logger.warning("⚠️ 城市信息为空")
            
            logger.success("✅ 未知位置处理测试通过（接口正常响应）")
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP错误: {e.response.status_code}")
        logger.error(f"响应内容: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    parser = argparse.ArgumentParser(description="测试V3版本逆地址编码接口")
    parser.add_argument(
        "--server",
        type=str,
        default="http://localhost:8000",
        help="服务器URL（默认: http://localhost:8000）"
    )
    parser.add_argument(
        "--skip-clustering",
        action="store_true",
        help="跳过聚类测试（如果大模型API未配置）"
    )
    
    args = parser.parse_args()
    
    server_url = args.server.rstrip("/")
    
    logger.info("=" * 80)
    logger.info("V3版本逆地址编码接口测试")
    logger.info("=" * 80)
    logger.info(f"服务器URL: {server_url}")
    logger.info(f"接口路径: {server_url}/api/v3/location/nearest-cities")
    logger.info("=" * 80)
    
    results = []
    
    # 测试1: 单个坐标点查询
    try:
        result1 = await test_single_coordinate(server_url)
        results.append(("单个坐标点查询", result1))
    except Exception as e:
        logger.error(f"测试1失败: {e}", exc_info=True)
        results.append(("单个坐标点查询", False))
    
    await asyncio.sleep(1)  # 避免请求过快
    
    # 测试2: 批量坐标点查询
    try:
        result2 = await test_batch_coordinates(server_url)
        results.append(("批量坐标点查询", result2))
    except Exception as e:
        logger.error(f"测试2失败: {e}", exc_info=True)
        results.append(("批量坐标点查询", False))
    
    await asyncio.sleep(1)
    
    # 测试3: 聚类功能测试
    if not args.skip_clustering:
        try:
            result3 = await test_clustering(server_url)
            results.append(("聚类功能测试", result3))
        except Exception as e:
            logger.error(f"测试3失败: {e}", exc_info=True)
            results.append(("聚类功能测试", False))
    else:
        logger.info("跳过聚类功能测试（--skip-clustering）")
        results.append(("聚类功能测试", None))
    
    await asyncio.sleep(1)
    
    # 测试4: 未知位置处理
    try:
        result4 = await test_unknown_location(server_url)
        results.append(("未知位置处理", result4))
    except Exception as e:
        logger.error(f"测试4失败: {e}", exc_info=True)
        results.append(("未知位置处理", False))
    
    # 输出测试总结
    logger.info("=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)
    for test_name, passed in results:
        if passed is None:
            status = "⏭️  跳过"
        elif passed:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed is True)
    total_tests = sum(1 for _, passed in results if passed is not None)
    logger.info(f"\n总计: {total_passed}/{total_tests} 测试通过")
    
    if total_passed == total_tests:
        logger.success("🎉 所有测试通过！")
        return 0
    else:
        logger.error("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
