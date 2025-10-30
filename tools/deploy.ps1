param(
  [string]$Server      = "123.57.68.4",
  [string]$User        = "root",
  [string]$RemoteDir   = "/opt/ImageClassifierBackend",
  [string]$ServiceName = "image-classifier",
  [int]$TailLines      = 120
)

$ErrorActionPreference = "Stop"

# 需要部署的文件（按需增减）
$Files = @(
  "app/database.py"
)

function ThrowIfFailed($Message) {
  if ($LASTEXITCODE -ne 0) {
    throw $Message
  }
}

# 进入本地项目根目录（请确认路径）
Set-Location "D:\ImageClassifierBackend"

# 打印计划
Write-Host "Deploying to $User@$Server → $RemoteDir" -ForegroundColor Cyan
Write-Host "Service: $ServiceName" -ForegroundColor Cyan
Write-Host "Files: `n  $($Files -join "`n  ")`n" -ForegroundColor Cyan

# 1) 远程创建备份目录
$Timestamp = (Get-Date -Format "yyyyMMdd_HHmmss")
$BackupDir = "/root/deploy_backups/$Timestamp"

ssh "$User@$Server" "mkdir -p $BackupDir"
ThrowIfFailed "远程创建备份目录失败"

# 2) 逐个备份远程旧文件
foreach ($f in $Files) {
  $RemoteFile = "$RemoteDir/$f"
  $RemoteParent = [System.IO.Path]::GetDirectoryName($RemoteFile)
  $BackupFile = "$BackupDir/$($f -replace '/', '_').bak"

  ssh "$User@$Server" "test -f $RemoteFile && cp -f $RemoteFile $BackupFile || echo 'skip:$RemoteFile not exist'"
  ThrowIfFailed "远程备份失败: $RemoteFile"

  ssh "$User@$Server" "mkdir -p $RemoteParent"
  ThrowIfFailed "远程创建目录失败: $RemoteParent"
}


# 3) 传输新文件
foreach ($f in $Files) {
  scp -o StrictHostKeyChecking=no $f "${User}@${Server}:$RemoteDir/$f"
  ThrowIfFailed "SCP 失败: $f"
}

# 4) 重启服务并查看状态
ssh "${User}@${Server}" "systemctl restart $ServiceName"
ThrowIfFailed "重启服务失败: $ServiceName"

Start-Sleep -Seconds 2
ssh "${User}@${Server}" "systemctl status $ServiceName --no-pager"
ssh "${User}@${Server}" "journalctl -u $ServiceName -n $TailLines --no-pager"

# 回滚提示
Write-Host "  scp ${User}@${Server}:${BackupDir}/app_api_user.py.bak D:\ImageClassifierBackend\app\api\user.py" -ForegroundColor Yellow
Write-Host "  scp ${User}@${Server}:${BackupDir}/app_api_auth.py.bak D:\ImageClassifierBackend\app\api\auth.py" -ForegroundColor Yellow
Write-Host "  ssh ${User}@${Server} 'systemctl restart $ServiceName && systemctl status $ServiceName --no-pager'" -ForegroundColor Yellow