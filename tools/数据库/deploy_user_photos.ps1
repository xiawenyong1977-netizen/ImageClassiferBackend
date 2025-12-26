# ====================================
# 在服务器上初始化user_photos表
# Windows PowerShell版本
# 支持主从复制环境（在主库执行，自动同步到从库）
# ====================================

# 服务器配置
$AppServer = "root@app"  # 主库服务器
$WebServer = "root@web"  # 从库服务器（可选）

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SqlFile = Join-Path $ScriptDir "create_user_photos.sql"
$RemoteSqlPath = "/tmp/create_user_photos.sql"

# 检查SQL文件是否存在
if (-not (Test-Path $SqlFile)) {
    Write-Host "错误: SQL文件不存在: $SqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "在服务器上初始化user_photos表" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 检查SSH连接
Write-Host "[1/3] 检查SSH连接..." -ForegroundColor Yellow
try {
    $result = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${AppServer} "echo '连接成功'" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ App服务器连接成功" -ForegroundColor Green
    } else {
        throw "连接失败"
    }
} catch {
    Write-Host "❌ 无法连接到App服务器: ${AppServer}" -ForegroundColor Red
    Write-Host "提示: 请确保SSH密钥已配置，可以无密码登录" -ForegroundColor Yellow
    exit 1
}

# 上传SQL文件到服务器
Write-Host "[2/3] 上传SQL文件到服务器..." -ForegroundColor Yellow
try {
    scp $SqlFile "${AppServer}:${RemoteSqlPath}"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SQL文件已上传" -ForegroundColor Green
    } else {
        throw "上传失败"
    }
} catch {
    Write-Host "❌ 文件上传失败" -ForegroundColor Red
    exit 1
}

# 在服务器上执行SQL脚本
Write-Host "[3/3] 在服务器上执行SQL脚本..." -ForegroundColor Yellow
Write-Host "提示: 如果MySQL需要密码，请输入密码" -ForegroundColor Yellow
Write-Host ""

try {
    ssh ${AppServer} "mysql -u root -p image_classifier < ${RemoteSqlPath}"
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ 表创建成功！" -ForegroundColor Green
    } else {
        throw "执行失败"
    }
} catch {
    Write-Host "❌ SQL执行失败" -ForegroundColor Red
    Write-Host "提示: 请检查MySQL密码是否正确" -ForegroundColor Yellow
    exit 1
}

# 验证表是否创建成功
Write-Host ""
Write-Host "验证表结构..." -ForegroundColor Yellow
try {
    ssh ${AppServer} "mysql -u root -p image_classifier -e 'DESCRIBE user_photos;'"
} catch {
    Write-Host "⚠️  无法验证表结构（可能需要输入密码）" -ForegroundColor Yellow
}

# 清理临时文件
Write-Host ""
Write-Host "清理临时文件..." -ForegroundColor Yellow
ssh ${AppServer} "rm -f ${RemoteSqlPath}" 2>&1 | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "初始化完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "注意:" -ForegroundColor Yellow
Write-Host "  - 如果配置了主从复制，表会自动同步到从库（web服务器）"
Write-Host "  - 可以在从库执行以下命令验证同步："
Write-Host "    ssh ${WebServer} `"mysql -u root -p image_classifier -e 'DESCRIBE user_photos;'`"" -ForegroundColor Green

