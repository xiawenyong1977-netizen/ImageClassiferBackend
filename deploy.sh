#!/bin/bash

# =====================================================
# 图片分类后端 - 快速部署脚本 (Linux/Mac)
# 使用 scp 同步代码到服务器
# 
# 部署策略：
# - 始终部署到 versions/debug 目录
# - current 符号链接指向 versions/debug
# - 适用于开发/测试环境的快速迭代
# 
# 注意：此脚本不支持版本管理和回滚
# 生产环境请使用 scripts/deploy-versioned.sh 或 CI/CD 自动部署
# 
# 使用方法：
#   ./deploy.sh                    # 交互式确认，全量部署
#   ./deploy.sh --incremental      # 增量部署（基于 git 检测变更文件）
#   ./deploy.sh --force --incremental # 增量部署，跳过确认
# 
# 增量部署说明：
# - 使用 git diff 检测变更的文件（需要项目是 git 仓库）
# - 只同步变更的文件和目录，加快部署速度
# - requirements.txt 等重要文件总是同步（即使未变更）
# - 如果不是 git 仓库，会自动回退到全量部署
# =====================================================

SERVER="root@web"
REMOTE_DIR="/opt/ICBackend"  # 与文档保持一致
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.10"  # 指定 Python 版本
INCREMENTAL=false
FORCE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --incremental|-i)
            INCREMENTAL=true
            shift
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "使用方法: $0 [--incremental] [--force]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "图片分类后端 - 代码部署"
echo "========================================"
echo "服务器: $SERVER"
echo "目标目录: $REMOTE_DIR"
echo "本地目录: $LOCAL_DIR"
if [ "$INCREMENTAL" = true ]; then
    echo "部署模式: 增量部署（只同步修改的文件）"
else
    echo "部署模式: 全量部署"
fi
echo ""

# 确认部署（除非使用 --force）
if [ "$FORCE" != true ]; then
    read -p "确认部署到服务器? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "部署已取消"
        exit 1
    fi
fi

echo ""
echo "[1/6] 检查版本化目录结构..."

# 检查并创建 debug 版本目录
VERSION_DIR=$(ssh $SERVER "cd $REMOTE_DIR && \
    CURRENT_LINK=\"$REMOTE_DIR/current\" && \
    VERSIONS_DIR=\"$REMOTE_DIR/versions\" && \
    DEBUG_VERSION_DIR=\"\$VERSIONS_DIR/debug\" && \
    mkdir -p \"\$VERSIONS_DIR\" && \
    mkdir -p \"\$DEBUG_VERSION_DIR\" && \
    ln -sfn \"\$DEBUG_VERSION_DIR\" \"\$CURRENT_LINK\" && \
    echo \"\$DEBUG_VERSION_DIR\"")

if [ -z "$VERSION_DIR" ]; then
    echo "  错误: 无法确定版本目录"
    exit 1
fi

echo "  版本目录: $VERSION_DIR (debug)"

echo ""
echo "[2/6] 同步代码文件..."

# 增量部署：使用 git 检测变更的文件
CHANGED_FILES=()
CHANGED_DIRS=()

if [ "$INCREMENTAL" = true ]; then
    # 检查是否是 git 仓库
    if git rev-parse --git-dir >/dev/null 2>&1; then
        echo "  检测 git 变更文件..."
        # 获取变更文件列表（包括新增、修改、删除）
        GIT_CHANGED=$(git diff --name-only HEAD 2>/dev/null)
        GIT_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)
        
        if [ -n "$GIT_CHANGED" ]; then
            while IFS= read -r file; do
                [ -n "$file" ] && CHANGED_FILES+=("$file")
            done <<< "$GIT_CHANGED"
        fi
        
        if [ -n "$GIT_UNTRACKED" ]; then
            while IFS= read -r file; do
                [ -n "$file" ] && CHANGED_FILES+=("$file")
            done <<< "$GIT_UNTRACKED"
        fi
        
        if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
            echo "  发现 ${#CHANGED_FILES[@]} 个变更文件"
            # 提取需要同步的目录（去重）
            for file in "${CHANGED_FILES[@]}"; do
                if [ -f "$LOCAL_DIR/$file" ]; then
                    parent_dir=$(dirname "$file")
                    if [ "$parent_dir" != "." ]; then
                        root_dir=$(echo "$parent_dir" | cut -d'/' -f1)
                        if [ -n "$root_dir" ] && [[ ! " ${CHANGED_DIRS[@]} " =~ " ${root_dir} " ]]; then
                            CHANGED_DIRS+=("$root_dir")
                        fi
                    fi
                fi
            done
        else
            echo "  未发现变更文件，将跳过文件同步"
        fi
    else
        echo "  警告: 当前目录不是 git 仓库，增量部署需要 git 支持"
        echo "  将执行全量部署..."
        INCREMENTAL=false
    fi
