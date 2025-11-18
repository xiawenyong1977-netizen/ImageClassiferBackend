#!/bin/bash
# 更新image_edit_cache表中的result_url字段
# 将旧域名替换为新域名

# ============================================
# 配置区域
# ============================================

# MySQL配置
MYSQL_USER="classifier"
MYSQL_PASSWORD="Classifier@2024"
MYSQL_DATABASE="image_classifier"

# 域名替换配置
OLD_DOMAIN="www.xintuxiangce.top"
NEW_DOMAIN="api.aifuture.net.cn"

# ============================================
# 脚本执行
# ============================================

echo "=========================================="
echo "更新image_edit_cache表中的result_url"
echo "=========================================="
echo ""
echo "旧域名: ${OLD_DOMAIN}"
echo "新域名: ${NEW_DOMAIN}"
echo ""

# 检查需要更新的记录数
echo "检查需要更新的记录..."
OLD_COUNT=$(mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "SELECT COUNT(*) as cnt FROM image_edit_cache WHERE result_url LIKE '%${OLD_DOMAIN}%';" -s -N 2>/dev/null)

if [ "$OLD_COUNT" = "0" ]; then
    echo "✅ 没有需要更新的记录，所有URL已经是新域名"
    exit 0
fi

echo "发现 ${OLD_COUNT} 条记录需要更新"
echo ""

# 显示更新前的示例
echo "更新前的示例URL："
mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "SELECT result_url FROM image_edit_cache WHERE result_url LIKE '%${OLD_DOMAIN}%' LIMIT 3;" 2>/dev/null
echo ""

# 执行更新
echo "正在更新..."
mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "
UPDATE image_edit_cache 
SET result_url = REPLACE(result_url, '${OLD_DOMAIN}', '${NEW_DOMAIN}')
WHERE result_url LIKE '%${OLD_DOMAIN}%';
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 更新成功"
    
    # 验证更新结果
    echo ""
    echo "验证更新结果..."
    NEW_COUNT=$(mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "SELECT COUNT(*) as cnt FROM image_edit_cache WHERE result_url LIKE '%${NEW_DOMAIN}%';" -s -N 2>/dev/null)
    REMAINING_OLD=$(mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "SELECT COUNT(*) as cnt FROM image_edit_cache WHERE result_url LIKE '%${OLD_DOMAIN}%';" -s -N 2>/dev/null)
    
    echo "新域名URL数量: ${NEW_COUNT}"
    echo "剩余旧域名URL数量: ${REMAINING_OLD}"
    
    if [ "$REMAINING_OLD" = "0" ]; then
        echo ""
        echo "✅ 所有URL已成功更新为新域名"
        
        # 显示更新后的示例
        echo ""
        echo "更新后的示例URL："
        mysql -u ${MYSQL_USER} -p"${MYSQL_PASSWORD}" ${MYSQL_DATABASE} -e "SELECT result_url FROM image_edit_cache WHERE result_url LIKE '%${NEW_DOMAIN}%' LIMIT 3;" 2>/dev/null
    else
        echo "⚠️  警告：仍有 ${REMAINING_OLD} 条记录使用旧域名"
    fi
else
    echo "❌ 更新失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "更新完成"
echo "=========================================="

