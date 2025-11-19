#!/bin/bash
# MySQL主从复制自动配置脚本
# 主库：root@app
# 从库：root@web

set -e

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# 服务器信息
APP_HOST="app"              # App服务器主机名或IP（主库）
WEB_HOST="web"              # Web服务器主机名或IP（从库）
APP_USER="root"             # App服务器SSH用户
WEB_USER="root"             # Web服务器SSH用户

# MySQL配置
MYSQL_ADMIN_USER="classifier"     # MySQL管理员用户名（需要有CREATE USER和REPLICATION SLAVE权限）
MYSQL_ADMIN_PASSWORD="Classifier@2024"     # MySQL管理员密码（如果为空，脚本会提示输入，也可以为空密码）
REPL_USER="repl_user"       # 复制用户名
REPL_PASSWORD=""            # 复制用户密码（如果为空，脚本会生成随机密码）
DATABASE_NAME="image_classifier"  # 需要同步的数据库名

# MySQL配置文件路径
MYSQL_CONF_APP="/etc/mysql/mysql.conf.d/mysqld.cnf"
MYSQL_CONF_WEB="/etc/mysql/mysql.conf.d/mysqld.cnf"
if [ ! -f "$MYSQL_CONF_APP" ]; then
    MYSQL_CONF_APP="/etc/my.cnf"
fi
if [ ! -f "$MYSQL_CONF_WEB" ]; then
    MYSQL_CONF_WEB="/etc/my.cnf"
fi

# ============================================
# 辅助函数
# ============================================

# 获取MySQL管理员密码
get_mysql_password() {
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        echo "提示：如果MySQL ${MYSQL_ADMIN_USER}用户没有密码，直接按回车"
        read -sp "请输入MySQL ${MYSQL_ADMIN_USER}用户密码（两个服务器使用相同密码）: " MYSQL_ADMIN_PASSWORD
        echo
    fi
}

# 生成复制用户密码
generate_repl_password() {
    if [ -z "$REPL_PASSWORD" ]; then
        REPL_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        echo "生成复制用户密码: ${REPL_PASSWORD}"
    fi
}

# 执行远程命令的辅助函数
run_remote_cmd() {
    local host=$1
    local need_ssh=$2
    local cmd=$3
    
    if [ "$need_ssh" = "false" ]; then
        # 本地执行
        eval "$cmd"
    else
        # 远程执行
        ssh ${APP_USER}@${host} "$cmd"
    fi
}

# 获取App服务器IP
get_app_ip() {
    if [ "$NEED_SSH_APP" = "false" ]; then
        # 本地获取IP
        APP_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    else
        # 远程获取IP
        APP_IP=$(ssh ${APP_USER}@${APP_HOST} "hostname -I | awk '{print \$1}'" 2>/dev/null || echo "")
    fi
    
    if [ -z "$APP_IP" ]; then
        read -p "请输入App服务器IP地址: " APP_IP
    fi
    echo "$APP_IP"
}

# ============================================
# 主程序
# ============================================

echo "=========================================="
echo "MySQL主从复制自动配置脚本"
echo "=========================================="
echo "主库服务器: ${APP_USER}@${APP_HOST}"
echo "从库服务器: ${WEB_USER}@${WEB_HOST}"
echo "=========================================="
echo ""

# 检查SSH连接
echo "检查SSH连接..."

# 获取当前主机名和IP（使用多种方法检测）
CURRENT_HOSTNAME=$(hostname 2>/dev/null || echo "")
CURRENT_HOSTNAME_SHORT=$(hostname -s 2>/dev/null || echo "$CURRENT_HOSTNAME" | cut -d. -f1)
CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip addr show 2>/dev/null | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}' | cut -d/ -f1 || echo "")

echo "当前主机信息: hostname=${CURRENT_HOSTNAME}, short=${CURRENT_HOSTNAME_SHORT}, ip=${CURRENT_IP}"

