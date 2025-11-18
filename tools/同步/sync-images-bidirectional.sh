#!/bin/bash
# Images目录双向同步脚本
# 支持从Web服务器同步到App服务器，以及从App服务器同步回Web服务器

# ============================================
# 配置区域 - 请根据实际情况修改
# ============================================

# 服务器信息
WEB_SERVER="web_server_ip_or_hostname"  # Web服务器IP或主机名
APP_SERVER="app_server_ip_or_hostname"  # App服务器IP或主机名（如果在本机执行，可以留空）

# 目录路径
WEB_IMAGES_PATH="/path/to/web/images"   # Web服务器上的images目录路径
APP_IMAGES_PATH="/path/to/web/images"   # App服务器上的images目录路径

# 同步方向配置
# 可选值：
#   "web-to-app" - 只从Web同步到App
#   "app-to-web" - 只从App同步到Web
#   "bidirectional" - 双向同步（先Web→App，再App→Web）
SYNC_DIRECTION="bidirectional"

# 冲突处理策略
#   "web-wins" - Web服务器优先（Web→App时，Web覆盖App）
#   "app-wins" - App服务器优先（App→Web时，App覆盖Web）
#   "newer-wins" - 较新的文件优先（需要额外工具支持）
CONFLICT_RESOLUTION="web-wins"

# 日志配置
LOG_FILE="/var/log/sync-images-bidirectional.log"
LOG_DIR=$(dirname $LOG_FILE)

# 同步前备份（可选）
ENABLE_BACKUP=true
BACKUP_DIR="/var/backup/images"

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

# 检查SSH连接
check_ssh_connection() {
    local server=$1
    local server_name=$2
    
    log_info "检查SSH连接到${server_name}..."
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes root@${server} exit 2>/dev/null; then
        log_error "无法连接到${server_name}: ${server}"
        return 1
    fi
    log_info "SSH连接到${server_name}正常"
    return 0
}

# 备份目录
backup_directory() {
    local source_dir=$1
    local backup_name=$2
    
    if [ "$ENABLE_BACKUP" != "true" ]; then
        return 0
    fi
    
    log_info "备份目录: ${source_dir} -> ${backup_name}"
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$source_dir" ]; then
        local backup_path="${BACKUP_DIR}/${backup_name}.$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$backup_path" -C "$(dirname $source_dir)" "$(basename $source_dir)" 2>/dev/null
        if [ $? -eq 0 ]; then
            log_info "备份成功: ${backup_path}"
            # 删除7天前的备份
            find "$BACKUP_DIR" -name "${backup_name}.*.tar.gz" -mtime +7 -delete 2>/dev/null
        else
            log_warn "备份失败，继续执行同步"
        fi
    fi
}

# 执行rsync同步
sync_direction() {
    local source_server=$1
    local source_path=$2
    local target_server=$3
    local target_path=$4
    local direction_name=$5
    local delete_flag=$6
    
    log_info "========================================="
    log_info "开始同步: ${direction_name}"
    log_info "源: root@${source_server}:${source_path}/"
    log_info "目标: root@${target_server}:${target_path}/"
    log_info "========================================="
    
    # 检查源目录
    if [ "$source_server" = "localhost" ] || [ -z "$source_server" ]; then
        if [ ! -d "$source_path" ]; then
            log_error "源目录不存在: ${source_path}"
            return 1
        fi
    else
        if ! ssh root@${source_server} "[ -d ${source_path} ]"; then
            log_error "源服务器上不存在目录: ${source_path}"
            return 1
        fi
    fi
    
    # 创建目标目录
    if [ "$target_server" = "localhost" ] || [ -z "$target_server" ]; then
        mkdir -p "$target_path"
    else
        ssh root@${target_server} "mkdir -p ${target_path}"
    fi
    
    # 构建rsync命令
    local rsync_cmd="rsync -avzh --progress"
    
    # 添加删除标志
    if [ "$delete_flag" = "true" ]; then
        rsync_cmd="$rsync_cmd --delete"
    fi
    
    # 排除文件
    rsync_cmd="$rsync_cmd --exclude='*.tmp' --exclude='*.log' --exclude='.DS_Store' --exclude='Thumbs.db'"
    
    # 执行同步
    if [ "$source_server" = "localhost" ] || [ -z "$source_server" ]; then
        # 本地到远程
        if [ "$target_server" = "localhost" ] || [ -z "$target_server" ]; then
            # 本地到本地（不应该发生，但处理一下）
            $rsync_cmd "${source_path}/" "${target_path}/" 2>&1 | tee -a $LOG_FILE
        else
            # 本地到远程
            $rsync_cmd "${source_path}/" root@${target_server}:${target_path}/ 2>&1 | tee -a $LOG_FILE
        fi
    else
        # 远程到本地或远程
        if [ "$target_server" = "localhost" ] || [ -z "$target_server" ]; then
            # 远程到本地
            $rsync_cmd root@${source_server}:${source_path}/ "${target_path}/" 2>&1 | tee -a $LOG_FILE
        else
            # 远程到远程（通过本地中转）
            log_warn "远程到远程同步，使用本地中转"
            local temp_dir="/tmp/sync_temp_$$"
            mkdir -p "$temp_dir"
            rsync -avzh root@${source_server}:${source_path}/ "$temp_dir/" 2>&1 | tee -a $LOG_FILE
            if [ $? -eq 0 ]; then
                rsync -avzh "$temp_dir/" root@${target_server}:${target_path}/ 2>&1 | tee -a $LOG_FILE
                rm -rf "$temp_dir"
            fi
        fi
    fi
    
    local sync_exit_code=${PIPESTATUS[0]}
    
    if [ $sync_exit_code -eq 0 ]; then
        log_info "✅ ${direction_name} 同步成功"
        return 0
    else
        log_error "❌ ${direction_name} 同步失败，错误代码: ${sync_exit_code}"
        return 1
    fi
}

