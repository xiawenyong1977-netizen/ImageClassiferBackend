# PowerShell脚本：停止MySQL测试容器

Write-Host "停止MySQL测试数据库容器..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

docker-compose -f docker-compose.test.yml down

Write-Host "✓ MySQL容器已停止" -ForegroundColor Green
Write-Host ""



