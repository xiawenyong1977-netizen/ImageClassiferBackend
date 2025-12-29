#!/bin/bash
# 导出数据库表结构（不包含数据）
# 用于测试数据库初始化

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# 服务器信息
SERVER="app"  # 服务器SSH别名或IP
MYSQL_USER="classifier"  # MySQL用户名
MYSQL_PASSWORD="Classifier@2024"  # MySQL密码
MYSQL_DATABASE="image_classifier"  # 数据库名

# 输出文件
OUTPUT_FILE="tests/setup_test_db.sql"

# ============================================
# 导出表结构
# ============================================

echo "=========================================="
echo "导出数据库表结构..."
echo "=========================================="

# 方法1：使用mysqldump只导出表结构（推荐）
echo "正在从服务器 ${SERVER} 导出表结构..."

# 导出表结构（不包含数据）
ssh root@${SERVER} "mysqldump -u ${MYSQL_USER} -p'${MYSQL_PASSWORD}' \
    --no-data \
    --skip-triggers \
    --skip-routines \
    --skip-events \
    --single-transaction \
    --routines=false \
    --databases ${MYSQL_DATABASE}" > "${OUTPUT_FILE}.tmp" 2>&1

# 过滤掉警告信息
grep -v "Warning: Using a password" "${OUTPUT_FILE}.tmp" > "${OUTPUT_FILE}.tmp2" || true

# 修改数据库名为测试数据库
sed "s/${MYSQL_DATABASE}/${MYSQL_DATABASE}_test/g" "${OUTPUT_FILE}.tmp2" > "${OUTPUT_FILE}.tmp3"

# 添加测试数据库创建语句到文件开头
cat > "${OUTPUT_FILE}" << EOF
-- ====================================
-- 测试数据库初始化脚本
-- 从生产环境导出，自动生成
-- 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
-- ====================================

-- 创建测试数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE}_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ${MYSQL_DATABASE}_test;

EOF

# 追加表结构（跳过CREATE DATABASE和USE语句）
grep -v "^CREATE DATABASE" "${OUTPUT_FILE}.tmp3" | \
    grep -v "^USE " | \
    grep -v "^-- Dump completed" | \
    grep -v "^/\*!40" | \
    grep -v "^SET " | \
    grep -v "^/\*!50003" >> "${OUTPUT_FILE}"

# 添加测试数据插入语句
cat >> "${OUTPUT_FILE}" << 'EOF'

-- ====================================
-- 插入测试数据
-- ====================================

-- 插入测试城市数据（v2）
INSERT INTO global_cities_v2 (name_en, latitude, longitude, country_code, data_source) VALUES
('Beijing', 39.9042, 116.4074, 'CN', 'local'),
('Shanghai', 31.2304, 121.4737, 'CN', 'local'),
('New York', 40.7128, -74.0060, 'US', 'local')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 插入测试映射数据
INSERT INTO city_name_mapping (name_zh, name_en, country_code) VALUES
('北京', 'Beijing', 'CN'),
('上海', 'Shanghai', 'CN'),
('纽约', 'New York', 'US')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

SELECT '测试数据库初始化完成！' AS 'Status';
EOF

# 清理临时文件
rm -f "${OUTPUT_FILE}.tmp" "${OUTPUT_FILE}.tmp2" "${OUTPUT_FILE}.tmp3"

echo "✅ 表结构导出成功"
echo "   文件: ${OUTPUT_FILE}"
echo "   数据库: ${MYSQL_DATABASE}_test"

