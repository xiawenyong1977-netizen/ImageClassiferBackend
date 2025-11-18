#!/bin/bash
# MySQL从服务器配置脚本（在App服务器上执行）

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# 主服务器信息
MASTER_HOST=""           # Web服务器IP或主机名（必填）
MASTER_USER="repl_user" # 复制用户名
MASTER_PASSWORD=""       # 复制用户密码（必填）
MASTER_LOG_FILE=""       # 主服务器日志文件（必填，如：mysql-bin.000001）
MASTER_LOG_POS=""        # 主服务器日志位置（必填，如：154）

# MySQL配置
MYSQL_ROOT_PASSWORD=""   # MySQL root密码（如果为空，脚本会提示输入）
DATABASE_NAME="image_classifier"  # 需要同步的数据库名

# MySQL配置文件路径
MYSQL_CONF="/etc/mysql/mysql.conf.d/mysqld.cnf"
if [ ! -f "$MYSQL_CONF" ]; then
    MYSQL_CONF="/etc/my.cnf"
fi

# ============================================
# 脚本执行
# ============================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "MySQL从服务器配置脚本"
echo "=========================================="

# 检查必需参数
if [ -z "$MASTER_HOST" ] || [ -z "$MASTER_PASSWORD" ] || [ -z "$MASTER_LOG_FILE" ] || [ -z "$MASTER_LOG_POS" ]; then
    echo "❌ 错误：缺少必需参数"
    echo ""
    echo "请设置以下变量："
    echo "  MASTER_HOST: Web服务器IP或主机名"
    echo "  MASTER_PASSWORD: 复制用户密码"
    echo "  MASTER_LOG_FILE: 主服务器日志文件（从主服务器SHOW MASTER STATUS获取）"
    echo "  MASTER_LOG_POS: 主服务器日志位置（从主服务器SHOW MASTER STATUS获取）"
    echo ""
    echo "或者编辑脚本文件，在配置区域设置这些变量"
    exit 1
fi

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

# 测试主服务器连接
echo "测试主服务器连接..."
if ! mysql -h "${MASTER_HOST}" -u "${MASTER_USER}" -p"${MASTER_PASSWORD}" -e "SELECT 1;" &> /dev/null; then
    echo "❌ 错误：无法连接到主服务器"
    echo "请检查："
    echo "  1. 主服务器IP是否正确: ${MASTER_HOST}"
    echo "  2. 复制用户密码是否正确"
    echo "  3. 主服务器MySQL端口是否开放（默认3306）"
    echo "  4. 防火墙规则是否允许连接"
    exit 1
fi
echo "✅ 主服务器连接成功"

# 备份MySQL配置文件
if [ -f "$MYSQL_CONF" ]; then
    echo "备份MySQL配置文件..."
    cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 配置文件已备份"
fi

# 配置MySQL从服务器
echo "配置MySQL从服务器..."

# 检查是否已配置server-id
if grep -q "^server-id" "$MYSQL_CONF" 2>/dev/null; then
    echo "⚠️  检测到已存在server-id配置，将更新为2"
    sed -i 's/^server-id.*/server-id = 2/' "$MYSQL_CONF"
else
    echo "添加server-id配置..."
    echo "" >> "$MYSQL_CONF"
    echo "# MySQL主从复制配置 - 从服务器" >> "$MYSQL_CONF"
    echo "server-id = 2" >> "$MYSQL_CONF"
fi

# 添加relay-log配置
if ! grep -q "^relay-log" "$MYSQL_CONF" 2>/dev/null; then
    echo "relay-log = mysql-relay-bin" >> "$MYSQL_CONF"
fi

# 添加log-slave-updates
if ! grep -q "^log-slave-updates" "$MYSQL_CONF" 2>/dev/null; then
    echo "log-slave-updates = 1" >> "$MYSQL_CONF"
fi

# 添加read-only（从服务器建议设置为只读）
if ! grep -q "^read-only" "$MYSQL_CONF" 2>/dev/null; then
    echo "read-only = 1" >> "$MYSQL_CONF"
fi

# 添加replicate-do-db（如果需要）
if [ -n "$DATABASE_NAME" ] && ! grep -q "^replicate-do-db" "$MYSQL_CONF" 2>/dev/null; then
    echo "replicate-do-db = ${DATABASE_NAME}" >> "$MYSQL_CONF"
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

# 配置主从复制
echo "配置主从复制..."
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
-- 停止从服务器
STOP SLAVE;

-- 配置主服务器信息
CHANGE MASTER TO
    MASTER_HOST='${MASTER_HOST}',
    MASTER_USER='${MASTER_USER}',
    MASTER_PASSWORD='${MASTER_PASSWORD}',
    MASTER_LOG_FILE='${MASTER_LOG_FILE}',
    MASTER_LOG_POS=${MASTER_LOG_POS};

-- 启动从服务器
START SLAVE;
EOF

if [ $? -eq 0 ]; then
    echo "✅ 主从复制配置成功"
else
    echo "❌ 错误：主从复制配置失败"
    exit 1
fi

# 等待几秒让从服务器启动
sleep 3

# 检查从服务器状态
echo ""
echo "=========================================="
echo "检查从服务器状态..."
echo "=========================================="
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW SLAVE STATUS\G" | grep -E "Slave_IO_Running|Slave_SQL_Running|Seconds_Behind_Master|Last_Error"

# 获取详细状态
IO_RUNNING=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW SLAVE STATUS\G" 2>/dev/null | grep "Slave_IO_Running:" | awk '{print $2}')
SQL_RUNNING=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW SLAVE STATUS\G" 2>/dev/null | grep "Slave_SQL_Running:" | awk '{print $2}')
SECONDS_BEHIND=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW SLAVE STATUS\G" 2>/dev/null | grep "Seconds_Behind_Master:" | awk '{print $2}')

echo ""
echo "=========================================="
if [ "$IO_RUNNING" = "Yes" ] && [ "$SQL_RUNNING" = "Yes" ]; then
    echo "✅ 主从同步配置成功！"
    echo ""
    echo "状态信息："
    echo "  IO线程运行: ${IO_RUNNING}"
    echo "  SQL线程运行: ${SQL_RUNNING}"
    echo "  延迟时间: ${SECONDS_BEHIND} 秒"
    echo ""
    echo "主从同步已启动，数据将自动从主服务器同步到从服务器"
else
    echo "⚠️  警告：主从同步可能存在问题"
    echo ""
    echo "状态信息："
    echo "  IO线程运行: ${IO_RUNNING}"
    echo "  SQL线程运行: ${SQL_RUNNING}"
    echo ""
    echo "请检查："
    echo "  1. 主服务器状态是否正常"
    echo "  2. 网络连接是否正常"
    echo "  3. 复制用户权限是否正确"
    echo "  4. MySQL错误日志: tail -f /var/log/mysql/error.log"
fi
echo "=========================================="

