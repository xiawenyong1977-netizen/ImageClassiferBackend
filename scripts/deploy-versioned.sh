#!/bin/bash

# =====================================================
# 版本化部署脚本
# 支持部署到新目录并保留旧版本以便回退
# =====================================================

set -e

# 配置
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ICBackend}"
VERSION="${VERSION:-$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'manual')}"
CURRENT_LINK="$DEPLOY_DIR/current"
VERSIONS_DIR="$DEPLOY_DIR/versions"
NEW_VERSION_DIR="$VERSIONS_DIR/$VERSION"
SHARED_VENV="$DEPLOY_DIR/venv"  # 共享虚拟环境路径
KEEP_VERSIONS=5  # 保留的版本数量
PYTHON_VERSION="3.10"  # 指定 Python 版本（如果不存在，会尝试 python3.8 或 python3）

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
cp env.example.secrets "$NEW_VERSION_DIR/" 2>/dev/null || true
cp -r prompts "$NEW_VERSION_DIR/" 2>/dev/null || true
cp -r tests "$NEW_VERSION_DIR/" 2>/dev/null || true
cp -r scripts "$NEW_VERSION_DIR/" 2>/dev/null || true
cp pytest.ini "$NEW_VERSION_DIR/" 2>/dev/null || true

# 转换 shell 脚本的行结束符（CRLF -> LF）
echo "  转换 .sh 文件的行结束符..."
find "$NEW_VERSION_DIR" -name "*.sh" -type f | while read file; do
    if command -v dos2unix >/dev/null 2>&1; then
        dos2unix "$file" 2>/dev/null || true
    elif command -v sed >/dev/null 2>&1; then
        sed -i "s/\r$//" "$file" 2>/dev/null || true
    else
        perl -pi -e "s/\r\n/\n/" "$file" 2>/dev/null || \
        python3 -c "import sys; data=open('$file','rb').read().replace(b'\r\n',b'\n'); open('$file','wb').write(data)" 2>/dev/null || true
    fi
done
echo "  ✓ 行结束符转换完成"

# 创建或使用共享虚拟环境
echo -e "${YELLOW}[3/6] 检查共享虚拟环境...${NC}"
if [ ! -d "$SHARED_VENV" ]; then
    echo "  创建共享虚拟环境..."
    # 优先使用 python3.10，如果不存在则使用 python3
    if command -v python${PYTHON_VERSION} &> /dev/null; then
        python${PYTHON_VERSION} -m venv "$SHARED_VENV"
    elif command -v python3 &> /dev/null; then
        python3 -m venv "$SHARED_VENV"
    else
        echo -e "${RED}错误: 未找到 Python 3${NC}"
        exit 1
    fi
    
    # 安装依赖到共享虚拟环境
    echo "  安装依赖到共享虚拟环境..."
    source "$SHARED_VENV/bin/activate"
    pip install --upgrade pip --quiet
    # 先安装CPU版本的PyTorch（服务器无GPU，使用CPU版本节省空间）
    echo "    安装PyTorch CPU版本..."
    pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu --quiet
    # 然后安装其他依赖
    echo "    安装其他依赖..."
    pip install -r "$NEW_VERSION_DIR/requirements.txt" --quiet
    deactivate
    echo "  ✓ 共享虚拟环境已创建并安装依赖"
else
    echo "  ✓ 共享虚拟环境已存在，跳过创建"
    # 检查是否需要更新依赖
    echo "  检查依赖更新..."
    source "$SHARED_VENV/bin/activate"
    pip install --upgrade pip --quiet
    pip install -r "$NEW_VERSION_DIR/requirements.txt" --quiet --upgrade
    deactivate
fi

# 在新版本目录创建指向共享虚拟环境的符号链接
echo "  创建虚拟环境符号链接..."
ln -sfn "$SHARED_VENV" "$NEW_VERSION_DIR/venv"
echo "  ✓ 已创建符号链接: $NEW_VERSION_DIR/venv -> $SHARED_VENV"

# 检查并初始化配置文件（如果不存在）
# .env 和 .env.secrets 文件放在部署根目录，通过符号链接共享给所有版本
echo -e "${YELLOW}[4/6] 检查配置文件...${NC}"
ENV_FILE="$DEPLOY_DIR/.env"
ENV_SECRETS_FILE="$DEPLOY_DIR/.env.secrets"

if [ ! -f "$ENV_FILE" ]; then
    echo "  从 env.example 创建 .env 文件..."
    cp "$NEW_VERSION_DIR/env.example" "$ENV_FILE"
    echo -e "${YELLOW}  警告: 请编辑 $ENV_FILE 文件配置数据库和API密钥等敏感信息${NC}"
else
    echo "  .env 文件已存在，跳过初始化"
fi

if [ ! -f "$ENV_SECRETS_FILE" ]; then
    if [ -f "$NEW_VERSION_DIR/env.example.secrets" ]; then
        echo "  从 env.example.secrets 创建 .env.secrets 文件..."
        cp "$NEW_VERSION_DIR/env.example.secrets" "$ENV_SECRETS_FILE"
        chmod 600 "$ENV_SECRETS_FILE"
        echo -e "${YELLOW}  警告: 请编辑 $ENV_SECRETS_FILE 文件填入实际的敏感信息${NC}"
    fi
else
    echo "  .env.secrets 文件已存在，跳过初始化"
fi

# 在新版本目录创建指向根目录配置文件的符号链接
ln -sfn "$ENV_FILE" "$NEW_VERSION_DIR/.env"
echo "  ✓ 已创建符号链接: $NEW_VERSION_DIR/.env -> $ENV_FILE"
if [ -f "$ENV_SECRETS_FILE" ]; then
    ln -sfn "$ENV_SECRETS_FILE" "$NEW_VERSION_DIR/.env.secrets"
    echo "  ✓ 已创建符号链接: $NEW_VERSION_DIR/.env.secrets -> $ENV_SECRETS_FILE"
fi

# 获取当前版本
OLD_VERSION=""
if [ -L "$CURRENT_LINK" ]; then
    OLD_VERSION=$(readlink -f "$CURRENT_LINK" 2>/dev/null | xargs basename 2>/dev/null || echo "")
fi

# 切换版本
echo -e "${YELLOW}[6/6] 切换版本...${NC}"
ln -sfn "$NEW_VERSION_DIR" "$CURRENT_LINK"

# 重启服务
if systemctl is-active --quiet image-classifier 2>/dev/null; then
    echo "  重启服务..."
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
    echo "  服务未运行，跳过重启"
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

