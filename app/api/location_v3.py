#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理位置相关API路由（v3版本）
基于大模型的逆地址编码，使用DBSCAN聚类算法优化API调用次数
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field
import math
import time
import json
import asyncio

from app.database import db
from app.auth import get_current_user
from app.services.llm import llm_service
from app.utils.id_generator import IDGenerator
from app.utils.request_logger import RequestLogger
from loguru import logger

# 复用V2版本的函数和模型
from app.api.location_v2 import (
    Coordinate,
    CityInfoV2,
    CityQueryResult,
    BatchNearestCityResponse,
    haversine_distance,
    create_unknown_location,
)

router = APIRouter(prefix="/api/v3/location", tags=["location-v3"])


# ===== 名称规范化 =====
# 中文行政区划后缀（按长度从长到短，避免 自治区 被 区 误删）
_PLACE_SUFFIXES_ZH = [
    "特别行政区", "自治区", "直辖市", "地区",
    "市", "省", "县", "区", "州", "盟",
]
# 英文常见后缀
_PLACE_SUFFIXES_EN = [
    " Special Administrative Region", " Autonomous Region", " Province",
    " City", " District", " County", " Prefecture", " Region",
]


def _normalize_place_name(name: Optional[str]) -> str:
    """
    规范化地名：trim + 去掉末尾的行政区划后缀
    与客户端 LocationStorageService 的 normalizeDisplayName 一致，便于 location_id 匹配
    中文 ≤2 字不规范化（如 北区、东区）
    """
    if not name or not isinstance(name, str):
        return ""
    s = name.strip()
    if not s:
        return ""
    has_chinese = any("\u4e00" <= c <= "\u9fff" for c in s)
    # 中文 ≤2 字不规范化
    if has_chinese and len(s) <= 2:
        return s
    # 中文：去掉 市、省、县、区、州 等
    if has_chinese:
        for suffix in _PLACE_SUFFIXES_ZH:
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[: -len(suffix)].strip()
                break
    else:
        # 英文：去掉 Province、City 等（忽略大小写）
        for suffix in _PLACE_SUFFIXES_EN:
            if len(s) > len(suffix) and s.lower().endswith(suffix.lower()):
                s = s[: -len(suffix)].strip()
                break
    return s


# ===== V3 专用：location_cache_v3 表 =====
async def query_location_cache_v3(latitude: float, longitude: float, max_distance_km: float = 3.0) -> Optional[dict]:
    """
    从 location_cache_v3 查询 3km 内最近的位置
    返回格式可直接转为 CityInfoV2（含完整中英文）
    """
    try:
        query = """
            SELECT id, latitude, longitude,
                   country_code, country_zh, country_en,
                   province_zh, province_en, city_zh, city_en, district_zh, district_en,
                   ST_Distance_Sphere(POINT(longitude, latitude), POINT(%s, %s)) / 1000 AS distance_km
            FROM location_cache_v3
            WHERE ST_Distance_Sphere(POINT(longitude, latitude), POINT(%s, %s)) / 1000 <= %s
            ORDER BY distance_km
            LIMIT 1
        """
        async with db.get_cursor() as cursor:
            await cursor.execute(query, (longitude, latitude, longitude, latitude, max_distance_km))
            row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"location_cache_v3 查询失败: {e}")
        return None


def _cache_row_to_normalized_dict(row: dict) -> dict:
    """将 location_cache_v3 行转为 API 使用的 normalized_data 格式"""
    province_zh = _normalize_place_name(row.get("province_zh")) or ""
    province_en = _normalize_place_name(row.get("province_en")) or ""
    city_zh = _normalize_place_name(row.get("city_zh")) or ""
    city_en = _normalize_place_name(row.get("city_en")) or ""
    district_zh = _normalize_place_name(row.get("district_zh")) or ""
    district_en = _normalize_place_name(row.get("district_en")) or ""

    admin1_zh = province_zh or None
    admin1_en = province_en or "unknown"
    admin2_zh = district_zh or city_zh or None
    admin2_en = district_en or city_en or _normalize_place_name(row.get("country_en")) or "unknown"

    name_en = city_en or district_en or row.get("country_en") or "Unknown"
    name_zh = city_zh or district_zh or row.get("country_zh") or "未知位置"

    return {
        "id": row["id"],
        "name_en": name_en,
        "name_zh": name_zh,
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "country_code": row.get("country_code", "UN"),
        "admin1_zh": admin1_zh or None,
        "admin1_en": admin1_en,
        "admin2_zh": admin2_zh or None,
        "admin2_en": admin2_en,
        "admin1_code": None,
        "admin2_code": None,
        "province": province_zh or province_en,
        "city": city_zh or city_en,
        "district": district_zh or district_en,
        "geoname_id": None,
        "population": None,
        "api_city_id": None,
        "api_adcode": None,
    }


