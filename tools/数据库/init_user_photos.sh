#!/bin/bash
# ====================================
# 初始化用户照片关系表（user_photos）
# 用于v2版本分类接口
# ====================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/create_user_photos.sql"

# 检查SQL文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}错误: SQL文件不存在: $SQL_FILE${NC}"
    exit 1
fi

# 读取数据库配置（从环境变量或使用默认值）
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-image_classifier}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}初始化用户照片关系表（user_photos）${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "数据库配置:"
echo "  主机: $MYSQL_HOST"
echo "  端口: $MYSQL_PORT"
echo "  用户: $MYSQL_USER"
echo "  数据库: $MYSQL_DATABASE"
echo ""

# 如果密码为空，提示输入
if [ -z "$MYSQL_PASSWORD" ]; then
    echo -e "${YELLOW}提示: 未设置MYSQL_PASSWORD环境变量${NC}"
    echo -e "${YELLOW}请输入MySQL root密码:${NC}"
    read -s MYSQL_PASSWORD
    echo ""
fi

# 执行SQL脚本
echo -e "${GREEN}正在创建表...${NC}"

if [ -z "$MYSQL_PASSWORD" ]; then
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" "$MYSQL_DATABASE" < "$SQL_FILE"
else
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$SQL_FILE"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 表创建成功！${NC}"
    echo ""
    
    # 验证表是否存在
    echo -e "${GREEN}验证表结构...${NC}"
    if [ -z "$MYSQL_PASSWORD" ]; then
        mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" "$MYSQL_DATABASE" -e "DESCRIBE user_photos;" > /dev/null 2>&1
    else
        mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "DESCRIBE user_photos;" > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 表结构验证通过！${NC}"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}初始化完成！${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo -e "${YELLOW}⚠️  警告: 无法验证表结构${NC}"
    fi
else
    echo -e "${RED}❌ 表创建失败！${NC}"
    exit 1
fi

