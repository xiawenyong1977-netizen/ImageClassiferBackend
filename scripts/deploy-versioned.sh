#!/bin/bash

# =====================================================
# 版本化部署脚本
# 支持部署到新目录并保留旧版本以便回退
# =====================================================

set -e

# 配置
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ImageClassifierBackend}"
VERSION="${VERSION:-$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'manual')}"
CURRENT_LINK="$DEPLOY_DIR/current"
VERSIONS_DIR="$DEPLOY_DIR/versions"
NEW_VERSION_DIR="$VERSIONS_DIR/$VERSION"
KEEP_VERSIONS=5  # 保留的版本数量

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}版本化部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo "部署目录: $DEPLOY_DIR"
echo "版本: $VERSION"
echo "新版本目录: $NEW_VERSION_DIR"
echo ""

# 检查当前目录
if [ ! -d "app" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 创建版本目录
echo -e "${YELLOW}[1/6] 创建版本目录...${NC}"
mkdir -p "$VERSIONS_DIR"
mkdir -p "$NEW_VERSION_DIR"

# 复制文件
echo -e "${YELLOW}[2/6] 复制文件到版本目录...${NC}"
cp -r app "$NEW_VERSION_DIR/"
cp requirements.txt "$NEW_VERSION_DIR/"
cp gunicorn_config.py "$NEW_VERSION_DIR/" 2>/dev/null || true
cp env.example "$NEW_VERSION_DIR/" 2>/dev/null || true

# 创建虚拟环境
if [ ! -d "$NEW_VERSION_DIR/venv" ]; then
    echo -e "${YELLOW}[3/6] 创建虚拟环境...${NC}"
    python3 -m venv "$NEW_VERSION_DIR/venv"
fi

# 安装依赖
echo -e "${YELLOW}[4/6] 安装依赖...${NC}"
source "$NEW_VERSION_DIR/venv/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$NEW_VERSION_DIR/requirements.txt" --quiet
deactivate

# 获取当前版本
OLD_VERSION=""
if [ -L "$CURRENT_LINK" ]; then
    OLD_VERSION=$(readlink -f "$CURRENT_LINK" 2>/dev/null | xargs basename 2>/dev/null || echo "")
fi

# 切换版本
echo -e "${YELLOW}[5/6] 切换版本...${NC}"
ln -sfn "$NEW_VERSION_DIR" "$CURRENT_LINK"

# 重启服务
if systemctl is-active --quiet image-classifier 2>/dev/null; then
    echo -e "${YELLOW}[6/6] 重启服务...${NC}"
    systemctl restart image-classifier || {
        echo -e "${RED}错误: 服务重启失败${NC}"
        # 尝试回退
        if [ -n "$OLD_VERSION" ] && [ -d "$VERSIONS_DIR/$OLD_VERSION" ]; then
            echo -e "${YELLOW}尝试回退到旧版本: $OLD_VERSION${NC}"
            ln -sfn "$VERSIONS_DIR/$OLD_VERSION" "$CURRENT_LINK"
            systemctl restart image-classifier
            echo -e "${RED}已回退到版本: $OLD_VERSION${NC}"
        fi
        exit 1
    }
    
    # 等待服务启动
    sleep 5
    
    # 健康检查
    if systemctl is-active --quiet image-classifier; then
        echo -e "${GREEN}✓ 服务运行正常${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        # 回退
        if [ -n "$OLD_VERSION" ] && [ -d "$VERSIONS_DIR/$OLD_VERSION" ]; then
            echo -e "${YELLOW}回退到旧版本: $OLD_VERSION${NC}"
            ln -sfn "$VERSIONS_DIR/$OLD_VERSION" "$CURRENT_LINK"
            systemctl restart image-classifier
        fi
        exit 1
    fi
else
    echo -e "${YELLOW}[6/6] 服务未运行，跳过重启${NC}"
    echo "使用以下命令启动服务:"
    echo "  systemctl start image-classifier"
fi

# 清理旧版本
echo ""
echo -e "${YELLOW}清理旧版本（保留最近 $KEEP_VERSIONS 个版本）...${NC}"
cd "$VERSIONS_DIR"
if [ $(ls -1 | wc -l) -gt $KEEP_VERSIONS ]; then
    ls -t | tail -n +$((KEEP_VERSIONS + 1)) | while read version; do
        echo "  删除旧版本: $version"
        rm -rf "$version"
    done
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo "当前版本: $VERSION"
if [ -n "$OLD_VERSION" ]; then
    echo "旧版本: $OLD_VERSION (已保留)"
fi
echo ""
echo "可用命令:"
echo "  查看所有版本: ls -la $VERSIONS_DIR"
echo "  回退版本: $DEPLOY_DIR/scripts/rollback.sh $OLD_VERSION"
echo "  查看服务状态: systemctl status image-classifier"
echo "  查看服务日志: journalctl -u image-classifier -f"

