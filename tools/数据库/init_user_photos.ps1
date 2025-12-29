# ====================================
# 初始化用户照片关系表（user_photos）
# 用于v2版本分类接口
# Windows PowerShell版本
# ====================================

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SqlFile = Join-Path $ScriptDir "create_user_photos.sql"

# 检查SQL文件是否存在
if (-not (Test-Path $SqlFile)) {
    Write-Host "错误: SQL文件不存在: $SqlFile" -ForegroundColor Red
    exit 1
}

# 读取数据库配置（从环境变量或使用默认值）
$MysqlHost = if ($env:MYSQL_HOST) { $env:MYSQL_HOST } else { "localhost" }
$MysqlPort = if ($env:MYSQL_PORT) { $env:MYSQL_PORT } else { "3306" }
$MysqlUser = if ($env:MYSQL_USER) { $env:MYSQL_USER } else { "root" }
$MysqlPassword = if ($env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD } else { "" }
$MysqlDatabase = if ($env:MYSQL_DATABASE) { $env:MYSQL_DATABASE } else { "image_classifier" }

Write-Host "========================================" -ForegroundColor Green
Write-Host "初始化用户照片关系表（user_photos）" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "数据库配置:"
Write-Host "  主机: $MysqlHost"
Write-Host "  端口: $MysqlPort"
Write-Host "  用户: $MysqlUser"
Write-Host "  数据库: $MysqlDatabase"
Write-Host ""

# 如果密码为空，提示输入
if ([string]::IsNullOrEmpty($MysqlPassword)) {
    Write-Host "提示: 未设置MYSQL_PASSWORD环境变量" -ForegroundColor Yellow
    $SecurePassword = Read-Host "请输入MySQL root密码" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
    $MysqlPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    Write-Host ""
}

# 执行SQL脚本
Write-Host "正在创建表..." -ForegroundColor Green

try {
    if ([string]::IsNullOrEmpty($MysqlPassword)) {
        Get-Content $SqlFile | mysql -h $MysqlHost -P $MysqlPort -u $MysqlUser $MysqlDatabase
    } else {
        $MysqlPassword | Get-Content $SqlFile | mysql -h $MysqlHost -P $MysqlPort -u $MysqlUser -p$MysqlPassword $MysqlDatabase
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 表创建成功！" -ForegroundColor Green
        Write-Host ""
        
        # 验证表是否存在
        Write-Host "验证表结构..." -ForegroundColor Green
        $VerifyQuery = "DESCRIBE user_photos;"
        
        if ([string]::IsNullOrEmpty($MysqlPassword)) {
            mysql -h $MysqlHost -P $MysqlPort -u $MysqlUser $MysqlDatabase -e $VerifyQuery | Out-Null
        } else {
            echo $MysqlPassword | mysql -h $MysqlHost -P $MysqlPort -u $MysqlUser -p$MysqlPassword $MysqlDatabase -e $VerifyQuery | Out-Null
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ 表结构验证通过！" -ForegroundColor Green
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "初始化完成！" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
        } else {
            Write-Host "⚠️  警告: 无法验证表结构" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ 表创建失败！" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ 执行失败: $_" -ForegroundColor Red
    exit 1
}

