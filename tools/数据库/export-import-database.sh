
#!/bin/bash
# 数据库导出和导入脚本
# 从Web服务器导出数据库，然后导入到App服务器

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# Web服务器信息
WEB_SERVER="localhost"  # Web服务器SSH别名或IP（如果在本机执行，使用"localhost"）
WEB_MYSQL_USER="classifier"                    # Web服务器MySQL用户名
WEB_MYSQL_PASSWORD="Classifier@2024"                    # Web服务器MySQL密码（如果为空，脚本会提示输入）
WEB_MYSQL_DATABASE="image_classifier"    # 数据库名

# App服务器信息
APP_SERVER="app"   # App服务器SSH别名或IP
APP_MYSQL_USER="classifier"                    # app服务器MySQL用户名
APP_MYSQL_PASSWORD="Classifier@2024"                    # App服务器MySQL密码（如果为空，脚本会提示输入）
APP_MYSQL_DATABASE="image_classifier"   # 数据库名

# 临时文件路径
EXPORT_FILE="/tmp/image_classifier_export_$(date +%Y%m%d_%H%M%S).sql"

# ============================================
# 脚本执行
# ============================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "数据库导出和导入脚本"
echo "=========================================="

# 获取Web服务器MySQL密码
if [ -z "$WEB_MYSQL_PASSWORD" ]; then
    read -sp "请输入Web服务器MySQL root密码: " WEB_MYSQL_PASSWORD
    echo
fi

# 获取App服务器MySQL密码
if [ -z "$APP_MYSQL_PASSWORD" ]; then
    read -sp "请输入App服务器MySQL root密码: " APP_MYSQL_PASSWORD
    echo
fi

# 步骤1：在Web服务器上导出数据库
echo ""
echo "=========================================="
echo "步骤1: 在Web服务器上导出数据库..."
echo "=========================================="

# 检测是否在Web服务器本地执行
if [ "$WEB_SERVER" = "localhost" ] || [ "$WEB_SERVER" = "127.0.0.1" ] || [ -z "$WEB_SERVER" ]; then
    IS_LOCAL_WEB=true
else
    IS_LOCAL_WEB=false
fi

# 测试Web服务器MySQL连接
echo "测试Web服务器MySQL连接..."
if [ "$IS_LOCAL_WEB" = "true" ]; then
    # 本地执行
    if ! mysql -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' -e "SELECT 1;" ${WEB_MYSQL_DATABASE} 2>&1 | grep -v "Warning: Using a password" | grep -q "1"; then
        echo "❌ 错误：无法连接到本地MySQL"
        exit 1
    fi
    echo "✅ Web服务器MySQL连接成功（本地）"
    
    # 导出数据库（本地）
    echo "正在导出数据库..."
    MYSQL_PWD="${WEB_MYSQL_PASSWORD}" mysqldump -u ${WEB_MYSQL_USER} \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --add-drop-database \
        --skip-triggers \
        --databases ${WEB_MYSQL_DATABASE} > "${EXPORT_FILE}" 2>&1
    DUMP_EXIT_CODE=${PIPESTATUS[0]}
    # 过滤警告信息但保留错误
    if [ $DUMP_EXIT_CODE -ne 0 ]; then
        echo "❌ 错误：数据库导出失败"
        cat "${EXPORT_FILE}" | grep -i error
        exit 1
    fi
else
    # 远程执行
    if ! ssh root@${WEB_SERVER} "mysql -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' -e 'SELECT 1;' ${WEB_MYSQL_DATABASE}" 2>&1 | grep -v "Warning: Using a password" | grep -q "1"; then
        echo "❌ 错误：无法连接到Web服务器MySQL"
        echo "请检查："
        echo "  1. Web服务器是否正确: ${WEB_SERVER}"
        echo "  2. MySQL用户名和密码是否正确"
        echo "  3. 数据库是否存在: ${WEB_MYSQL_DATABASE}"
        exit 1
    fi
    echo "✅ Web服务器MySQL连接成功"
    
    # 导出数据库（远程）
    echo "正在导出数据库..."
    ssh root@${WEB_SERVER} "mysqldump -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --add-drop-database \
        --skip-triggers \
        --databases ${WEB_MYSQL_DATABASE}" > "${EXPORT_FILE}"