fi

# 检查文件是否需要同步（增量部署时）
need_sync_file() {
    local file="$1"
    if [ "$INCREMENTAL" != true ]; then
        return 0  # 全量部署，总是同步
    fi
    
    # 检查文件是否在变更列表中
    for changed_file in "${CHANGED_FILES[@]}"; do
        if [ "$changed_file" = "$file" ]; then
            return 0  # 需要同步
        fi
    done
    return 1  # 不需要同步
}

# 检查目录是否需要同步（增量部署时）
need_sync_dir() {
    local dir="$1"
    if [ "$INCREMENTAL" != true ]; then
        return 0  # 全量部署，总是同步
    fi
    
    # 检查目录是否在变更目录列表中
    for changed_dir in "${CHANGED_DIRS[@]}"; do
        if [ "$changed_dir" = "$dir" ]; then
            return 0  # 需要同步
        fi
    done
    return 1  # 不需要同步
}

# 同步函数：根据模式选择同步方式
sync_directory() {
    local local_path="$1"
    local remote_path="$2"
    local description="$3"
    local always_sync="${4:-false}"
    
    if [ ! -e "$local_path" ]; then
        return
    fi
    
    # 增量部署时，检查目录是否需要同步
    if [ "$INCREMENTAL" = true ] && [ "$always_sync" != "true" ]; then
        dir_name=$(basename "$local_path")
        if ! need_sync_dir "$dir_name"; then
            echo "  跳过 $description (未变更)"
            return
        fi
    fi
    
    echo "  同步 $description..."
    scp -r "$local_path" "${SERVER}:${remote_path}/" 2>/dev/null || {
        echo "    错误: $description 同步失败"
        if [ "$description" = "app/ 目录" ]; then
            exit 1
        fi
    }
}

sync_file() {
    local local_path="$1"
    local remote_path="$2"
    local description="$3"
    local always_sync="${4:-false}"
    
    if [ ! -f "$local_path" ]; then
        return
    fi
    
    # 增量部署时，检查文件是否需要同步
    if [ "$INCREMENTAL" = true ] && [ "$always_sync" != "true" ]; then
        relative_path="${local_path#$LOCAL_DIR/}"
        if ! need_sync_file "$relative_path"; then
            echo "  跳过 $description (未变更)"
            return
        fi
    fi
    
    echo "  同步 $description..."
    scp "$local_path" "${SERVER}:${remote_path}" 2>/dev/null || {
        echo "    警告: $description 同步失败"
    }
}

# 同步 app 目录到版本目录
sync_directory "$LOCAL_DIR/app" "${VERSION_DIR}/app" "app/ 目录"

# 同步其他重要文件到版本目录（requirements.txt 等重要文件总是同步）
sync_file "$LOCAL_DIR/requirements.txt" "${VERSION_DIR}/requirements.txt" "requirements.txt" "true"
sync_file "$LOCAL_DIR/gunicorn_config.py" "${VERSION_DIR}/gunicorn_config.py" "gunicorn_config.py" "true"
sync_file "$LOCAL_DIR/env.example" "${VERSION_DIR}/env.example" "env.example" "true"
sync_file "$LOCAL_DIR/env.example.secrets" "${VERSION_DIR}/env.example.secrets" "env.example.secrets" "true"

# 同步 prompts 目录（如果存在）
sync_directory "$LOCAL_DIR/prompts" "${VERSION_DIR}/prompts" "prompts/ 目录"

# 同步 tests 目录（用于服务器端测试）
sync_directory "$LOCAL_DIR/tests" "${VERSION_DIR}/tests" "tests/ 目录"

# 同步 pytest.ini（如果存在）
sync_file "$LOCAL_DIR/pytest.ini" "${VERSION_DIR}/pytest.ini" "pytest.ini"

# 同步 scripts 目录（包含回滚等运维脚本）
sync_directory "$LOCAL_DIR/scripts" "${VERSION_DIR}/scripts" "scripts/ 目录"
# 确保脚本有执行权限
ssh $SERVER "chmod +x ${VERSION_DIR}/scripts/*.sh 2>/dev/null || true"

# tools 目录包含开发和运维工具，不需要部署到生产环境
# 如需使用工具脚本，请手动通过 SSH 执行

echo "✓ 代码同步完成"

