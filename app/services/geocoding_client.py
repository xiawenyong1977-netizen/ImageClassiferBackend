"""
地理编码客户端
支持高德地图和Nominatim API
"""

import httpx
import asyncio
import time
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
                    
                    # 记录高德API完整原始返回数据（用于调试）
                    logger.info(f"高德API完整原始返回数据: {data}")
                    logger.info(f"高德API原始返回摘要: status={data.get('status')}, info={data.get('info')}, has_regeocode={bool(data.get('regeocode'))}")
                    
                    if data.get("status") == "1" and data.get("regeocode"):
                        regeocode = data["regeocode"]
                        address_component = regeocode.get("addressComponent", {})
                        
                        # 记录regeocode和address_component的完整数据（用于调试）
                        logger.info(f"高德API regeocode完整数据: {regeocode}")
                        logger.info(f"高德API addressComponent完整数据: {address_component}")
                        logger.info(f"高德API formatted_address: {regeocode.get('formatted_address')}")
                        
                        # 提取城市信息（确保city和district是字符串，不是列表）
                        def ensure_string(value):
                            """确保值是字符串，如果是列表则取第一个元素，空列表返回None"""
                            if value is None:
                                return None
                            if isinstance(value, list):
                                # 空列表返回None，非空列表取第一个元素
                                return value[0] if value else None
                            # 空字符串也返回None
                            if isinstance(value, str) and not value.strip():
                                return None
                            return str(value) if value else None
                        
                        city_val = ensure_string(address_component.get("city"))
                        district_val = ensure_string(address_component.get("district"))
                        province_val = ensure_string(address_component.get("province"))
                        
                        logger.debug(f"提取后的值: city={city_val}, district={district_val}, province={province_val}")
                        
                        # 确保 adcode 是字符串或 None，不能是列表
                        adcode_val = address_component.get("adcode")
                        if isinstance(adcode_val, list):
                            adcode_val = adcode_val[0] if adcode_val else None
                        if adcode_val:
                            adcode_val = str(adcode_val)
                        
                        # 确保 citycode 是字符串或 None
                        citycode_val = address_component.get("citycode")
                        if isinstance(citycode_val, list):
                            citycode_val = citycode_val[0] if citycode_val else None
                        if citycode_val:
                            citycode_val = str(citycode_val)
                        
                        # 城市名称：优先使用 city，其次 district，最后使用 formatted_address
                        name_zh = city_val or district_val
                        formatted_address = regeocode.get("formatted_address", "")
                        
                        # 确保 formatted_address 是字符串，不是列表
                        if isinstance(formatted_address, list):
                            formatted_address = formatted_address[0] if formatted_address else ""
                        if not isinstance(formatted_address, str):
                            formatted_address = str(formatted_address) if formatted_address else ""
                        
                        if not name_zh:
                            # 如果都没有，尝试从 formatted_address 提取
                            if formatted_address and formatted_address.strip():
                                # 提取地址中的城市名（通常是第一个逗号前的部分）
                                name_zh = formatted_address.split(",")[0].strip()
                        
                        # 如果仍然没有名称，检查是否是海外坐标（高德API对海外坐标支持有限）
                        if not name_zh:
                            logger.warning(f"高德API返回数据但无城市名称（可能是海外坐标）: ({latitude}, {longitude})")
                            logger.debug(f"addressComponent详情: city={address_component.get('city')}, district={address_component.get('district')}, formatted_address={formatted_address}")
                            # 高德API对海外坐标可能返回空数据，视为失败
                            return None
                        
                        # name_en 使用 name_zh（高德API主要返回中文）
                        name_en = name_zh
                        
                        result = {
                            "name_zh": name_zh,
                            "name_en": name_en,  # 高德API主要返回中文，name_en 使用 name_zh
                            "province": province_val,
                            "city": city_val,
                            "district": district_val,
                            "country_code": "CN",  # 高德主要用于中国
                            "api_city_id": adcode_val,
                            "api_adcode": adcode_val,
                            "api_city_code": citycode_val,
                            "latitude": latitude,
                            "longitude": longitude,
                            "data_source": "gaode"
                        }
                        
                        logger.info(f"高德API查询成功: name_zh={name_zh}, name_en={name_en}, adcode={adcode_val}")
                        return result
                    else:
                        # 记录详细的错误信息
                        status = data.get("status")
                        info = data.get("info", "未知错误")
                        logger.warning(f"高德API返回错误: status={status}, info={info}, 坐标=({latitude}, {longitude})")
                        
                        # 如果是海外坐标，这是正常的（高德API主要支持中国境内）
                        if status == "0":
                            logger.debug(f"高德API不支持该坐标（可能是海外坐标）: ({latitude}, {longitude})")
                        
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
        request_start_time = time.time()
        
        try:
            # 检查API URL配置
            if not self.nominatim_api_url:
                logger.error(f"Nominatim API URL未配置")
                return None
            
            logger.info(f"Nominatim API准备调用: URL={self.nominatim_api_url}, 坐标=({latitude}, {longitude})")
            
            # 等待频率限制
            await self._wait_for_nominatim_rate_limit()
            
            # 超时时间设置为10秒（Cloudflare Worker免费版限制是10秒）
            # 如果使用付费版Worker，可以增加到30秒
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
                
                logger.info(f"Nominatim API请求开始: ({latitude}, {longitude}), URL: {self.nominatim_api_url}, 超时=10秒")
                logger.debug(f"Nominatim API请求参数: {params}")
                
                # 发起请求并处理响应
                response = await client.get(self.nominatim_api_url, params=params, headers=headers)
                request_duration = time.time() - request_start_time
                
                logger.info(f"Nominatim API响应收到: 状态码={response.status_code}, 耗时={request_duration:.2f}秒")
                logger.debug(f"Nominatim API响应头: {dict(response.headers)}")
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Nominatim API完整原始返回数据: {data}")
                
                # 检查返回数据
                if not data:
                    logger.warning(f"Nominatim API返回空数据: ({latitude}, {longitude})")
                    return None
                
                if isinstance(data, dict):
                    address = data.get("address", {})
                    
                    # 提取城市信息
                    city = (
                        address.get("city") or
                        address.get("town") or
                        address.get("village") or
                        address.get("municipality")
                    )
                    
                    # 如果没有提取到城市信息，记录详细信息
                    if not city:
                        logger.warning(f"Nominatim API未找到城市信息: ({latitude}, {longitude}), address={address}, name={data.get('name')}")
                    
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
                    
                    if result.get("name_en"):
                        logger.info(f"Nominatim API查询成功: {result.get('name_en')}, 耗时={request_duration:.2f}秒")
                    else:
                        logger.warning(f"Nominatim API返回结果但无城市名: ({latitude}, {longitude}), result={result}")
                    
                    return result
                else:
                    logger.warning(f"Nominatim API返回格式错误: 期望dict，实际={type(data)}, data={data}")
                    return None
                    
        except httpx.TimeoutException as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Nominatim API请求超时: ({latitude}, {longitude}), 耗时={request_duration:.2f}秒, 超时限制=10.0秒")
            logger.error(f"超时原因分析: 1) Cloudflare Worker超时（免费版限制10秒） 2) 网络连接慢 3) Nominatim服务器响应慢")
            logger.error(f"请检查: URL={self.nominatim_api_url}, 如果使用免费版Worker，考虑升级到付费版（30秒超时）")
            return None
        except httpx.ConnectError as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Nominatim API连接失败（无法连接到服务器）: ({latitude}, {longitude}), 耗时={request_duration:.2f}秒")
            logger.error(f"连接失败原因: 1) 服务器无法访问外网 2) DNS解析失败 3) 防火墙阻止连接 4) URL配置错误")
            logger.error(f"请检查: URL={self.nominatim_api_url}, 服务器网络连接, 防火墙设置")
            return None
        except httpx.NetworkError as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Nominatim API网络错误: ({latitude}, {longitude}), 耗时={request_duration:.2f}秒, 错误={e}")
            return None
        except httpx.HTTPStatusError as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Nominatim API HTTP错误: ({latitude}, {longitude}), 状态码={e.response.status_code}, 耗时={request_duration:.2f}秒")
            logger.error(f"HTTP错误响应: {e.response.text[:500]}")
            return None
        except Exception as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Nominatim API调用失败: ({latitude}, {longitude}), 耗时={request_duration:.2f}秒, 错误类型={type(e).__name__}, 错误={e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
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

