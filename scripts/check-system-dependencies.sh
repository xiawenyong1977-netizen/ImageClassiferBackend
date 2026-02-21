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
echo "检查 Python 包 scikit-learn 是否可以导入（V3逆地址编码接口需要）..."
if python3 -c "import sklearn; from sklearn.cluster import DBSCAN; print('✓ scikit-learn 可以正常导入')" 2>/dev/null; then
    echo "✓ scikit-learn 可以正常导入"
    python3 -c "import sklearn; print(f\"  版本: {sklearn.__version__}\")" 2>/dev/null || true
else
    echo "✗ scikit-learn 无法导入"
    echo "  可能原因: scikit-learn Python 包未安装"
    echo ""
    echo "安装步骤:"
    echo "  pip install scikit-learn>=1.3.0"
    echo ""
    echo "  注意: V3逆地址编码接口需要 scikit-learn 依赖"
fi

echo ""
echo "========================================"

