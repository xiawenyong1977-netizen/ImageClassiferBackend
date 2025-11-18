#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理位置相关API路由
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import math
import time

from app.database import db
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/location", tags=["location"])


class LocationStats(BaseModel):
    """位置数据库统计信息"""
    total_cities: int = Field(description="总城市数")
    cities_with_chinese: int = Field(description="有中文名称的城市数")
    cities_above_100k: int = Field(description="人口≥10万的城市数")
    cities_queryable: int = Field(description="可查询的城市数（人口≥10万且有中文）")
    chinese_coverage_percent: float = Field(description="中文覆盖率")
    queryable_coverage_percent: float = Field(description="可查询城市覆盖率")
    
    # 调用统计
    total_queries_today: int = Field(0, description="今日查询总数")
    nearest_queries_today: int = Field(0, description="今日最近城市查询数")
    nearby_queries_today: int = Field(0, description="今日附近城市查询数")
    total_queries_all: int = Field(0, description="累计查询总数")


class CityInfo(BaseModel):
    """城市信息"""
    id: int
    geoname_id: int
    name: str
    name_zh: Optional[str] = Field(None, description="中文名称")
    ascii_name: Optional[str]
    latitude: float
    longitude: float
    country_code: str
    population: int
    distance_km: float = Field(description="距离查询点的距离(公里)")


@router.get("/stats", response_model=LocationStats, summary="获取位置数据库统计信息")
async def get_location_stats(current_user: str = Depends(get_current_user)):
    """
    获取位置数据库的统计信息（需要认证）
    
    **返回:** 位置数据库统计数据
    
    **示例:**
    ```
    GET /api/v1/location/stats
    ```
    """
    try:
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN name_zh IS NOT NULL THEN 1 ELSE 0 END) as has_chinese,
                SUM(CASE WHEN population >= 100000 THEN 1 ELSE 0 END) as above_100k,
                SUM(CASE WHEN population >= 100000 AND name_zh IS NOT NULL THEN 1 ELSE 0 END) as queryable
            FROM global_cities 
            WHERE country_code = 'CN'
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query)
            row = await cursor.fetchone()
        
        # 处理可能的None值
        total = row['total'] or 0
        has_chinese = row['has_chinese'] or 0
        above_100k = row['above_100k'] or 0
        queryable = row['queryable'] or 0
        
        chinese_coverage = (has_chinese / total * 100) if total > 0 else 0
        queryable_coverage = (queryable / total * 100) if total > 0 else 0
        
        # 查询调用统计
        stats_query = """
            SELECT 
                COUNT(*) as total_all,
                SUM(CASE WHEN DATE(created_at) = CURDATE() THEN 1 ELSE 0 END) as total_today,
                SUM(CASE WHEN DATE(created_at) = CURDATE() AND query_type = 'nearest' THEN 1 ELSE 0 END) as nearest_today,
                SUM(CASE WHEN DATE(created_at) = CURDATE() AND query_type = 'nearby' THEN 1 ELSE 0 END) as nearby_today
            FROM location_query_log
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(stats_query)
            stats_row = await cursor.fetchone()
        
        # 处理可能的None值
        total_queries_today = stats_row['total_today'] or 0 if stats_row else 0
        nearest_queries_today = stats_row['nearest_today'] or 0 if stats_row else 0
        nearby_queries_today = stats_row['nearby_today'] or 0 if stats_row else 0
        total_queries_all = stats_row['total_all'] or 0 if stats_row else 0
        
        return LocationStats(
            total_cities=total,
            cities_with_chinese=has_chinese,
            cities_above_100k=above_100k,
            cities_queryable=queryable,
            chinese_coverage_percent=round(chinese_coverage, 2),
            queryable_coverage_percent=round(queryable_coverage, 2),
            total_queries_today=total_queries_today,
            nearest_queries_today=nearest_queries_today,
            nearby_queries_today=nearby_queries_today,
            total_queries_all=total_queries_all
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两个经纬度点之间的距离（公里）
    使用Haversine公式
    """
    # 地球半径（公里）
    R = 6371.0
    
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 计算差值
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine公式
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