# 检查是否需要SSH到App服务器
NEED_SSH_APP=true
APP_HOST_ORIGINAL="$APP_HOST"
if [ "$CURRENT_HOSTNAME" = "$APP_HOST" ] || [ "$CURRENT_HOSTNAME_SHORT" = "$APP_HOST" ] || [ "$CURRENT_HOSTNAME" = "app" ] || [ "$CURRENT_HOSTNAME_SHORT" = "app" ]; then
    echo "ℹ️  检测到当前已在App服务器上，跳过SSH连接检查"
    NEED_SSH_APP=false
    APP_HOST="localhost"
else
    # 尝试SSH连接，如果失败则检查是否是localhost的情况
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${APP_USER}@${APP_HOST} "echo 'App服务器连接成功'" &>/dev/null 2>&1; then
        # 如果APP_HOST是"app"，尝试使用IP地址
        if [ "$APP_HOST" = "app" ]; then
            echo "⚠️  无法通过主机名连接，请手动输入App服务器IP地址"
            read -p "请输入App服务器IP地址: " APP_HOST_IP
            if [ -n "$APP_HOST_IP" ]; then
                APP_HOST="$APP_HOST_IP"
                if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${APP_USER}@${APP_HOST} "echo 'App服务器连接成功'" &>/dev/null 2>&1; then
                    echo "✅ App服务器连接成功（使用IP: ${APP_HOST}）"
                else
                    echo "❌ 错误：无法连接到App服务器 ${APP_USER}@${APP_HOST}"
                    exit 1
                fi
            else
                echo "❌ 错误：无法连接到App服务器"
                exit 1
            fi
        else
            echo "❌ 错误：无法连接到App服务器 ${APP_USER}@${APP_HOST}"
            echo "提示：请确保可以从当前服务器SSH连接到App服务器"
            exit 1
        fi
    else
        echo "✅ App服务器连接成功"
    fi
fi

# 检查是否需要SSH到Web服务器
NEED_SSH_WEB=true
WEB_HOST_ORIGINAL="$WEB_HOST"
if [ "$CURRENT_HOSTNAME" = "$WEB_HOST" ] || [ "$CURRENT_HOSTNAME_SHORT" = "$WEB_HOST" ] || [ "$CURRENT_HOSTNAME" = "web" ] || [ "$CURRENT_HOSTNAME_SHORT" = "web" ]; then
    echo "ℹ️  检测到当前已在Web服务器上，跳过SSH连接检查"
    NEED_SSH_WEB=false
    WEB_HOST="localhost"
else
    # 尝试SSH连接
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${WEB_USER}@${WEB_HOST} "echo 'Web服务器连接成功'" &>/dev/null 2>&1; then
        # 如果WEB_HOST是"web"，尝试使用IP地址
        if [ "$WEB_HOST" = "web" ]; then
            echo "⚠️  无法通过主机名连接，请手动输入Web服务器IP地址"
            read -p "请输入Web服务器IP地址: " WEB_HOST_IP
            if [ -n "$WEB_HOST_IP" ]; then
                WEB_HOST="$WEB_HOST_IP"
                if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${WEB_USER}@${WEB_HOST} "echo 'Web服务器连接成功'" &>/dev/null 2>&1; then
                    echo "✅ Web服务器连接成功（使用IP: ${WEB_HOST}）"
                else
                    echo "❌ 错误：无法连接到Web服务器 ${WEB_USER}@${WEB_HOST}"
                    exit 1
                fi
            else
                echo "❌ 错误：无法连接到Web服务器"
                exit 1
            fi
        else
            echo "❌ 错误：无法连接到Web服务器 ${WEB_USER}@${WEB_HOST}"
            echo "提示：请确保可以从当前服务器SSH连接到Web服务器"
            exit 1
        fi
    else
        echo "✅ Web服务器连接成功"
    fi
fi
echo ""

# 获取MySQL密码
get_mysql_password

