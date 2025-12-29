#!/bin/bash

# =====================================================
# 在服务器上检查系统依赖和 Python 包
# 使用方法: ssh root@web 'bash -s' < scripts/check-server-dependencies.sh
# 或者在服务器上直接执行: bash check-server-dependencies.sh
# =====================================================

SERVER="${1:-root@web}"
REMOTE_DIR="${2:-/opt/ICBackend}"

echo "========================================"
echo "检查服务器系统依赖和 Python 包"
echo "========================================"
echo "服务器: $SERVER"
echo "部署目录: $REMOTE_DIR"
echo ""

# 检查系统依赖
echo "[1/3] 检查系统依赖 libzbar0..."
ssh $SERVER "
    echo '检查 libzbar0 (pyzbar 所需)...'
    if dpkg -l | grep -q '^ii.*libzbar0'; then
        echo '✓ libzbar0 已安装'
        dpkg -l | grep libzbar0
    else
        echo '✗ libzbar0 未安装'
        echo ''
        echo '安装命令:'
        echo '  sudo apt-get update'
        echo '  sudo apt-get install -y libzbar0'
    fi
"

echo ""
echo "[2/3] 检查 Python 虚拟环境中的 pyzbar..."
ssh $SERVER "cd $REMOTE_DIR && \
    SHARED_VENV=\"$REMOTE_DIR/venv\" && \
    if [ -d \"\$SHARED_VENV\" ]; then
        echo '检查虚拟环境: \$SHARED_VENV'
        source \"\$SHARED_VENV/bin/activate\" && \
        if python -c 'from pyzbar.pyzbar import decode; print(\"✓ pyzbar 可以正常导入\")' 2>/dev/null; then
            echo '✓ pyzbar 可以正常导入'
        else
            echo '✗ pyzbar 无法导入'
            echo '  可能原因:'
            echo '  1. libzbar0 系统库未安装'
            echo '  2. pyzbar Python 包未安装'
            echo ''
            echo '安装步骤:'
            echo '  1. sudo apt-get update && sudo apt-get install -y libzbar0'
            echo '  2. source venv/bin/activate && pip install pyzbar'
        fi && \
        deactivate
    else
        echo '✗ 虚拟环境不存在: \$SHARED_VENV'
    fi
"

echo ""
echo "[3/3] 检查系统 Python 中的 pyzbar..."
ssh $SERVER "
    if python3 -c 'from pyzbar.pyzbar import decode; print(\"✓ pyzbar 可以正常导入\")' 2>/dev/null; then
        echo '✓ pyzbar 可以正常导入（系统 Python）'
    else
        echo '✗ pyzbar 无法导入（系统 Python）'
        echo '  注意: 应用使用虚拟环境，此检查仅供参考'
    fi
"

echo ""
echo "========================================"
echo "检查完成"
echo "========================================"

