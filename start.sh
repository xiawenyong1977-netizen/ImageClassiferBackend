#!/bin/bash

# 图片分类后端启动脚本

echo "========================================" 
echo "图片分类后端服务启动脚本"
echo "========================================"

# 检查conda环境
if ! conda env list | grep -q "wechat-classifier"; then
    echo "❌ 错误：未找到conda环境 'wechat-classifier'"
    echo "请先创建conda环境：conda create -n wechat-classifier python=3.10"
    exit 1
fi

# 激活环境
echo "✅ 激活conda环境..."
eval "$(conda shell.bash hook)"
conda activate wechat-classifier

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告：未找到.env文件"
    echo "请复制 env.example 为 .env 并配置：cp env.example .env"
    exit 1
fi

echo "✅ 环境变量已加载"

# 检查MySQL连接
echo "🔍 检查MySQL连接..."
# (这里可以添加MySQL连接检查逻辑)

# 启动服务
echo "========================================" 
echo "启动选项："
echo "1. 开发模式（Uvicorn + 热重载）"
echo "2. 生产模式（Gunicorn）"
echo "========================================" 
read -p "请选择 (1/2): " choice

case $choice in
    1)
        echo "🚀 启动开发模式..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    2)
        echo "🚀 启动生产模式..."
        gunicorn -c gunicorn_config.py app.main:app
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

