#!/bin/bash
# MySQL主从同步状态检查脚本（在App服务器上执行）

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# MySQL配置
MYSQL_ROOT_PASSWORD=""  # MySQL root密码（如果为空，脚本会提示输入）

# 日志配置
LOG_FILE="/var/log/mysql-replication-check.log"
LOG_DIR=$(dirname $LOG_FILE)

# 告警配置（可选）
ALERT_EMAIL=""  # 告警邮箱（如果为空则不发送邮件）
ALERT_THRESHOLD=60  # 延迟告警阈值（秒）

# ============================================
# 脚本执行
# ============================================

# 创建日志目录
mkdir -p $LOG_DIR

# 日志函数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1" | tee -a $LOG_FILE
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" | tee -a $LOG_FILE
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $1" | tee -a $LOG_FILE
}

# 获取MySQL root密码
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    # 尝试从环境变量或配置文件读取
    if [ -f ~/.my.cnf ]; then
        MYSQL_ROOT_PASSWORD=$(grep password ~/.my.cnf | awk '{print $3}' | head -1)
    fi
    
    # 如果还是为空，提示输入
    if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
        read -sp "请输入MySQL root密码: " MYSQL_ROOT_PASSWORD
        echo
    fi
fi

# 检查MySQL连接
if ! mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1;" &> /dev/null; then
    log_error "无法连接到MySQL"
    exit 1
fi

# 获取从服务器状态
STATUS=$(mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SHOW SLAVE STATUS\G" 2>/dev/null)

if [ -z "$STATUS" ]; then
    log_error "无法获取从服务器状态，可能未配置主从复制"
    exit 1
fi

# 解析状态信息
IO_RUNNING=$(echo "$STATUS" | grep "Slave_IO_Running:" | awk '{print $2}')
SQL_RUNNING=$(echo "$STATUS" | grep "Slave_SQL_Running:" | awk '{print $2}')
SECONDS_BEHIND=$(echo "$STATUS" | grep "Seconds_Behind_Master:" | awk '{print $2}')
LAST_ERROR=$(echo "$STATUS" | grep "Last_Error:" | cut -d: -f2- | sed 's/^[ \t]*//')
MASTER_HOST=$(echo "$STATUS" | grep "Master_Host:" | awk '{print $2}')
MASTER_LOG_FILE=$(echo "$STATUS" | grep "Master_Log_File:" | awk '{print $2}')
READ_MASTER_LOG_POS=$(echo "$STATUS" | grep "Read_Master_Log_Pos:" | awk '{print $2}')

# 检查状态
log_info "========================================="
log_info "检查主从同步状态..."
log_info "主服务器: ${MASTER_HOST}"
log_info "========================================="

# 检查IO线程
if [ "$IO_RUNNING" = "Yes" ]; then
    log_info "✅ IO线程运行正常"
else
    log_error "❌ IO线程未运行 (状态: ${IO_RUNNING})"
    if [ -n "$LAST_ERROR" ]; then
        log_error "最后错误: ${LAST_ERROR}"
    fi
fi

# 检查SQL线程
if [ "$SQL_RUNNING" = "Yes" ]; then
    log_info "✅ SQL线程运行正常"
else
    log_error "❌ SQL线程未运行 (状态: ${SQL_RUNNING})"
    if [ -n "$LAST_ERROR" ]; then
        log_error "最后错误: ${LAST_ERROR}"
    fi
fi

# 检查延迟
if [ "$SECONDS_BEHIND" = "NULL" ]; then
    log_warn "⚠️  无法获取延迟信息（可能正在初始化）"
elif [ "$SECONDS_BEHIND" -eq 0 ]; then
    log_info "✅ 无延迟，同步正常"
elif [ "$SECONDS_BEHIND" -lt "$ALERT_THRESHOLD" ]; then
    log_info "⚠️  延迟: ${SECONDS_BEHIND} 秒（正常范围）"
else
    log_warn "⚠️  延迟较大: ${SECONDS_BEHIND} 秒（超过阈值 ${ALERT_THRESHOLD} 秒）"
fi

# 显示详细信息
log_info "详细信息："
log_info "  主服务器日志文件: ${MASTER_LOG_FILE}"
log_info "  读取位置: ${READ_MASTER_LOG_POS}"

# 判断整体状态
if [ "$IO_RUNNING" = "Yes" ] && [ "$SQL_RUNNING" = "Yes" ]; then
    if [ "$SECONDS_BEHIND" != "NULL" ] && [ "$SECONDS_BEHIND" -lt "$ALERT_THRESHOLD" ]; then
        log_info "========================================="
        log_info "✅ 主从同步状态正常"
        log_info "========================================="
        exit 0
    else
        log_warn "========================================="
        log_warn "⚠️  主从同步运行中，但存在延迟"
        log_warn "========================================="
        exit 0
    fi
else
    log_error "========================================="
    log_error "❌ 主从同步异常！"
    log_error "========================================="
    
    # 发送告警邮件（如果配置了）
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "MySQL主从同步异常
IO线程: ${IO_RUNNING}
SQL线程: ${SQL_RUNNING}
延迟: ${SECONDS_BEHIND} 秒
错误: ${LAST_ERROR}

请检查MySQL主从同步状态。" | mail -s "MySQL Replication Alert" "$ALERT_EMAIL"
    fi
    
    exit 1
fi

