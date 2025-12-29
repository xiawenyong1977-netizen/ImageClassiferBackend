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
# =====================================================

SERVER="root@web"
REMOTE_DIR="/opt/ICBackend"  # 与文档保持一致
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.10"  # 指定 Python 版本

echo "========================================"
echo "图片分类后端 - 代码部署"
echo "========================================"
echo "服务器: $SERVER"
echo "目标目录: $REMOTE_DIR"
echo "本地目录: $LOCAL_DIR"
echo ""

# 确认部署
read -p "确认部署到服务器? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 1
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

# 同步 app 目录到版本目录
echo "  同步 app/ 目录..."
scp -r "$LOCAL_DIR/app" "${SERVER}:${VERSION_DIR}/" || {
    echo "  错误: app 目录同步失败"
    exit 1
}

# 同步其他重要文件到版本目录
echo "  同步重要文件..."
scp "$LOCAL_DIR/requirements.txt" "${SERVER}:${VERSION_DIR}/" 2>/dev/null
scp "$LOCAL_DIR/gunicorn_config.py" "${SERVER}:${VERSION_DIR}/" 2>/dev/null
scp "$LOCAL_DIR/env.example" "${SERVER}:${VERSION_DIR}/" 2>/dev/null
scp "$LOCAL_DIR/env.example.secrets" "${SERVER}:${VERSION_DIR}/" 2>/dev/null || true

# 同步 prompts 目录（如果存在）
if [ -d "$LOCAL_DIR/prompts" ]; then
    echo "  同步 prompts/ 目录..."
    scp -r "$LOCAL_DIR/prompts" "${SERVER}:${VERSION_DIR}/" 2>/dev/null || true
fi

# 同步 tests 目录（用于服务器端测试）
if [ -d "$LOCAL_DIR/tests" ]; then
    echo "  同步 tests/ 目录..."
    scp -r "$LOCAL_DIR/tests" "${SERVER}:${VERSION_DIR}/" 2>/dev/null || true
fi

# 同步 pytest.ini（如果存在）
if [ -f "$LOCAL_DIR/pytest.ini" ]; then
    echo "  同步 pytest.ini..."
    scp "$LOCAL_DIR/pytest.ini" "${SERVER}:${VERSION_DIR}/" 2>/dev/null || true
fi

# 同步 scripts 目录（包含回滚等运维脚本）
if [ -d "$LOCAL_DIR/scripts" ]; then
    echo "  同步 scripts/ 目录..."
    scp -r "$LOCAL_DIR/scripts" "${SERVER}:${VERSION_DIR}/" 2>/dev/null || true
    # 确保脚本有执行权限
    ssh $SERVER "chmod +x ${VERSION_DIR}/scripts/*.sh 2>/dev/null || true"
fi

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


