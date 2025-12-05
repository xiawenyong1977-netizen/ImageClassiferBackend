#!/bin/bash
# 快速更新菜单代码到服务器

SERVER="admin.xintuxiangce.top"
SERVER_USER="root"
SERVER_PATH="/opt/ImageClassifierBackend"

echo "正在更新服务器代码..."
echo "服务器: $SERVER"
echo "文件: app/api/auth.py"
echo

# 上传更新后的文件
scp app/api/auth.py ${SERVER_USER}@${SERVER}:${SERVER_PATH}/app/api/auth.py

echo
echo "文件上传完成！"
echo
echo "请在服务器上执行以下命令重启服务："
echo "  systemctl restart image-classifier"
echo "  或"
echo "  cd $SERVER_PATH && systemctl restart image-classifier"
echo

