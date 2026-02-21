# 大模型逆地址编码功能测试

## 概述

本测试脚本用于验证使用大模型进行逆地址编码（坐标转地址）的功能。

## 测试场景

1. **单个坐标点查询**：测试单个坐标点的逆地址编码
2. **批量坐标点查询**：测试多个坐标点的批量逆地址编码（模拟聚类后的圆心查询）
3. **海外坐标查询**：测试海外坐标的逆地址编码能力

## 测试数据

测试脚本包含以下测试坐标：

### 中国坐标
- 北京天安门：`(39.9042, 116.4074)`
- 上海外滩：`(31.2304, 121.4737)`
- 广州塔：`(23.1064, 113.3245)`

### 海外坐标
- 纽约时代广场：`(40.7580, -73.9855)`
- 巴黎埃菲尔铁塔：`(48.8584, 2.2945)`
- 东京塔：`(35.6586, 139.7454)`
- 梵蒂冈：`(41.9029, 12.4534)`（测试小国场景）

## 使用方法

### 1. 环境准备

确保已配置 Deepseek API Key：

```bash
# 在环境变量或配置文件中设置
export DEEPSEEK_API_KEY="your-api-key"
```

或者在 `app/config.py` 中配置 `DEEPSEEK_API_KEY`。

### 2. 运行测试

```bash
# 在服务器上运行（部署目录：/opt/ICBackend/current）
cd /opt/ICBackend/current
python tools/测试/test_reverse_geocoding_llm.py
```

### 3. 测试输出

测试脚本会输出：
- 每个测试场景的详细执行过程
- 大模型返回的原始内容
- 解析后的JSON结果
- 验证结果（是否符合预期）

## 验证标准

测试脚本会验证以下内容：

1. **必需字段**：
   - `index`: 索引（必须与输入顺序一致）
   - `query_latitude`, `query_longitude`: 查询坐标（必须与输入坐标一致）
   - `city_latitude`, `city_longitude`: 城市坐标
   - `country_code`: 国家代码
   - `country_name_zh`, `country_name_en`: 国家名称（中英文）
   - `admin1_name_zh`, `admin1_name_en`: 一级行政区（省/州）
   - `admin2_name_zh`, `admin2_name_en`: 二级行政区（市/县）

2. **坐标一致性**：
   - `query_latitude` 和 `query_longitude` 必须与输入坐标完全一致（允许小误差）

3. **国家代码匹配**：
   - 返回的国家代码必须与预期一致

4. **行政区匹配**：
   - 一级行政区名称应包含预期的关键词

## 预期结果

### 成功示例

```json
[
    {
        "index": 0,
        "query_latitude": 39.9042,
        "query_longitude": 116.4074,
        "city_latitude": 39.9042,
        "city_longitude": 116.4074,
        "country_code": "CN",
        "country_name_zh": "中国",
        "country_name_en": "China",
        "admin1_name_zh": "北京市",
        "admin1_name_en": "Beijing",
        "admin2_name_zh": "东城区",
        "admin2_name_en": "Dongcheng",
        "city_name_zh": "北京市",
        "city_name_en": "Beijing"
    }
]
```

## 注意事项

1. **API限流**：测试脚本在测试之间会等待2秒，避免API限流
2. **Token消耗**：批量查询会消耗更多token，注意API配额
3. **海外坐标**：海外坐标的验证可能不完全匹配，只记录警告
4. **小国场景**：梵蒂冈等小国可能没有一级或二级行政区，这是正常情况

## 故障排查

### 1. API Key未配置

```
错误: 文本生成失败：未提供Deepseek API Key
```

**解决方案**：检查 `DEEPSEEK_API_KEY` 环境变量或配置文件

### 2. JSON解析失败

```
错误: JSON解析失败
```

**解决方案**：
- 检查大模型返回的内容格式
- 可能需要调整提示词，要求大模型只返回JSON

### 3. 坐标不匹配

```
错误: query坐标不匹配
```

**解决方案**：
- 检查大模型是否正确返回了query坐标
- 可能需要加强提示词，明确要求返回query坐标

## 扩展测试

可以根据需要添加更多测试坐标：

1. 在 `TEST_COORDINATES` 列表中添加新的测试用例
2. 设置预期的国家代码和一级行政区名称
3. 运行测试验证

## 相关文档

- [逆地址编码V2接口实现逻辑](../../docs/开发/逆地址编码V2接口实现逻辑.md)
- [LLM服务使用文档](../../app/services/llm/README.md)
