# PowerShell脚本：启动MySQL测试容器
# 用于本地测试

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动MySQL测试数据库容器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Docker是否安装
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker命令执行失败"
    }
    Write-Host "✓ Docker已安装: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误：未找到Docker！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装Docker Desktop：" -ForegroundColor Yellow
    Write-Host "  https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 检查Docker是否运行
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 错误：Docker Desktop未运行！" -ForegroundColor Red
        Write-Host ""
        Write-Host "请执行以下步骤：" -ForegroundColor Yellow
        Write-Host "  1. 启动Docker Desktop应用" -ForegroundColor White
        Write-Host "  2. 等待Docker完全启动（系统托盘图标变为绿色）" -ForegroundColor White
        Write-Host "  3. 重新运行此脚本" -ForegroundColor White
        Write-Host ""
        Write-Host "如果问题仍然存在，请尝试：" -ForegroundColor Yellow
        Write-Host "  - 重启Docker Desktop" -ForegroundColor White
        Write-Host "  - 检查Docker Desktop设置 > Resources 确保有足够资源" -ForegroundColor White
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "❌ 错误：无法连接到Docker守护进程！" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "✓ Docker正在运行" -ForegroundColor Green
Write-Host ""

# 切换到项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

# 检查容器是否已运行
$existingContainer = docker ps -a --filter "name=image-classifier-mysql-test" --format "{{.Names}}"

if ($existingContainer -eq "image-classifier-mysql-test") {
    Write-Host "检测到已存在的容器..." -ForegroundColor Yellow
    
    $running = docker ps --filter "name=image-classifier-mysql-test" --format "{{.Names}}"
    if ($running -eq "image-classifier-mysql-test") {
        Write-Host "✓ MySQL容器已在运行" -ForegroundColor Green
        Write-Host ""
        Write-Host "数据库连接信息：" -ForegroundColor Cyan
        Write-Host "  Host: localhost" -ForegroundColor White
        Write-Host "  Port: 3307" -ForegroundColor White
        Write-Host "  User: root" -ForegroundColor White
        Write-Host "  Password: test_password" -ForegroundColor White
        Write-Host "  Database: image_classifier_test" -ForegroundColor White
        Write-Host ""
        exit 0
    } else {
        Write-Host "启动已存在的容器..." -ForegroundColor Yellow
        docker start image-classifier-mysql-test | Out-Null
        Write-Host "✓ 容器已启动" -ForegroundColor Green
    }
} else {
    Write-Host "创建新的MySQL容器..." -ForegroundColor Yellow
    
    # 先尝试拉取镜像
    Write-Host "正在拉取MySQL 8.0镜像..." -ForegroundColor Yellow
    $pullResult = docker pull mysql:8.0 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 镜像拉取失败" -ForegroundColor Red
        Write-Host ""
        Write-Host "错误信息：" -ForegroundColor Yellow
        Write-Host $pullResult -ForegroundColor Gray
        Write-Host ""
        Write-Host "这通常是网络连接问题，请尝试以下解决方案：" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "【推荐】配置Docker镜像源（中国大陆用户）：" -ForegroundColor Cyan
        Write-Host "  1. 打开Docker Desktop > 设置 > Docker Engine" -ForegroundColor White
        Write-Host "  2. 添加以下配置到JSON：" -ForegroundColor White
        Write-Host ""
        Write-Host '  {' -ForegroundColor Gray
        Write-Host '    "registry-mirrors": [' -ForegroundColor Gray
        Write-Host '      "https://docker.m.daocloud.io",' -ForegroundColor Gray
        Write-Host '      "https://dockerproxy.com"' -ForegroundColor Gray
        Write-Host '    ]' -ForegroundColor Gray
        Write-Host '  }' -ForegroundColor Gray
        Write-Host ""
        Write-Host "  3. 点击 Apply & Restart 重启Docker" -ForegroundColor White
        Write-Host "  4. 详细配置说明请查看：tests/Docker镜像源配置说明.md" -ForegroundColor White
        Write-Host ""
        Write-Host "【备选方案】临时使用镜像源拉取：" -ForegroundColor Cyan
        Write-Host '  docker pull docker.m.daocloud.io/library/mysql:8.0' -ForegroundColor White
        Write-Host '  docker tag docker.m.daocloud.io/library/mysql:8.0 mysql:8.0' -ForegroundColor White
        Write-Host ""
        Write-Host "其他解决方案：" -ForegroundColor Yellow
        Write-Host "  - 检查网络连接和防火墙设置" -ForegroundColor White
        Write-Host "  - 如果使用代理，在Docker Desktop中配置代理" -ForegroundColor White
        Write-Host ""
        exit 1
    }
    Write-Host "✓ 镜像拉取成功" -ForegroundColor Green
    
    # 启动容器
    Write-Host "正在启动容器..." -ForegroundColor Yellow
    # 过滤掉"your"变量相关的警告（这是docker-compose的误报，不影响功能）
    $composeResult = docker-compose -f docker-compose.test.yml up -d 2>&1 | Where-Object { $_ -notmatch 'The "your" variable is not set' }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 容器启动失败" -ForegroundColor Red
        Write-Host ""
        Write-Host "错误详情：" -ForegroundColor Yellow
        # 只显示真正的错误，忽略"your"变量警告
        $realErrors = $composeResult | Where-Object { $_ -notmatch 'The "your" variable is not set' -and $_ -notmatch 'the attribute.*version.*is obsolete' }
        if ($realErrors) {
            Write-Host $realErrors -ForegroundColor Red
        }
        Write-Host ""
        exit 1
    }
    Write-Host "✓ 容器已创建并启动" -ForegroundColor Green
}

# 等待数据库就绪
Write-Host ""
Write-Host "等待数据库启动..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    docker exec image-classifier-mysql-test mysqladmin ping -h localhost -u root -ptest_password 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ MySQL数据库已就绪" -ForegroundColor Green
        break
    }
    $attempt++
    Start-Sleep -Seconds 2
    Write-Host "  等待中... ($attempt/$maxAttempts)" -ForegroundColor Gray
}

if ($attempt -ge $maxAttempts) {
    Write-Host "❌ 数据库启动超时" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySQL测试数据库已启动！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "连接信息：" -ForegroundColor Cyan
Write-Host "  Host:     localhost" -ForegroundColor White
Write-Host "  Port:     3307" -ForegroundColor White
Write-Host "  User:     root" -ForegroundColor White
Write-Host "  Password: test_password" -ForegroundColor White
Write-Host "  Database: image_classifier_test" -ForegroundColor White
Write-Host ""
Write-Host "注意：需要在.env文件中配置：" -ForegroundColor Yellow
Write-Host "  MYSQL_HOST=localhost" -ForegroundColor White
Write-Host "  MYSQL_PORT=3307" -ForegroundColor White
Write-Host "  MYSQL_USER=root" -ForegroundColor White
Write-Host "  MYSQL_PASSWORD=test_password" -ForegroundColor White
Write-Host "  MYSQL_DATABASE=image_classifier_test" -ForegroundColor White
Write-Host ""
Write-Host "停止容器：" -ForegroundColor Yellow
Write-Host "  docker stop image-classifier-mysql-test" -ForegroundColor White
Write-Host ""
Write-Host "删除容器：" -ForegroundColor Yellow
Write-Host "  docker-compose -f docker-compose.test.yml down" -ForegroundColor White
Write-Host ""


