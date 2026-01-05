#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理位置相关API路由（v2版本）
支持外部API调用和批量查询
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import math
import time
import uuid

from app.database import db
from app.auth import get_current_user
from app.services.geocoding_client import geocoding_client
from app.utils.id_generator import IDGenerator
from app.utils.request_logger import RequestLogger
from loguru import logger

router = APIRouter(prefix="/api/v2/location", tags=["location-v2"])


# ===== 请求/响应模型 =====

class Coordinate(BaseModel):
    """坐标点"""
    id: Optional[str] = Field(None, description="位置ID（客户端自定义，用于响应映射）")
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")


class BatchNearestCityRequest(BaseModel):
    """批量查询最近城市请求"""
    coordinates: List[Coordinate] = Field(..., min_length=1, max_length=500, description="坐标点列表，最多500个")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")


class CityInfoV2(BaseModel):
    """城市信息（v2版本）"""
    id: int = Field(description="主键ID")
    name_en: str = Field(description="英文名称")
    name_zh: Optional[str] = Field(None, description="中文名称（通过映射表获取）")
    latitude: float = Field(description="纬度")
    longitude: float = Field(description="经度")
    country_code: str = Field(description="国家代码（ISO 3166-1 alpha-2）")
    
    # 行政区划信息
    admin1_code: Optional[str] = Field(None, description="一级行政区代码")
    admin2_code: Optional[str] = Field(None, description="二级行政区代码")
    province: Optional[str] = Field(None, description="省份/州名称")
    city: Optional[str] = Field(None, description="城市名称")
    district: Optional[str] = Field(None, description="区县名称")
    
    # 数据来源信息
    data_source: str = Field(description="数据来源：local/gaode")
    
    # 其他信息
    geoname_id: Optional[int] = Field(None, description="GeoNames ID")
    population: Optional[int] = Field(None, description="人口数")
    distance_km: float = Field(description="距离查询点的距离(公里)")
    
    # 元数据
    api_city_id: Optional[str] = Field(None, description="外部API返回的城市ID")
    api_adcode: Optional[str] = Field(None, description="高德地图的行政区划代码")


class CityQueryResult(BaseModel):
    """单个坐标点的查询结果"""
    location_id: Optional[str] = Field(None, description="位置ID（来自请求，用于响应映射）")
    coordinate: Coordinate = Field(description="查询的坐标点")
    city: Optional[CityInfoV2] = Field(None, description="最近的城市信息，查询失败时为None")
    success: bool = Field(description="是否查询成功")
    error: Optional[str] = Field(None, description="错误信息（失败时）")
    data_source: Optional[str] = Field(None, description="数据来源：local/gaode/fallback")
    query_time_ms: int = Field(description="查询耗时（毫秒）")


class BatchNearestCityResponse(BaseModel):
    """批量查询最近城市响应"""
    success: bool = Field(True, description="整体是否成功")
    results: List[CityQueryResult] = Field(description="每个坐标点的查询结果")
    total_count: int = Field(description="总查询数")
    success_count: int = Field(description="成功查询数")
    failed_count: int = Field(description="失败查询数")
    total_time_ms: int = Field(description="总耗时（毫秒）")
    request_id: str = Field(description="请求ID")


class LocationStatsV2(BaseModel):
    """位置数据库统计信息（v2版本）"""
    # 数据库统计
    total_cities: int = Field(description="总城市数（global_cities_v2）")
    cities_with_chinese: int = Field(description="有中文名称的城市数（可通过映射表获取）")
    mapping_table_size: int = Field(description="映射表记录数（city_name_mapping）")
    
    # 外部API调用统计（今日）
    api_calls_today: dict = Field(description="今日外部API调用统计")
    
    # 外部API调用统计（累计）
    api_calls_all: dict = Field(description="累计外部API调用统计")
    
    # 数据来源分布
    data_source_distribution: dict = Field(description="数据来源分布")


# ===== 工具函数 =====

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两个经纬度点之间的距离（公里）"""
    R = 6371.0  # 地球半径（公里）
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


async def query_local_db(latitude: float, longitude: float, max_distance_km: float = 3.0) -> Optional[dict]:
    """
    在本地数据库查询3km内的城市
    
    Args:
        latitude: 纬度
        longitude: 经度
        max_distance_km: 最大距离（公里），默认3km
        
    Returns:
        城市信息字典，未找到返回None
    """
    try:
        query = """
            SELECT 
                gc.id,
                gc.name_en,
                cnm.name_zh,
                gc.latitude,
                gc.longitude,
                gc.country_code,
                gc.admin1_code,
                gc.admin2_code,
                gc.province,
                gc.city,
                gc.district,
                gc.data_source,
                gc.geoname_id,
                gc.population,
                gc.api_city_id,
                gc.api_adcode,
                ST_Distance_Sphere(
                    POINT(gc.longitude, gc.latitude),
                    POINT(%s, %s)
                ) / 1000 AS distance_km
            FROM global_cities_v2 gc
            LEFT JOIN city_name_mapping cnm ON gc.name_en = cnm.name_en COLLATE utf8mb4_unicode_ci
            WHERE ST_Distance_Sphere(
                POINT(gc.longitude, gc.latitude),
                POINT(%s, %s)
            ) / 1000 <= %s
            ORDER BY distance_km
            LIMIT 1
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query, (longitude, latitude, longitude, latitude, max_distance_km))
            row = await cursor.fetchone()
        
        if row:
            result = dict(row)
            logger.debug(f"本地数据库查询成功: 坐标=({latitude}, {longitude}), 找到城市={result.get('name_en')}, 距离={result.get('distance_km', 0):.2f}km")
            return result
        logger.debug(f"本地数据库查询未命中: 坐标=({latitude}, {longitude}), 3km内无城市")
        return None
        
    except Exception as e:
        logger.error(f"本地数据库查询失败: {e}")
        return None


