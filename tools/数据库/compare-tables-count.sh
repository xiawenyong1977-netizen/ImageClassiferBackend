#!/bin/bash
# 比较Web服务器和App服务器上所有表的记录数

# ============================================
# 配置区域
# ============================================

# Web服务器信息
WEB_SERVER="web"
WEB_MYSQL_USER="root"
WEB_MYSQL_PASSWORD=""  # 从.env文件读取
WEB_MYSQL_DATABASE="image_classifier"

# App服务器信息
APP_SERVER="app"
APP_MYSQL_USER="root"
APP_MYSQL_PASSWORD=""  # 从.env文件读取
APP_MYSQL_DATABASE="image_classifier"

# ============================================
# 脚本执行
# ============================================

echo "=========================================="
echo "比较Web和App服务器数据库表记录数"
echo "=========================================="
echo ""

# 读取密码
WEB_MYSQL_PASSWORD=$(ssh root@${WEB_SERVER} "cat /opt/ImageClassifierBackend/.env 2>/dev/null | grep '^MYSQL_PASSWORD=' | head -1 | cut -d'=' -f2-" 2>/dev/null)
APP_MYSQL_PASSWORD=$(ssh root@${APP_SERVER} "cat /opt/ImageClassifierBackend/.env 2>/dev/null | grep '^MYSQL_PASSWORD=' | head -1 | cut -d'=' -f2-" 2>/dev/null)

if [ -z "$WEB_MYSQL_PASSWORD" ]; then
    echo "❌ 错误：无法读取Web服务器MySQL密码"
    exit 1
fi

if [ -z "$APP_MYSQL_PASSWORD" ]; then
    echo "❌ 错误：无法读取App服务器MySQL密码"
    exit 1
fi

# 获取所有表名
echo "正在获取表列表..."
WEB_TABLES=$(ssh root@${WEB_SERVER} "mysql -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' ${WEB_MYSQL_DATABASE} -e 'SHOW TABLES;' 2>/dev/null | tail -n +2")
APP_TABLES=$(ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' ${APP_MYSQL_DATABASE} -e 'SHOW TABLES;' 2>/dev/null | tail -n +2")

# 计算总记录数
echo ""
echo "=========================================="
echo "计算总记录数..."
echo "=========================================="

WEB_TOTAL=0
APP_TOTAL=0

for table in $WEB_TABLES; do
    count=$(ssh root@${WEB_SERVER} "mysql -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' ${WEB_MYSQL_DATABASE} -e 'SELECT COUNT(*) FROM \`${table}\`;' 2>/dev/null | tail -1")
    if [ ! -z "$count" ] && [ "$count" != "COUNT(*)" ]; then
        WEB_TOTAL=$((WEB_TOTAL + count))
    fi
done

for table in $APP_TABLES; do
    count=$(ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' ${APP_MYSQL_DATABASE} -e 'SELECT COUNT(*) FROM \`${table}\`;' 2>/dev/null | tail -1")
    if [ ! -z "$count" ] && [ "$count" != "COUNT(*)" ]; then
        APP_TOTAL=$((APP_TOTAL + count))
    fi
done

echo ""
echo "Web服务器总记录数: $WEB_TOTAL"
echo "App服务器总记录数: $APP_TOTAL"
echo ""

if [ "$WEB_TOTAL" -eq "$APP_TOTAL" ]; then
    echo "✅ 总记录数一致"
else
    echo "❌ 总记录数不一致，差异: $((WEB_TOTAL - APP_TOTAL))"
fi

echo ""
echo "=========================================="
echo "详细比较每个表的记录数..."
echo "=========================================="
echo ""

# 获取所有唯一表名
ALL_TABLES=$(echo -e "$WEB_TABLES\n$APP_TABLES" | sort -u)

printf "%-40s %15s %15s %10s\n" "表名" "Web记录数" "App记录数" "状态"
echo "--------------------------------------------------------------------------------"

for table in $ALL_TABLES; do
    # Web服务器记录数
    web_count=$(ssh root@${WEB_SERVER} "mysql -u ${WEB_MYSQL_USER} -p'${WEB_MYSQL_PASSWORD}' ${WEB_MYSQL_DATABASE} -e 'SELECT COUNT(*) FROM \`${table}\`;' 2>/dev/null | tail -1" 2>/dev/null)
    if [ -z "$web_count" ] || [ "$web_count" = "COUNT(*)" ]; then
        web_count="N/A"
        web_num=0
    else
        web_num=$web_count
    fi
    
    # App服务器记录数
    app_count=$(ssh root@${APP_SERVER} "mysql -u ${APP_MYSQL_USER} -p'${APP_MYSQL_PASSWORD}' ${APP_MYSQL_DATABASE} -e 'SELECT COUNT(*) FROM \`${table}\`;' 2>/dev/null | tail -1" 2>/dev/null)
    if [ -z "$app_count" ] || [ "$app_count" = "COUNT(*)" ]; then
        app_count="N/A"
        app_num=0
    else
        app_num=$app_count
    fi
    
    # 比较
    if [ "$web_count" = "N/A" ] && [ "$app_count" = "N/A" ]; then
        status="不存在"
    elif [ "$web_count" = "N/A" ]; then
        status="仅App有"
    elif [ "$app_count" = "N/A" ]; then
        status="仅Web有"
    elif [ "$web_num" -eq "$app_num" ]; then
        status="✅一致"
    else
        diff=$((web_num - app_num))
        status="❌差异:$diff"
    fi
    
    printf "%-40s %15s %15s %10s\n" "$table" "$web_count" "$app_count" "$status"
done

echo ""
echo "=========================================="
echo "比较完成"
echo "=========================================="

