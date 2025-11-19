#!/bin/bash
# MySQL主从复制防火墙配置脚本
# 用于在主库（App服务器）开放3306端口

set -e

# ============================================
# 配置区域
# ============================================

APP_HOST="app"              # App服务器主机名或IP（主库）
APP_USER="root"             # App服务器SSH用户
MYSQL_PORT="3306"           # MySQL端口

# ============================================
# 主程序
# ============================================

echo "=========================================="
echo "MySQL主从复制防火墙配置脚本"
echo "=========================================="
echo "目标服务器: ${APP_USER}@${APP_HOST}"
echo "需要开放的端口: ${MYSQL_PORT}"
echo "=========================================="
echo ""

# 检查SSH连接
echo "检查SSH连接..."
if ! ssh -o ConnectTimeout=5 ${APP_USER}@${APP_HOST} "echo '连接成功'" &>/dev/null; then
    echo "❌ 错误：无法连接到服务器 ${APP_USER}@${APP_HOST}"
    exit 1
fi
echo "✅ SSH连接成功"
echo ""

# 检测防火墙类型并配置
echo "检测防火墙类型..."
FIREWALL_TYPE=$(ssh ${APP_USER}@${APP_HOST} "
    if command -v firewall-cmd &> /dev/null; then
        echo 'firewalld'
    elif command -v ufw &> /dev/null; then
        echo 'ufw'
    elif command -v iptables &> /dev/null; then
        echo 'iptables'
    else
        echo 'none'
    fi
")

echo "检测到防火墙类型: ${FIREWALL_TYPE}"
echo ""

# 配置防火墙
case "$FIREWALL_TYPE" in
    firewalld)
        echo "使用 firewalld 配置防火墙..."
        ssh ${APP_USER}@${APP_HOST} bash <<EOF
set -e
# 检查端口是否已开放
if firewall-cmd --list-ports | grep -q "${MYSQL_PORT}/tcp"; then
    echo "⚠️  端口 ${MYSQL_PORT} 已经开放"
else
    echo "开放端口 ${MYSQL_PORT}..."
    firewall-cmd --permanent --add-port=${MYSQL_PORT}/tcp
    firewall-cmd --reload
    echo "✅ 端口 ${MYSQL_PORT} 已开放"
fi

# 显示当前开放的端口
echo ""
echo "当前开放的端口："
firewall-cmd --list-ports
EOF
        ;;
    ufw)
        echo "使用 ufw 配置防火墙..."
        ssh ${APP_USER}@${APP_HOST} bash <<EOF
set -e
# 检查端口是否已开放
if ufw status | grep -q "${MYSQL_PORT}"; then
    echo "⚠️  端口 ${MYSQL_PORT} 已经开放"
else
    echo "开放端口 ${MYSQL_PORT}..."
    ufw allow ${MYSQL_PORT}/tcp
    ufw reload
    echo "✅ 端口 ${MYSQL_PORT} 已开放"
fi

# 显示当前防火墙状态
echo ""
echo "当前防火墙状态："
ufw status | grep ${MYSQL_PORT}
EOF
        ;;
    iptables)
        echo "使用 iptables 配置防火墙..."
        ssh ${APP_USER}@${APP_HOST} bash <<EOF
set -e
# 检查规则是否已存在
if iptables -L -n | grep -q "dpt:${MYSQL_PORT}"; then
    echo "⚠️  端口 ${MYSQL_PORT} 的规则已存在"
else
    echo "添加 iptables 规则..."
    iptables -A INPUT -p tcp --dport ${MYSQL_PORT} -j ACCEPT
    
    # 尝试保存规则
    if command -v iptables-save &> /dev/null; then
        if [ -d /etc/iptables ]; then
            iptables-save > /etc/iptables/rules.v4
        elif [ -f /etc/sysconfig/iptables ]; then
            service iptables save 2>/dev/null || iptables-save > /etc/sysconfig/iptables
        fi
    fi
    
    echo "✅ 端口 ${MYSQL_PORT} 规则已添加"
fi

# 显示相关规则
echo ""
echo "当前 iptables 规则："
iptables -L -n | grep ${MYSQL_PORT}
EOF
        ;;
    none)
        echo "⚠️  警告：未检测到防火墙工具"
        echo "请手动配置防火墙，开放端口 ${MYSQL_PORT}"
        exit 1
        ;;
esac

# 检查MySQL是否监听外部连接
echo ""
echo "=========================================="
echo "检查MySQL监听配置"
echo "=========================================="

MYSQL_BIND=$(ssh ${APP_USER}@${APP_HOST} "netstat -tlnp 2>/dev/null | grep ${MYSQL_PORT} | awk '{print \$4}' | head -1")

if [ -z "$MYSQL_BIND" ]; then
    echo "⚠️  警告：未检测到MySQL监听端口 ${MYSQL_PORT}"
    echo "请检查MySQL服务是否运行"
else
    echo "MySQL监听地址: ${MYSQL_BIND}"
    
    if echo "$MYSQL_BIND" | grep -q "127.0.0.1"; then
        echo ""
        echo "⚠️  警告：MySQL只监听本地连接（127.0.0.1）"
        echo "需要修改MySQL配置以允许外部连接："
        echo ""
        echo "1. 编辑MySQL配置文件："
        echo "   vim /etc/mysql/mysql.conf.d/mysqld.cnf"
        echo "   或"
        echo "   vim /etc/my.cnf"
        echo ""
        echo "2. 找到并修改（或添加）："
        echo "   bind-address = 0.0.0.0"
        echo ""
        echo "3. 重启MySQL："
        echo "   systemctl restart mysql"
        echo "   或"
        echo "   systemctl restart mysqld"
    else
        echo "✅ MySQL已配置为监听外部连接"
    fi
fi

echo ""
echo "=========================================="
echo "防火墙配置完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 如果MySQL只监听本地连接，请按照上面的提示修改配置"
echo "2. 如果使用云服务器，请在云控制台配置安全组规则"
echo "3. 在从库测试连接："
echo "   ssh root@web \"nc -zv 主库IP ${MYSQL_PORT}\""
echo ""