def _cache_row_to_city_info(row: dict, query_lat: float, query_lon: float) -> CityInfoV2:
    """将 location_cache_v3 行转为 CityInfoV2（兼容客户端）"""
    nd = _cache_row_to_normalized_dict(row)
    return CityInfoV2(
        id=nd["id"],
        name_en=nd["name_en"],
        name_zh=nd["name_zh"],
        latitude=nd["latitude"],
        longitude=nd["longitude"],
        country_code=nd["country_code"],
        admin1_zh=nd.get("admin1_zh"),
        admin1_en=nd.get("admin1_en"),
        admin2_zh=nd.get("admin2_zh"),
        admin2_en=nd.get("admin2_en"),
        admin1_code=None,
        admin2_code=None,
        province=nd["province"],
        city=nd["city"],
        district=nd["district"],
        data_source="local",
        geoname_id=None,
        population=None,
        distance_km=float(row.get("distance_km", 0)),
        api_city_id=None,
        api_adcode=None,
    )


async def save_location_cache_v3(
    latitude: float, longitude: float, location_info: dict
) -> Optional[int]:
    """
    保存到 location_cache_v3，带去重（坐标 0.0001 度内视为同点）
    名称规范化：trim 后存储
    """
    try:
        # 规范化
        country_zh = _normalize_place_name(location_info.get("country_name_zh")) or ""
        country_en = _normalize_place_name(location_info.get("country_name_en")) or ""
        province_zh = _normalize_place_name(location_info.get("admin1_name_zh")) or None
        province_en = _normalize_place_name(location_info.get("admin1_name_en")) or None
        city_zh = _normalize_place_name(location_info.get("city_name_zh")) or None
        city_en = _normalize_place_name(location_info.get("city_name_en")) or None
        district_zh = _normalize_place_name(location_info.get("admin2_name_zh")) or None
        district_en = _normalize_place_name(location_info.get("admin2_name_en")) or None
        country_code = (location_info.get("country_code") or "UN").strip().upper()[:2]

        # 国家名兜底
        if not country_en:
            country_en = country_code
        if not country_zh:
            country_zh = "未知"

        # 去重：同坐标 0.0001 度内已存在则跳过
        async with db.get_cursor() as cursor:
            await cursor.execute(
                """SELECT id FROM location_cache_v3
                   WHERE ABS(latitude - %s) < 0.0001 AND ABS(longitude - %s) < 0.0001 LIMIT 1""",
                (latitude, longitude),
            )
            if await cursor.fetchone():
                return None

            await cursor.execute(
                """INSERT INTO location_cache_v3 (
                    latitude, longitude, country_code,
                    country_zh, country_en, province_zh, province_en,
                    city_zh, city_en, district_zh, district_en
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    latitude, longitude, country_code,
                    country_zh, country_en, province_zh, province_en,
                    city_zh, city_en, district_zh, district_en,
                ),
            )
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"保存 location_cache_v3 失败: {e}", exc_info=True)
        return None


# ===== 请求/响应模型 =====

class BatchNearestCityRequestV3(BaseModel):
    """批量查询最近城市请求（v3版本）"""
    coordinates: List[Coordinate] = Field(..., min_length=1, max_length=1000, description="坐标点列表，最多1000个")
    user_id: Optional[str] = Field(None, description="用户ID（可选）")


# ===== 工具函数 =====
# 注意：聚类、LLM查询等核心逻辑已迁移到 app/services/llm/llm_service.py
# 以下函数仅用于本地数据处理和结果转换

async def save_cluster_results_to_db(
    clusters: List[Tuple[float, float, List[Coordinate]]],
    llm_results: Dict[str, dict]
) -> None:
    """
    将聚类结果保存到 location_cache_v3（保存聚类内的所有坐标点）
    """
    saved_count = 0
    skipped_count = 0

    for center_lat, center_lon, coordinates in clusters:
        if not coordinates:
            continue

        for coord in coordinates:
            coord_id = coord.id or f"{coord.latitude}_{coord.longitude}"
            location_info = llm_results.get(coord_id)

            if not location_info:
                for point_id, result in llm_results.items():
                    qlat = result.get("query_latitude")
                    qlon = result.get("query_longitude")
                    if qlat and qlon and abs(qlat - center_lat) < 0.0001 and abs(qlon - center_lon) < 0.0001:
                        location_info = result
                        break
                if not location_info:
                    logger.warning(f"未找到坐标点位置信息: {coord_id}")
                    continue

            cid = await save_location_cache_v3(coord.latitude, coord.longitude, location_info)
            if cid:
                saved_count += 1
            else:
                skipped_count += 1

    logger.info(f"location_cache_v3 保存完成: 新增={saved_count}, 跳过={skipped_count}")


def convert_llm_result_to_city_info(
    llm_result: dict,
    query_lat: float,
    query_lon: float
) -> Optional[CityInfoV2]:
    """
    将大模型返回的结果转换为CityInfoV2格式
    
    Args:
        llm_result: 大模型返回的位置信息字典
        query_lat: 查询的纬度
        query_lon: 查询的经度
    
    Returns:
        CityInfoV2对象，失败返回None
    """
    try:
        city_lat = llm_result.get("city_latitude", query_lat)
        city_lon = llm_result.get("city_longitude", query_lon)
        
        # 计算距离
        distance_km = haversine_distance(query_lat, query_lon, city_lat, city_lon)
        
        admin1_zh = llm_result.get("admin1_name_zh")
        admin1_en = llm_result.get("admin1_name_en") or "unknown"
        admin2_zh = llm_result.get("admin2_name_zh")
        admin2_en = llm_result.get("admin2_name_en") or llm_result.get("city_name_en") or llm_result.get("country_name_en") or "unknown"

        city_info = CityInfoV2(
            id=0,  # 临时ID，保存到数据库后会更新
            name_en=llm_result.get("city_name_en") or llm_result.get("country_name_en") or "Unknown",
            name_zh=llm_result.get("city_name_zh") or llm_result.get("country_name_zh") or "未知位置",
            latitude=city_lat,
            longitude=city_lon,
            country_code=llm_result.get("country_code", "UN"),
            admin1_zh=admin1_zh,
            admin1_en=admin1_en,
            admin2_zh=admin2_zh,
            admin2_en=admin2_en,
            admin1_code=None,
            admin2_code=None,
            province=admin1_zh or admin1_en,
            city=llm_result.get("city_name_zh") or llm_result.get("city_name_en"),
            district=admin2_zh or admin2_en,
            data_source="llm",
            geoname_id=None,
            population=None,
            distance_km=distance_km,
            api_city_id=None,
            api_adcode=None
        )
        
        return city_info
    except Exception as e:
        logger.error(f"转换大模型结果为CityInfoV2失败: {e}", exc_info=True)
        return None


# ===== API接口 =====

@router.post("/nearest-cities", response_model=BatchNearestCityResponse, summary="批量查询最近的城市（v3版本）")
async def batch_get_nearest_cities_v3(
    request: BatchNearestCityRequestV3,
    request_obj: Request = None
) -> BatchNearestCityResponse:
    """
    批量查询多个坐标点的最近城市（v3版本 - 基于大模型）
    
    核心流程：
    1. 本地数据库查询（依次查询，命中则返回）
    2. DBSCAN聚类算法（eps=3km，min_samples=1）
    3. 计算聚类中心点（自适应方案）
    4. 大模型批量查询（分批查询圆心，30个/批次）
    5. 结果映射（圆心结果 → 原始坐标点）
    6. 保存到数据库（保存聚类内的所有坐标点）
    
    """
    start_time = time.time()
    request_id = IDGenerator.generate_request_id("nearest_cities_v3")
    user_id = request.user_id
    
    RequestLogger.log_request(
        request_id,
        "/api/v3/location/nearest-cities",
        user_id,
        {"coordinates_count": len(request.coordinates)}
    )
    
    try:
        # 步骤1：本地数据库查询（依次查询）
        logger.info(f"[{request_id}] 步骤1: 本地数据库查询，坐标数量={len(request.coordinates)}")
        mapped_coords = []  # 已命中的坐标
        unmapped_coords = []  # 未命中的坐标
        
        for coord in request.coordinates:
            row = await query_location_cache_v3(coord.latitude, coord.longitude, max_distance_km=3.0)
            if row:
                normalized_data = _cache_row_to_normalized_dict(row)
                mapped_coords.append((coord, normalized_data))
                continue

            unmapped_coords.append(coord)
        
        logger.info(f"[{request_id}] 步骤1完成: 命中={len(mapped_coords)}个, 未命中={len(unmapped_coords)}个")
        
        # 如果所有坐标都已命中，直接返回
        if len(unmapped_coords) == 0:
            results = []
            for coord, normalized_data in mapped_coords:
                distance_km = haversine_distance(
                    coord.latitude, coord.longitude,
                    normalized_data["latitude"], normalized_data["longitude"]
                )
                city_info = CityInfoV2(
                    id=normalized_data["id"],
                    name_en=normalized_data["name_en"],
                    name_zh=normalized_data.get("name_zh"),
                    latitude=normalized_data["latitude"],
                    longitude=normalized_data["longitude"],
                    country_code=normalized_data["country_code"],
                    admin1_zh=normalized_data.get("admin1_zh"),
                    admin1_en=normalized_data.get("admin1_en"),
                    admin2_zh=normalized_data.get("admin2_zh"),
                    admin2_en=normalized_data.get("admin2_en"),
                    admin1_code=normalized_data.get("admin1_code"),
                    admin2_code=normalized_data.get("admin2_code"),
                    province=normalized_data["province"],
                    city=normalized_data.get("city"),
                    district=normalized_data.get("district"),
                    data_source="local",
                    geoname_id=normalized_data.get("geoname_id"),
                    population=normalized_data.get("population"),
                    distance_km=distance_km,
                    api_city_id=normalized_data.get("api_city_id"),
                    api_adcode=normalized_data.get("api_adcode")
                )
                results.append(CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=city_info,
                    success=True,
                    error=None,
                    data_source="local",
                    query_time_ms=int((time.time() - start_time) * 1000)
                ))
            
            total_time_ms = int((time.time() - start_time) * 1000)
            RequestLogger.log_response(
                request_id=request_id,
                endpoint="/api/v3/location/nearest-cities",
                status_code=200,
                user_id=user_id,
                response_time_ms=total_time_ms,
                total_count=len(results),
                success_count=len(results)
            )
            
            return BatchNearestCityResponse(
                success=True,
                results=results,
                total_count=len(results),
                success_count=len(results),
                failed_count=0,
                total_time_ms=total_time_ms,
                request_id=request_id
            )
        
        # 步骤2：调用LLM服务进行批量逆地址编码（包含聚类、LLM查询等）
        logger.info(f"[{request_id}] 步骤2: 调用LLM服务进行批量逆地址编码，未命中坐标数量={len(unmapped_coords)}")
        llm_service_result = await llm_service.reverse_geocode_batch(
            coordinates=unmapped_coords,
            use_clustering=True,
            radius_km=3.0,
            min_samples=1
        )
        
        if not llm_service_result.get("success"):
            error_info = llm_service_result.get("error", {})
            raise Exception(f"LLM服务调用失败: {error_info.get('message', '未知错误')}")
        
        clusters = llm_service_result.get("clusters", [])
        llm_results = llm_service_result.get("results", [])
        logger.info(f"[{request_id}] 步骤2完成: 聚类数量={len(clusters)}, 结果数量={len(llm_results)}")
        
        # 步骤3：构建结果映射字典（用于数据库保存）
        logger.info(f"[{request_id}] 步骤3: 构建结果映射")
        llm_results_dict = {}
        for result_item in llm_results:
            coord = result_item.get("coordinate")
            location_info = result_item.get("location_info", {})
            if coord and location_info and "error" not in location_info:
                point_id = coord.id or f"{coord.latitude}_{coord.longitude}"
                llm_results_dict[point_id] = location_info
        
        # 步骤4：保存到数据库（保存聚类内的所有坐标点）
        logger.info(f"[{request_id}] 步骤4: 保存到数据库")
        await save_cluster_results_to_db(clusters, llm_results_dict)
        logger.info(f"[{request_id}] 步骤4完成: 数据库保存完成")
        
        # 步骤5：构建响应结果
        logger.info(f"[{request_id}] 步骤5: 构建响应结果")
        results = []
        
        # 处理已命中的坐标
        for coord, normalized_data in mapped_coords:
            distance_km = haversine_distance(
                coord.latitude, coord.longitude,
                normalized_data["latitude"], normalized_data["longitude"]
            )
            city_info = CityInfoV2(
                id=normalized_data["id"],
                name_en=normalized_data["name_en"],
                name_zh=normalized_data.get("name_zh"),
                latitude=normalized_data["latitude"],
                longitude=normalized_data["longitude"],
                country_code=normalized_data["country_code"],
                admin1_zh=normalized_data.get("admin1_zh"),
                admin1_en=normalized_data.get("admin1_en"),
                admin2_zh=normalized_data.get("admin2_zh"),
                admin2_en=normalized_data.get("admin2_en"),
                admin1_code=normalized_data.get("admin1_code"),
                admin2_code=normalized_data.get("admin2_code"),
                province=normalized_data["province"],
                city=normalized_data.get("city"),
                district=normalized_data.get("district"),
                data_source="local",
                geoname_id=normalized_data.get("geoname_id"),
                population=normalized_data.get("population"),
                distance_km=distance_km,
                api_city_id=normalized_data.get("api_city_id"),
                api_adcode=normalized_data.get("api_adcode")
            )
            results.append(CityQueryResult(
                location_id=coord.id,
                coordinate=coord,
                city=city_info,
                success=True,
                error=None,
                data_source="local",
                query_time_ms=int((time.time() - start_time) * 1000)
            ))
        
        # 处理未命中的坐标（使用LLM查询结果）
        for result_item in llm_results:
            coord = result_item.get("coordinate")
            location_info = result_item.get("location_info", {})
            
            if not coord:
                continue
            
            # 检查是否有错误
            if "error" in location_info:
                results.append(CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=None,
                    success=False,
                    error=location_info.get("error", "未知错误"),
                    data_source="llm",
                    query_time_ms=int((time.time() - start_time) * 1000)
                ))
                continue
            
            # 转换LLM结果为CityInfoV2
            city_info = convert_llm_result_to_city_info(
                location_info,
                coord.latitude,
                coord.longitude
            )
            
            if city_info:
                results.append(CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=city_info,
                    success=True,
                    error=None,
                    data_source="llm",
                    query_time_ms=int((time.time() - start_time) * 1000)
                ))
            else:
                # 转换失败，返回未知位置
                results.append(CityQueryResult(
                    location_id=coord.id,
                    coordinate=coord,
                    city=create_unknown_location(coord.latitude, coord.longitude),
                    success=True,
                    error=None,
                    data_source="unknown",
                    query_time_ms=int((time.time() - start_time) * 1000)
                ))
        
        # 确保结果顺序与输入顺序一致
        coord_id_to_result = {r.location_id or f"{r.coordinate.latitude}_{r.coordinate.longitude}": r for r in results}
        ordered_results = []
        for coord in request.coordinates:
            coord_id = coord.id or f"{coord.latitude}_{coord.longitude}"
            result = coord_id_to_result.get(coord_id)
            if result:
                ordered_results.append(result)
        
        total_time_ms = int((time.time() - start_time) * 1000)
        success_count = sum(1 for r in ordered_results if r.success and r.city and r.city.country_code != "UN")
        failed_count = len(ordered_results) - success_count
        
        RequestLogger.log_response(
            request_id=request_id,
            endpoint="/api/v3/location/nearest-cities",
            status_code=200,
            user_id=user_id,
            response_time_ms=total_time_ms,
            total_count=len(ordered_results),
            success_count=success_count,
            failed_count=failed_count
        )
        
        return BatchNearestCityResponse(
            success=True,
            results=ordered_results,
            total_count=len(ordered_results),
            success_count=success_count,
            failed_count=failed_count,
            total_time_ms=total_time_ms,
            request_id=request_id
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] 批量查询失败: {e}", exc_info=True)
        RequestLogger.log_error(
            request_id,
            e,
            "/api/v3/location/nearest-cities",
            user_id,
            "batch_query_failed"
        )
        raise HTTPException(status_code=500, detail=f"批量查询失败: {str(e)}")