# 主函数
main() {
    log_info "========================================="
    log_info "Images目录双向同步开始"
    log_info "同步方向: ${SYNC_DIRECTION}"
    log_info "冲突处理: ${CONFLICT_RESOLUTION}"
    log_info "========================================="
    
    # 检查SSH连接
    if ! check_ssh_connection "$WEB_SERVER" "Web服务器"; then
        exit 1
    fi
    
    if [ -n "$APP_SERVER" ] && [ "$APP_SERVER" != "localhost" ]; then
        if ! check_ssh_connection "$APP_SERVER" "App服务器"; then
            exit 1
        fi
    fi
    
    # 根据同步方向执行
    case "$SYNC_DIRECTION" in
        "web-to-app")
            log_info "执行单向同步: Web → App"
            backup_directory "$APP_IMAGES_PATH" "app_images"
            sync_direction "$WEB_SERVER" "$WEB_IMAGES_PATH" "$APP_SERVER" "$APP_IMAGES_PATH" "Web→App" "true"
            ;;
            
        "app-to-web")
            log_info "执行单向同步: App → Web"
            backup_directory "$WEB_IMAGES_PATH" "web_images"
            sync_direction "$APP_SERVER" "$APP_IMAGES_PATH" "$WEB_SERVER" "$WEB_IMAGES_PATH" "App→Web" "true"
            ;;
            
        "bidirectional")
            log_info "执行双向同步"
            
            # 第一步：Web → App
            log_info "第一步：Web → App"
            backup_directory "$APP_IMAGES_PATH" "app_images"
            if sync_direction "$WEB_SERVER" "$WEB_IMAGES_PATH" "$APP_SERVER" "$APP_IMAGES_PATH" "Web→App" "true"; then
                log_info "Web→App 同步成功，等待5秒后执行App→Web同步..."
                sleep 5
                
                # 第二步：App → Web
                log_info "第二步：App → Web"
                backup_directory "$WEB_IMAGES_PATH" "web_images"
                
                # 根据冲突处理策略决定是否使用--delete
                local delete_flag="false"
                if [ "$CONFLICT_RESOLUTION" = "app-wins" ]; then
                    delete_flag="true"
                fi
                
                sync_direction "$APP_SERVER" "$APP_IMAGES_PATH" "$WEB_SERVER" "$WEB_IMAGES_PATH" "App→Web" "$delete_flag"
            else
                log_error "Web→App 同步失败，跳过App→Web同步"
                exit 1
            fi
            ;;
            
        *)
            log_error "未知的同步方向: ${SYNC_DIRECTION}"
            log_error "可选值: web-to-app, app-to-web, bidirectional"
            exit 1
            ;;
    esac
    
    log_info "========================================="
    log_info "同步完成"
    log_info "========================================="
}

# 执行主函数
main

