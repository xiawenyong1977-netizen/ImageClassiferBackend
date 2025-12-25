#!/bin/bash

# =====================================================
# 版本回退脚本
# =====================================================

set -e

# 配置
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ImageClassifierBackend}"
CURRENT_LINK="$DEPLOY_DIR/current"
VERSIONS_DIR="$DEPLOY_DIR/versions"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查参数
if [ -z "$1" ]; then
    echo -e "${YELLOW}用法: $0 <version>${NC}"
    echo ""
    echo "可用版本:"
    if [ -d "$VERSIONS_DIR" ]; then
        ls -1t "$VERSIONS_DIR" 2>/dev/null | while read version; do
            if [ -L "$CURRENT_LINK" ] && [ "$(readlink -f "$CURRENT_LINK" | xargs basename)" == "$version" ]; then
                echo -e "  ${GREEN}* $version (当前)${NC}"
            else
                echo "    $version"
            fi
        done || echo "  无可用版本"
    else
        echo "  无可用版本"
    fi
    exit 1
fi

TARGET_VERSION="$1"
TARGET_DIR="$VERSIONS_DIR/$TARGET_VERSION"

# 检查版本是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}错误: 版本 $TARGET_VERSION 不存在${NC}"
    exit 1
fi

# 获取当前版本
CURRENT_VERSION=""
if [ -L "$CURRENT_LINK" ]; then
    CURRENT_VERSION=$(readlink -f "$CURRENT_LINK" 2>/dev/null | xargs basename 2>/dev/null || echo "")
fi

if [ "$CURRENT_VERSION" == "$TARGET_VERSION" ]; then
    echo -e "${YELLOW}版本 $TARGET_VERSION 已经是当前版本${NC}"
    exit 0
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}版本回退${NC}"
echo -e "${GREEN}========================================${NC}"
echo "当前版本: ${CURRENT_VERSION:-无}"
echo "目标版本: $TARGET_VERSION"
echo ""

# 切换版本
echo -e "${YELLOW}[1/2] 切换版本...${NC}"
ln -sfn "$TARGET_DIR" "$CURRENT_LINK"
echo -e "${GREEN}✓ 版本已切换${NC}"

# 重启服务
if systemctl is-active --quiet image-classifier 2>/dev/null; then
    echo -e "${YELLOW}[2/2] 重启服务...${NC}"
    systemctl restart image-classifier
    sleep 5
    
    if systemctl is-active --quiet image-classifier; then
        echo -e "${GREEN}✓ 服务运行正常${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[2/2] 服务未运行，跳过重启${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}回退完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo "当前版本: $TARGET_VERSION"
echo ""
echo "查看服务状态: systemctl status image-classifier"
echo "查看服务日志: journalctl -u image-classifier -f"

