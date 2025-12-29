#!/bin/bash

# =====================================================
# 检查部署状态并运行测试
# 使用方法: ssh root@web 'bash -s' < scripts/check-deployment-and-test.sh
# 或者在服务器上直接执行: bash check-deployment-and-test.sh
# =====================================================

SERVER="${1:-root@web}"
REMOTE_DIR="${2:-/opt/ICBackend}"

echo "========================================"
echo "检查部署状态并运行测试"
echo "========================================"
echo "服务器: $SERVER"
echo "部署目录: $REMOTE_DIR"
echo ""

# 检查部署状态
echo "[1/5] 检查部署状态..."
ssh $SERVER "
    echo '检查部署目录结构...'
    cd $REMOTE_DIR && \
    echo '  当前版本目录:' && \
    if [ -L current ]; then
        echo \"    \$(readlink -f current)\"
        ls -la current | head -5
    else
        echo '    ✗ current 符号链接不存在'
    fi && \
    echo '' && \
    echo '检查服务状态...' && \
    systemctl status image-classifier --no-pager | head -10
"

echo ""
echo "[2/5] 检查系统依赖..."
ssh $SERVER "
    echo '检查 libzbar0...'
    if dpkg -l | grep -q '^ii.*libzbar0'; then
        echo '  ✓ libzbar0 已安装'
    else
        echo '  ✗ libzbar0 未安装'
    fi
"

echo ""
echo "[3/5] 检查虚拟环境..."
ssh $SERVER "cd $REMOTE_DIR && \
    if [ -d venv ]; then
        echo '✓ 虚拟环境存在'
        source venv/bin/activate && \
        echo '  Python 版本:' && \
        python --version && \
        echo '  检查关键包:' && \
        python -c 'import fastapi; print(\"  ✓ fastapi\")' 2>/dev/null || echo '  ✗ fastapi' && \
        python -c 'import torch; print(\"  ✓ torch\")' 2>/dev/null || echo '  ✗ torch' && \
        python -c 'from pyzbar.pyzbar import decode; print(\"  ✓ pyzbar\")' 2>/dev/null || echo '  ✗ pyzbar' && \
        deactivate
    else
        echo '✗ 虚拟环境不存在'
    fi
"

echo ""
echo "[4/5] 检查日志文件..."
ssh $SERVER "
    echo '检查日志文件...'
    if [ -f /var/log/image-classifier/app.log ]; then
        echo '  ✓ 日志文件存在'
        echo '  最近日志（最后5行）:'
        tail -n 5 /var/log/image-classifier/app.log
    else
        echo '  ✗ 日志文件不存在'
    fi
"

echo ""
echo "[5/5] 运行自动化测试..."
echo "执行测试脚本: cd $REMOTE_DIR/current/tests && ./run-tests-on-server.sh"
ssh $SERVER "cd $REMOTE_DIR/current/tests && bash ./run-tests-on-server.sh"

echo ""
echo "========================================"
echo "检查和测试完成"
echo "========================================"