# 测试MySQL连接（在主库）
echo "测试MySQL连接..."
if [ "$NEED_SSH_APP" = "false" ]; then
    # 本地测试
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        if ! mysql -u "${MYSQL_ADMIN_USER}" -e "SELECT 1;" &>/dev/null; then
            echo "❌ 错误：无法使用空密码连接MySQL"
            echo "提示："
            echo "  1. 如果MySQL ${MYSQL_ADMIN_USER}用户有密码，请重新运行脚本并输入密码"
            echo "  2. 如果使用socket认证，可以尝试: sudo mysql"
            echo "  3. 或者创建一个新的MySQL管理员用户"
            exit 1
        fi
        MYSQL_CMD="mysql -u ${MYSQL_ADMIN_USER}"
    else
        if ! mysql -u "${MYSQL_ADMIN_USER}" -p"${MYSQL_ADMIN_PASSWORD}" -e "SELECT 1;" &>/dev/null; then
            echo "❌ 错误：MySQL ${MYSQL_ADMIN_USER}用户密码不正确"
            echo "提示：请检查密码是否正确，或尝试使用空密码（直接按回车）"
            exit 1
        fi
        MYSQL_CMD="mysql -u ${MYSQL_ADMIN_USER} -p${MYSQL_ADMIN_PASSWORD}"
    fi
else
    # 远程测试
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        if ! ssh ${APP_USER}@${APP_HOST} "mysql -u ${MYSQL_ADMIN_USER} -e 'SELECT 1;'" &>/dev/null; then
            echo "❌ 错误：无法使用空密码连接MySQL"
            echo "提示：请检查MySQL ${MYSQL_ADMIN_USER}用户是否有密码"
            exit 1
        fi
        MYSQL_CMD_REMOTE="mysql -u ${MYSQL_ADMIN_USER}"
    else
        if ! ssh ${APP_USER}@${APP_HOST} "mysql -u ${MYSQL_ADMIN_USER} -p'${MYSQL_ADMIN_PASSWORD}' -e 'SELECT 1;'" &>/dev/null; then
            echo "❌ 错误：MySQL ${MYSQL_ADMIN_USER}用户密码不正确"
            echo "提示：请检查密码是否正确"
            exit 1
        fi
        MYSQL_CMD_REMOTE="mysql -u ${MYSQL_ADMIN_USER} -p'${MYSQL_ADMIN_PASSWORD}'"
    fi
fi
echo "✅ MySQL连接测试成功"
echo ""

# 生成复制用户密码
generate_repl_password

# 获取App服务器IP
APP_IP=$(get_app_ip)
echo "App服务器IP: ${APP_IP}"
echo ""

# ============================================
# 步骤1：配置主库（App服务器）
# ============================================

echo "=========================================="
echo "步骤1：配置主库（App服务器）"
echo "=========================================="


# 上传并执行主库配置脚本
echo "在App服务器上配置主库..."
if [ "$NEED_SSH_APP" = "false" ]; then
    # 本地执行
    (
    set -e
    MYSQL_CONF="$MYSQL_CONF_APP"

    echo "配置MySQL主服务器..."

    # 备份配置文件
    if [ -f "$MYSQL_CONF" ]; then
        cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # 配置server-id
    if grep -q "^server-id" "$MYSQL_CONF" 2>/dev/null; then
        sed -i 's/^server-id.*/server-id = 1/' "$MYSQL_CONF"
    else
        echo "" >> "$MYSQL_CONF"
        echo "# MySQL主从复制配置 - 主服务器" >> "$MYSQL_CONF"
        echo "server-id = 1" >> "$MYSQL_CONF"
    fi

    # 配置log-bin
    if grep -q "^log-bin" "$MYSQL_CONF" 2>/dev/null; then
        sed -i 's|^log-bin.*|log-bin = mysql-bin|' "$MYSQL_CONF"
    else
        echo "log-bin = mysql-bin" >> "$MYSQL_CONF"
    fi

    # 添加其他配置
    if ! grep -q "^binlog_format" "$MYSQL_CONF" 2>/dev/null; then
        echo "binlog_format = ROW" >> "$MYSQL_CONF"
    fi

    if [ -n "$DATABASE_NAME" ] && ! grep -q "^binlog-do-db" "$MYSQL_CONF" 2>/dev/null; then
        echo "binlog-do-db = ${DATABASE_NAME}" >> "$MYSQL_CONF"
    fi

    if ! grep -q "^expire_logs_days" "$MYSQL_CONF" 2>/dev/null; then
        echo "expire_logs_days = 7" >> "$MYSQL_CONF"
    fi

    # 重启MySQL
    systemctl restart mysql 2>/dev/null || systemctl restart mysqld 2>/dev/null
    sleep 3

    # 创建复制用户
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        mysql -u "${MYSQL_ADMIN_USER}" <<SQL
DROP USER IF EXISTS '${REPL_USER}'@'%';
CREATE USER '${REPL_USER}'@'%' IDENTIFIED BY '${REPL_PASSWORD}';
GRANT REPLICATION SLAVE ON *.* TO '${REPL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
    else
        mysql -u "${MYSQL_ADMIN_USER}" -p"${MYSQL_ADMIN_PASSWORD}" <<SQL
DROP USER IF EXISTS '${REPL_USER}'@'%';
CREATE USER '${REPL_USER}'@'%' IDENTIFIED BY '${REPL_PASSWORD}';
GRANT REPLICATION SLAVE ON *.* TO '${REPL_USER}'@'%';
FLUSH PRIVILEGES;
SQL
    fi

    echo "主库配置完成"
    )
