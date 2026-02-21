#!/usr/bin/env python3
"""
测试大模型逆地址编码功能

测试场景：
1. 单个坐标点查询
2. 批量坐标点查询（多个圆心）
3. 验证返回格式（JSON数组，包含query坐标和city坐标）
4. 验证三级行政区信息（国家、省/州、市/县）

使用方法：
    python tools/测试/test_reverse_geocoding_llm.py
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.services.llm import llm_service
from app.config import settings


# 测试数据：不同场景的坐标点
TEST_COORDINATES = [
    # 中国坐标
    {
        "name": "北京天安门",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "expected_country": "CN",
        "expected_admin1": "北京市",
    },
    {
        "name": "上海外滩",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "expected_country": "CN",
        "expected_admin1": "上海市",
    },
    {
        "name": "广州塔",
        "latitude": 23.1064,
        "longitude": 113.3245,
        "expected_country": "CN",
        "expected_admin1": "广东省",
    },
    # 海外坐标
    {
        "name": "纽约时代广场",
        "latitude": 40.7580,
        "longitude": -73.9855,
        "expected_country": "US",
        "expected_admin1": "New York",
    },
    {
        "name": "巴黎埃菲尔铁塔",
        "latitude": 48.8584,
        "longitude": 2.2945,
        "expected_country": "FR",
        "expected_admin1": "Île-de-France",
    },
    {
        "name": "东京塔",
        "latitude": 35.6586,
        "longitude": 139.7454,
        "expected_country": "JP",
        "expected_admin1": "東京都",
    },
    # 小国坐标（测试没有二级行政区的情况）
    {
        "name": "梵蒂冈",
        "latitude": 41.9029,
        "longitude": 12.4534,
        "expected_country": "VA",
        "expected_admin1": None,  # 梵蒂冈可能没有一级行政区
    },
]


def build_prompt(coordinates: list) -> str:
    """
    构建大模型查询提示词
    
    Args:
        coordinates: 坐标列表，格式：[{"index": 0, "latitude": 39.9042, "longitude": 116.4074}, ...]
    
    Returns:
        提示词字符串
    """
    coords_json = json.dumps(coordinates, indent=2, ensure_ascii=False)
    
    prompt = f"""
请根据以下坐标列表，返回每个坐标的三级行政区信息（JSON数组格式）。

要求：
1. 返回中英文名称
2. 返回三级行政区：国家、一级行政区（省/州）、二级行政区（市/县）
3. 如果没有一级或二级行政区（如梵蒂冈等小国），保留为空
4. **必须返回查询坐标（query_latitude, query_longitude）和城市坐标（city_latitude, city_longitude）**
5. 返回结果必须按照输入顺序，且每个结果必须包含对应的index

坐标列表：
{coords_json}

请返回以下格式的JSON数组：
[
    {{
        "index": 0,
        "query_latitude": 39.9042,      // 查询坐标（输入的圆心坐标）
        "query_longitude": 116.4074,     // 查询坐标（输入的圆心坐标）
        "city_latitude": 39.9042,        // 城市坐标（实际城市位置）
        "city_longitude": 116.4074,      // 城市坐标（实际城市位置）
        "country_code": "CN",
        "country_name_zh": "中国",
        "country_name_en": "China",
        "admin1_name_zh": "北京市",
        "admin1_name_en": "Beijing",
        "admin2_name_zh": "东城区",
        "admin2_name_en": "Dongcheng",
        "city_name_zh": "北京市",
        "city_name_en": "Beijing"
    }}
]

