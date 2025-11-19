#!/bin/bash
# Nginx日志检查脚本
# 用于检查POST请求是否被记录

echo "=========================================="
echo "Nginx配置和日志检查"
echo "=========================================="
echo ""

# 1. 检查nginx配置文件位置
echo "1. 查找nginx配置文件..."
NGINX_CONF=$(nginx -t 2>&1 | grep "configuration file" | awk '{print $NF}')
if [ -n "$NGINX_CONF" ]; then
    echo "   主配置文件: $NGINX_CONF"
    echo ""
    
    # 检查是否有自定义log_format
    echo "2. 检查日志格式配置..."
    if grep -q "log_format.*detailed" "$NGINX_CONF" /etc/nginx/conf.d/*.conf 2>/dev/null; then
        echo "   ✓ 找到自定义日志格式 'detailed'"
        grep "log_format.*detailed" "$NGINX_CONF" /etc/nginx/conf.d/*.conf 2>/dev/null | head -1
    else
        echo "   ✗ 未找到自定义日志格式，使用默认格式"
    fi
    echo ""
    
    # 检查access_log配置
    echo "3. 检查access_log配置..."
    echo "   当前access_log配置:"
    grep -r "access_log" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null | grep -v "#" | head -5
    echo ""
else
    echo "   ✗ 无法找到nginx配置文件"
fi

# 4. 检查日志文件
echo "4. 检查日志文件..."
LOG_FILES=(
    "/var/log/nginx/api-aifuture-access.log"
    "/var/log/nginx/access.log"
    "/var/log/nginx/api-aifuture-error.log"
    "/var/log/nginx/error.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        echo "   ✓ 找到日志文件: $log_file"
        echo "      文件大小: $(du -h "$log_file" | cut -f1)"
        echo "      最后修改: $(stat -c %y "$log_file" 2>/dev/null || stat -f %Sm "$log_file" 2>/dev/null)"
        
        # 检查最近的POST请求
        POST_COUNT=$(grep -c "POST" "$log_file" 2>/dev/null || echo "0")
        if [ "$POST_COUNT" -gt 0 ]; then
            echo "      ✓ 包含 $POST_COUNT 条POST请求记录"
            echo "      最近的POST请求:"
            grep "POST" "$log_file" 2>/dev/null | tail -3 | sed 's/^/        /'
        else
            echo "      ⚠ 未找到POST请求记录"
        fi
        echo ""
    fi
done

# 5. 检查最近的访问日志（所有请求）
echo "5. 最近的访问日志（最后10条）..."
if [ -f "/var/log/nginx/api-aifuture-access.log" ]; then
    tail -10 /var/log/nginx/api-aifuture-access.log | while read line; do
        if echo "$line" | grep -q "POST"; then
            echo "   [POST] $line"
        else
            echo "   [其他] $line"
        fi
    done
elif [ -f "/var/log/nginx/access.log" ]; then
    tail -10 /var/log/nginx/access.log | while read line; do
        if echo "$line" | grep -q "POST"; then
            echo "   [POST] $line"
        else
            echo "   [其他] $line"
        fi
    done
else
    echo "   ⚠ 未找到访问日志文件"
fi
echo ""

# 6. 实时监控建议
echo "6. 实时监控POST请求命令:"
echo "   sudo tail -f /var/log/nginx/api-aifuture-access.log | grep --line-buffered POST"
echo ""

# 7. 测试POST请求
echo "7. 测试POST请求（可选）:"
echo "   curl -X POST https://api.aifuture.net.cn/api/v1/health -v"
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="


