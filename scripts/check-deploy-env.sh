#!/bin/bash

# =====================================================
# 部署环境检查脚本
# 检查部署目录是否准备好
# =====================================================

set -e

# 配置
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ICBackend}"
PYTHON_VERSION="3.10"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}部署环境检查${NC}"
echo -e "${BLUE}========================================${NC}"
echo "部署目录: $DEPLOY_DIR"
echo "Python 版本: $PYTHON_VERSION"
echo ""

# 检查结果统计
PASSED=0
FAILED=0
WARNINGS=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. 检查部署目录是否存在
echo -e "${BLUE}[1/10] 检查部署目录...${NC}"
if [ -d "$DEPLOY_DIR" ]; then
    check_pass "部署目录存在: $DEPLOY_DIR"
else
    check_fail "部署目录不存在: $DEPLOY_DIR"
    echo "  创建目录: mkdir -p $DEPLOY_DIR"
fi

# 2. 检查目录权限
if [ -d "$DEPLOY_DIR" ]; then
    echo -e "${BLUE}[2/10] 检查目录权限...${NC}"
    PERM=$(stat -c "%a" "$DEPLOY_DIR" 2>/dev/null || stat -f "%OLp" "$DEPLOY_DIR" 2>/dev/null || echo "unknown")
    OWNER=$(stat -c "%U:%G" "$DEPLOY_DIR" 2>/dev/null || stat -f "%Su:%Sg" "$DEPLOY_DIR" 2>/dev/null || echo "unknown")
    echo "  权限: $PERM"
    echo "  所有者: $OWNER"
    if [ "$PERM" = "755" ] || [ "$PERM" = "750" ]; then
        check_pass "目录权限正确"
    else
        check_warn "目录权限可能不合适（建议 755 或 750）"
    fi
fi

# 3. 检查 Python 版本
echo -e "${BLUE}[3/10] 检查 Python 版本...${NC}"
if command -v python${PYTHON_VERSION} &> /dev/null; then
    PYTHON_VER=$(python${PYTHON_VERSION} --version 2>&1)
    check_pass "Python $PYTHON_VERSION 已安装: $PYTHON_VER"
elif command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version 2>&1)
    check_warn "Python 3 已安装: $PYTHON_VER（但未找到 python${PYTHON_VERSION}）"
else
    check_fail "未找到 Python 3"
fi

# 4. 检查虚拟环境
echo -e "${BLUE}[4/10] 检查虚拟环境...${NC}"
if [ -d "$DEPLOY_DIR/venv" ]; then
    check_pass "共享虚拟环境存在: $DEPLOY_DIR/venv"
    if [ -f "$DEPLOY_DIR/venv/bin/activate" ]; then
        check_pass "虚拟环境激活脚本存在"
    else
        check_fail "虚拟环境不完整（缺少 activate 脚本）"
    fi
else
    check_warn "共享虚拟环境不存在（部署时会自动创建）"
fi

# 5. 检查配置文件
echo -e "${BLUE}[5/10] 检查配置文件...${NC}"
if [ -f "$DEPLOY_DIR/.env" ]; then
    check_pass ".env 文件存在"
    ENV_SIZE=$(stat -c "%s" "$DEPLOY_DIR/.env" 2>/dev/null || stat -f "%z" "$DEPLOY_DIR/.env" 2>/dev/null || echo "0")
    if [ "$ENV_SIZE" -gt 100 ]; then
        check_pass ".env 文件大小正常（${ENV_SIZE} 字节）"
    else
        check_warn ".env 文件可能为空或未配置（${ENV_SIZE} 字节）"
    fi
else
    check_warn ".env 文件不存在（部署时会从 env.example 创建）"
fi

if [ -f "$DEPLOY_DIR/.env.secrets" ]; then
    check_pass ".env.secrets 文件存在"
    SECRETS_PERM=$(stat -c "%a" "$DEPLOY_DIR/.env.secrets" 2>/dev/null || stat -f "%OLp" "$DEPLOY_DIR/.env.secrets" 2>/dev/null || echo "unknown")
    if [ "$SECRETS_PERM" = "600" ]; then
        check_pass ".env.secrets 文件权限正确（600）"
    else
        check_warn ".env.secrets 文件权限为 $SECRETS_PERM（建议 600）"
        echo "  修复命令: chmod 600 $DEPLOY_DIR/.env.secrets"
    fi
