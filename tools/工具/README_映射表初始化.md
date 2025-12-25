# 城市名称映射表初始化指南

## 概述

本工具用于初始化 `city_name_mapping` 表，该表存储全球城市的中英文名称映射关系。

## 文件说明

- `create_city_name_mapping.sql` - 创建数据库表的SQL脚本
- `extract_city_mapping.py` - 从GeoNames数据提取映射关系的Python脚本
- `import_city_mapping.py` - 导入映射关系到数据库的Python脚本
- `init_city_mapping.sh` - 一键初始化脚本（包含所有步骤）

## 快速开始

### 方式1：使用一键脚本（推荐）

```bash
# 在项目根目录执行
bash tools/工具/init_city_mapping.sh
```

### 方式2：分步执行

#### 步骤1：创建数据库表

```bash
mysql -u root -p image_classifier < tools/数据库/create_city_name_mapping.sql
```

#### 步骤2：下载GeoNames数据

```bash
# 创建数据目录
mkdir -p tools/数据/geonames
cd tools/数据/geonames

# 下载全球主要城市数据
wget https://download.geonames.org/export/dump/cities15000.zip
unzip cities15000.zip

# 下载中国详细数据
wget https://download.geonames.org/export/dump/CN.zip
unzip CN.zip
```

#### 步骤3：提取映射关系

```bash
cd ../../..
python3 tools/工具/extract_city_mapping.py \
    tools/数据/geonames/cities15000.txt \
    tools/数据/geonames/CN.txt \
    city_mapping.csv
```

#### 步骤4：导入到数据库

```bash
python3 tools/工具/import_city_mapping.py city_mapping.csv
```

## 数据来源

- **cities15000.txt**: 全球人口≥15000的城市（约2.3万个）
- **CN.txt**: 中国所有地点数据（约100万条，提取城市级别）

## 数据量估算

- 预计映射关系：约8000-12000条
- 中国城市：约3000-5000条
- 其他国家城市：约5000-7000条
- 存储空间：约1-2MB

## 验证

导入完成后，可以验证数据：

```sql
-- 查看总记录数
SELECT COUNT(*) FROM city_name_mapping;

-- 查看中国城市数量
SELECT COUNT(*) FROM city_name_mapping WHERE country_code = 'CN';

-- 查看示例数据
SELECT name_zh, name_en, country_code 
FROM city_name_mapping 
LIMIT 10;
```

## 注意事项

1. 确保已安装Python3和必要的依赖（pymysql, python-dotenv）
2. 确保数据库配置正确（.env文件或环境变量）
3. 下载GeoNames数据可能需要一些时间（取决于网络速度）
4. 导入过程可能需要几分钟（取决于数据量）

## 依赖安装

```bash
pip install pymysql python-dotenv
```

## 故障排查

### 问题1：数据库连接失败
- 检查.env文件中的数据库配置
- 确认数据库服务正在运行
- 确认用户有足够的权限

### 问题2：文件下载失败
- 检查网络连接
- 可以手动下载文件到指定目录

### 问题3：Python脚本执行失败
- 检查Python版本（需要Python 3.6+）
- 检查依赖是否已安装
- 查看错误信息进行排查

