#!/bin/bash
# 本地测试运行脚本
# 自动加载测试环境变量并运行测试

set -e

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# 检查测试环境变量文件
TEST_ENV_FILE="$SCRIPT_DIR/.env.test"

if [ -f "$TEST_ENV_FILE" ]; then
    echo "✓ 找到测试环境变量文件: $TEST_ENV_FILE"
    # 加载环境变量
    set -a
    source "$TEST_ENV_FILE"
    set +a
else
    echo "⚠ 未找到测试环境变量文件: $TEST_ENV_FILE"
    echo "  使用系统环境变量或默认配置"
fi

# 切换到项目目录
cd "$PROJECT_DIR"

# 检查pytest是否安装
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest未安装，正在安装..."
    pip install pytest pytest-asyncio pytest-cov
fi

# 运行测试
echo ""
echo "========================================"
echo "开始运行测试..."
echo "========================================"
echo ""

# 如果提供了参数，传递给pytest
if [ $# -gt 0 ]; then
    pytest "$@"
else
    # 默认运行所有测试
    pytest tests/ -v
fi