else
    check_warn ".env.secrets 文件不存在（部署时会从 env.example.secrets 创建）"
fi

# 6. 检查版本目录结构
echo -e "${BLUE}[6/10] 检查版本目录结构...${NC}"
if [ -d "$DEPLOY_DIR/versions" ]; then
    check_pass "versions 目录存在"
    VERSION_COUNT=$(ls -1 "$DEPLOY_DIR/versions" 2>/dev/null | wc -l)
    if [ "$VERSION_COUNT" -gt 0 ]; then
        check_pass "已有 $VERSION_COUNT 个版本"
        echo "  最新版本: $(ls -1t "$DEPLOY_DIR/versions" 2>/dev/null | head -n 1)"
    else
        check_warn "versions 目录为空（首次部署正常）"
    fi
else
    check_warn "versions 目录不存在（首次部署时会自动创建）"
fi

# 7. 检查 current 符号链接
echo -e "${BLUE}[7/10] 检查 current 符号链接...${NC}"
if [ -L "$DEPLOY_DIR/current" ]; then
    CURRENT_TARGET=$(readlink -f "$DEPLOY_DIR/current" 2>/dev/null || echo "unknown")
    check_pass "current 符号链接存在"
    echo "  指向: $CURRENT_TARGET"
    if [ -d "$CURRENT_TARGET" ]; then
        check_pass "current 指向的目录存在"
    else
        check_fail "current 指向的目录不存在"
    fi
else
    check_warn "current 符号链接不存在（首次部署时会自动创建）"
fi

# 8. 检查 Systemd 服务
echo -e "${BLUE}[8/10] 检查 Systemd 服务...${NC}"
if systemctl list-unit-files | grep -q "image-classifier.service"; then
    check_pass "image-classifier 服务已配置"
    if systemctl is-enabled image-classifier &> /dev/null; then
        check_pass "服务已启用（开机自启）"
    else
        check_warn "服务未启用（建议启用：systemctl enable image-classifier）"
    fi
    if systemctl is-active image-classifier &> /dev/null; then
        check_pass "服务正在运行"
    else
        check_warn "服务未运行（部署后会自动启动）"
    fi
else
    check_warn "image-classifier 服务未配置（需要创建 systemd 服务文件）"
fi

# 9. 检查磁盘空间
echo -e "${BLUE}[9/10] 检查磁盘空间...${NC}"
if [ -d "$DEPLOY_DIR" ]; then
    AVAILABLE=$(df -h "$DEPLOY_DIR" | tail -n 1 | awk '{print $4}')
    USED=$(df -h "$DEPLOY_DIR" | tail -n 1 | awk '{print $3}')
    USAGE=$(df -h "$DEPLOY_DIR" | tail -n 1 | awk '{print $5}' | sed 's/%//')
    echo "  可用空间: $AVAILABLE"
    echo "  已用空间: $USED"
    echo "  使用率: ${USAGE}%"
    if [ "$USAGE" -lt 80 ]; then
        check_pass "磁盘空间充足"
    elif [ "$USAGE" -lt 90 ]; then
        check_warn "磁盘空间使用率较高（${USAGE}%）"
    else
        check_fail "磁盘空间不足（${USAGE}%）"
    fi
fi

# 10. 检查必要的命令工具
echo -e "${BLUE}[10/10] 检查必要的命令工具...${NC}"
TOOLS=("git" "pip" "gunicorn")
for tool in "${TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        check_pass "$tool 已安装"
    else
        check_warn "$tool 未找到（可能需要安装）"
    fi
done

# 总结
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}检查总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${YELLOW}警告: $WARNINGS${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ 部署环境检查通过，可以开始部署！${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ 部署环境基本就绪，但有一些警告，建议检查后部署${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ 部署环境存在问题，请先解决上述问题${NC}"
    exit 1
fi

