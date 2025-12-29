#!/bin/bash

# =====================================================
# 检查系统依赖是否已安装
# 用于检查 pyzbar 所需的 libzbar0 系统库
# =====================================================

echo "========================================"
echo "检查系统依赖..."
echo "========================================"
echo ""

# 检查 libzbar0 是否已安装
echo "检查 libzbar0 (pyzbar 所需)..."
if dpkg -l | grep -q "^ii.*libzbar0"; then
    echo "✓ libzbar0 已安装"
    dpkg -l | grep libzbar0
else
    echo "✗ libzbar0 未安装"
    echo ""
    echo "安装命令:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y libzbar0"
fi

echo ""
echo "检查 Python 包 pyzbar 是否可以导入..."
if python3 -c "from pyzbar.pyzbar import decode; print('✓ pyzbar 可以正常导入')" 2>/dev/null; then
    echo "✓ pyzbar 可以正常导入"
else
    echo "✗ pyzbar 无法导入"
    echo "  可能原因:"
    echo "  1. libzbar0 系统库未安装"
    echo "  2. pyzbar Python 包未安装"
    echo ""
    echo "安装步骤:"
    echo "  1. sudo apt-get update && sudo apt-get install -y libzbar0"
    echo "  2. pip install pyzbar"
fi

echo ""
echo "========================================"

