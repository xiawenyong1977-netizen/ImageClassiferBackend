#!/bin/bash
# Images目录同步脚本（在App服务器上执行）
# 从Web服务器同步images目录到App服务器

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# Web服务器信息
WEB_SERVER="web_server_ip_or_hostname"  # 替换为Web服务器IP或主机名
WEB_IMAGES_PATH="/path/to/web/images"   # Web服务器上的images目录路径

# App服务器信息
APP_IMAGES_PATH="/path/to/web/images"   # App服务器上的images目录路径

# 日志配置
LOG_FILE="/var/log/sync-images.log"
LOG_DIR=$(dirname $LOG_FILE)

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

# 检查SSH连接
log_info "检查SSH连接到Web服务器..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes root@${WEB_SERVER} exit 2>/dev/null; then
    log_error "无法连接到Web服务器: ${WEB_SERVER}"
    log_error "请检查："
    log_error "  1. SSH免密登录是否已配置"
    log_error "  2. Web服务器是否可访问"
    log_error "  3. 网络连接是否正常"
    exit 1
fi
log_info "SSH连接正常"

# 检查源目录是否存在
log_info "检查Web服务器源目录..."
if ! ssh root@${WEB_SERVER} "[ -d ${WEB_IMAGES_PATH} ]"; then
    log_error "Web服务器上不存在目录: ${WEB_IMAGES_PATH}"
    exit 1
fi
log_info "源目录存在: ${WEB_IMAGES_PATH}"

# 创建目标目录（如果不存在）
if [ ! -d "$APP_IMAGES_PATH" ]; then
    log_info "创建目标目录: ${APP_IMAGES_PATH}"
    mkdir -p "$APP_IMAGES_PATH"
fi

# 执行同步
log_info "========================================="
log_info "开始同步images目录..."
log_info "源: root@${WEB_SERVER}:${WEB_IMAGES_PATH}/"
log_info "目标: ${APP_IMAGES_PATH}/"
log_info "========================================="

# rsync同步命令
# 参数说明：
#   -a: 归档模式，保持文件属性
#   -v: 详细输出
#   -z: 压缩传输
#   -h: 人类可读的文件大小
#   --delete: 删除目标目录中源目录不存在的文件
#   --progress: 显示进度
#   --exclude: 排除特定文件或目录
rsync -avzh --delete --progress \
    --exclude='*.tmp' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    root@${WEB_SERVER}:${WEB_IMAGES_PATH}/ \
    ${APP_IMAGES_PATH}/ \
    2>&1 | tee -a $LOG_FILE

# 检查同步结果
SYNC_EXIT_CODE=${PIPESTATUS[0]}

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    log_info "========================================="
    log_info "✅ 同步成功完成"
    log_info "========================================="
    
    # 统计同步的文件数量
    FILE_COUNT=$(find ${APP_IMAGES_PATH} -type f | wc -l)
    DIR_COUNT=$(find ${APP_IMAGES_PATH} -type d | wc -l)
    TOTAL_SIZE=$(du -sh ${APP_IMAGES_PATH} | awk '{print $1}')
    
    log_info "统计信息："
    log_info "  文件数量: ${FILE_COUNT}"
    log_info "  目录数量: ${DIR_COUNT}"
    log_info "  总大小: ${TOTAL_SIZE}"
    
    exit 0
else
    log_error "========================================="
    log_error "❌ 同步失败，错误代码: ${SYNC_EXIT_CODE}"
    log_error "========================================="
    exit 1
fi

