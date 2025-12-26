# PowerShell脚本：导出数据库表结构（不包含数据）
# 用于测试数据库初始化

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# 服务器信息
$SERVER = "app"  # 服务器SSH别名或IP
$MYSQL_USER = "classifier"  # MySQL用户名
$MYSQL_PASSWORD = "Classifier@2024"  # MySQL密码
$MYSQL_DATABASE = "image_classifier"  # 数据库名

# 输出文件
$OUTPUT_FILE = "tests\setup_test_db.sql"

# ============================================
# 导出表结构
# ============================================

Write-Host "=========================================="
Write-Host "导出数据库表结构..." -ForegroundColor Cyan
Write-Host "=========================================="

# 临时文件
$TEMP_FILE = "setup_test_db_temp.sql"

Write-Host "正在从服务器 ${SERVER} 导出表结构..." -ForegroundColor Yellow

# 导出表结构（不包含数据）
# 注意：需要先配置SSH密钥或使用密码认证
$exportCommand = @"
mysqldump -u ${MYSQL_USER} -p'${MYSQL_PASSWORD}' --no-data --skip-triggers --skip-routines --skip-events --single-transaction --routines=false --databases ${MYSQL_DATABASE}
"@

# 通过SSH执行命令并保存到临时文件
ssh root@${SERVER} $exportCommand 2>&1 | Where-Object { $_ -notmatch "Warning: Using a password" } | Out-File -FilePath $TEMP_FILE -Encoding UTF8

# 读取临时文件内容
$content = Get-Content $TEMP_FILE -Raw -Encoding UTF8

# 修改数据库名为测试数据库
$content = $content -replace $MYSQL_DATABASE, "${MYSQL_DATABASE}_test"

# 创建输出文件
$header = @"
-- ====================================
-- 测试数据库初始化脚本
-- 从生产环境导出，自动生成
-- 生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
-- ====================================

-- 创建测试数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ${MYSQL_DATABASE}_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ${MYSQL_DATABASE}_test;

"@

# 过滤掉不需要的语句
$lines = $content -split "`n" | Where-Object {
    $_ -notmatch "^CREATE DATABASE" -and
    $_ -notmatch "^USE " -and
    $_ -notmatch "^-- Dump completed" -and
    $_ -notmatch "^/\*!40" -and
    $_ -notmatch "^SET " -and
    $_ -notmatch "^/\*!50003"
}

# 写入输出文件
$header | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8 -NoNewline
$lines | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8 -Append

# 添加测试数据
$testData = @"

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
"@

$testData | Out-File -FilePath $OUTPUT_FILE -Encoding UTF8 -Append

# 清理临时文件
Remove-Item $TEMP_FILE -ErrorAction SilentlyContinue

Write-Host "✅ 表结构导出成功" -ForegroundColor Green
Write-Host "   文件: $OUTPUT_FILE"
Write-Host "   数据库: ${MYSQL_DATABASE}_test"