@router.get("/nearest-city", response_model=CityInfo, summary="查询最近的城市")
async def get_nearest_city(
    latitude: float = Query(..., ge=-90, le=90, description="纬度"),
    longitude: float = Query(..., ge=-180, le=180, description="经度"),
    user_id: Optional[str] = Query(None, description="用户ID（可选）"),
    request: Request = None
):
    """
    根据给定的经纬度查询最近的城市
    
    **参数:**
    - **latitude**: 纬度，范围 -90 到 90
    - **longitude**: 经度，范围 -180 到 180
    - **user_id**: 用户ID（可选）
    
    **返回:** 最近的城市信息，包括距离
    
    **示例:**
    ```
    GET /api/v1/location/nearest-city?latitude=39.9042&longitude=116.4074
    ```
    """
    start_time = time.time()
    ip_address = request.client.host if request else None
    
    try:
        # 使用MySQL的球面距离计算公式
        # ST_Distance_Sphere 计算两点之间的球面距离（米）
        query = """
            SELECT 
                id,
                geoname_id,
                name,
                name_zh,
                ascii_name,
                latitude,
                longitude,
                country_code,
                population,
                ST_Distance_Sphere(
                    POINT(longitude, latitude),
                    POINT(%s, %s)
                ) / 1000 AS distance_km
            FROM global_cities
            WHERE population >= 100000 AND name_zh IS NOT NULL
            ORDER BY distance_km
            LIMIT 1
        """
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query, (longitude, latitude))
            row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="未找到任何城市数据")
        
        city_info = CityInfo(
            id=row['id'],
            geoname_id=row['geoname_id'],
            name=row['name'],
            name_zh=row['name_zh'],
            ascii_name=row['ascii_name'],
            latitude=float(row['latitude']),
            longitude=float(row['longitude']),
            country_code=row['country_code'],
            population=row['population'],
            distance_km=float(row['distance_km'])
        )
        
        # 记录查询日志
        processing_time = int((time.time() - start_time) * 1000)
        log_query = """
            INSERT INTO location_query_log 
            (query_type, latitude, longitude, result_city_id, result_city_name, 
             result_city_name_zh, distance_km, user_id, ip_address, processing_time_ms, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        async with db.get_cursor() as cursor:
            await cursor.execute(log_query, (
                'nearest', latitude, longitude, city_info.id, city_info.name,
                city_info.name_zh, city_info.distance_km, user_id, ip_address, processing_time, datetime.now()
            ))
        
        return city_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/nearby-cities", response_model=List[CityInfo], summary="查询附近的城市列表")
async def get_nearby_cities(
    latitude: float = Query(..., ge=-90, le=90, description="纬度"),
    longitude: float = Query(..., ge=-180, le=180, description="经度"),
    limit: int = Query(10, ge=1, le=100, description="返回结果数量"),
    max_distance_km: Optional[float] = Query(None, ge=0, description="最大距离（公里），不填则不限制"),
    user_id: Optional[str] = Query(None, description="用户ID（可选）"),
    request: Request = None
):
    """
    根据给定的经纬度查询附近的城市列表
    
    **参数:**
    - **latitude**: 纬度，范围 -90 到 90
    - **longitude**: 经度，范围 -180 到 180
    - **limit**: 返回结果数量，默认10，最多100
    - **max_distance_km**: 最大距离（公里），可选
    - **user_id**: 用户ID（可选）
    
    **返回:** 附近城市列表，按距离排序
    
    **示例:**
    ```
    GET /api/v1/location/nearby-cities?latitude=39.9042&longitude=116.4074&limit=5
    GET /api/v1/location/nearby-cities?latitude=39.9042&longitude=116.4074&limit=5&max_distance_km=50
    ```
    """
    start_time = time.time()
    ip_address = request.client.host if request else None
    
    try:
        # 构建查询
        if max_distance_km:
            query = """
                SELECT 
                    id,
                    geoname_id,
                    name,
                    name_zh,
                    ascii_name,
                    latitude,
                    longitude,
                    country_code,
                    population,
                    ST_Distance_Sphere(
                        POINT(longitude, latitude),
                        POINT(%s, %s)
                    ) / 1000 AS distance_km
                FROM global_cities
                WHERE population >= 100000 AND name_zh IS NOT NULL
                HAVING distance_km <= %s
                ORDER BY distance_km
                LIMIT %s
            """
            params = (longitude, latitude, max_distance_km, limit)
        else:
            query = """
                SELECT 
                    id,
                    geoname_id,
                    name,
                    name_zh,
                    ascii_name,
                    latitude,
                    longitude,
                    country_code,
                    population,
                    ST_Distance_Sphere(
                        POINT(longitude, latitude),
                        POINT(%s, %s)
                    ) / 1000 AS distance_km
                FROM global_cities
                WHERE population >= 100000 AND name_zh IS NOT NULL
                ORDER BY distance_km
                LIMIT %s
            """
            params = (longitude, latitude, limit)
        
        async with db.get_cursor() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
        
        if not rows:
            return []
        
        cities = []
        for row in rows:
            cities.append(CityInfo(
                id=row['id'],
                geoname_id=row['geoname_id'],
                name=row['name'],
                name_zh=row['name_zh'],
                ascii_name=row['ascii_name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                country_code=row['country_code'],
                population=row['population'],
                distance_km=float(row['distance_km'])
            ))
        
        # 记录查询日志
        if cities:
            processing_time = int((time.time() - start_time) * 1000)
            first_city = cities[0]
            log_query = """
                INSERT INTO location_query_log 
                (query_type, latitude, longitude, result_city_id, result_city_name, 
                 result_city_name_zh, result_count, distance_km, user_id, ip_address, processing_time_ms, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            async with db.get_cursor() as cursor:
                await cursor.execute(log_query, (
                    'nearby', latitude, longitude, first_city.id, first_city.name,
                    first_city.name_zh, len(cities), first_city.distance_km, user_id, ip_address, processing_time, datetime.now()
                ))
        
        return cities
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

