# =====================================================
# 图片分类后端 - 快速部署脚本
# 使用 scp 同步代码到服务器
# 
# 部署策略：
# - 始终部署到 versions/debug 目录
# - current 符号链接指向 versions/debug
# - 适用于开发/测试环境的快速迭代
# 
# 注意：此脚本不支持版本管理和回滚
# 生产环境请使用 scripts/deploy-versioned.sh 或 CI/CD 自动部署
# 
# 使用方法：
#   .\deploy.ps1          # 交互式确认
#   .\deploy.ps1 -Force   # 跳过确认，直接部署
# =====================================================

param(
    [switch]$Force
)

$SERVER = "root@web"
$REMOTE_DIR = "/opt/ICBackend"  # 与文档保持一致
$LOCAL_DIR = $PSScriptRoot
$PYTHON_VERSION = "3.10"  # 指定 Python 版本

Write-Host "========================================" -ForegroundColor Green
Write-Host "图片分类后端 - 代码部署" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "服务器: $SERVER" -ForegroundColor Yellow
Write-Host "目标目录: $REMOTE_DIR" -ForegroundColor Yellow
Write-Host "本地目录: $LOCAL_DIR" -ForegroundColor Yellow
Write-Host ""

# 确认部署（支持 -Force 参数跳过确认）
if (-not $Force) {
    $confirm = Read-Host "确认部署到服务器? (y/n)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "部署已取消" -ForegroundColor Red
        exit
    }
} else {
    Write-Host "使用 -Force 参数，跳过确认..." -ForegroundColor Yellow
}

Write-Host "`n[1/6] 检查版本化目录结构..." -ForegroundColor Green

# 检查并创建 debug 版本目录
$versionCheckCmd = 'cd ' + $REMOTE_DIR + ' && ' +
    'CURRENT_LINK="' + $REMOTE_DIR + '/current" && ' +
    'VERSIONS_DIR="' + $REMOTE_DIR + '/versions" && ' +
    'DEBUG_VERSION_DIR="$VERSIONS_DIR/debug" && ' +
    'mkdir -p "$VERSIONS_DIR" && ' +
    'mkdir -p "$DEBUG_VERSION_DIR" && ' +
    'ln -sfn "$DEBUG_VERSION_DIR" "$CURRENT_LINK" && ' +
    'echo "$DEBUG_VERSION_DIR"'

$VERSION_DIR = ssh $SERVER $versionCheckCmd 2>&1 | Select-Object -Last 1

if ([string]::IsNullOrWhiteSpace($VERSION_DIR)) {
    Write-Host "  错误: 无法确定版本目录" -ForegroundColor Red
    exit 1
}

Write-Host "  版本目录: $VERSION_DIR (debug)" -ForegroundColor Cyan

Write-Host "`n[2/6] 同步代码文件..." -ForegroundColor Green

# 同步 app 目录到版本目录
Write-Host "  同步 app/ 目录..." -ForegroundColor Cyan
scp -r "$LOCAL_DIR\app" "${SERVER}:${VERSION_DIR}/" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  错误: app 目录同步失败" -ForegroundColor Red
    exit 1
}

# 同步其他重要文件到版本目录
$importantFiles = @(
    "requirements.txt",
    "gunicorn_config.py",
    "env.example",
    "env.example.secrets"
)

foreach ($file in $importantFiles) {
    $filePath = Join-Path $LOCAL_DIR $file
    if (Test-Path $filePath) {
        Write-Host "  同步 $file..." -ForegroundColor Cyan
        scp "$filePath" "${SERVER}:${VERSION_DIR}/" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  警告: $file 同步失败" -ForegroundColor Yellow
        }
    }
}

# 同步 prompts 目录（如果存在）
$promptsPath = Join-Path $LOCAL_DIR "prompts"
if (Test-Path $promptsPath) {
    Write-Host "  同步 prompts/ 目录..." -ForegroundColor Cyan
    scp -r "$promptsPath" "${SERVER}:${VERSION_DIR}/" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  警告: prompts 目录同步失败" -ForegroundColor Yellow
    }
}

# 同步 tests 目录（用于服务器端测试）
$testsPath = Join-Path $LOCAL_DIR "tests"
if (Test-Path $testsPath) {
    Write-Host "  同步 tests/ 目录..." -ForegroundColor Cyan
    scp -r "$testsPath" "${SERVER}:${VERSION_DIR}/" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  警告: tests 目录同步失败" -ForegroundColor Yellow
    }
}

# 同步 pytest.ini（如果存在）
$pytestIniPath = Join-Path $LOCAL_DIR "pytest.ini"
if (Test-Path $pytestIniPath) {
    Write-Host "  同步 pytest.ini..." -ForegroundColor Cyan
    scp "$pytestIniPath" "${SERVER}:${VERSION_DIR}/" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  警告: pytest.ini 同步失败" -ForegroundColor Yellow
    }
}