echo ""
echo "[3/6] 检查配置文件..."
# 检查并初始化共享配置文件（如果不存在）
ssh $SERVER "cd $REMOTE_DIR && \
    if [ ! -f .env ]; then
        if [ -f \"$VERSION_DIR/env.example\" ]; then
            echo '  从 env.example 创建 .env 文件...'
            cp \"$VERSION_DIR/env.example\" .env
            echo '  警告: 请编辑 .env 文件配置数据库和API密钥等敏感信息'
        fi
    else
        echo '  .env 文件已存在，跳过初始化'
    fi && \
    if [ ! -f .env.secrets ]; then
        if [ -f \"$VERSION_DIR/env.example.secrets\" ]; then
            echo '  从 env.example.secrets 创建 .env.secrets 文件...'
            cp \"$VERSION_DIR/env.example.secrets\" .env.secrets
            chmod 600 .env.secrets
            echo '  警告: 请编辑 .env.secrets 文件填入实际的敏感信息'
        fi
    else
        echo '  .env.secrets 文件已存在，跳过初始化'
    fi && \
    # 在版本目录创建符号链接指向共享配置文件
    ln -sfn \"$REMOTE_DIR/.env\" \"$VERSION_DIR/.env\" && \
    ln -sfn \"$REMOTE_DIR/.env.secrets\" \"$VERSION_DIR/.env.secrets\" 2>/dev/null || true && \
    echo '  ✓ 已创建配置文件符号链接'" || {
    echo "  警告: 配置文件检查可能有问题"
}

echo ""
echo "[4/7] 检查系统依赖..."
ssh $SERVER "
    echo '检查系统依赖 zbar (pyzbar 所需)...'
    if command -v dpkg >/dev/null 2>&1; then
        # Debian/Ubuntu 系统
        if ! dpkg -l | grep -q '^ii.*libzbar0'; then
            echo '  libzbar0 未安装，正在安装...'
            sudo apt-get update -qq
            sudo apt-get install -y libzbar0
            echo '  ✓ libzbar0 安装完成'
        else
            echo '  ✓ libzbar0 已安装'
        fi
    elif command -v rpm >/dev/null 2>&1; then
        # CentOS/RHEL/Alibaba Cloud Linux 系统
        if ! rpm -qa | grep -q '^zbar-libs'; then
            echo '  zbar-libs 未安装，正在安装...'
            sudo yum install -y zbar-libs
            echo '  ✓ zbar-libs 安装完成'
        else
            echo '  ✓ zbar-libs 已安装'
        fi
    else
        echo '  ⚠ 无法检测系统类型，跳过系统依赖检查'
    fi
    echo ''
    echo '检查系统依赖 scikit-learn (V3逆地址编码接口所需)...'
    echo '  注意: scikit-learn 是 Python 包，将在虚拟环境中安装'
    echo '  ✓ 将在虚拟环境安装依赖时自动安装 scikit-learn'
" || {
    echo "  警告: 系统依赖检查可能有问题"
}

echo ""
echo "[5/7] 检查共享虚拟环境..."
ssh $SERVER "cd $REMOTE_DIR && \
    SHARED_VENV=\"$REMOTE_DIR/venv\" && \
    if [ ! -d \"\$SHARED_VENV\" ]; then
        echo '  创建共享虚拟环境...'
        if command -v python${PYTHON_VERSION} &> /dev/null; then
            python${PYTHON_VERSION} -m venv \"\$SHARED_VENV\"
        elif command -v python3 &> /dev/null; then
            python3 -m venv \"\$SHARED_VENV\"
        else
            echo '错误: 未找到 Python 3'
            exit 1
        fi
        echo '  安装依赖到共享虚拟环境...'
        source \"\$SHARED_VENV/bin/activate\" && \
        pip install --upgrade pip --quiet && \
        pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu --quiet && \
        pip install -r \"$VERSION_DIR/requirements.txt\" --quiet && \
        deactivate
    else
        echo '  ✓ 共享虚拟环境已存在'
        echo '  更新依赖...'
        source \"\$SHARED_VENV/bin/activate\" && \
        pip install --upgrade pip --quiet && \
        pip install -r \"$VERSION_DIR/requirements.txt\" --quiet --upgrade && \
        deactivate
    fi && \
    # 在版本目录创建符号链接指向共享虚拟环境
    ln -sfn \"\$SHARED_VENV\" \"$VERSION_DIR/venv\" && \
    echo '  ✓ 已创建虚拟环境符号链接'" || {
    echo "  警告: 虚拟环境检查可能有问题"
}

echo ""
echo "[6/7] 重启服务..."
ssh $SERVER "systemctl daemon-reload && systemctl restart image-classifier" || {
    echo "  警告: 服务重启失败，请手动检查"
}

echo ""
echo "[7/7] 检查服务状态..."
ssh $SERVER "systemctl status image-classifier --no-pager | head -n 5"

echo ""
echo "========================================"
echo "部署完成！"
echo "========================================"
echo ""
echo "查看服务日志: ssh $SERVER 'tail -f /var/log/image-classifier/app.log'"
echo "查看最近日志: ssh $SERVER 'tail -n 100 /var/log/image-classifier/app.log'"
echo "查看服务状态: ssh $SERVER 'systemctl status image-classifier'"
echo ""