async def save_city_to_db(city_data: dict) -> Optional[int]:
    """
    将城市信息保存到本地数据库
    
    Args:
        city_data: 城市信息字典
        
    Returns:
        保存的城市ID，失败返回None
    """
    try:
        # 检查是否已存在（通过api_adcode或api_city_id）
        check_query = None
        check_params = None
        
        if city_data.get("api_adcode"):
            check_query = "SELECT id FROM global_cities_v2 WHERE api_adcode = %s"
            check_params = (city_data["api_adcode"],)
        elif city_data.get("api_city_id"):
            check_query = """
                SELECT id FROM global_cities_v2 
                WHERE data_source = %s AND api_city_id = %s
            """
            check_params = (city_data.get("data_source", "gaode"), city_data["api_city_id"])
        
        if check_query:
            async with db.get_cursor() as cursor:
                await cursor.execute(check_query, check_params)
                existing = await cursor.fetchone()
                if existing:
                    return existing["id"]
        
        # 插入新记录
        insert_query = """
            INSERT INTO global_cities_v2 (
                name_en, latitude, longitude, country_code,
                admin1_code, admin2_code, province, city, district,
                data_source, api_city_id, api_city_code, api_adcode,
                geoname_id, population
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        # 确保 name_en 不为空（必填字段）
        name_en = city_data.get("name_en") or city_data.get("name_zh") or ""
        if not name_en:
            logger.warning(f"城市数据缺少name_en和name_zh字段: {city_data}")
            return None
        
        # 确保 api_adcode 是字符串或 None，不能是列表
        api_adcode = city_data.get("api_adcode")
        if isinstance(api_adcode, list):
            api_adcode = api_adcode[0] if api_adcode else None
        if api_adcode:
            api_adcode = str(api_adcode)
        
        # 确保 api_city_id 是字符串或 None
        api_city_id = city_data.get("api_city_id")
        if isinstance(api_city_id, list):
            api_city_id = api_city_id[0] if api_city_id else None
        if api_city_id:
            api_city_id = str(api_city_id)
        
        # 确保 api_city_code 是字符串或 None
        api_city_code = city_data.get("api_city_code")
        if isinstance(api_city_code, list):
            api_city_code = api_city_code[0] if api_city_code else None
        if api_city_code:
            api_city_code = str(api_city_code)
        
        insert_params = (
            name_en,
            city_data["latitude"],
            city_data["longitude"],
            city_data.get("country_code", "UN"),
            city_data.get("admin1_code"),
            city_data.get("admin2_code"),
            city_data.get("province"),
            city_data.get("city"),
            city_data.get("district"),
            city_data.get("data_source", "local"),
            api_city_id,
            api_city_code,
            api_adcode,
            city_data.get("geoname_id"),
            city_data.get("population")
        )
        
        async with db.get_cursor() as cursor:
            await cursor.execute(insert_query, insert_params)
            city_id = cursor.lastrowid
            
            # 如果外部API返回了中文名，且映射表中没有，则插入映射表
            if city_data.get("name_zh") and city_data.get("name_en"):
                try:
                    mapping_query = """
                        INSERT INTO city_name_mapping (name_zh, name_en, country_code)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                    """
                    await cursor.execute(mapping_query, (
                        city_data["name_zh"],
                        city_data["name_en"],
                        city_data.get("country_code", "UN")
                    ))
                except Exception as e:
                    logger.warning(f"插入映射表失败: {e}")
            
            return city_id
            
    except Exception as e:
        logger.error(f"保存城市信息到数据库失败: {e}")
        return None


def validate_and_normalize_location(
    city_data: dict,
    latitude: float,
    longitude: float
) -> Optional[dict]:
    """
    验证和规范化位置信息
    
    判定规则：
    1. name_en：优先使用原始 name_en（如果有），否则用 name_zh 填充，都没有则为 "Unknown"
    2. name_zh：优先使用原始 name_zh（如果有），否则用 name_en 填充，都没有则为 "未知位置"
    3. country_code：可以按实际返回的，如果没有返回，整个位置信息也回退到未知位置
    4. province：如果是中国，没有的话，该数据就认为是错误数据，也回退到未知；如果是国外，可以用某个级别的行政区来代替
    
    如果 name_en、province、country_code 这三个元素有一个不能确定，这个位置就是未知位置（返回 None）
    
    Args:
        city_data: 城市信息字典
        latitude: 纬度（用于判断是否在中国）
        longitude: 经度（用于判断是否在中国）
        
    Returns:
        规范化后的城市信息字典，所有字段都是规范化后的值；如果验证失败返回 None（表示未知位置）
    """
    # 判断是否在中国境内
    is_china = geocoding_client.is_china_location(latitude, longitude)
    
    # 1. 规范化 name_en 和 name_zh
    name_zh = city_data.get("name_zh")
    name_en = city_data.get("name_en")
    
    # 去除空白字符并检查是否为空
    name_zh_clean = name_zh.strip() if name_zh and name_zh.strip() else None
    name_en_clean = name_en.strip() if name_en and name_en.strip() else None
    
    # name_en：优先使用原始 name_en（如果有），否则用 name_zh 填充，都没有则为 "Unknown"
    if name_en_clean:
        normalized_name_en = name_en_clean
    elif name_zh_clean:
        normalized_name_en = name_zh_clean
    else:
        normalized_name_en = "Unknown"
    
    # name_zh：优先使用原始 name_zh（如果有），否则用 name_en 填充，都没有则为 "未知位置"
    if name_zh_clean:
        normalized_name_zh = name_zh_clean
    elif name_en_clean:
        normalized_name_zh = name_en_clean
    else:
        normalized_name_zh = "未知位置"
    
    # 2. 规范化 country_code：必须有效（2位字符）
    country_code = city_data.get("country_code")
    if not country_code or len(str(country_code).strip()) != 2:
        # 如果没有有效的国家代码，尝试根据坐标判断
        if is_china:
            normalized_country_code = "CN"
        else:
            # 海外坐标但无法确定国家代码，视为未知位置
            logger.warning(f"位置信息验证失败：无法确定国家代码，坐标=({latitude}, {longitude}), city_data={city_data}")
            return None
    else:
        normalized_country_code = str(country_code).strip().upper()
    
    # 3. 规范化 province：根据国家代码判断要求
    province = city_data.get("province")
    
    if normalized_country_code == "CN":
        # 中国坐标：province 是必填的，如果没有则视为错误数据
        if not province or not str(province).strip():
            logger.warning(f"位置信息验证失败：中国坐标缺少省份信息，坐标=({latitude}, {longitude}), city_data={city_data}")
            return None
        normalized_province = str(province).strip()
    else:
        # 海外坐标：可以用 state 或 region 代替 province
        if not province or not str(province).strip():
            # 尝试从其他字段获取行政区信息
            province = (
                city_data.get("state") or
                city_data.get("region") or
                city_data.get("admin1_code") or
                None
            )
            if province:
                normalized_province = str(province).strip()
            else:
                # 海外坐标如果完全没有行政区信息，也视为未知位置
                logger.warning(f"位置信息验证失败：海外坐标缺少行政区信息，坐标=({latitude}, {longitude}), country_code={normalized_country_code}, city_data={city_data}")
                return None
        else:
            normalized_province = str(province).strip()
    
    # 4. 验证通过，返回规范化后的数据（所有字段都是规范化后的值）
    normalized_data = city_data.copy()
    normalized_data["name_en"] = normalized_name_en  # 规范化后的值
    normalized_data["name_zh"] = normalized_name_zh  # 规范化后的值
    normalized_data["country_code"] = normalized_country_code  # 规范化后的值
    normalized_data["province"] = normalized_province  # 规范化后的值
    
    return normalized_data


def create_unknown_location(latitude: float, longitude: float) -> CityInfoV2:
    """
    创建未知位置的默认 CityInfoV2 对象
    
    Args:
        latitude: 纬度
        longitude: 经度
        
    Returns:
        未知位置的 CityInfoV2 对象
    """
    return CityInfoV2(
        id=0,
        name_en="Unknown",
        name_zh="未知位置",
        latitude=latitude,
        longitude=longitude,
        country_code="UN",
        admin1_code=None,
        admin2_code=None,
        province="Unknown",
        city=None,
        district=None,
        data_source="unknown",
        geoname_id=None,
        population=None,
        distance_km=0.0,
        api_city_id=None,
        api_adcode=None
    )


async def query_fallback_v1(latitude: float, longitude: float) -> Optional[dict]:
    """
    降级到v1逻辑：查询最近的城市（不限制距离）
    
    Args:
        latitude: 纬度
        longitude: 经度
        
    Returns:
        城市信息字典，未找到返回None
    """
    try:
        # 判断是否在中国境内
        is_china = geocoding_client.is_china_location(latitude, longitude)
        logger.debug(f"v1降级查询: 坐标({latitude}, {longitude}), 是否中国: {is_china}")
        
        # 按行政级别筛选：优先选择城市级别的feature_code（PPLC, PPLG, PPLA, PPLA2）
        # 排除太细的行政级别（PPLA3, PPLA4, PPLX）
        valid_feature_codes = ("PPLC", "PPLG", "PPLA", "PPLA2")
        excluded_feature_codes = ("PPLA3", "PPLA4", "PPLX")
        
        # 构建 IN 子句的占位符（MySQL需要多个%s）
        valid_placeholders = ",".join(["%s"] * len(valid_feature_codes))
        excluded_placeholders = ",".join(["%s"] * len(excluded_feature_codes))
        
        # 对于中国坐标，优先查询有中文名的城市
        # 对于海外坐标，不要求中文名（因为海外城市可能没有中文名）
        if is_china:
            query = f"""
                SELECT 
                    id,
                    geoname_id,
                    COALESCE(ascii_name, name) AS name_en,
                    name_zh,
                    latitude,
                    longitude,
                    country_code,
                    population,
                    ST_Distance_Sphere(
                        POINT(longitude, latitude),
                        POINT(%s, %s)
                    ) / 1000 AS distance_km
                FROM global_cities
                WHERE feature_code IN ({valid_placeholders})
                  AND feature_code NOT IN ({excluded_placeholders})
                  AND name_zh IS NOT NULL
                ORDER BY distance_km
                LIMIT 1
            """
        else:
            # 海外坐标：不要求中文名，只要有英文名即可
            query = f"""
                SELECT 
                    id,
                    geoname_id,
                    COALESCE(ascii_name, name) AS name_en,
                    name_zh,
                    latitude,
                    longitude,
                    country_code,
                    population,
                    ST_Distance_Sphere(
                        POINT(longitude, latitude),
                        POINT(%s, %s)
                    ) / 1000 AS distance_km
                FROM global_cities
                WHERE feature_code IN ({valid_placeholders})
                  AND feature_code NOT IN ({excluded_placeholders})
                  AND (COALESCE(ascii_name, name) IS NOT NULL)
                ORDER BY distance_km
                LIMIT 1
            """
        
        async with db.get_cursor() as cursor:
            # 执行查询，传入参数：longitude, latitude, valid_feature_codes, excluded_feature_codes
            params = (longitude, latitude) + valid_feature_codes + excluded_feature_codes
            logger.debug(f"v1降级查询第1层: 执行SQL查询，坐标=({latitude}, {longitude}), feature_codes={valid_feature_codes}")
            await cursor.execute(query, params)
            row = await cursor.fetchone()
            
            if row:
                logger.debug(f"v1降级查询第1层成功: 找到城市 {row.get('name_en')}, 距离={row.get('distance_km')}km")
            else:
                logger.debug(f"v1降级查询第1层失败: 未找到符合条件的城市")
            
            # 如果没找到结果，尝试放宽行政级别限制（包含PPLA3，但仍排除PPLA4和PPLX）
            if not row:
                logger.debug(f"v1降级查询: 未找到城市级别的地点，尝试放宽行政级别限制...")
                relaxed_feature_codes = ("PPLC", "PPLG", "PPLA", "PPLA2", "PPLA3")
                relaxed_excluded = ("PPLA4", "PPLX")
                relaxed_valid_placeholders = ",".join(["%s"] * len(relaxed_feature_codes))
                relaxed_excluded_placeholders = ",".join(["%s"] * len(relaxed_excluded))
                
                if is_china:
                    relaxed_query = f"""
                        SELECT 
                            id,
                            geoname_id,
                            COALESCE(ascii_name, name) AS name_en,
                            name_zh,
                            latitude,
                            longitude,
                            country_code,
                            population,
                            ST_Distance_Sphere(
                                POINT(longitude, latitude),
                                POINT(%s, %s)
                            ) / 1000 AS distance_km
                        FROM global_cities
                        WHERE feature_code IN ({relaxed_valid_placeholders})
                          AND feature_code NOT IN ({relaxed_excluded_placeholders})
                          AND name_zh IS NOT NULL
                        ORDER BY distance_km
                        LIMIT 1
                    """
                else:
                    relaxed_query = f"""
                        SELECT 
                            id,
                            geoname_id,
                            COALESCE(ascii_name, name) AS name_en,
                            name_zh,
                            latitude,
                            longitude,
                            country_code,
                            population,
                            ST_Distance_Sphere(
                                POINT(longitude, latitude),
                                POINT(%s, %s)
                            ) / 1000 AS distance_km
                        FROM global_cities
                        WHERE feature_code IN ({relaxed_valid_placeholders})
                          AND feature_code NOT IN ({relaxed_excluded_placeholders})
                          AND (COALESCE(ascii_name, name) IS NOT NULL)
                        ORDER BY distance_km
                        LIMIT 1
                    """
                
                relaxed_params = (longitude, latitude) + relaxed_feature_codes + relaxed_excluded
                logger.debug(f"v1降级查询第2层: 执行SQL查询，坐标=({latitude}, {longitude}), feature_codes={relaxed_feature_codes}")
                await cursor.execute(relaxed_query, relaxed_params)
                row = await cursor.fetchone()
                
                if row:
                    logger.debug(f"v1降级查询第2层成功: 找到城市 {row.get('name_en')}, 距离={row.get('distance_km')}km")
                else:
                    logger.debug(f"v1降级查询第2层失败: 未找到符合条件的城市")
                
                # 如果还是没找到，完全移除行政级别限制（最后的降级策略）
                if not row:
                    logger.debug(f"v1降级查询: 放宽行政级别后仍未找到，尝试移除行政级别限制...")
                    if is_china:
                        final_query = """
                            SELECT 
                                id,
                                geoname_id,
                                COALESCE(ascii_name, name) AS name_en,
                                name_zh,
                                latitude,
                                longitude,
                                country_code,
                                population,
                                ST_Distance_Sphere(
                                    POINT(longitude, latitude),
                                    POINT(%s, %s)
                                ) / 1000 AS distance_km
                            FROM global_cities
                            WHERE name_zh IS NOT NULL
                            ORDER BY distance_km
                            LIMIT 1
                        """
                    else:
                        final_query = """
                            SELECT 
                                id,
                                geoname_id,
                                COALESCE(ascii_name, name) AS name_en,
                                name_zh,
                                latitude,
                                longitude,
                                country_code,
                                population,
                                ST_Distance_Sphere(
                                    POINT(longitude, latitude),
                                    POINT(%s, %s)
                                ) / 1000 AS distance_km
                            FROM global_cities
                            WHERE COALESCE(ascii_name, name) IS NOT NULL
                            ORDER BY distance_km
                            LIMIT 1
                        """
                    
                    logger.debug(f"v1降级查询第3层: 执行SQL查询，坐标=({latitude}, {longitude}), 无feature_code限制")
                    await cursor.execute(final_query, (longitude, latitude))
                    row = await cursor.fetchone()
                    
                    if row:
                        logger.debug(f"v1降级查询第3层成功: 找到城市 {row.get('name_en')}, 距离={row.get('distance_km')}km")
                    else:
                        # 检查数据库中是否有任何城市数据（用于诊断）
                        check_query = "SELECT COUNT(*) as total FROM global_cities WHERE COALESCE(ascii_name, name) IS NOT NULL LIMIT 1"
                        await cursor.execute(check_query)
                        count_row = await cursor.fetchone()
                        total_cities = count_row.get("total", 0) if count_row else 0
                        
                        logger.warning(f"v1降级查询: 所有降级策略都失败，坐标({latitude}, {longitude})")
                        logger.warning(f"数据库诊断: global_cities表中共有 {total_cities} 个城市记录")
                        
                        # 尝试查询最近的城市（完全无限制，用于诊断）
                        diagnostic_query = """
                            SELECT 
                                COALESCE(ascii_name, name) AS name_en,
                                latitude,
                                longitude,
                                ST_Distance_Sphere(
                                    POINT(longitude, latitude),
                                    POINT(%s, %s)
                                ) / 1000 AS distance_km
                            FROM global_cities
                            WHERE COALESCE(ascii_name, name) IS NOT NULL
                            ORDER BY distance_km
                            LIMIT 5
                        """
                        await cursor.execute(diagnostic_query, (longitude, latitude))
                        nearest_cities = await cursor.fetchall()
                        if nearest_cities:
                            city_list = [(c.get('name_en'), f"{c.get('distance_km'):.1f}km") for c in nearest_cities]
                            logger.warning(f"最近的5个城市: {city_list}")
                        else:
                            logger.error(f"数据库中没有找到任何城市数据！")
        
        if row:
            return {
                "id": row["id"],
                "name_en": row["name_en"],
                "name_zh": row["name_zh"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "country_code": row["country_code"],
                "geoname_id": row["geoname_id"],
                "population": row["population"],
                "distance_km": float(row["distance_km"]),
                "data_source": "fallback",
                "admin1_code": None,
                "admin2_code": None,
                "province": None,  # v1表没有province字段
                "city": None,
                "district": None,
                "api_city_id": None,
                "api_adcode": None,
                # 添加这些字段用于海外坐标的province替代
                "state": None,  # 海外坐标可能用到
                "region": None  # 海外坐标可能用到
            }
        return None
        
    except Exception as e:
        logger.error(f"v1降级查询失败: {e}")
        return None


async def query_single_coordinate(coord: Coordinate) -> CityQueryResult:
    """
    查询单个坐标点的最近城市
    
    Args:
        coord: 坐标点
        
    Returns:
        查询结果
    """
    start_time = time.time()
    latitude = coord.latitude
    longitude = coord.longitude
    
    try:
        # 1. 先在本地数据库查询3km内的城市
        city_data = await query_local_db(latitude, longitude, max_distance_km=3.0)
        
        if city_data:
            # 本地数据库命中，验证和规范化位置信息
            normalized_data = validate_and_normalize_location(city_data, latitude, longitude)
            
            if not normalized_data:
                # 验证失败，返回未知位置
                logger.warning(f"本地数据库命中但位置信息不完整，返回未知位置: 坐标=({latitude}, {longitude})")
                query_time_ms = int((time.time() - start_time) * 1000)
                return CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=create_unknown_location(latitude, longitude),
                    success=True,  # 仍然返回成功，但位置是未知的
                    error=None,
                    data_source="local",
                    query_time_ms=query_time_ms
                )
            
            # 验证通过，使用规范化后的数据
            query_time_ms = int((time.time() - start_time) * 1000)
            
            city_info = CityInfoV2(
                id=normalized_data["id"],
                name_en=normalized_data["name_en"],  # 已规范化
                name_zh=normalized_data.get("name_zh"),  # 已规范化
                latitude=float(normalized_data["latitude"]),
                longitude=float(normalized_data["longitude"]),
                country_code=normalized_data["country_code"],  # 已规范化
                admin1_code=normalized_data.get("admin1_code"),
                admin2_code=normalized_data.get("admin2_code"),
                province=normalized_data["province"],  # 已规范化
                city=normalized_data.get("city"),
                district=normalized_data.get("district"),
                data_source=normalized_data.get("data_source", "local"),
                geoname_id=normalized_data.get("geoname_id"),
                population=normalized_data.get("population"),
                distance_km=float(normalized_data.get("distance_km", 0)),
                api_city_id=str(normalized_data["api_city_id"]) if normalized_data.get("api_city_id") else None,
                api_adcode=normalized_data.get("api_adcode")
            )
            
            return CityQueryResult(
                location_id=coord.id,
                coordinate=coord,
                city=city_info,
                success=True,
                error=None,
                data_source="local",
                query_time_ms=query_time_ms
            )
        
        # 2. 本地数据库未命中，调用外部API
        # 中国坐标：使用高德API
        # 海外坐标：使用Nominatim API（通过Cloudflare Worker代理，绕过防火墙限制）
        api_result = None
        api_provider = None
        api_error = None
        is_china = geocoding_client.is_china_location(latitude, longitude)
        
        try:
            if is_china:
                # 中国坐标：使用高德API
                api_provider = "gaode"
                logger.info(f"本地数据库未命中，调用高德API: 坐标=({latitude}, {longitude})")
                api_result = await geocoding_client.reverse_geocode_gaode(latitude, longitude)
                
                # 记录API调用统计
                if api_result:
                    await record_api_call(api_provider, success=True)
                    logger.info(f"高德API调用成功: 坐标=({latitude}, {longitude}), name_zh={api_result.get('name_zh')}, name_en={api_result.get('name_en')}")
                else:
                    await record_api_call(api_provider, success=False)
                    logger.warning(f"高德API调用失败（中国坐标）: 坐标=({latitude}, {longitude})")
            else:
                # 海外坐标：使用Nominatim API（通过Cloudflare Worker代理）
                api_provider = "nominatim"
                logger.info(f"本地数据库未命中，调用Nominatim API: 坐标=({latitude}, {longitude})")
                api_result = await geocoding_client.reverse_geocode_nominatim(latitude, longitude)
                
                # 记录API调用统计
                if api_result:
                    await record_api_call(api_provider, success=True)
                    logger.info(f"Nominatim API调用成功: 坐标=({latitude}, {longitude}), name_en={api_result.get('name_en')}")
                else:
                    await record_api_call(api_provider, success=False)
                    logger.warning(f"Nominatim API调用失败，返回None: 坐标=({latitude}, {longitude})")
        except Exception as api_e:
            api_error = str(api_e)
            logger.error(f"外部API调用异常 ({api_provider}, {latitude}, {longitude}): {api_error}")
            if api_provider:
                await record_api_call(api_provider, success=False)
        
        if api_result:
            # 3. 外部API成功，验证和规范化位置信息
            normalized_data = validate_and_normalize_location(api_result, latitude, longitude)
            
            if not normalized_data:
                # 验证失败，返回未知位置
                logger.warning(f"外部API返回但位置信息不完整，返回未知位置: 坐标=({latitude}, {longitude}), provider={api_provider}")
                query_time_ms = int((time.time() - start_time) * 1000)
                return CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=create_unknown_location(latitude, longitude),
                    success=True,
                    error=None,
                    data_source=api_provider or "unknown",
                    query_time_ms=query_time_ms
                )
            
            # 验证通过，保存到本地数据库（使用原始数据，保持数据真实可靠）
            city_id = await save_city_to_db(api_result)  # 保存原始数据
            
            if city_id:
                normalized_data["id"] = city_id
            
            # 计算距离
            distance_km = haversine_distance(
                latitude, longitude,
                normalized_data["latitude"], normalized_data["longitude"]
            )
            
            query_time_ms = int((time.time() - start_time) * 1000)
            
            # 确保 api_adcode 是字符串或 None
            api_adcode = normalized_data.get("api_adcode")
            if isinstance(api_adcode, list):
                api_adcode = api_adcode[0] if api_adcode else None
            if api_adcode:
                api_adcode = str(api_adcode)
            
            # 确保 api_city_id 是字符串或 None
            api_city_id = normalized_data.get("api_city_id")
            if isinstance(api_city_id, list):
                api_city_id = api_city_id[0] if api_city_id else None
            if api_city_id:
                api_city_id = str(api_city_id)
            
            city_info = CityInfoV2(
                id=normalized_data.get("id", 0),
                name_en=normalized_data["name_en"],  # 已规范化
                name_zh=normalized_data.get("name_zh"),  # 已规范化
                latitude=normalized_data["latitude"],
                longitude=normalized_data["longitude"],
                country_code=normalized_data["country_code"],  # 已规范化
                admin1_code=normalized_data.get("admin1_code"),
                admin2_code=normalized_data.get("admin2_code"),
                province=normalized_data["province"],  # 已规范化
                city=normalized_data.get("city"),
                district=normalized_data.get("district"),
                data_source=normalized_data.get("data_source", api_provider),
                geoname_id=normalized_data.get("geoname_id"),
                population=normalized_data.get("population"),
                distance_km=distance_km,
                api_city_id=api_city_id,
                api_adcode=api_adcode
            )
            
            return CityQueryResult(
                location_id=coord.id,
                coordinate=coord,
                city=city_info,
                success=True,
                error=None,
                data_source=api_provider,
                query_time_ms=query_time_ms
            )
        
        # 4. 外部API失败，降级到v1逻辑
        if not api_result:
            logger.info(f"外部API未返回结果，降级到v1逻辑: ({latitude}, {longitude}), provider={api_provider}, error={api_error}")
        
        fallback_data = await query_fallback_v1(latitude, longitude)
        
        if fallback_data:
            # 验证和规范化 fallback 数据
            normalized_data = validate_and_normalize_location(fallback_data, latitude, longitude)
            
            if not normalized_data:
                # 验证失败，返回未知位置
                logger.warning(f"v1降级查询返回但位置信息不完整，返回未知位置: 坐标=({latitude}, {longitude})")
                query_time_ms = int((time.time() - start_time) * 1000)
                return CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=create_unknown_location(latitude, longitude),
                    success=True,
                    error=None,
                    data_source="fallback",
                    query_time_ms=query_time_ms
                )
            
            # 验证通过
            logger.debug(f"v1降级查询成功: ({latitude}, {longitude}) -> {normalized_data.get('name_en')}")
            query_time_ms = int((time.time() - start_time) * 1000)
            
            city_info = CityInfoV2(
                id=normalized_data["id"],
                name_en=normalized_data["name_en"],  # 已规范化
                name_zh=normalized_data.get("name_zh"),  # 已规范化
                latitude=normalized_data["latitude"],
                longitude=normalized_data["longitude"],
                country_code=normalized_data["country_code"],  # 已规范化
                admin1_code=normalized_data.get("admin1_code"),
                admin2_code=normalized_data.get("admin2_code"),
                province=normalized_data["province"],  # 已规范化
                city=normalized_data.get("city"),
                district=normalized_data.get("district"),
                data_source="fallback",
                geoname_id=normalized_data.get("geoname_id"),
                population=normalized_data.get("population"),
                distance_km=normalized_data["distance_km"],
                api_city_id=normalized_data.get("api_city_id"),
                api_adcode=normalized_data.get("api_adcode")
            )
            
            return CityQueryResult(
                location_id=coord.id,
                coordinate=coord,
                city=city_info,
                success=True,
                error=None,
                data_source="fallback",
                query_time_ms=query_time_ms
            )
        
        # 所有查询都失败，返回未知位置
        query_time_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"所有查询都失败，返回未知位置: ({latitude}, {longitude}), location_id={coord.id}")
        
        return CityQueryResult(
            location_id=coord.id,
            coordinate=coord,
            city=create_unknown_location(latitude, longitude),
            success=True,  # 返回成功，但位置是未知的
            error=None,
            data_source="unknown",
            query_time_ms=query_time_ms
        )
        
    except Exception as e:
        query_time_ms = int((time.time() - start_time) * 1000)
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"查询坐标点异常 ({latitude}, {longitude}), location_id={coord.id}: {e}\n{error_traceback}")
        return CityQueryResult(
            location_id=coord.id,
            coordinate=coord,
            city=create_unknown_location(latitude, longitude),  # 异常时也返回未知位置
            success=True,
            error=None,
            data_source="unknown",
            query_time_ms=query_time_ms
        )


async def record_api_call(api_provider: str, success: bool):
    """记录外部API调用统计"""
    try:
        query = """
            INSERT INTO location_api_call_stats 
                (stat_date, api_provider, total_calls, success_calls, failed_calls)
            VALUES 
                (CURDATE(), %s, 1, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_calls = total_calls + 1,
                success_calls = success_calls + %s,
                failed_calls = failed_calls + %s,
                updated_at = CURRENT_TIMESTAMP
        """
        
        success_int = 1 if success else 0
        failed_int = 1 if not success else 0
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query, (
                api_provider, success_int, failed_int, success_int, failed_int
            ))
    except Exception as e:
        logger.warning(f"记录API调用统计失败: {e}")


# ===== API端点 =====

@router.get("/stats", response_model=LocationStatsV2, summary="获取位置数据库统计信息（v2）")
async def get_location_stats_v2(
    current_user: str = Depends(get_current_user),
    request: Request = None
):
    """
    获取位置数据库的统计信息（v2版本，需要认证）
    
    **返回:** 
    - 数据库统计（总城市数、有中文名的城市数、映射表大小）
    - 外部API调用统计（今日和累计）
    - 数据来源分布
    
    **示例:**
    ```
    GET /api/v2/location/stats
    ```
    """
    request_id = IDGenerator.generate_request_id("location_stats")
    start_time = time.time()
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint="/api/v2/location/stats",
            method="GET",
            user_id=current_user,
            ip_address=ip_address
        )
        
        RequestLogger.log_step(request_id, "query_db_stats", "查询数据库统计", user_id=current_user)
        # 查询数据库统计
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT gc.name_en) as unique_name_en
            FROM global_cities_v2 gc
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query)
            db_stats = await cursor.fetchone()
        
        # 查询可通过映射表获取中文名的城市数
        mapping_query = """
            SELECT COUNT(DISTINCT gc.name_en) as mappable_count
            FROM global_cities_v2 gc
            INNER JOIN city_name_mapping cnm ON gc.name_en = cnm.name_en COLLATE utf8mb4_unicode_ci
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(mapping_query)
            mapping_stats = await cursor.fetchone()
        
        # 查询映射表大小
        mapping_size_query = "SELECT COUNT(*) as total FROM city_name_mapping"
        async with db.get_cursor() as cursor:
            await cursor.execute(mapping_size_query)
            mapping_size = await cursor.fetchone()
        
        # 查询数据来源分布
        source_query = """
            SELECT data_source, COUNT(*) as count
            FROM global_cities_v2
            GROUP BY data_source
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(source_query)
            source_rows = await cursor.fetchall()
        
        data_source_distribution = {row["data_source"]: row["count"] for row in source_rows}
        
        # 查询外部API调用统计（今日）
        today_query = """
            SELECT api_provider, SUM(total_calls) as total, SUM(success_calls) as success, SUM(failed_calls) as failed
            FROM location_api_call_stats
            WHERE stat_date = CURDATE()
            GROUP BY api_provider
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(today_query)
            today_rows = await cursor.fetchall()
        
        api_calls_today = {}
        for row in today_rows:
            api_calls_today[row["api_provider"]] = {
                "total": row["total"],
                "success": row["success"],
                "failed": row["failed"]
            }
        
        # 查询外部API调用统计（累计）
        all_query = """
            SELECT api_provider, SUM(total_calls) as total, SUM(success_calls) as success, SUM(failed_calls) as failed
            FROM location_api_call_stats
            GROUP BY api_provider
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(all_query)
            all_rows = await cursor.fetchall()
        
        api_calls_all = {}
        for row in all_rows:
            api_calls_all[row["api_provider"]] = {
                "total": row["total"],
                "success": row["success"],
                "failed": row["failed"]
            }
        
        response = LocationStatsV2(
            total_cities=db_stats["total"] or 0,
            cities_with_chinese=mapping_stats["mappable_count"] or 0,
            mapping_table_size=mapping_size["total"] or 0,
            api_calls_today=api_calls_today,
            api_calls_all=api_calls_all,
            data_source_distribution=data_source_distribution
        )
        
        # 记录响应
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/location/stats",
            status_code=200,
            user_id=current_user,
            response_time_ms=response_time_ms,
            total_cities=db_stats["total"] or 0
        )
        
        return response
        
    except Exception as e:
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/location/stats",
            current_user,
            "query_failed"
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/location/stats",
            status_code=500,
            user_id=current_user,
            response_time_ms=response_time_ms
        )
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/nearest-cities", response_model=BatchNearestCityResponse, summary="批量查询最近的城市（v2）")
async def batch_get_nearest_cities_v2(
    request_body: BatchNearestCityRequest,
    request: Request = None
):
    """
    批量查询多个坐标点的最近城市（v2版本）
    
    **查询逻辑（对每个坐标点）:**
    1. 先在本地数据库查询3km内的城市
    2. 如果未找到，调用高德API进行逆地理编码
    3. 如果高德API成功，将结果保存到本地数据库
    4. 如果高德API失败，降级到v1逻辑（查询最近的城市，不限制距离）
    
    **参数:**
    - **coordinates**: 坐标点列表，最多500个
      - **id**: 位置ID（可选，客户端自定义，用于响应映射）
      - **latitude**: 纬度，范围 -90 到 90
      - **longitude**: 经度，范围 -180 到 180
    - **user_id**: 用户ID（可选）
    
    **返回:** 
    - 每个坐标点的查询结果（成功或失败）
    - 结果中包含 `location_id` 字段，与请求中的 `id` 对应，便于映射
    - 整体统计信息（总数、成功数、失败数、总耗时）
    
    **性能说明:**
    - 本地数据库查询：并发处理，响应快速（<1秒）
    - 高德API调用：按需调用，通常<1秒
    - 建议客户端异步调用，避免阻塞主流程
    
    **注意:** 
    - 部分坐标点查询失败不影响其他坐标点的查询
    - 每个坐标点独立处理，可能使用不同的数据来源
    - 如果请求中提供了 `id`，响应中的 `location_id` 会原样返回
    
    **客户端使用建议:**
    - 批量照片分类时，可以一张一张处理
    - 本地照片处理时异步访问获取位置信息
    - 不需要等待位置查询完成即可继续处理下一张照片
    
    **示例:**
    ```json
    POST /api/v2/location/nearest-cities
    {
      "coordinates": [
        {"id": "photo_001", "latitude": 39.9042, "longitude": 116.4074},
        {"id": "photo_002", "latitude": 31.2304, "longitude": 121.4737},
        {"id": "photo_003", "latitude": 40.7128, "longitude": -74.0060}
      ],
      "user_id": "user123"
    }
    ```
    """
    start_time = time.time()
    request_id = IDGenerator.generate_request_id("nearest_cities")
    user_id = request_body.user_id
    ip_address = request.client.host if request else None
    
    try:
        # 记录请求开始
        RequestLogger.log_request(
            request_id=request_id,
            endpoint="/api/v2/location/nearest-cities",
            method="POST",
            user_id=user_id,
            ip_address=ip_address,
            params={"coordinates_count": len(request_body.coordinates)}
        )
        
        # 批量查询所有坐标点
        RequestLogger.log_step(request_id, "query_coordinates", f"开始批量查询 {len(request_body.coordinates)} 个坐标点", user_id=user_id)
        import asyncio
        tasks = [query_single_coordinate(coord) for coord in request_body.coordinates]
        results = await asyncio.gather(*tasks)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        RequestLogger.log_step(
            request_id,
            "query_complete",
            f"批量查询完成: 成功={success_count}, 失败={failed_count}",
            user_id=user_id
        )
        
        total_time_ms = int((time.time() - start_time) * 1000)
        
        response = BatchNearestCityResponse(
            success=True,
            results=results,
            total_count=len(results),
            success_count=success_count,
            failed_count=failed_count,
            total_time_ms=total_time_ms,
            request_id=request_id
        )
        
        # 记录响应
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/location/nearest-cities",
            status_code=200,
            user_id=user_id,
            response_time_ms=total_time_ms,
            total_count=len(results),
            success_count=success_count,
            failed_count=failed_count
        )
        
        return response
        
    except Exception as e:
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v2/location/nearest-cities",
            user_id,
            "query_failed"
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v2/location/nearest-cities",
            status_code=500,
            user_id=user_id,
            response_time_ms=response_time_ms
        )
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