else
    # 远程执行
    ssh ${APP_USER}@${APP_HOST} bash <<MASTER_SCRIPT_EOF
set -e
MYSQL_ADMIN_USER="$MYSQL_ADMIN_USER"
MYSQL_ADMIN_PASSWORD="$MYSQL_ADMIN_PASSWORD"
REPL_USER="$REPL_USER"
REPL_PASSWORD="$REPL_PASSWORD"
DATABASE_NAME="$DATABASE_NAME"
MYSQL_CONF="$MYSQL_CONF_APP"

echo "配置MySQL主服务器..."

# 备份配置文件
if [ -f "\$MYSQL_CONF" ]; then
    cp "\$MYSQL_CONF" "\${MYSQL_CONF}.backup.\$(date +%Y%m%d_%H%M%S)"
fi

# 配置server-id
if grep -q "^server-id" "\$MYSQL_CONF" 2>/dev/null; then
    sed -i 's/^server-id.*/server-id = 1/' "\$MYSQL_CONF"
else
    echo "" >> "\$MYSQL_CONF"
    echo "# MySQL主从复制配置 - 主服务器" >> "\$MYSQL_CONF"
    echo "server-id = 1" >> "\$MYSQL_CONF"
fi

# 配置log-bin
if grep -q "^log-bin" "\$MYSQL_CONF" 2>/dev/null; then
    sed -i 's|^log-bin.*|log-bin = mysql-bin|' "\$MYSQL_CONF"
else
    echo "log-bin = mysql-bin" >> "\$MYSQL_CONF"
fi

# 添加其他配置
if ! grep -q "^binlog_format" "\$MYSQL_CONF" 2>/dev/null; then
    echo "binlog_format = ROW" >> "\$MYSQL_CONF"
fi

if [ -n "\$DATABASE_NAME" ] && ! grep -q "^binlog-do-db" "\$MYSQL_CONF" 2>/dev/null; then
    echo "binlog-do-db = \${DATABASE_NAME}" >> "\$MYSQL_CONF"
fi

if ! grep -q "^expire_logs_days" "\$MYSQL_CONF" 2>/dev/null; then
    echo "expire_logs_days = 7" >> "\$MYSQL_CONF"
fi

# 重启MySQL
systemctl restart mysql 2>/dev/null || systemctl restart mysqld 2>/dev/null
sleep 3

# 创建复制用户
if [ -z "\$MYSQL_ADMIN_PASSWORD" ]; then
    mysql -u "\${MYSQL_ADMIN_USER}" -e "DROP USER IF EXISTS '\${REPL_USER}'@'%';" 2>/dev/null || true
    mysql -u "\${MYSQL_ADMIN_USER}" -e "CREATE USER '\${REPL_USER}'@'%' IDENTIFIED BY '\${REPL_PASSWORD}';"
    mysql -u "\${MYSQL_ADMIN_USER}" -e "GRANT REPLICATION SLAVE ON *.* TO '\${REPL_USER}'@'%';"
    mysql -u "\${MYSQL_ADMIN_USER}" -e "FLUSH PRIVILEGES;"
else
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "DROP USER IF EXISTS '\${REPL_USER}'@'%';" 2>/dev/null || true
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "CREATE USER '\${REPL_USER}'@'%' IDENTIFIED BY '\${REPL_PASSWORD}';"
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "GRANT REPLICATION SLAVE ON *.* TO '\${REPL_USER}'@'%';"
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "FLUSH PRIVILEGES;"
fi

