#!/bin/bash
# MySQL主服务器配置脚本（在Web服务器上执行）

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# MySQL配置
MYSQL_ROOT_PASSWORD=""  # MySQL root密码（如果为空，脚本会提示输入）
REPL_USER="repl_user"  # 复制用户名
REPL_PASSWORD=""        # 复制用户密码（如果为空，脚本会生成随机密码）
DATABASE_NAME="image_classifier"  # 需要同步的数据库名

# MySQL配置文件路径（根据系统不同可能不同）
MYSQL_CONF="/etc/mysql/mysql.conf.d/mysqld.cnf"
# 如果上面的路径不存在，尝试其他路径
if [ ! -f "$MYSQL_CONF" ]; then
    MYSQL_CONF="/etc/my.cnf"
fi

# ============================================
# 脚本执行
# ============================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "MySQL主服务器配置脚本"
echo "=========================================="

# 检查MySQL是否安装
if ! command -v mysql &> /dev/null; then
    echo "❌ 错误：未找到MySQL，请先安装MySQL"
    exit 1
fi

# 检查MySQL服务是否运行
if ! systemctl is-active --quiet mysql && ! systemctl is-active --quiet mysqld; then
    echo "❌ 错误：MySQL服务未运行"
    exit 1
fi

echo "✅ MySQL服务运行正常"

# 获取MySQL root密码
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    read -sp "请输入MySQL root密码: " MYSQL_ROOT_PASSWORD
    echo
fi

# 测试MySQL连接
echo "测试MySQL连接..."
if ! mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1;" &> /dev/null; then
    echo "❌ 错误：MySQL root密码不正确或无法连接"
    exit 1
fi
echo "✅ MySQL连接成功"

# 生成复制用户密码（如果未指定）
if [ -z "$REPL_PASSWORD" ]; then
    REPL_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo "生成复制用户密码: ${REPL_PASSWORD}"
    echo "⚠️  请妥善保存此密码，配置从服务器时需要用到"
fi

# 备份MySQL配置文件
if [ -f "$MYSQL_CONF" ]; then
    echo "备份MySQL配置文件..."
    cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 配置文件已备份"
fi

# 配置MySQL主服务器
echo "配置MySQL主服务器..."

# 检查是否已配置server-id
if grep -q "^server-id" "$MYSQL_CONF" 2>/dev/null; then
    echo "⚠️  检测到已存在server-id配置，将更新"
    sed -i 's/^server-id.*/server-id = 1/' "$MYSQL_CONF"
else
    echo "添加server-id配置..."
    echo "" >> "$MYSQL_CONF"
    echo "# MySQL主从复制配置 - 主服务器" >> "$MYSQL_CONF"
    echo "server-id = 1" >> "$MYSQL_CONF"
fi

# 检查是否已配置log-bin
if grep -q "^log-bin" "$MYSQL_CONF" 2>/dev/null; then
    echo "⚠️  检测到已存在log-bin配置，将更新"
    sed -i 's|^log-bin.*|log-bin = mysql-bin|' "$MYSQL_CONF"
else
    echo "添加log-bin配置..."
    echo "log-bin = mysql-bin" >> "$MYSQL_CONF"
fi

# 添加binlog_format
if ! grep -q "^binlog_format" "$MYSQL_CONF" 2>/dev/null; then
    echo "binlog_format = ROW" >> "$MYSQL_CONF"
fi

# 添加binlog-do-db（如果需要）
if [ -n "$DATABASE_NAME" ] && ! grep -q "^binlog-do-db" "$MYSQL_CONF" 2>/dev/null; then
    echo "binlog-do-db = ${DATABASE_NAME}" >> "$MYSQL_CONF"
fi

# 添加其他配置
if ! grep -q "^expire_logs_days" "$MYSQL_CONF" 2>/dev/null; then
    echo "expire_logs_days = 7" >> "$MYSQL_CONF"
fi

if ! grep -q "^max_binlog_size" "$MYSQL_CONF" 2>/dev/null; then
    echo "max_binlog_size = 100M" >> "$MYSQL_CONF"
fi

echo "✅ MySQL配置文件已更新"

# 重启MySQL服务
echo "重启MySQL服务..."
if systemctl restart mysql 2>/dev/null || systemctl restart mysqld 2>/dev/null; then
    echo "✅ MySQL服务已重启"
    sleep 3
else
    echo "❌ 错误：MySQL服务重启失败"
    exit 1
fi

# 创建复制用户
echo "创建复制用户..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
-- 删除已存在的复制用户（如果存在）
DROP USER IF EXISTS '${REPL_USER}'@'%';

-- 创建复制用户
CREATE USER '${REPL_USER}'@'%' IDENTIFIED BY '${REPL_PASSWORD}';

-- 授予复制权限
GRANT REPLICATION SLAVE ON *.* TO '${REPL_USER}'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示主服务器状态
SHOW MASTER STATUS;
EOF

if [ $? -eq 0 ]; then
    echo "✅ 复制用户创建成功"
else
    echo "❌ 错误：复制用户创建失败"
    exit 1
fi

# 获取主服务器状态
echo ""
echo "=========================================="
echo "主服务器配置完成！"
echo "=========================================="
echo ""
echo "📋 重要信息（请保存，配置从服务器时需要）："
echo ""
echo "复制用户信息："
echo "  用户名: ${REPL_USER}"
echo "  密码: ${REPL_PASSWORD}"
echo ""
echo "主服务器状态："
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW MASTER STATUS\G" | grep -E "File|Position"
echo ""
echo "=========================================="
echo "下一步："
echo "1. 在App服务器上运行 setup-mysql-slave.sh"
echo "2. 使用上面的信息配置从服务器"
echo "=========================================="