Write-Host "✓ 代码同步完成" -ForegroundColor Green

Write-Host "`n[3/6] 检查配置文件..." -ForegroundColor Green
# 检查并初始化共享配置文件（如果不存在）
$configCmd = 'cd ' + $REMOTE_DIR + ' && ' +
    'if [ ! -f .env ]; then ' +
    'if [ -f "' + $VERSION_DIR + '/env.example" ]; then ' +
    'echo "  从 env.example 创建 .env 文件..."; ' +
    'cp "' + $VERSION_DIR + '/env.example" .env && ' +
    'echo "  警告: 请编辑 .env 文件配置数据库和API密钥等敏感信息"; ' +
    'fi; ' +
    'else ' +
    'echo "  .env 文件已存在，跳过初始化"; ' +
    'fi && ' +
    'if [ ! -f .env.secrets ]; then ' +
    'if [ -f "' + $VERSION_DIR + '/env.example.secrets" ]; then ' +
    'echo "  从 env.example.secrets 创建 .env.secrets 文件..."; ' +
    'cp "' + $VERSION_DIR + '/env.example.secrets" .env.secrets && ' +
    'chmod 600 .env.secrets && ' +
    'echo "  警告: 请编辑 .env.secrets 文件填入实际的敏感信息"; ' +
    'fi; ' +
    'else ' +
    'echo "  .env.secrets 文件已存在，跳过初始化"; ' +
    'fi && ' +
    'ln -sfn "' + $REMOTE_DIR + '/.env" "' + $VERSION_DIR + '/.env" && ' +
    'ln -sfn "' + $REMOTE_DIR + '/.env.secrets" "' + $VERSION_DIR + '/.env.secrets" 2>/dev/null || true && ' +
    'echo "  ✓ 已创建配置文件符号链接"'
ssh $SERVER $configCmd 2>&1 | Out-Null

Write-Host "`n[4/6] 检查共享虚拟环境..." -ForegroundColor Green
# 检查并创建共享虚拟环境
$venvCmd = 'cd ' + $REMOTE_DIR + ' && ' +
    'SHARED_VENV="' + $REMOTE_DIR + '/venv" && ' +
    'if [ ! -d "$SHARED_VENV" ]; then ' +
    'echo "  创建共享虚拟环境..."; ' +
    'if command -v python' + $PYTHON_VERSION + ' &> /dev/null; then ' +
    'python' + $PYTHON_VERSION + ' -m venv "$SHARED_VENV"; ' +
    'elif command -v python3 &> /dev/null; then ' +
    'python3 -m venv "$SHARED_VENV"; ' +
    'else ' +
    'echo "错误: 未找到 Python 3"; ' +
    'exit 1; ' +
    'fi; ' +
    'echo "  安装依赖到共享虚拟环境..."; ' +
    'source "$SHARED_VENV/bin/activate" && ' +
    'pip install --upgrade pip --quiet && ' +
    'pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu --quiet && ' +
    'pip install -r "' + $VERSION_DIR + '/requirements.txt" --quiet && ' +
    'deactivate; ' +
    'else ' +
    'echo "  ✓ 共享虚拟环境已存在"; ' +
    'echo "  更新依赖..."; ' +
    'source "$SHARED_VENV/bin/activate" && ' +
    'pip install --upgrade pip --quiet && ' +
    'pip install -r "' + $VERSION_DIR + '/requirements.txt" --quiet --upgrade && ' +
    'deactivate; ' +
    'fi && ' +
    'ln -sfn "$SHARED_VENV" "' + $VERSION_DIR + '/venv" && ' +
    'echo "  ✓ 已创建虚拟环境符号链接"'
ssh $SERVER $venvCmd 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 虚拟环境检查完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 虚拟环境检查可能有问题，请手动检查" -ForegroundColor Yellow
}

Write-Host "`n[5/6] 重启服务..." -ForegroundColor Green
ssh $SERVER "systemctl daemon-reload && systemctl restart image-classifier" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 服务重启完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 服务重启失败，请手动检查" -ForegroundColor Yellow
}

Write-Host "`n[6/6] 检查服务状态..." -ForegroundColor Green
$status = ssh $SERVER "systemctl status image-classifier --no-pager | head -n 5" 2>&1
Write-Host $status

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "查看服务日志: ssh $SERVER 'journalctl -u image-classifier -f'" -ForegroundColor Cyan
Write-Host "查看服务状态: ssh $SERVER 'systemctl status image-classifier'" -ForegroundColor Cyan
Write-Host ""

