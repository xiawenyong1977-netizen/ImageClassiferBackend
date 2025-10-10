#!/bin/bash

# =====================================================
# 阿里云服务器自动化部署脚本
# 在服务器上执行此脚本完成部署
# =====================================================

set -e  # 遇到错误立即退出

echo "========================================" 
echo "图片分类后端 - 自动化部署脚本"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root用户运行此脚本${NC}"
    exit 1
fi

# =====================================================
# 步骤1: 更新系统
# =====================================================
echo -e "\n${GREEN}[1/10] 更新系统...${NC}"
apt update && apt upgrade -y
apt install -y git curl wget vim build-essential software-properties-common

# =====================================================
# 步骤2: 安装Python 3.10
# =====================================================
echo -e "\n${GREEN}[2/10] 安装Python 3.10...${NC}"

# 检查Python 3.10是否已安装
if command -v python3.10 &> /dev/null; then
    echo "Python 3.10 已安装"
else
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
fi

python3 --version

# =====================================================
# 步骤3: 安装MySQL
# =====================================================
echo -e "\n${GREEN}[3/10] 安装MySQL 8.0...${NC}"

if command -v mysql &> /dev/null; then
    echo "MySQL 已安装"
else
    apt install -y mysql-server
    systemctl start mysql
    systemctl enable mysql
    
    echo -e "${YELLOW}请设置MySQL root密码${NC}"
    mysql_secure_installation
fi

# =====================================================
# 步骤4: 配置MySQL数据库
# =====================================================
echo -e "\n${GREEN}[4/10] 配置MySQL数据库...${NC}"

read -sp "请输入MySQL root密码: " MYSQL_ROOT_PASSWORD
echo

# 创建数据库和用户
mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS image_classifier DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'classifier'@'localhost' IDENTIFIED BY 'Classifier@2024';
GRANT ALL PRIVILEGES ON image_classifier.* TO 'classifier'@'localhost';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}✓ 数据库配置完成${NC}"

# =====================================================
# 步骤5: 创建项目目录
# =====================================================
echo -e "\n${GREEN}[5/10] 准备项目目录...${NC}"

cd /opt
if [ -d "ImageClassifierBackend" ]; then
    echo "项目目录已存在，备份旧版本..."
    mv ImageClassifierBackend ImageClassifierBackend.backup.$(date +%Y%m%d_%H%M%S)
fi

mkdir -p ImageClassifierBackend
cd ImageClassifierBackend

echo -e "${YELLOW}请选择代码上传方式:${NC}"
echo "1) 从Git仓库克隆"
echo "2) 手动上传（需要先用scp上传到/tmp/project.tar.gz）"
read -p "请选择 (1/2): " UPLOAD_METHOD

if [ "$UPLOAD_METHOD" = "1" ]; then
    read -p "请输入Git仓库URL: " GIT_REPO
    git clone "$GIT_REPO" .
elif [ "$UPLOAD_METHOD" = "2" ]; then
    if [ -f "/tmp/project.tar.gz" ]; then
        tar -xzf /tmp/project.tar.gz -C /opt/ImageClassifierBackend
        echo "代码解压完成"
    else
        echo -e "${RED}错误: 未找到 /tmp/project.tar.gz${NC}"
        echo "请先在本地执行: scp -r d:\ImageClassifierBackend\* root@123.57.68.4:/opt/ImageClassifierBackend/"
        exit 1
    fi
fi

# =====================================================
# 步骤6: 安装Python依赖
# =====================================================
echo -e "\n${GREEN}[6/10] 安装Python依赖...${NC}"

cd /opt/ImageClassifierBackend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

echo -e "${GREEN}✓ Python依赖安装完成${NC}"

# =====================================================
# 步骤7: 配置环境变量
# =====================================================
echo -e "\n${GREEN}[7/10] 配置环境变量...${NC}"

