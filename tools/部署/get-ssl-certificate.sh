#!/bin/bash
# 获取Let's Encrypt证书脚本
# 使用方法: ./get-ssl-certificate.sh

set -e

DOMAIN="api.aifuture.net.cn"
EMAIL="xiawenyong@xintuxiangce.top"

echo "=========================================="
echo "Let's Encrypt 证书获取脚本"
echo "=========================================="
echo "域名: $DOMAIN"
echo "邮箱: $EMAIL"
echo ""

# 检查域名解析
echo "1. 检查域名解析..."
SERVER_IP=$(curl -s ifconfig.me || curl -s ip.sb)
DNS_IP=$(nslookup $DOMAIN 2>/dev/null | grep -A 2 "Name:" | grep "Address" | awk '{print $2}' | head -1 || echo "")

if [ -z "$DNS_IP" ]; then
    echo "⚠️  警告: 无法解析域名 $DOMAIN"
    echo "   请确保DNS已正确配置"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   DNS解析: $DOMAIN -> $DNS_IP"
    echo "   服务器IP: $SERVER_IP"
    if [ "$DNS_IP" != "$SERVER_IP" ]; then
        echo "⚠️  警告: DNS解析IP ($DNS_IP) 与服务器IP ($SERVER_IP) 不匹配"
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 检查端口
echo ""
echo "2. 检查端口..."
if ! netstat -tlnp 2>/dev/null | grep -q ":80 " || ! ss -tlnp 2>/dev/null | grep -q ":80 "; then
    echo "⚠️  警告: 80端口未监听，请确保Nginx正在运行"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   ✓ 80端口正在监听"
fi

# 检查Nginx配置
echo ""
echo "3. 检查Nginx配置..."
if ! nginx -t 2>&1 | grep -q "syntax is ok"; then
    echo "❌ Nginx配置有误，请先修复"
    nginx -t
    exit 1
fi
echo "   ✓ Nginx配置正确"

# 获取证书
echo ""
echo "4. 获取Let's Encrypt证书..."
echo "   注意: 如果失败，请检查:"
echo "   1. 阿里云安全组是否开放80和443端口"
echo "   2. DNS解析是否正确"
echo ""

# 尝试使用nginx模式（推荐）
if certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect 2>&1 | tee /tmp/certbot.log; then
    echo ""
    echo "✅ 证书获取成功！"
    echo ""
    echo "5. 验证证书..."
    certbot certificates
    echo ""
    echo "6. 重载Nginx..."
    systemctl reload nginx
    echo ""
    echo "✅ 完成！现在可以通过 https://$DOMAIN 访问"
else
    echo ""
    echo "❌ 证书获取失败"
    echo ""
    echo "可能的原因:"
    echo "1. 阿里云安全组未开放80端口"
    echo "2. DNS解析不正确"
    echo "3. 域名无法从外网访问"
    echo ""
    echo "详细日志: /var/log/letsencrypt/letsencrypt.log"
    echo ""
    echo "如果安全组暂时无法配置，可以尝试standalone模式:"
    echo "  systemctl stop nginx"
    echo "  certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email $EMAIL"
    echo "  systemctl start nginx"
    echo "  然后手动配置HTTPS（参考文档）"
    exit 1
fi

# 检查自动续期
echo ""
echo "7. 检查证书自动续期配置..."
if systemctl is-enabled certbot.timer >/dev/null 2>&1; then
    echo "   ✓ certbot.timer 已启用"
    systemctl status certbot.timer --no-pager | head -5
else
    echo "   ⚠️  certbot.timer 未启用，正在启用..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
    echo "   ✓ 已启用"
fi

echo ""
echo "8. 测试证书续期（dry-run）..."
if certbot renew --dry-run 2>&1 | grep -q "The dry run was successful"; then
    echo "   ✓ 自动续期配置正常"
else
    echo "   ⚠️  自动续期测试失败，请检查配置"
fi

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
echo "证书位置: /etc/letsencrypt/live/$DOMAIN/"
echo "Nginx配置: /etc/nginx/conf.d/api-aifuture.conf"
echo "访问地址: https://$DOMAIN"
echo ""

