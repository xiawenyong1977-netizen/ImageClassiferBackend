# 测试说明

## 测试文件结构

- `test_health.py` - 健康检查接口测试
- `test_location_v2.py` - 地理位置API v2版本测试
- `conftest.py` - pytest配置和测试工具

## 运行测试

### 安装依赖

```bash
pip install pytest pytest-asyncio
```

### 运行所有测试

```bash
pytest tests/
```

### 运行特定测试文件

```bash
pytest tests/test_location_v2.py
```

### 运行特定测试类

```bash
pytest tests/test_location_v2.py::TestLocationV2BatchQuery
```

### 运行特定测试函数

```bash
pytest tests/test_location_v2.py::TestLocationV2BatchQuery::test_batch_query_single_coordinate
```

### 显示详细输出

```bash
pytest tests/ -v
```

### 显示打印输出

```bash
pytest tests/ -s
```

## 测试覆盖范围

### test_location_v2.py

#### TestLocationV2Stats
- ✅ 测试未认证访问统计接口（应该失败）
- ✅ 测试认证后访问统计接口

#### TestLocationV2BatchQuery
- ✅ 测试空坐标列表
- ✅ 测试无效坐标
- ✅ 测试单个坐标查询
- ✅ 测试多个坐标查询
- ✅ 测试不带location_id的坐标查询
- ✅ 测试最大坐标数量（500个）
- ✅ 测试超过最大坐标数量（应该失败）
- ✅ 测试响应结构完整性

#### TestLocationV2EdgeCases
- ✅ 测试无效纬度
- ✅ 测试无效经度
- ✅ 测试缺少coordinates字段
- ✅ 测试缺少纬度
- ✅ 测试缺少经度

#### TestLocationV2ExternalAPI（外部API调用测试）
- ✅ 测试中国坐标调用高德API（成功场景）
- ✅ 测试国外坐标调用Nominatim API（成功场景）
- ✅ 测试高德API失败后降级到v1逻辑
- ✅ 测试Nominatim API失败后降级到v1逻辑
- ✅ 测试混合查询（中国+国外坐标）
- ✅ 测试所有API都失败的情况

#### TestLocationV2Integration
- ⏸️ 测试本地数据库命中场景（需要数据库连接）

## 本地测试数据库配置

### 方式1：使用测试环境变量文件（推荐）

1. **创建测试环境变量文件**：
   ```bash
   cp tests/.env.test.example tests/.env.test
   ```

2. **编辑 `tests/.env.test`**，配置测试数据库：
   ```bash
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_test_password
   MYSQL_DATABASE=image_classifier_test
   ```

3. **初始化测试数据库**：
   ```bash
   mysql -u root -p < tests/setup_test_db.sql
   ```

4. **运行测试**：
   ```bash
   pytest tests/ -v
   ```

### 方式2：使用环境变量

直接在运行测试时设置环境变量：

```bash
# Windows (PowerShell)
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_DATABASE="image_classifier_test"
pytest tests/ -v

# Linux/Mac
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=image_classifier_test
pytest tests/ -v
```

### 方式3：使用pytest.ini配置（不推荐，不够灵活）

创建 `pytest.ini` 文件：
```ini
[pytest]
env =
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=root
    MYSQL_PASSWORD=test_password
    MYSQL_DATABASE=image_classifier_test
```

## 注意事项

1. **大部分测试不需要数据库**: 大部分测试已经使用mock，不需要真实数据库连接
   - ✅ 外部API测试：已mock，不需要数据库
   - ✅ 接口结构测试：不需要数据库
   - ⚠️ 集成测试：需要数据库（已标记为skip）

2. **测试数据库隔离**: 建议使用独立的测试数据库（如`image_classifier_test`），避免影响生产数据

3. **外部API**: 测试外部API调用时，建议使用mock避免真实调用，节省时间和成本

4. **认证测试**: 统计接口需要JWT认证，使用`conftest.py`中的`auth_headers` fixture或`get_test_token()`函数

5. **跳过测试**: 使用`@pytest.mark.skip`标记需要特殊环境的测试

6. **快速测试**: 如果只想快速验证代码，可以只运行不需要数据库的测试：
   ```bash
   # 只运行外部API测试（已mock，不需要数据库）
   pytest tests/test_location_v2.py::TestLocationV2ExternalAPI -v
   ```

## Mock外部API示例

### Mock高德API（中国坐标）

```python
from unittest.mock import patch

@patch('app.api.location_v2.query_local_db')
@patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode')
@patch('app.api.location_v2.save_city_to_db')
def test_gaode_api(mock_save, mock_gaode, mock_local_db):
    # 本地数据库未命中
    mock_local_db.return_value = None
    
    # 高德API返回成功
    mock_gaode.return_value = {
        "name_zh": "北京市",
        "name_en": "Beijing",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "country_code": "CN",
        "api_adcode": "110101",
        "data_source": "gaode"
    }
    
    # Mock保存成功
    mock_save.return_value = 12345
    
    # 执行测试...
    response = client.post("/api/v2/location/nearest-cities", ...)
    
    # 验证调用了高德API
    mock_gaode.assert_called_once_with(39.9042, 116.4074)
```

### Mock Nominatim API（国外坐标）

```python
@patch('app.api.location_v2.query_local_db')
@patch('app.services.geocoding_client.geocoding_client.reverse_geocode_nominatim')
@patch('app.api.location_v2.save_city_to_db')
def test_nominatim_api(mock_save, mock_nominatim, mock_local_db):
    # 本地数据库未命中
    mock_local_db.return_value = None
    
    # Nominatim API返回成功
    mock_nominatim.return_value = {
        "name_en": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "country_code": "US",
        "api_city_id": "123456789",
        "data_source": "nominatim"
    }
    
    # Mock保存成功
    mock_save.return_value = 67890
    
    # 执行测试...
    response = client.post("/api/v2/location/nearest-cities", ...)
    
    # 验证调用了Nominatim API
    mock_nominatim.assert_called_once_with(40.7128, -74.0060)
```

### 测试API失败场景

```python
@patch('app.api.location_v2.query_local_db')
@patch('app.services.geocoding_client.geocoding_client.reverse_geocode_gaode')
@patch('app.api.location_v2.query_fallback_v1')
def test_api_failure_fallback(mock_fallback, mock_gaode, mock_local_db):
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
        "distance_km": 5.0,
        "data_source": "fallback"
    }
    
    # 执行测试...
    # 验证降级逻辑被调用
    mock_fallback.assert_called_once()
```

## 持续集成

在CI/CD环境中运行测试时，确保：

1. 设置必要的环境变量（`.env`文件或环境变量）
2. 配置测试数据库（如果需要）
3. Mock外部API调用
4. 安装所有依赖：`pip install -r requirements.txt`