echo "主库配置完成"
MASTER_SCRIPT_EOF
fi

if [ $? -eq 0 ]; then
    echo "✅ 主库配置完成"
else
    echo "❌ 主库配置失败"
    exit 1
fi

# 获取主库状态
echo "获取主库状态..."
if [ "$NEED_SSH_APP" = "false" ]; then
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        MASTER_STATUS=$(mysql -u "${MYSQL_ADMIN_USER}" -e "SHOW MASTER STATUS\G" 2>/dev/null)
    else
        MASTER_STATUS=$(mysql -u "${MYSQL_ADMIN_USER}" -p"${MYSQL_ADMIN_PASSWORD}" -e "SHOW MASTER STATUS\G" 2>/dev/null)
    fi
else
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        MASTER_STATUS=$(ssh ${APP_USER}@${APP_HOST} "mysql -u ${MYSQL_ADMIN_USER} -e 'SHOW MASTER STATUS\G'" 2>/dev/null)
    else
        MASTER_STATUS=$(ssh ${APP_USER}@${APP_HOST} "mysql -u ${MYSQL_ADMIN_USER} -p'${MYSQL_ADMIN_PASSWORD}' -e 'SHOW MASTER STATUS\G'" 2>/dev/null)
    fi
fi
MASTER_LOG_FILE=$(echo "$MASTER_STATUS" | grep "File:" | awk '{print $2}')
MASTER_LOG_POS=$(echo "$MASTER_STATUS" | grep "Position:" | awk '{print $2}')

if [ -z "$MASTER_LOG_FILE" ] || [ -z "$MASTER_LOG_POS" ]; then
    echo "❌ 错误：无法获取主库状态"
    exit 1
fi

echo "主库日志文件: ${MASTER_LOG_FILE}"
echo "主库日志位置: ${MASTER_LOG_POS}"
echo ""

# ============================================
# 步骤2：配置从库（Web服务器）
# ============================================

echo "=========================================="
echo "步骤2：配置从库（Web服务器）"
echo "=========================================="


# 上传并执行从库配置脚本
echo "在Web服务器上配置从库..."
if [ "$NEED_SSH_WEB" = "false" ]; then
    # 本地执行
    (
    set -e
    MASTER_HOST="$APP_IP"
    MYSQL_CONF="$MYSQL_CONF_WEB"

    echo "配置MySQL从服务器..."

    # 备份配置文件
    if [ -f "$MYSQL_CONF" ]; then
        cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # 配置server-id
    if grep -q "^server-id" "$MYSQL_CONF" 2>/dev/null; then
        sed -i 's/^server-id.*/server-id = 2/' "$MYSQL_CONF"
    else
        echo "" >> "$MYSQL_CONF"
        echo "# MySQL主从复制配置 - 从服务器" >> "$MYSQL_CONF"
        echo "server-id = 2" >> "$MYSQL_CONF"
    fi

    # 添加从库配置
    if ! grep -q "^relay-log" "$MYSQL_CONF" 2>/dev/null; then
        echo "relay-log = mysql-relay-bin" >> "$MYSQL_CONF"
    fi

    if ! grep -q "^log-slave-updates" "$MYSQL_CONF" 2>/dev/null; then
        echo "log-slave-updates = 1" >> "$MYSQL_CONF"
    fi

    if ! grep -q "^read-only" "$MYSQL_CONF" 2>/dev/null; then
        echo "read-only = 1" >> "$MYSQL_CONF"
    fi

    if [ -n "$DATABASE_NAME" ] && ! grep -q "^replicate-do-db" "$MYSQL_CONF" 2>/dev/null; then
        echo "replicate-do-db = ${DATABASE_NAME}" >> "$MYSQL_CONF"
    fi

    # 重启MySQL
    systemctl restart mysql 2>/dev/null || systemctl restart mysqld 2>/dev/null
    sleep 3

    # 配置主从复制
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        mysql -u "${MYSQL_ADMIN_USER}" <<SQL
STOP SLAVE;
CHANGE MASTER TO
    MASTER_HOST='${MASTER_HOST}',
    MASTER_USER='${MASTER_USER}',
    MASTER_PASSWORD='${MASTER_PASSWORD}',
    MASTER_LOG_FILE='${MASTER_LOG_FILE}',
    MASTER_LOG_POS=${MASTER_LOG_POS};
START SLAVE;
SQL
    else
        mysql -u "${MYSQL_ADMIN_USER}" -p"${MYSQL_ADMIN_PASSWORD}" <<SQL
STOP SLAVE;
CHANGE MASTER TO
    MASTER_HOST='${MASTER_HOST}',
    MASTER_USER='${MASTER_USER}',
    MASTER_PASSWORD='${MASTER_PASSWORD}',
    MASTER_LOG_FILE='${MASTER_LOG_FILE}',
    MASTER_LOG_POS=${MASTER_LOG_POS};
START SLAVE;
SQL
    fi

    echo "从库配置完成"
    )