if [ ! -f ".env" ]; then
    cp env.example .env
    
    echo -e "${YELLOW}请输入大模型配置:${NC}"
    read -p "LLM提供商 (openai/claude) [openai]: " LLM_PROVIDER
    LLM_PROVIDER=${LLM_PROVIDER:-openai}
    
    read -p "LLM API密钥: " LLM_API_KEY
    
    read -p "LLM模型 [gpt-4-vision-preview]: " LLM_MODEL
    LLM_MODEL=${LLM_MODEL:-gpt-4-vision-preview}
    
    # 更新.env文件
    sed -i "s/MYSQL_PASSWORD=.*/MYSQL_PASSWORD=Classifier@2024/" .env
    sed -i "s/LLM_PROVIDER=.*/LLM_PROVIDER=$LLM_PROVIDER/" .env
    sed -i "s/LLM_API_KEY=.*/LLM_API_KEY=$LLM_API_KEY/" .env
    sed -i "s/LLM_MODEL=.*/LLM_MODEL=$LLM_MODEL/" .env
    sed -i "s/APP_DEBUG=.*/APP_DEBUG=false/" .env
    sed -i "s/APP_ENV=.*/APP_ENV=production/" .env
    
    echo -e "${GREEN}✓ 环境变量配置完成${NC}"
else
    echo ".env 文件已存在，跳过配置"
fi

# =====================================================
# 步骤8: 初始化数据库
# =====================================================
echo -e "\n${GREEN}[8/10] 初始化数据库表...${NC}"

mysql -u classifier -pClassifier@2024 image_classifier < sql/init.sql

echo -e "${GREEN}✓ 数据库表初始化完成${NC}"

# 验证表
echo "验证数据库表:"
mysql -u classifier -pClassifier@2024 -e "USE image_classifier; SHOW TABLES;"

# =====================================================
# 步骤9: 创建日志目录
# =====================================================
echo -e "\n${GREEN}[9/10] 创建日志目录...${NC}"

mkdir -p /var/log/image-classifier
chown -R root:root /var/log/image-classifier

# =====================================================
# 步骤10: 配置systemd服务
# =====================================================
echo -e "\n${GREEN}[10/10] 配置systemd服务...${NC}"

cat > /etc/systemd/system/image-classifier.service <<EOF
[Unit]
Description=Image Classifier API Service
After=network.target mysql.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/ImageClassifierBackend
Environment="PATH=/opt/ImageClassifierBackend/venv/bin"
ExecStart=/opt/ImageClassifierBackend/venv/bin/gunicorn -c gunicorn_config.py app.main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd
systemctl daemon-reload

# 启动服务
systemctl start image-classifier

# 设置开机自启
systemctl enable image-classifier

# 等待服务启动
sleep 3

# 检查服务状态
systemctl status image-classifier

# =====================================================
# 步骤11: 配置防火墙
# =====================================================
echo -e "\n${GREEN}配置防火墙...${NC}"

ufw --force enable
ufw allow 22/tcp
ufw allow 8000/tcp
ufw reload

echo -e "${GREEN}✓ 防火墙配置完成${NC}"

# =====================================================
# 部署完成
# =====================================================
echo -e "\n========================================" 
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "========================================"

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me)

echo -e "\n${GREEN}服务信息:${NC}"
echo "  API文档: http://$SERVER_IP:8000/docs"
echo "  健康检查: http://$SERVER_IP:8000/api/v1/health"
echo ""
echo -e "${GREEN}服务管理命令:${NC}"
echo "  启动: systemctl start image-classifier"
echo "  停止: systemctl stop image-classifier"
echo "  重启: systemctl restart image-classifier"
echo "  状态: systemctl status image-classifier"
echo "  日志: journalctl -u image-classifier -f"
echo ""

# 测试健康检查
echo -e "${GREEN}测试健康检查...${NC}"
sleep 2
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "服务可能还在启动中，请稍等片刻"

echo -e "\n${YELLOW}重要提示:${NC}"
echo "1. 记得在阿里云控制台开放8000端口"
echo "2. MySQL classifier用户密码: Classifier@2024"
echo "3. 日志位置: /var/log/image-classifier/"
echo ""
echo "========================================" 

