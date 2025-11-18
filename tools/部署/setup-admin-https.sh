#!/bin/bash
# 为admin.xintuxiangce.top配置HTTPS

set -e

echo "=========================================="
echo "为 admin.xintuxiangce.top 配置HTTPS"
echo "=========================================="

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo "请以root用户运行此脚本"
    exit 1
fi

# 1. 获取SSL证书
echo ""
echo "步骤1: 获取SSL证书..."
echo "----------------------------------------"

# 检查certbot是否安装
if ! command -v certbot &> /dev/null; then
    echo "❌ certbot未安装，正在安装..."
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        yum install -y certbot
    else
        echo "❌ 无法自动安装certbot，请手动安装"
        exit 1
    fi
fi

# 检查webroot目录
WEBROOT="/var/www/xintuxiangce/admin"
if [ ! -d "$WEBROOT" ]; then
    echo "❌ Webroot目录不存在: $WEBROOT"
    exit 1
fi

# 获取证书
echo "正在获取SSL证书..."
certbot certonly \
    --webroot \
    -w "$WEBROOT" \
    -d admin.xintuxiangce.top \
    --email xiawenyong@xintuxiangce.top \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring

if [ $? -eq 0 ]; then
    echo "✅ SSL证书获取成功"
else
    echo "❌ SSL证书获取失败"
    exit 1
fi

# 2. 更新Lighttpd配置
echo ""
echo "步骤2: 更新Lighttpd配置..."
echo "----------------------------------------"

CONFIG_FILE="/etc/lighttpd/conf.d/admin-vhost.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 备份配置
cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ 配置已备份"

# 检查证书文件
CERT_FILE="/etc/letsencrypt/live/admin.xintuxiangce.top/fullchain.pem"
KEY_FILE="/etc/letsencrypt/live/admin.xintuxiangce.top/privkey.pem"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "❌ 证书文件不存在"
    exit 1
fi

echo "✅ 证书文件检查通过"

# 3. 测试Lighttpd配置
echo ""
echo "步骤3: 测试Lighttpd配置..."
echo "----------------------------------------"

if lighttpd -t -f /etc/lighttpd/lighttpd.conf; then
    echo "✅ Lighttpd配置测试通过"
else
    echo "❌ Lighttpd配置测试失败"
    exit 1
fi

# 4. 重启Lighttpd
echo ""
echo "步骤4: 重启Lighttpd服务..."
echo "----------------------------------------"

if systemctl restart lighttpd; then
    echo "✅ Lighttpd服务重启成功"
else
    echo "❌ Lighttpd服务重启失败"
    exit 1
fi

# 5. 验证HTTPS
echo ""
echo "步骤5: 验证HTTPS配置..."
echo "----------------------------------------"

sleep 2

if curl -s -I https://admin.xintuxiangce.top | grep -q "HTTP/1.1 200\|HTTP/2 200"; then
    echo "✅ HTTPS访问正常"
else
    echo "⚠️  HTTPS访问可能有问题，请检查"
fi

echo ""
echo "=========================================="
echo "HTTPS配置完成！"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  - HTTP:  http://admin.xintuxiangce.top (会自动重定向到HTTPS)"
echo "  - HTTPS: https://admin.xintuxiangce.top"
echo ""
echo "证书自动续期:"
echo "  certbot renew --dry-run"
echo ""

