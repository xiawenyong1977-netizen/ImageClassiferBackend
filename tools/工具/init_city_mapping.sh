#!/bin/bash
# 初始化城市名称映射表的完整脚本
# 包括：下载数据、提取映射、导入数据库

set -e

echo "=========================================="
echo "城市名称映射表初始化脚本"
echo "=========================================="
echo ""

# 配置
DATA_DIR="tools/数据/geonames"
SCRIPTS_DIR="tools/工具"
DB_SCRIPTS_DIR="tools/数据库"
OUTPUT_FILE="city_mapping.csv"

# 创建数据目录
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

echo "【步骤1】下载GeoNames数据"
echo "----------------------------------------"
echo ""

# 检查是否已下载
if [ ! -f "cities15000.txt" ]; then
    echo "正在下载全球主要城市数据 (cities15000.zip)..."
    wget -q --show-progress https://download.geonames.org/export/dump/cities15000.zip
    echo "正在解压..."
    unzip -q cities15000.zip
    echo "✓ 下载完成"
else
    echo "✓ cities15000.txt 已存在，跳过下载"
fi

echo ""

if [ ! -f "CN.txt" ]; then
    echo "正在下载中国详细数据 (CN.zip)..."
    wget -q --show-progress https://download.geonames.org/export/dump/CN.zip
    echo "正在解压..."
    unzip -q CN.zip
    echo "✓ 下载完成"
else
    echo "✓ CN.txt 已存在，跳过下载"
fi

echo ""
echo "【步骤2】提取映射关系"
echo "----------------------------------------"
echo ""

cd ../../..

# 检查Python脚本
if [ ! -f "$SCRIPTS_DIR/extract_city_mapping.py" ]; then
    echo "错误: extract_city_mapping.py 不存在"
    exit 1
fi

# 执行提取
echo "正在提取映射关系..."
python3 "$SCRIPTS_DIR/extract_city_mapping.py" \
    "$DATA_DIR/cities15000.txt" \
    "$DATA_DIR/CN.txt" \
    "$OUTPUT_FILE"

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "错误: 提取失败，未生成 $OUTPUT_FILE"
    exit 1
fi

echo ""
echo "【步骤3】创建数据库表"
echo "----------------------------------------"
echo ""

# 检查SQL脚本
if [ ! -f "$DB_SCRIPTS_DIR/create_city_name_mapping.sql" ]; then
    echo "错误: create_city_name_mapping.sql 不存在"
    exit 1
fi

# 读取数据库配置（从.env文件）
if [ -f ".env" ]; then
    source .env
    MYSQL_USER=${MYSQL_USER:-root}
    MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
    MYSQL_HOST=${MYSQL_HOST:-localhost}
    MYSQL_DATABASE=${MYSQL_DATABASE:-image_classifier}
else
    echo "警告: .env 文件不存在，使用默认配置"
    MYSQL_USER="root"
    MYSQL_PASSWORD=""
    MYSQL_HOST="localhost"
    MYSQL_DATABASE="image_classifier"
fi

echo "正在创建数据库表..."
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$DB_SCRIPTS_DIR/create_city_name_mapping.sql"

echo ""
echo "【步骤4】导入数据到数据库"
echo "----------------------------------------"
echo ""

# 检查导入脚本
if [ ! -f "$SCRIPTS_DIR/import_city_mapping.py" ]; then
    echo "错误: import_city_mapping.py 不存在"
    exit 1
fi

# 执行导入
echo "正在导入数据..."
python3 "$SCRIPTS_DIR/import_city_mapping.py" "$OUTPUT_FILE"

echo ""
echo "=========================================="
echo "初始化完成！"
echo "=========================================="
echo ""
echo "映射表已创建并导入数据"
echo "CSV文件保存在: $OUTPUT_FILE"
echo ""

