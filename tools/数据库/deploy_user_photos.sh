#!/bin/bash
# ====================================
# 在服务器上初始化user_photos表
# 支持主从复制环境（在主库执行，自动同步到从库）
# ====================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
APP_SERVER="root@app"  # 主库服务器
WEB_SERVER="root@web"  # 从库服务器（可选）

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/create_user_photos.sql"
REMOTE_SQL_PATH="/tmp/create_user_photos.sql"

# 检查SQL文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}错误: SQL文件不存在: $SQL_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}在服务器上初始化user_photos表${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查SSH连接
echo -e "${YELLOW}[1/3] 检查SSH连接...${NC}"
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${APP_SERVER} "echo '连接成功'" &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ App服务器连接成功${NC}"
else
    echo -e "${RED}❌ 无法连接到App服务器: ${APP_SERVER}${NC}"
    echo -e "${YELLOW}提示: 请确保SSH密钥已配置，可以无密码登录${NC}"
    exit 1
fi

# 上传SQL文件到服务器
echo -e "${YELLOW}[2/3] 上传SQL文件到服务器...${NC}"
scp "$SQL_FILE" "${APP_SERVER}:${REMOTE_SQL_PATH}" || {
    echo -e "${RED}❌ 文件上传失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ SQL文件已上传${NC}"

# 在服务器上执行SQL脚本
echo -e "${YELLOW}[3/3] 在服务器上执行SQL脚本...${NC}"
echo -e "${YELLOW}提示: 如果MySQL需要密码，请输入密码${NC}"
echo ""

ssh ${APP_SERVER} "mysql -u root -p image_classifier < ${REMOTE_SQL_PATH}" || {
    echo -e "${RED}❌ SQL执行失败${NC}"
    echo -e "${YELLOW}提示: 请检查MySQL密码是否正确${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✅ 表创建成功！${NC}"

# 验证表是否创建成功
echo ""
echo -e "${YELLOW}验证表结构...${NC}"
ssh ${APP_SERVER} "mysql -u root -p image_classifier -e 'DESCRIBE user_photos;'" || {
    echo -e "${YELLOW}⚠️  无法验证表结构（可能需要输入密码）${NC}"
}

# 清理临时文件
echo ""
echo -e "${YELLOW}清理临时文件...${NC}"
ssh ${APP_SERVER} "rm -f ${REMOTE_SQL_PATH}" 2>/dev/null || true

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}初始化完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}注意:${NC}"
echo -e "  - 如果配置了主从复制，表会自动同步到从库（web服务器）"
echo -e "  - 可以在从库执行以下命令验证同步："
echo -e "    ${GREEN}ssh ${WEB_SERVER} \"mysql -u root -p image_classifier -e 'DESCRIBE user_photos;'\"${NC}"

