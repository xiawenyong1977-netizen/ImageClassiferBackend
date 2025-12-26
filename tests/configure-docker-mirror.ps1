# PowerShell脚本：配置Docker镜像源
# 用于解决无法从Docker Hub拉取镜像的问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置Docker镜像源" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Docker是否安装
try {
    docker --version | Out-Null
    Write-Host "✓ Docker已安装" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误：未找到Docker！" -ForegroundColor Red
    Write-Host "请先安装Docker Desktop" -ForegroundColor Yellow
    exit 1
}

# 配置文件路径
$daemonJsonPath = Join-Path $env:USERPROFILE ".docker\daemon.json"
$dockerDir = Split-Path -Parent $daemonJsonPath

# 确保.docker目录存在
if (-not (Test-Path $dockerDir)) {
    New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
    Write-Host "✓ 创建Docker配置目录" -ForegroundColor Green
}

# 镜像源配置
$mirrors = @(
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.nju.edu.cn"
)

Write-Host ""
Write-Host "配置的镜像源：" -ForegroundColor Cyan
foreach ($mirror in $mirrors) {
    Write-Host "  - $mirror" -ForegroundColor White
}
Write-Host ""

# 读取现有配置
$config = @{}
if (Test-Path $daemonJsonPath) {
    try {
        $existingJson = Get-Content $daemonJsonPath -Raw
        $existingContent = $existingJson | ConvertFrom-Json
        Write-Host "✓ 找到现有配置文件，将合并配置" -ForegroundColor Green
        
        # 转换为哈希表
        $config = @{}
        $existingContent.PSObject.Properties | ForEach-Object {
            $config[$_.Name] = $_.Value
        }
    } catch {
        Write-Host "⚠ 现有配置文件格式错误，将创建新配置" -ForegroundColor Yellow
        $config = @{}
    }
} else {
    Write-Host "✓ 创建新配置文件" -ForegroundColor Green
}

# 添加或更新镜像源配置
$existingMirrors = @()
if ($config.ContainsKey("registry-mirrors")) {
    $existingMirrors = if ($config["registry-mirrors"] -is [Array]) { 
        $config["registry-mirrors"] 
    } else { 
        @($config["registry-mirrors"]) 
    }
}

# 合并镜像源，避免重复
$allMirrors = ($mirrors + $existingMirrors) | Select-Object -Unique
$config["registry-mirrors"] = $allMirrors

# 转换为JSON并格式化
$jsonContent = $config | ConvertTo-Json -Depth 10 -Compress:$false

# 备份现有配置
if (Test-Path $daemonJsonPath) {
    $backupPath = "$daemonJsonPath.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item $daemonJsonPath $backupPath -Force
    Write-Host "✓ 已备份现有配置到: $backupPath" -ForegroundColor Green
}

# 写入新配置
try {
    # 确保JSON格式正确（添加缩进）
    $formattedJson = $jsonContent | ConvertFrom-Json | ConvertTo-Json -Depth 10
    $formattedJson | Set-Content $daemonJsonPath -Encoding UTF8
    Write-Host "✓ 配置文件已更新: $daemonJsonPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "配置文件内容：" -ForegroundColor Cyan
    Write-Host $formattedJson -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "❌ 写入配置文件失败: $_" -ForegroundColor Red
    exit 1
}

# 提示重启Docker
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠ 重要：请重启Docker Desktop使配置生效" -ForegroundColor Yellow
Write-Host ""
Write-Host "重启方法：" -ForegroundColor Cyan
Write-Host "  1. 右键点击系统托盘中的Docker图标" -ForegroundColor White
Write-Host "  2. 选择 'Restart Docker Desktop' 或 'Quit Docker Desktop' 然后重新启动" -ForegroundColor White
Write-Host ""
Write-Host "验证配置（重启后运行）：" -ForegroundColor Cyan
Write-Host '  docker info | Select-String -Pattern "Registry Mirrors"' -ForegroundColor White
Write-Host ""
Write-Host "配置完成后，重新运行 docker-mysql-start.ps1 脚本" -ForegroundColor Green
Write-Host ""

