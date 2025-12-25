#!/bin/bash
# check-nominatim-requirements.sh
# 检查服务器配置是否满足Nominatim部署要求

echo "=========================================="
echo "Nominatim 部署前系统检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果统计
PASSED=0
FAILED=0
WARNING=0

# 检查函数
check_item() {
    local name=$1
    local value=$2
    local min_value=$3
    local unit=$4
    
    echo -n "检查 $name: $value $unit ... "
    
    if (( $(echo "$value >= $min_value" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ 不满足 (最低要求: $min_value $unit)${NC}"
        ((FAILED++))
        return 1
    fi
}

check_warning() {
    local name=$1
    local value=$2
    local recommended=$3
    local unit=$4
    
    echo -n "检查 $name: $value $unit ... "
    
    if (( $(echo "$value >= $recommended" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}✓ 推荐配置${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ 低于推荐值 (推荐: $recommended $unit)${NC}"
        ((WARNING++))
    fi
}

# 1. 检查操作系统
echo "【1】操作系统信息"
echo "----------------------------------------"
if [ -f /etc/os-release ]; then
    OS_NAME=$(cat /etc/os-release | grep "^NAME=" | cut -d'"' -f2)
    OS_VERSION=$(cat /etc/os-release | grep "^VERSION_ID=" | cut -d'"' -f2)
    echo "操作系统: $OS_NAME $OS_VERSION"
    
    if [[ "$OS_NAME" == *"Ubuntu"* ]] || [[ "$OS_NAME" == *"Debian"* ]]; then
        echo -e "${GREEN}✓ 支持的操作系统${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ 未测试的操作系统，可能存在问题${NC}"
        ((WARNING++))
    fi
else
    echo -e "${YELLOW}⚠ 无法检测操作系统${NC}"
    ((WARNING++))
fi
echo ""

# 2. 检查CPU
echo "【2】CPU信息"
echo "----------------------------------------"
CPU_CORES=$(nproc 2>/dev/null || echo "0")
if [ -f /proc/cpuinfo ]; then
    CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs 2>/dev/null || echo "未知")
    echo "CPU型号: $CPU_MODEL"
fi
echo "CPU核心数: $CPU_CORES"

if [ "$CPU_CORES" -ge 2 ]; then
    echo -e "${GREEN}✓ CPU核心数: $CPU_CORES 核心 (最低要求: 2核心)${NC}"
    ((PASSED++))
    if [ "$CPU_CORES" -ge 4 ]; then
        echo -e "${GREEN}✓ 推荐配置: 4核心以上${NC}"
    else
        echo -e "${YELLOW}⚠ 推荐配置: 4核心以上${NC}"
        ((WARNING++))
    fi
else
    echo -e "${RED}✗ CPU核心数不足 (最低要求: 2核心)${NC}"
    ((FAILED++))
fi
echo ""

# 3. 检查内存
echo "【3】内存信息"
echo "----------------------------------------"
TOTAL_MEM_GB=$(free -g | grep "Mem:" | awk '{print $2}' 2>/dev/null || echo "0")
AVAILABLE_MEM_GB=$(free -g | grep "Mem:" | awk '{print $7}' 2>/dev/null || echo "0")
USED_MEM_GB=$((TOTAL_MEM_GB - AVAILABLE_MEM_GB))
echo "总内存: ${TOTAL_MEM_GB}GB"
echo "可用内存: ${AVAILABLE_MEM_GB}GB"
echo "已用内存: ${USED_MEM_GB}GB"

if [ "$TOTAL_MEM_GB" -ge 8 ]; then
    echo -e "${GREEN}✓ 总内存: ${TOTAL_MEM_GB}GB (最低要求: 8GB)${NC}"
    ((PASSED++))
    if [ "$TOTAL_MEM_GB" -ge 16 ]; then
        echo -e "${GREEN}✓ 推荐配置: 16GB以上${NC}"
    else
        echo -e "${YELLOW}⚠ 推荐配置: 16GB以上${NC}"
        ((WARNING++))
    fi
else
    echo -e "${RED}✗ 总内存不足 (最低要求: 8GB)${NC}"
    ((FAILED++))
fi
echo ""

# 4. 检查磁盘空间
echo "【4】磁盘空间"
echo "----------------------------------------"
DISK_INFO=$(df -h / | tail -1)
TOTAL_DISK=$(echo $DISK_INFO | awk '{print $2}')
AVAILABLE_DISK=$(echo $DISK_INFO | awk '{print $4}')
USED_DISK=$(echo $DISK_INFO | awk '{print $3}')
USED_PERCENT=$(echo $DISK_INFO | awk '{print $5}' | sed 's/%//')

echo "根分区总空间: $TOTAL_DISK"
echo "根分区可用空间: $AVAILABLE_DISK"
echo "根分区已用空间: $USED_DISK (${USED_PERCENT}%)"

# 提取数字（GB）
AVAILABLE_DISK_GB=$(echo $AVAILABLE_DISK | sed 's/[^0-9.]//g')
if [[ $AVAILABLE_DISK == *"T"* ]] || [[ $AVAILABLE_DISK == *"Ti"* ]]; then
    AVAILABLE_DISK_GB=$(echo "$AVAILABLE_DISK_GB * 1024" | bc 2>/dev/null || echo "$AVAILABLE_DISK_GB")
fi

# 转换为整数进行比较
AVAILABLE_DISK_GB_INT=$(echo "$AVAILABLE_DISK_GB" | cut -d'.' -f1)

if [ "$AVAILABLE_DISK_GB_INT" -ge 50 ]; then
    echo -e "${GREEN}✓ 可用磁盘空间: ${AVAILABLE_DISK} (最低要求: 50GB，仅中国数据)${NC}"
    ((PASSED++))
    if [ "$AVAILABLE_DISK_GB_INT" -ge 500 ]; then
        echo -e "${GREEN}✓ 推荐配置: 500GB以上 (全球数据)${NC}"
    else
        echo -e "${YELLOW}⚠ 推荐配置: 500GB以上 (全球数据)${NC}"
        ((WARNING++))
    fi
else
    echo -e "${RED}✗ 可用磁盘空间不足 (最低要求: 50GB)${NC}"
    ((FAILED++))
fi

if [ "$USED_PERCENT" -gt 80 ]; then
    echo -e "${YELLOW}⚠ 磁盘使用率较高 (${USED_PERCENT}%)，建议清理空间${NC}"
    ((WARNING++))
fi
echo ""

# 5. 检查Docker（如果使用Docker部署）
echo "【5】Docker环境"
echo "----------------------------------------"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "Docker: $DOCKER_VERSION"
    echo -e "${GREEN}✓ Docker已安装${NC}"
    ((PASSED++))
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        if command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_VERSION=$(docker-compose --version)
        else
            DOCKER_COMPOSE_VERSION=$(docker compose version)
        fi
        echo "Docker Compose: $DOCKER_COMPOSE_VERSION"
        echo -e "${GREEN}✓ Docker Compose已安装${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ Docker Compose未安装${NC}"
        ((WARNING++))
    fi
else
    echo -e "${YELLOW}⚠ Docker未安装（如果使用Docker部署需要安装）${NC}"
    ((WARNING++))
fi
echo ""

# 6. 检查PostgreSQL（如果使用源码部署）
echo "【6】PostgreSQL环境"
echo "----------------------------------------"
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version)
    echo "PostgreSQL: $PSQL_VERSION"
    echo -e "${GREEN}✓ PostgreSQL已安装${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ PostgreSQL未安装（如果使用源码部署需要安装）${NC}"
    ((WARNING++))
fi
echo ""

# 7. 检查网络连接
echo "【7】网络连接"
echo "----------------------------------------"
echo -n "检查互联网连接 ... "
if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
    echo -e "${GREEN}✓ 正常${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ 无法连接互联网${NC}"
    ((FAILED++))
fi

echo -n "检查Geofabrik下载源 ... "
if curl -s --head --max-time 5 https://download.geofabrik.de/ | head -1 | grep -q "200 OK"; then
    echo -e "${GREEN}✓ 可访问${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ 无法访问Geofabrik（可能需要代理）${NC}"
    ((WARNING++))
fi
echo ""

# 8. 检查端口占用
echo "【8】端口占用检查"
echo "----------------------------------------"
echo -n "检查8080端口 ... "
if command -v netstat &> /dev/null; then
    if netstat -tuln 2>/dev/null | grep ":8080" > /dev/null; then
        echo -e "${YELLOW}⚠ 8080端口已被占用${NC}"
        if command -v lsof &> /dev/null; then
            echo "   占用进程: $(lsof -i:8080 2>/dev/null | tail -1 | awk '{print $2}')"
        fi
        ((WARNING++))
    else
        echo -e "${GREEN}✓ 8080端口可用${NC}"
        ((PASSED++))
    fi
elif command -v ss &> /dev/null; then
    if ss -tuln 2>/dev/null | grep ":8080" > /dev/null; then
        echo -e "${YELLOW}⚠ 8080端口已被占用${NC}"
        ((WARNING++))
    else
        echo -e "${GREEN}✓ 8080端口可用${NC}"
        ((PASSED++))
    fi
else
    echo -e "${YELLOW}⚠ 无法检查端口占用（netstat/ss未安装）${NC}"
    ((WARNING++))
fi
echo ""

# 9. 检查系统负载
echo "【9】系统负载"
echo "----------------------------------------"
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | xargs)
LOAD_1MIN=$(echo $LOAD_AVG | awk -F',' '{print $1}' | xargs)
echo "1分钟负载: $LOAD_1MIN"

LOAD_1MIN_INT=$(echo "$LOAD_1MIN" | cut -d'.' -f1)
if [ "$LOAD_1MIN_INT" -lt "$CPU_CORES" ]; then
    echo -e "${GREEN}✓ 系统负载正常${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ 系统负载较高${NC}"
    ((WARNING++))
fi
echo ""

# 10. 检查swap空间
echo "【10】Swap空间"
echo "----------------------------------------"
SWAP_TOTAL=$(free -g | grep "Swap:" | awk '{print $2}' 2>/dev/null || echo "0")
if [ "$SWAP_TOTAL" -gt 0 ]; then
    echo "Swap总空间: ${SWAP_TOTAL}GB"
    echo -e "${GREEN}✓ Swap已配置${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Swap未配置（建议配置2-4GB Swap）${NC}"
    ((WARNING++))
fi
echo ""

# 总结
echo "=========================================="
echo "检查总结"
echo "=========================================="
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo -e "${YELLOW}警告: $WARNING${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNING -eq 0 ]; then
        echo -e "${GREEN}✓ 系统配置完全满足Nominatim部署要求！${NC}"
        echo ""
        echo "推荐部署方案："
        if [ "$AVAILABLE_DISK_GB_INT" -ge 500 ] && [ "$TOTAL_MEM_GB" -ge 16 ]; then
            echo "  - 可以部署全球数据版本（推荐Docker方式）"
        elif [ "$AVAILABLE_DISK_GB_INT" -ge 50 ]; then
            echo "  - 可以部署中国地区数据版本（推荐Docker方式）"
        fi
    else
        echo -e "${YELLOW}⚠ 系统配置基本满足要求，但有一些警告项需要注意${NC}"
    fi
else
    echo -e "${RED}✗ 系统配置不满足最低要求，请先解决失败项${NC}"
fi
echo ""

