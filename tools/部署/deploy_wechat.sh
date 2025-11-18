#!/bin/bash
# 微信扫码关注功能部署脚本

echo "========================================"
echo "微信扫码关注功能部署"
echo "========================================"

# 服务器配置
SERVER_USER="root"
SERVER_HOST="123.57.68.4"
SERVER_PATH="/root/ImageClassifierBackend"

echo "📦 准备部署文件到服务器: $SERVER_HOST"

# 需要上传的文件列表
FILES=(
    "app/main.py"
    "app/api/auth.py"
    "app/api/user.py"
    "app/api/image_edit.py"
    "app/services/image_editor.py"
    "app/config.py"
    "tools/数据库/add_wechat_qrcode_bindings.sql"
)

echo ""
echo "需要上传的文件:"
for file in "${FILES[@]}"; do
    echo "  - $file"
done

echo ""
read -p "确认上传到服务器 $SERVER_HOST 吗? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "取消部署"
    exit 0
fi

echo ""
echo "📤 上传文件到服务器..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "上传: $file"
        scp "$file" "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/$file"
        if [ $? -eq 0 ]; then
            echo "  ✓ 上传成功"
        else
            echo "  ✗ 上传失败"
            exit 1
        fi
    else
        echo "⚠️  文件不存在: $file"
    fi
done

echo ""
echo "✅ 文件上传完成！"
echo ""
echo "========================================"
echo "下一步操作（请在服务器上执行）："
echo "========================================"
echo ""
echo "1. 创建数据库表（如果还没执行）："
echo "   ssh $SERVER_USER@$SERVER_HOST"
echo "   cd $SERVER_PATH"
echo "   mysql -u root -p image_classifier < tools/数据库/add_wechat_qrcode_bindings.sql"
echo ""
echo "2. 检查环境变量："
echo "   cat .env | grep WECHAT"
echo ""
echo "3. 重启服务："
echo "   bash deploy-to-server.sh"
echo "   # 或"
echo "   systemctl restart imageclassifier"
echo ""
echo "4. 查看日志确认启动成功："
echo "   journalctl -u imageclassifier -n 50 -f"
echo ""
echo "5. 测试接口："
echo "   curl https://admin.xintuxiangce.top/api/v1/health"
echo ""
echo "========================================"
