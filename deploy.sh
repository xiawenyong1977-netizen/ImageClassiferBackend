#!/bin/bash

# =====================================================
# 图片分类后端 - 快速部署脚本 (Linux/Mac)
# 使用 scp 同步代码到服务器
# =====================================================

SERVER="root@app"
REMOTE_DIR="/opt/ImageClassifierBackend"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "图片分类后端 - 代码部署"
echo "========================================"
echo "服务器: $SERVER"
echo "目标目录: $REMOTE_DIR"
echo "本地目录: $LOCAL_DIR"
echo ""

# 确认部署
read -p "确认部署到服务器? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 1
fi

echo ""
echo "[1/4] 同步代码文件..."

# 同步 app 目录
echo "  同步 app/ 目录..."
scp -r "$LOCAL_DIR/app" "${SERVER}:${REMOTE_DIR}/" || {
    echo "  错误: app 目录同步失败"
    exit 1
}

# 同步其他重要文件
echo "  同步重要文件..."
scp "$LOCAL_DIR/requirements.txt" "${SERVER}:${REMOTE_DIR}/" 2>/dev/null
scp "$LOCAL_DIR/gunicorn_config.py" "${SERVER}:${REMOTE_DIR}/" 2>/dev/null
scp "$LOCAL_DIR/env.example" "${SERVER}:${REMOTE_DIR}/" 2>/dev/null

# 同步 tools 目录（如果需要）
if [ -d "$LOCAL_DIR/tools" ]; then
    echo "  同步 tools/ 目录..."
    scp -r "$LOCAL_DIR/tools" "${SERVER}:${REMOTE_DIR}/" 2>/dev/null
fi

echo "✓ 代码同步完成"

echo ""
echo "[2/4] 在服务器上安装依赖..."
ssh $SERVER "cd $REMOTE_DIR && source venv/bin/activate && pip install -r requirements.txt --quiet" || {
    echo "  警告: 依赖安装可能有问题，请手动检查"
}

echo ""
echo "[3/4] 重启服务..."
ssh $SERVER "systemctl restart image-classifier" || {
    echo "  警告: 服务重启失败，请手动检查"
}

echo ""
echo "[4/4] 检查服务状态..."
ssh $SERVER "systemctl status image-classifier --no-pager | head -n 5"

echo ""
echo "========================================"
echo "部署完成！"
echo "========================================"
echo ""
echo "查看服务日志: ssh $SERVER 'journalctl -u image-classifier -f'"
echo "查看服务状态: ssh $SERVER 'systemctl status image-classifier'"
echo ""