else
    # 远程执行
    ssh ${WEB_USER}@${WEB_HOST} bash <<SLAVE_SCRIPT_EOF
set -e
MYSQL_ADMIN_USER="$MYSQL_ADMIN_USER"
MYSQL_ADMIN_PASSWORD="$MYSQL_ADMIN_PASSWORD"
MASTER_HOST="$APP_IP"
MASTER_USER="$REPL_USER"
MASTER_PASSWORD="$REPL_PASSWORD"
MASTER_LOG_FILE="$MASTER_LOG_FILE"
MASTER_LOG_POS="$MASTER_LOG_POS"
DATABASE_NAME="$DATABASE_NAME"
MYSQL_CONF="$MYSQL_CONF_WEB"

echo "配置MySQL从服务器..."

# 备份配置文件
if [ -f "\$MYSQL_CONF" ]; then
    cp "\$MYSQL_CONF" "\${MYSQL_CONF}.backup.\$(date +%Y%m%d_%H%M%S)"
fi

# 配置server-id
if grep -q "^server-id" "\$MYSQL_CONF" 2>/dev/null; then
    sed -i 's/^server-id.*/server-id = 2/' "\$MYSQL_CONF"
else
    echo "" >> "\$MYSQL_CONF"
    echo "# MySQL主从复制配置 - 从服务器" >> "\$MYSQL_CONF"
    echo "server-id = 2" >> "\$MYSQL_CONF"
fi

# 添加从库配置
if ! grep -q "^relay-log" "\$MYSQL_CONF" 2>/dev/null; then
    echo "relay-log = mysql-relay-bin" >> "\$MYSQL_CONF"
fi

if ! grep -q "^log-slave-updates" "\$MYSQL_CONF" 2>/dev/null; then
    echo "log-slave-updates = 1" >> "\$MYSQL_CONF"
fi

if ! grep -q "^read-only" "\$MYSQL_CONF" 2>/dev/null; then
    echo "read-only = 1" >> "\$MYSQL_CONF"
fi

if [ -n "\$DATABASE_NAME" ] && ! grep -q "^replicate-do-db" "\$MYSQL_CONF" 2>/dev/null; then
    echo "replicate-do-db = \${DATABASE_NAME}" >> "\$MYSQL_CONF"
fi

# 重启MySQL
systemctl restart mysql 2>/dev/null || systemctl restart mysqld 2>/dev/null
sleep 3

# 配置主从复制
if [ -z "\$MYSQL_ADMIN_PASSWORD" ]; then
    mysql -u "\${MYSQL_ADMIN_USER}" -e "STOP SLAVE;" 2>/dev/null || true
    mysql -u "\${MYSQL_ADMIN_USER}" -e "CHANGE MASTER TO MASTER_HOST='\${MASTER_HOST}', MASTER_USER='\${MASTER_USER}', MASTER_PASSWORD='\${MASTER_PASSWORD}', MASTER_LOG_FILE='\${MASTER_LOG_FILE}', MASTER_LOG_POS=\${MASTER_LOG_POS};"
    mysql -u "\${MYSQL_ADMIN_USER}" -e "START SLAVE;"