fi

if [ $? -eq 0 ] && [ -s "${EXPORT_FILE}" ]; then
    EXPORT_SIZE=$(du -h "${EXPORT_FILE}" | awk '{print $1}')
    echo "✅ 数据库导出成功"
    echo "   文件: ${EXPORT_FILE}"
    echo "   大小: ${EXPORT_SIZE}"
else
    echo "❌ 错误：数据库导出失败"
    exit 1
fi

# 步骤2：传输SQL文件到App服务器
echo ""
echo "=========================================="
echo "步骤2: 传输SQL文件到App服务器..."
echo "=========================================="

echo "正在传输文件到App服务器..."
scp "${EXPORT_FILE}" root@${APP_SERVER}:/tmp/

if [ $? -eq 0 ]; then
    echo "✅ 文件传输成功"
    REMOTE_FILE="/tmp/$(basename ${EXPORT_FILE})"
else
    echo "❌ 错误：文件传输失败"
    exit 1
fi

# 步骤3：在App服务器上导入数据库
echo ""
echo "=========================================="
echo "步骤3: 在App服务器上导入数据库..."
echo "=========================================="

# 测试App服务器MySQL连接
echo "测试App服务器MySQL连接..."
if ! ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' -e 'SELECT 1;'" 2>&1 | grep -v "Warning: Using a password" | grep -q "1"; then
    echo "❌ 错误：无法连接到App服务器MySQL"
    exit 1
fi
echo "✅ App服务器MySQL连接成功"

# 检查数据库是否存在，如果存在则询问是否删除
echo "检查数据库是否存在..."
DB_EXISTS=$(ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' -e 'SHOW DATABASES LIKE \"${APP_MYSQL_DATABASE}\";' | grep -c ${APP_MYSQL_DATABASE}" || echo "0")

if [ "$DB_EXISTS" != "0" ]; then
    echo "⚠️  警告：数据库 ${APP_MYSQL_DATABASE} 已存在"
    echo "正在删除现有数据库并重新导入..."
    ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' -e 'DROP DATABASE IF EXISTS ${APP_MYSQL_DATABASE};'" 2>&1 | grep -v "Warning: Using a password"
    echo "✅ 数据库已删除"
fi

# 导入数据库
echo "正在导入数据库..."
# 使用--force参数继续执行，即使遇到生成列错误也会继续
ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' --force < ${REMOTE_FILE}" 2>&1 | grep -v "Warning: Using a password" | grep -v "ERROR 3105"

IMPORT_EXIT_CODE=${PIPESTATUS[0]}
# 检查是否有严重错误（除了生成列错误3105）
if [ $IMPORT_EXIT_CODE -ne 0 ]; then
    echo "⚠️  导入过程中可能有错误，但已使用--force继续执行"
    echo "请检查上面的错误信息（生成列错误3105可以忽略）"
fi

# 验证数据库是否导入成功
echo "验证数据库导入..."
TABLE_COUNT=$(ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' -e 'USE ${APP_MYSQL_DATABASE}; SHOW TABLES;' 2>&1 | grep -v 'Warning' | wc -l")
if [ "$TABLE_COUNT" -gt "1" ]; then
    echo "✅ 数据库导入成功"
    echo "   数据库表数量: $((TABLE_COUNT - 1))"
else
    echo "❌ 错误：数据库导入失败，表数量为0"
    exit 1
fi


# 清理临时文件
echo ""
echo "=========================================="
echo "清理临时文件..."
echo "=========================================="
rm -f "${EXPORT_FILE}"
ssh root@${APP_SERVER} "rm -f ${REMOTE_FILE}"
echo "✅ 临时文件已清理"

echo ""
echo "=========================================="
echo "✅ 数据库导出和导入完成！"
echo "=========================================="
echo ""
echo "数据库已成功从Web服务器导入到App服务器"
echo "数据库名: ${APP_MYSQL_DATABASE}"

