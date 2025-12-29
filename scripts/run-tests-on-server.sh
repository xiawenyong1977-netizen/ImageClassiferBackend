#!/bin/bash

# =====================================================
# 在服务器上运行测试用例
# 部署后可以使用此脚本验证部署是否正确
# 
# 使用方法：
#   cd /opt/ICBackend/current
#   ./tests/run-tests-on-server.sh
#   或
#   ./tests/run-tests-on-server.sh tests/test_health.py
# =====================================================

set -e

# 获取脚本所在目录（tests目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 项目根目录（current目录）
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
# 虚拟环境目录
VENV_DIR="$( cd "$PROJECT_DIR/../venv" && pwd )"

echo "========================================"
echo "在服务器上运行测试用例"
echo "========================================"
echo "项目目录: $PROJECT_DIR"
echo "虚拟环境: $VENV_DIR"
echo "测试目录: $SCRIPT_DIR"
echo ""

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "错误: 虚拟环境不存在: $VENV_DIR"
    exit 1
fi

# 检查 tests 目录是否存在
if [ ! -d "$SCRIPT_DIR" ]; then
    echo "警告: tests 目录不存在: $SCRIPT_DIR"
    echo "请先部署代码（包含 tests 目录）"
    exit 1
fi

# 切换到项目目录
cd "$PROJECT_DIR"

# 激活虚拟环境
echo "[1/3] 激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 检查 pytest 是否安装
echo "[2/3] 检查测试依赖..."
if ! python -m pytest --version &> /dev/null; then
    echo "  安装测试依赖..."
    pip install pytest pytest-asyncio pytest-cov pytest-httpx --quiet
fi

# 运行测试
echo "[3/3] 运行测试用例..."
echo ""

# 如果提供了参数，传递给pytest
if [ $# -gt 0 ]; then
    pytest "$@"
else
    # 默认运行所有测试（排除标记为 slow 的测试）
    pytest tests/ -v -m "not slow" --tb=short
fi

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"