else
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "STOP SLAVE;" 2>/dev/null || true
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "CHANGE MASTER TO MASTER_HOST='\${MASTER_HOST}', MASTER_USER='\${MASTER_USER}', MASTER_PASSWORD='\${MASTER_PASSWORD}', MASTER_LOG_FILE='\${MASTER_LOG_FILE}', MASTER_LOG_POS=\${MASTER_LOG_POS};"
    mysql -u "\${MYSQL_ADMIN_USER}" -p"\${MYSQL_ADMIN_PASSWORD}" -e "START SLAVE;"
fi

echo "从库配置完成"
SLAVE_SCRIPT_EOF
fi

if [ $? -eq 0 ]; then
    echo "✅ 从库配置完成"
else
    echo "❌ 从库配置失败"
    exit 1
fi

# 等待同步启动
echo "等待从库同步启动..."
sleep 5

# 检查从库状态
echo ""
echo "=========================================="
echo "检查从库同步状态..."
echo "=========================================="

if [ "$NEED_SSH_WEB" = "false" ]; then
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        SLAVE_STATUS=$(mysql -u "${MYSQL_ADMIN_USER}" -e "SHOW SLAVE STATUS\G" 2>/dev/null)
    else
        SLAVE_STATUS=$(mysql -u "${MYSQL_ADMIN_USER}" -p"${MYSQL_ADMIN_PASSWORD}" -e "SHOW SLAVE STATUS\G" 2>/dev/null)
    fi
else
    if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
        SLAVE_STATUS=$(ssh ${WEB_USER}@${WEB_HOST} "mysql -u ${MYSQL_ADMIN_USER} -e 'SHOW SLAVE STATUS\G'" 2>/dev/null)
    else
        SLAVE_STATUS=$(ssh ${WEB_USER}@${WEB_HOST} "mysql -u ${MYSQL_ADMIN_USER} -p'${MYSQL_ADMIN_PASSWORD}' -e 'SHOW SLAVE STATUS\G'" 2>/dev/null)
    fi
fi
IO_RUNNING=$(echo "$SLAVE_STATUS" | grep "Slave_IO_Running:" | awk '{print $2}')
SQL_RUNNING=$(echo "$SLAVE_STATUS" | grep "Slave_SQL_Running:" | awk '{print $2}')
SECONDS_BEHIND=$(echo "$SLAVE_STATUS" | grep "Seconds_Behind_Master:" | awk '{print $2}')

echo "IO线程运行: ${IO_RUNNING}"
echo "SQL线程运行: ${SQL_RUNNING}"
echo "延迟时间: ${SECONDS_BEHIND} 秒"
echo ""

if [ "$IO_RUNNING" = "Yes" ] && [ "$SQL_RUNNING" = "Yes" ]; then
    echo "=========================================="
    echo "✅ 主从复制配置成功！"
    echo "=========================================="
    echo ""
    echo "配置信息："
    echo "  主库: ${APP_USER}@${APP_HOST} (${APP_IP})"
    echo "  从库: ${WEB_USER}@${WEB_HOST}"
    echo "  复制用户: ${REPL_USER}"
    echo "  复制密码: ${REPL_PASSWORD}"
    echo "  数据库: ${DATABASE_NAME}"
    echo ""
    echo "主从同步已启动，数据将自动从主库同步到从库"
else
    echo "=========================================="
    echo "⚠️  警告：主从同步可能存在问题"
    echo "=========================================="
    echo ""
    echo "请检查："
    echo "  1. 主库状态是否正常"
    echo "  2. 网络连接是否正常"
    echo "  3. 防火墙是否允许3306端口"
    echo "  4. MySQL错误日志"
    echo ""
    echo "查看从库详细状态："
    if [ "$NEED_SSH_WEB" = "false" ]; then
        if [ -z "$MYSQL_ADMIN_PASSWORD" ]; then
            echo "  mysql -u ${MYSQL_ADMIN_USER} -e 'SHOW SLAVE STATUS\\G'"
        else
            echo "  mysql -u ${MYSQL_ADMIN_USER} -p -e 'SHOW SLAVE STATUS\\G'"
        fi
    else
        echo "  ssh ${WEB_USER}@${WEB_HOST} \"mysql -u ${MYSQL_ADMIN_USER} -p -e 'SHOW SLAVE STATUS\\G'\""
    fi
fi
