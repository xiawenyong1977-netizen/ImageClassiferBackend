"""
地理位置API v2版本测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from tests.conftest import get_test_token

client = TestClient(app)


class TestLocationV2Stats:
    """测试统计接口"""
    
    def test_stats_without_auth(self):
        """测试未认证访问统计接口（应该失败）"""
        response = client.get("/api/v2/location/stats")
        # 统计接口需要认证，应该返回401或403
        assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_stats_with_auth(self, async_client, auth_headers):
        """测试认证后访问统计接口（使用异步客户端）"""
        response = await async_client.get(
            "/api/v2/location/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_cities" in data
        assert "cities_with_chinese" in data
        assert "mapping_table_size" in data
        assert "api_calls_today" in data
        assert "api_calls_all" in data
        assert "data_source_distribution" in data
        # 验证数据类型
        assert isinstance(data["total_cities"], int)
        assert isinstance(data["api_calls_today"], dict)
        assert isinstance(data["data_source_distribution"], dict)


class TestLocationV2BatchQuery:
    """测试批量查询接口"""
    
    def test_batch_query_empty_coordinates(self):
        """测试空坐标列表"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={"coordinates": []}
        )
        assert response.status_code == 422  # 验证错误
    
    def test_batch_query_invalid_coordinate(self):
        """测试无效坐标"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {"latitude": 100, "longitude": 200}  # 超出范围
                ]
            }
        )
        assert response.status_code == 422  # 验证错误
    
    def test_batch_query_single_coordinate(self):
        """测试单个坐标查询"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {
                        "id": "test_001",
                        "latitude": 39.9042,
                        "longitude": 116.4074
                    }
                ]
            }
        )
        # 即使查询失败，接口也应该返回200（因为部分失败不影响整体）
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "results" in data
        assert "total_count" in data
        assert "success_count" in data
        assert "failed_count" in data
        assert "request_id" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["location_id"] == "test_001"
    
    def test_batch_query_multiple_coordinates(self):
        """测试多个坐标查询"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {
                        "id": "test_001",
                        "latitude": 39.9042,
                        "longitude": 116.4074
                    },
                    {
                        "id": "test_002",
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert data["total_count"] == 2
        # 验证每个结果都有location_id
        assert data["results"][0]["location_id"] == "test_001"
        assert data["results"][1]["location_id"] == "test_002"
    
    def test_batch_query_without_location_id(self):
        """测试不带location_id的坐标查询"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {
                        "latitude": 39.9042,
                        "longitude": 116.4074
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        # location_id应该为None
        assert data["results"][0]["location_id"] is None
    
    def test_batch_query_max_coordinates(self):
        """测试最大坐标数量（500个）"""
        coordinates = [
            {
                "id": f"test_{i:03d}",
                "latitude": 39.9042 + (i * 0.01),
                "longitude": 116.4074 + (i * 0.01)
            }
            for i in range(500)
        ]
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={"coordinates": coordinates}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 500
        assert len(data["results"]) == 500
    
    def test_batch_query_exceed_max_coordinates(self):
        """测试超过最大坐标数量（应该失败）"""
        coordinates = [
            {
                "id": f"test_{i:03d}",
                "latitude": 39.9042,
                "longitude": 116.4074
            }
            for i in range(501)  # 超过500个
        ]
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={"coordinates": coordinates}
        )
        assert response.status_code == 422  # 验证错误
    
    def test_batch_query_response_structure(self):
        """测试响应结构完整性"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {
                        "id": "test_001",
                        "latitude": 39.9042,
                        "longitude": 116.4074
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # 验证顶层字段
        assert "success" in data
        assert "results" in data
        assert "total_count" in data
        assert "success_count" in data
        assert "failed_count" in data
        assert "total_time_ms" in data
        assert "request_id" in data
        
        # 验证结果项结构
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "location_id" in result
            assert "coordinate" in result
            assert "success" in result
            assert "data_source" in result
            assert "query_time_ms" in result
            
            # 验证坐标结构
            coord = result["coordinate"]
            assert "latitude" in coord
            assert "longitude" in coord
            if result["success"]:
                assert "city" in result
                city = result["city"]
                assert "id" in city
                assert "name_en" in city
                assert "latitude" in city
                assert "longitude" in city
                assert "country_code" in city
                assert "data_source" in city
                assert "distance_km" in city
            else:
                assert "error" in result


class TestLocationV2EdgeCases:
    """测试边界情况"""
    
    def test_batch_query_invalid_latitude(self):
        """测试无效纬度"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {"latitude": -100, "longitude": 116.4074}  # 纬度超出范围
                ]
            }
        )
        assert response.status_code == 422
    
    def test_batch_query_invalid_longitude(self):
        """测试无效经度"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {"latitude": 39.9042, "longitude": 200}  # 经度超出范围
                ]
            }
        )
        assert response.status_code == 422
    
    def test_batch_query_missing_coordinates(self):
        """测试缺少coordinates字段"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={}
        )
        assert response.status_code == 422
    
    def test_batch_query_missing_latitude(self):
        """测试缺少纬度"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {"longitude": 116.4074}
                ]
            }
        )
        assert response.status_code == 422
    
    def test_batch_query_missing_longitude(self):
        """测试缺少经度"""
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {"latitude": 39.9042}
                ]
            }
        )
        assert response.status_code == 422


class TestLocationV2ExternalAPI:
    """测试外部API调用（高德和Nominatim）"""
    
    def test_query_china_location_with_gaode_api(self):
        """测试中国坐标调用高德API"""
        # Mock本地数据库查询返回None（未命中）
        # Mock高德API返回成功结果
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode') as mock_gaode, \
             patch('app.api.location_v2.save_city_to_db') as mock_save:
            
            # 本地数据库未命中
            mock_local_db.return_value = None
            
            # 高德API返回成功
            mock_gaode.return_value = {
                "name_zh": "北京市",
                "name_en": "Beijing",
                "latitude": 39.9042,
                "longitude": 116.4074,
                "country_code": "CN",
                "province": "北京市",
                "city": "北京市",
                "district": "东城区",
                "api_adcode": "110101",
                "api_city_code": "010",
                "api_city_id": "110101",
                "data_source": "gaode"
            }
            
            # Mock保存成功
            mock_save.return_value = 12345
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "china_test",
                            "latitude": 39.9042,
                            "longitude": 116.4074
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            result = data["results"][0]
            
            # 验证调用了高德API
            mock_gaode.assert_called_once_with(39.9042, 116.4074)
            
            # 验证结果
            assert result["success"] is True
            assert result["data_source"] == "gaode"
            assert result["city"] is not None
            assert result["city"]["name_zh"] == "北京市"
            assert result["city"]["country_code"] == "CN"
            assert result["city"]["data_source"] == "gaode"
    
    def test_query_overseas_location_with_nominatim_api(self):
        """测试国外坐标调用Nominatim API"""
        # Mock本地数据库查询返回None（未命中）
        # Mock Nominatim API返回成功结果
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_nominatim') as mock_nominatim, \
             patch('app.api.location_v2.save_city_to_db') as mock_save:
            
            # 本地数据库未命中
            mock_local_db.return_value = None
            
            # Nominatim API返回成功
            mock_nominatim.return_value = {
                "name_en": "New York",
                "name_zh": None,  # Nominatim可能没有中文名
                "latitude": 40.7128,
                "longitude": -74.0060,
                "country_code": "US",
                "province": "New York",
                "city": "New York",
                "district": "Manhattan",
                "api_city_id": "123456789",
                "api_adcode": None,
                "api_city_code": None,
                "data_source": "nominatim"
            }
            
            # Mock保存成功
            mock_save.return_value = 67890
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "overseas_test",
                            "latitude": 40.7128,
                            "longitude": -74.0060
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            result = data["results"][0]
            
            # 验证调用了Nominatim API
            mock_nominatim.assert_called_once_with(40.7128, -74.0060)
            
            # 验证结果
            assert result["success"] is True
            assert result["data_source"] == "nominatim"
            assert result["city"] is not None
            assert result["city"]["name_en"] == "New York"
            assert result["city"]["country_code"] == "US"
            assert result["city"]["data_source"] == "nominatim"
    
    def test_query_china_location_gaode_api_failed(self):
        """测试中国坐标高德API失败后降级到v1逻辑"""
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode') as mock_gaode, \
             patch('app.api.location_v2.query_fallback_v1') as mock_fallback:
            
            # 本地数据库未命中
            mock_local_db.return_value = None
            
            # 高德API失败
            mock_gaode.return_value = None
            
            # v1降级逻辑返回成功
            mock_fallback.return_value = {
                "id": 99999,
                "name_en": "Beijing",
                "name_zh": "北京",
                "latitude": 39.9042,
                "longitude": 116.4074,
                "country_code": "CN",
                "geoname_id": 1816670,
                "population": 21540000,
                "distance_km": 5.0,
                "data_source": "fallback"
            }
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "gaode_failed_test",
                            "latitude": 39.9042,
                            "longitude": 116.4074
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            result = data["results"][0]
            
            # 验证调用了高德API
            mock_gaode.assert_called_once()
            
            # 验证降级到v1逻辑
            mock_fallback.assert_called_once()
            
            # 验证结果
            assert result["success"] is True
            assert result["data_source"] == "fallback"
            assert result["city"] is not None
    
    def test_query_overseas_location_nominatim_api_failed(self):
        """测试国外坐标Nominatim API失败后降级到v1逻辑"""
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_nominatim') as mock_nominatim, \
             patch('app.api.location_v2.query_fallback_v1') as mock_fallback:
            
            # 本地数据库未命中
            mock_local_db.return_value = None
            
            # Nominatim API失败
            mock_nominatim.return_value = None
            
            # v1降级逻辑返回成功
            mock_fallback.return_value = {
                "id": 88888,
                "name_en": "New York",
                "name_zh": "纽约",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "country_code": "US",
                "geoname_id": 5128581,
                "population": 8175133,
                "distance_km": 10.0,
                "data_source": "fallback"
            }
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "nominatim_failed_test",
                            "latitude": 40.7128,
                            "longitude": -74.0060
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            result = data["results"][0]
            
            # 验证调用了Nominatim API
            mock_nominatim.assert_called_once()
            
            # 验证降级到v1逻辑
            mock_fallback.assert_called_once()
            
            # 验证结果
            assert result["success"] is True
            assert result["data_source"] == "fallback"
            assert result["city"] is not None
    
    def test_query_mixed_china_and_overseas(self):
        """测试混合查询：中国和国外坐标"""
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode') as mock_gaode, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_nominatim') as mock_nominatim, \
             patch('app.api.location_v2.save_city_to_db') as mock_save:
            
            # 本地数据库都未命中
            mock_local_db.return_value = None
            
            # 高德API返回成功（中国坐标）
            mock_gaode.return_value = {
                "name_zh": "北京市",
                "name_en": "Beijing",
                "latitude": 39.9042,
                "longitude": 116.4074,
                "country_code": "CN",
                "api_adcode": "110101",
                "data_source": "gaode"
            }
            
            # Nominatim API返回成功（国外坐标）
            mock_nominatim.return_value = {
                "name_en": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "country_code": "US",
                "api_city_id": "123456789",
                "data_source": "nominatim"
            }
            
            # Mock保存成功
            mock_save.return_value = 11111
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "china_coord",
                            "latitude": 39.9042,
                            "longitude": 116.4074
                        },
                        {
                            "id": "overseas_coord",
                            "latitude": 40.7128,
                            "longitude": -74.0060
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2
            
            # 验证中国坐标调用了高德API
            mock_gaode.assert_called_once_with(39.9042, 116.4074)
            
            # 验证国外坐标调用了Nominatim API
            mock_nominatim.assert_called_once_with(40.7128, -74.0060)
            
            # 验证结果
            china_result = data["results"][0]
            overseas_result = data["results"][1]
            
            assert china_result["data_source"] == "gaode"
            assert overseas_result["data_source"] == "nominatim"
    
    def test_query_all_apis_failed(self):
        """测试所有API都失败的情况"""
        with patch('app.api.location_v2.query_local_db') as mock_local_db, \
             patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode') as mock_gaode, \
             patch('app.api.location_v2.query_fallback_v1') as mock_fallback:
            
            # 本地数据库未命中
            mock_local_db.return_value = None
            
            # 高德API失败
            mock_gaode.return_value = None
            
            # v1降级逻辑也失败
            mock_fallback.return_value = None
            
            response = client.post(
                "/api/v2/location/nearest-cities",
                json={
                    "coordinates": [
                        {
                            "id": "all_failed_test",
                            "latitude": 39.9042,
                            "longitude": 116.4074
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            result = data["results"][0]
            
            # 验证查询失败
            assert result["success"] is False
            assert result["city"] is None
            assert result["error"] is not None


class TestLocationV2Integration:
    """集成测试（需要数据库连接）"""
    
    @pytest.mark.skip(reason="需要数据库连接，在CI/CD中可能需要mock")
    def test_query_with_local_db_hit(self):
        """测试本地数据库命中场景"""
        # 这个测试需要数据库中有数据
        # 可以使用已知的坐标点（如北京天安门）
        response = client.post(
            "/api/v2/location/nearest-cities",
            json={
                "coordinates": [
                    {
                        "id": "beijing_test",
                        "latitude": 39.9042,
                        "longitude": 116.4074
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        # 如果数据库中有数据，应该能查询到
        # 这里只验证结构，不验证具体数据
        assert len(data["results"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

