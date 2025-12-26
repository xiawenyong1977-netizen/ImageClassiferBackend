"""
地理编码客户端
支持高德地图和Nominatim API
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from app.config import settings
from loguru import logger


class GeocodingClient:
    """地理编码客户端类"""
    
    def __init__(self):
        self.gaode_api_key = settings.GAODE_API_KEY
        self.gaode_api_url = settings.GAODE_API_URL
        self.nominatim_api_url = settings.NOMINATIM_API_URL
        self.nominatim_rate_limit = settings.NOMINATIM_RATE_LIMIT
        self._last_nominatim_call = 0.0
        self._nominatim_lock = asyncio.Lock()
        # 高德API并发限制：30/s，我们设置为25/s以留出安全余量
        # 使用Semaphore限制同时进行的请求数
        self._gaode_semaphore = asyncio.Semaphore(25)
    
    async def _wait_for_nominatim_rate_limit(self):
        """等待Nominatim API频率限制"""
        async with self._nominatim_lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_call = current_time - self._last_nominatim_call
            if time_since_last_call < self.nominatim_rate_limit:
                wait_time = self.nominatim_rate_limit - time_since_last_call
                await asyncio.sleep(wait_time)
            self._last_nominatim_call = asyncio.get_event_loop().time()
    
    async def reverse_geocode_gaode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        使用高德地图API进行逆地理编码
        
        注意：高德API频率限制为30/s，通过Semaphore限制并发为25，确保不超过限制
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            城市信息字典，失败返回None
        """
        if not self.gaode_api_key:
            logger.warning("高德地图API密钥未配置")
            return None
        
        # 使用Semaphore限制并发，确保不超过25个并发请求（高德限制30/s）
        async with self._gaode_semaphore:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    params = {
                        "key": self.gaode_api_key,
                        "location": f"{longitude},{latitude}",
                        "output": "json",
                        "radius": 1000,
                        "extensions": "all"
                    }
                    response = await client.get(self.gaode_api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("status") == "1" and data.get("regeocode"):
                        regeocode = data["regeocode"]
                        address_component = regeocode.get("addressComponent", {})
                        
                        # 提取城市信息（确保city和district是字符串，不是列表）
                        def ensure_string(value):
                            """确保值是字符串，如果是列表则取第一个元素"""
                            if value is None:
                                return None
                            if isinstance(value, list):
                                return value[0] if value else None
                            return str(value) if value else None
                        
                        city_val = ensure_string(address_component.get("city"))
                        district_val = ensure_string(address_component.get("district"))
                        province_val = ensure_string(address_component.get("province"))
                        
                        result = {
                            "name_zh": city_val or district_val,
                            "province": province_val,
                            "city": city_val,
                            "district": district_val,
                            "country_code": "CN",  # 高德主要用于中国
                            "api_city_id": address_component.get("adcode"),
                            "api_adcode": address_component.get("adcode"),
                            "api_city_code": address_component.get("citycode"),
                            "latitude": latitude,
                            "longitude": longitude,
                            "data_source": "gaode"
                        }
                        
                        logger.info(f"高德API查询成功: {result.get('name_zh')}")
                        return result
                    else:
                        logger.warning(f"高德API返回错误: {data.get('info', '未知错误')}")
                        return None
                            
            except httpx.TimeoutException:
                logger.error("高德API请求超时")
                return None
            except httpx.HTTPStatusError as e:
                logger.error(f"高德API HTTP错误: {e.response.status_code}")
                return None
            except Exception as e:
                logger.error(f"高德API调用失败: {e}")
                return None
    
    async def reverse_geocode_nominatim(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        使用Nominatim API进行逆地理编码
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            城市信息字典，失败返回None
        """
        try:
            # 等待频率限制
            await self._wait_for_nominatim_rate_limit()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {
                    "lat": str(latitude),
                    "lon": str(longitude),
                    "format": "json",
                    "addressdetails": 1,
                    "accept-language": "zh-CN,en"
                }
                headers = {
                    "User-Agent": "ImageClassifierBackend/1.0"  # Nominatim要求提供User-Agent
                }
                response = await client.get(self.nominatim_api_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data and isinstance(data, dict):
                    address = data.get("address", {})
                    
                    # 提取城市信息
                    city = (
                        address.get("city") or
                        address.get("town") or
                        address.get("village") or
                        address.get("municipality")
                    )
                    
                    country_code = address.get("country_code", "").upper()
                    if len(country_code) == 2:
                        country_code = country_code
                    else:
                        country_code = None
                    
                    result = {
                        "name_en": city or data.get("name", ""),
                        "name_zh": None,  # Nominatim可能没有中文名，需要通过映射表获取
                        "province": address.get("state") or address.get("region"),
                        "city": city,
                        "district": address.get("suburb") or address.get("neighbourhood"),
                        "country_code": country_code or "UN",
                        "api_city_id": str(data.get("place_id", "")),
                        "api_adcode": None,
                        "api_city_code": None,
                        "latitude": float(data.get("lat", latitude)),
                        "longitude": float(data.get("lon", longitude)),
                        "data_source": "nominatim"
                    }
                    
                    logger.info(f"Nominatim API查询成功: {result.get('name_en')}")
                    return result
                else:
                    logger.warning("Nominatim API返回格式错误")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Nominatim API请求超时")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Nominatim API HTTP错误: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Nominatim API调用失败: {e}")
            return None
    
    def is_china_location(self, latitude: float, longitude: float) -> bool:
        """
        判断坐标是否在中国境内（粗略判断）
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            是否在中国境内
        """
        # 中国大致范围：纬度 18°-54°，经度 73°-135°
        return 18.0 <= latitude <= 54.0 and 73.0 <= longitude <= 135.0


# 全局地理编码客户端实例
geocoding_client = GeocodingClient()

