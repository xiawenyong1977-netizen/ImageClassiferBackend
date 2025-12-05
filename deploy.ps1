# =====================================================
# 图片分类后端 - 快速部署脚本
# 使用 scp 同步代码到服务器
# =====================================================

$SERVER = "root@app"
$REMOTE_DIR = "/opt/ImageClassifierBackend"
$LOCAL_DIR = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Green
Write-Host "图片分类后端 - 代码部署" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "服务器: $SERVER" -ForegroundColor Yellow
Write-Host "目标目录: $REMOTE_DIR" -ForegroundColor Yellow
Write-Host "本地目录: $LOCAL_DIR" -ForegroundColor Yellow
Write-Host ""

# 确认部署
$confirm = Read-Host "确认部署到服务器? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "部署已取消" -ForegroundColor Red
    exit
}

Write-Host "`n[1/4] 同步代码文件..." -ForegroundColor Green

# 使用 scp 同步代码（排除不需要的文件）
# 注意：scp 不支持 --exclude，所以我们需要先创建临时文件列表
$excludePatterns = @(
    ".git",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache",
    "venv",
    ".venv",
    "*.log",
    ".env",
    "*.tar.gz",
    "*.zip",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~"
)

# 创建临时排除文件列表
$excludeFile = Join-Path $env:TEMP "scp_exclude_$(Get-Date -Format 'yyyyMMddHHmmss').txt"
$excludePatterns | ForEach-Object { Add-Content -Path $excludeFile -Value $_ }

Write-Host "正在同步文件..." -ForegroundColor Cyan

# 使用 rsync 风格的排除方式，但 scp 不支持，所以我们直接同步主要目录
# 先同步 app 目录
Write-Host "  同步 app/ 目录..." -ForegroundColor Cyan
scp -r "$LOCAL_DIR\app" "${SERVER}:${REMOTE_DIR}/" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  错误: app 目录同步失败" -ForegroundColor Red
    exit 1
}

# 同步其他重要文件和目录
$importantFiles = @(
    "requirements.txt",
    "gunicorn_config.py",
    "env.example",
    "README.md"
)

foreach ($file in $importantFiles) {
    $filePath = Join-Path $LOCAL_DIR $file
    if (Test-Path $filePath) {
        Write-Host "  同步 $file..." -ForegroundColor Cyan
        scp "$filePath" "${SERVER}:${REMOTE_DIR}/" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  警告: $file 同步失败" -ForegroundColor Yellow
        }
    }
}

# 同步 tools 目录（如果需要）
if (Test-Path "$LOCAL_DIR\tools") {
    Write-Host "  同步 tools/ 目录..." -ForegroundColor Cyan
    scp -r "$LOCAL_DIR\tools" "${SERVER}:${REMOTE_DIR}/" 2>&1 | Out-Null
}

Write-Host "✓ 代码同步完成" -ForegroundColor Green

# 清理临时文件
Remove-Item $excludeFile -ErrorAction SilentlyContinue

Write-Host "`n[2/4] 在服务器上安装依赖..." -ForegroundColor Green
ssh $SERVER "cd $REMOTE_DIR && source venv/bin/activate && pip install -r requirements.txt --quiet" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 依赖安装可能有问题，请手动检查" -ForegroundColor Yellow
}

Write-Host "`n[3/4] 重启服务..." -ForegroundColor Green
ssh $SERVER "systemctl restart image-classifier" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 服务重启完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 服务重启失败，请手动检查" -ForegroundColor Yellow
}

Write-Host "`n[4/4] 检查服务状态..." -ForegroundColor Green
$status = ssh $SERVER "systemctl status image-classifier --no-pager | head -n 5" 2>&1
Write-Host $status

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "查看服务日志: ssh $SERVER 'journalctl -u image-classifier -f'" -ForegroundColor Cyan
Write-Host "查看服务状态: ssh $SERVER 'systemctl status image-classifier'" -ForegroundColor Cyan
Write-Host ""