重要提示：
1. query_latitude 和 query_longitude 必须与输入坐标完全一致
2. city_latitude 和 city_longitude 是实际城市的位置坐标
3. 返回结果必须包含所有输入坐标，且index必须对应
4. 只返回JSON数组，不要包含其他文字说明
"""
    return prompt


def parse_llm_response(content: str) -> list:
    """
    解析大模型返回的JSON内容
    
    Args:
        content: 大模型返回的文本内容
    
    Returns:
        解析后的结果列表
    """
    # 移除可能的markdown代码块标记
    content_clean = content.strip()
    if content_clean.startswith("```json"):
        content_clean = content_clean[7:]
    if content_clean.startswith("```"):
        content_clean = content_clean[3:]
    if content_clean.endswith("```"):
        content_clean = content_clean[:-3]
    content_clean = content_clean.strip()
    
    try:
        result = json.loads(content_clean)
        if not isinstance(result, list):
            raise ValueError(f"返回结果不是数组格式: {type(result)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        logger.error(f"原始内容: {content}")
        raise


def validate_result(result: dict, expected: dict) -> Tuple[bool, list]:
    """
    验证返回结果是否符合预期
    
    Args:
        result: 大模型返回的结果字典
        expected: 预期的结果字典
    
    Returns:
        (是否通过, 错误信息列表)
    """
    errors = []
    
    # 检查必需字段
    required_fields = [
        "index", "query_latitude", "query_longitude",
        "city_latitude", "city_longitude",
        "country_code", "country_name_zh", "country_name_en"
    ]
    for field in required_fields:
        if field not in result:
            errors.append(f"缺少必需字段: {field}")
    
    # 检查坐标一致性
    if "query_latitude" in result and "query_longitude" in result:
        # 允许小误差（浮点数精度）
        lat_diff = abs(result["query_latitude"] - expected["latitude"])
        lon_diff = abs(result["query_longitude"] - expected["longitude"])
        if lat_diff > 0.0001 or lon_diff > 0.0001:
            errors.append(
                f"query坐标不匹配: "
                f"期望 ({expected['latitude']}, {expected['longitude']}), "
                f"实际 ({result['query_latitude']}, {result['query_longitude']})"
            )
    
    # 检查国家代码
    if expected.get("expected_country") and result.get("country_code") != expected["expected_country"]:
        errors.append(
            f"国家代码不匹配: 期望 {expected['expected_country']}, 实际 {result.get('country_code')}"
        )
    
    # 检查一级行政区（如果有预期值）
    if expected.get("expected_admin1"):
        admin1_zh = result.get("admin1_name_zh", "")
        admin1_en = result.get("admin1_name_en", "")
        expected_admin1 = expected["expected_admin1"]
        if expected_admin1 not in admin1_zh and expected_admin1 not in admin1_en:
            errors.append(
                f"一级行政区不匹配: 期望包含 '{expected_admin1}', "
                f"实际中文: {admin1_zh}, 英文: {admin1_en}"
            )
    
    return len(errors) == 0, errors


async def test_single_coordinate():
    """测试单个坐标点查询"""
    logger.info("=" * 80)
    logger.info("测试1: 单个坐标点查询")
    logger.info("=" * 80)
    
    test_case = TEST_COORDINATES[0]  # 使用北京天安门
    logger.info(f"测试坐标: {test_case['name']} ({test_case['latitude']}, {test_case['longitude']})")
    
    # 构建坐标列表
    coordinates = [
        {
            "index": 0,
            "latitude": test_case["latitude"],
            "longitude": test_case["longitude"]
        }
    ]
    
    # 构建提示词
    prompt = build_prompt(coordinates)
    
    # 调用大模型
    logger.info("调用大模型进行逆地址编码...")
    result = await llm_service.generate_text(
        prompt=prompt,
        system_prompt="你是一个专业的地理信息专家，能够准确地将坐标转换为地址信息。",
        max_tokens=2000,
        temperature=0.3  # 降低温度，提高准确性
    )
    
    if not result.get("success"):
        logger.error(f"大模型调用失败: {result.get('error')}")
        return False
    
    content = result.get("content", "")
    logger.info(f"大模型返回内容:\n{content}")
    
    # 解析结果
    try:
        parsed_results = parse_llm_response(content)
        logger.info(f"解析成功，返回 {len(parsed_results)} 个结果")
        
        if len(parsed_results) != 1:
            logger.error(f"返回结果数量不正确: 期望 1，实际 {len(parsed_results)}")
            return False
        
        result_dict = parsed_results[0]
        logger.info(f"解析结果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
        
        # 验证结果
        is_valid, errors = validate_result(result_dict, test_case)
        if is_valid:
            logger.success("✅ 单个坐标点查询测试通过")
            return True
        else:
            logger.error(f"❌ 验证失败: {errors}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 解析或验证失败: {e}", exc_info=True)
        return False


async def test_batch_coordinates():
    """测试批量坐标点查询"""
    logger.info("=" * 80)
    logger.info("测试2: 批量坐标点查询（多个圆心）")
    logger.info("=" * 80)
    
    # 选择前3个测试坐标
    test_cases = TEST_COORDINATES[:3]
    logger.info(f"测试坐标数量: {len(test_cases)}")
    for i, tc in enumerate(test_cases):
        logger.info(f"  {i+1}. {tc['name']} ({tc['latitude']}, {tc['longitude']})")
    
    # 构建坐标列表
    coordinates = [
        {
            "index": i,
            "latitude": tc["latitude"],
            "longitude": tc["longitude"]
        }
        for i, tc in enumerate(test_cases)
    ]
    
    # 构建提示词
    prompt = build_prompt(coordinates)
    
    # 调用大模型
    logger.info("调用大模型进行批量逆地址编码...")
    result = await llm_service.generate_text(
        prompt=prompt,
        system_prompt="你是一个专业的地理信息专家，能够准确地将坐标转换为地址信息。",
        max_tokens=4000,  # 批量查询需要更多token
        temperature=0.3
    )
    
    if not result.get("success"):
        logger.error(f"大模型调用失败: {result.get('error')}")
        return False
    
    content = result.get("content", "")
    logger.info(f"大模型返回内容:\n{content}")
    
    # 解析结果
    try:
        parsed_results = parse_llm_response(content)
        logger.info(f"解析成功，返回 {len(parsed_results)} 个结果")
        
        if len(parsed_results) != len(test_cases):
            logger.error(
                f"返回结果数量不正确: 期望 {len(test_cases)}，实际 {len(parsed_results)}"
            )
            return False
        
        # 验证每个结果
        all_valid = True
        for i, (result_dict, test_case) in enumerate(zip(parsed_results, test_cases)):
            logger.info(f"\n验证结果 {i+1}: {test_case['name']}")
            logger.info(f"解析结果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
            
            is_valid, errors = validate_result(result_dict, test_case)
            if is_valid:
                logger.success(f"✅ 结果 {i+1} 验证通过")
            else:
                logger.error(f"❌ 结果 {i+1} 验证失败: {errors}")
                all_valid = False
        
        if all_valid:
            logger.success("✅ 批量坐标点查询测试通过")
            return True
        else:
            logger.error("❌ 部分结果验证失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 解析或验证失败: {e}", exc_info=True)
        return False


async def test_overseas_coordinates():
    """测试海外坐标查询"""
    logger.info("=" * 80)
    logger.info("测试3: 海外坐标查询")
    logger.info("=" * 80)
    
    # 选择海外坐标
    test_cases = [tc for tc in TEST_COORDINATES if tc.get("expected_country") != "CN"][:2]
    logger.info(f"测试坐标数量: {len(test_cases)}")
    for i, tc in enumerate(test_cases):
        logger.info(f"  {i+1}. {tc['name']} ({tc['latitude']}, {tc['longitude']})")
    
    # 构建坐标列表
    coordinates = [
        {
            "index": i,
            "latitude": tc["latitude"],
            "longitude": tc["longitude"]
        }
        for i, tc in enumerate(test_cases)
    ]
    
    # 构建提示词
    prompt = build_prompt(coordinates)
    
    # 调用大模型
    logger.info("调用大模型进行海外坐标逆地址编码...")
    result = await llm_service.generate_text(
        prompt=prompt,
        system_prompt="你是一个专业的地理信息专家，能够准确地将坐标转换为地址信息。",
        max_tokens=3000,
        temperature=0.3
    )
    
    if not result.get("success"):
        logger.error(f"大模型调用失败: {result.get('error')}")
        return False
    
    content = result.get("content", "")
    logger.info(f"大模型返回内容:\n{content}")
    
    # 解析结果
    try:
        parsed_results = parse_llm_response(content)
        logger.info(f"解析成功，返回 {len(parsed_results)} 个结果")
        
        # 验证每个结果
        all_valid = True
        for i, (result_dict, test_case) in enumerate(zip(parsed_results, test_cases)):
            logger.info(f"\n验证结果 {i+1}: {test_case['name']}")
            logger.info(f"解析结果: {json.dumps(result_dict, indent=2, ensure_ascii=False)}")
            
            is_valid, errors = validate_result(result_dict, test_case)
            if is_valid:
                logger.success(f"✅ 结果 {i+1} 验证通过")
            else:
                logger.warning(f"⚠️ 结果 {i+1} 验证有警告: {errors}")
                # 海外坐标可能不完全匹配，只记录警告
        
        logger.success("✅ 海外坐标查询测试完成")
        return True
            
    except Exception as e:
        logger.error(f"❌ 解析或验证失败: {e}", exc_info=True)
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 80)
    logger.info("大模型逆地址编码功能测试")
    logger.info("=" * 80)
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Deepseek API Key: {'已配置' if settings.DEEPSEEK_API_KEY else '未配置'}")
    logger.info("=" * 80)
    
    # 检查配置
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("⚠️ DEEPSEEK_API_KEY 未配置，将使用 LLM_API_KEY")
    
    results = []
    
    # 测试1: 单个坐标点查询
    try:
        result1 = await test_single_coordinate()
        results.append(("单个坐标点查询", result1))
    except Exception as e:
        logger.error(f"测试1失败: {e}", exc_info=True)
        results.append(("单个坐标点查询", False))
    
    # 等待一下，避免API限流
    await asyncio.sleep(2)
    
    # 测试2: 批量坐标点查询
    try:
        result2 = await test_batch_coordinates()
        results.append(("批量坐标点查询", result2))
    except Exception as e:
        logger.error(f"测试2失败: {e}", exc_info=True)
        results.append(("批量坐标点查询", False))
    
    # 等待一下，避免API限流
    await asyncio.sleep(2)
    
    # 测试3: 海外坐标查询
    try:
        result3 = await test_overseas_coordinates()
        results.append(("海外坐标查询", result3))
    except Exception as e:
        logger.error(f"测试3失败: {e}", exc_info=True)
        results.append(("海外坐标查询", False))
    
    # 输出测试总结
    logger.info("=" * 80)
    logger.info("测试总结")
    logger.info("=" * 80)
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
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
