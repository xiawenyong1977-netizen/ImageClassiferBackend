# PowerShell脚本 - 快速更新菜单代码到服务器

$SERVER = "admin.xintuxiangce.top"
$SERVER_USER = "root"
$SERVER_PATH = "/opt/ImageClassifierBackend"

Write-Host "正在更新服务器代码..." -ForegroundColor Green
Write-Host "服务器: $SERVER"
Write-Host "文件: app/api/auth.py"
Write-Host ""

# 使用scp上传文件（需要先安装OpenSSH客户端）
# 或者使用WinSCP、FileZilla等工具手动上传

Write-Host "请使用以下方法之一上传文件：" -ForegroundColor Yellow
Write-Host ""
Write-Host "方法1: 使用scp命令（如果已安装OpenSSH）" -ForegroundColor Cyan
Write-Host "  scp app/api/auth.py ${SERVER_USER}@${SERVER}:${SERVER_PATH}/app/api/auth.py"
Write-Host ""
Write-Host "方法2: 使用WinSCP或FileZilla等工具" -ForegroundColor Cyan
Write-Host "  服务器: $SERVER"
Write-Host "  路径: $SERVER_PATH/app/api/"
Write-Host "  文件: auth.py"
Write-Host ""
Write-Host "上传完成后，在服务器上执行：" -ForegroundColor Yellow
Write-Host "  systemctl restart image-classifier" -ForegroundColor Green
Write-Host ""

