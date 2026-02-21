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
#   .\deploy.ps1                    # 交互式确认，全量部署
#   .\deploy.ps1 -Force             # 跳过确认，全量部署
#   .\deploy.ps1 -Incremental       # 增量部署（基于 git 检测变更文件）
#   .\deploy.ps1 -Force -Incremental # 增量部署，跳过确认
# 
# 增量部署说明：
# - 检测工作区变更文件（需要项目是 git 仓库）
#   * 未跟踪的新文件
#   * 工作区中已修改但未提交的文件
# - 只同步工作区未提交的修改，加快部署速度
# - 已提交但未 push 的文件不会自动部署（需要先 push 后再部署）
# - requirements.txt 等重要文件总是同步（即使未变更）
# - 如果不是 git 仓库，会自动回退到全量部署
# =====================================================

param(
    [switch]$Force,
    [switch]$Incremental
)

$SERVER = "root@app"
$REMOTE_DIR = "/opt/ICBackend"  # 与文档保持一致
$LOCAL_DIR = $PSScriptRoot
$PYTHON_VERSION = "3.10"  # 指定 Python 版本

Write-Host "========================================" -ForegroundColor Green
Write-Host "图片分类后端 - 代码部署" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "服务器: $SERVER" -ForegroundColor Yellow
Write-Host "目标目录: $REMOTE_DIR" -ForegroundColor Yellow
Write-Host "本地目录: $LOCAL_DIR" -ForegroundColor Yellow
if ($Incremental) {
    Write-Host "部署模式: 增量部署（只同步工作区未提交的修改）" -ForegroundColor Cyan
} else {
    Write-Host "部署模式: 全量部署" -ForegroundColor Cyan
}
Write-Host ""

# 确认部署（支持 -Force 参数跳过确认）
if (-not $Force) {
    try {
        $confirm = Read-Host "确认部署到服务器? (y/n)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "部署已取消" -ForegroundColor Red
            exit
        }
    } catch {
        # 非交互模式（如 CI/CD），自动确认
        Write-Host "非交互模式，自动确认部署..." -ForegroundColor Yellow
    }
} else {
    Write-Host "使用 -Force 参数，跳过确认..." -ForegroundColor Yellow
}

# 记录已部署的文件列表
$deployedFiles = @()
$deployedDirs = @()

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

# 不需要部署到服务器的目录（过滤列表）
$excludedDirs = @(
    "docs",              # 文档目录
    "tools/测试",        # 测试脚本目录
    "tools/工具",        # 开发工具目录
    "tools/数据库",      # 数据库工具目录（部分可能需要，但测试脚本不需要）
    ".git",              # Git 目录
    ".vscode",           # VS Code 配置
    ".idea",             # IntelliJ IDEA 配置
    "__pycache__",       # Python 缓存
    "*.pyc",             # Python 编译文件
    "node_modules",      # Node.js 依赖（如果有）
    ".pytest_cache"      # pytest 缓存
)

# 增量部署：使用 git 检测变更的文件
$changedFiles = @()
$changedDirs = @()

if ($Incremental) {
    # 检查是否是 git 仓库
    Push-Location $LOCAL_DIR
    $isGitRepo = git rev-parse --git-dir 2>$null
    Pop-Location
    
    if ($isGitRepo) {
        Write-Host "  检测工作区变更文件（未提交的修改）..." -ForegroundColor Cyan
        Push-Location $LOCAL_DIR
        
        # 设置 git 输出编码为 UTF-8，避免中文路径编码问题
        $env:GIT_PAGER = ""
        $env:LANG = "en_US.UTF-8"
        
        # 1. 检测未跟踪的文件（新文件，从未 push）
        $gitUntracked = git -c core.quotepath=false ls-files --others --exclude-standard 2>$null
        
        # 2. 检测工作区中已修改但未提交的文件
        $gitWorktreeChanged = git -c core.quotepath=false diff --name-only HEAD 2>$null
        
        # 3. 合并工作区变更文件（只检测未提交的修改，不检测已提交但未 push 的文件）
        $allChangedFiles = @()
        
        if ($gitUntracked) {
            # 未跟踪的文件都是新文件，需要部署
            $allChangedFiles += $gitUntracked -split "`n" | Where-Object { $_ -and $_.Trim() }
        }
        
        if ($gitWorktreeChanged) {
            # 工作区变更的文件（未提交的修改），需要部署
            $allChangedFiles += $gitWorktreeChanged -split "`n" | Where-Object { $_ -and $_.Trim() }
        }
        
        # 去重并过滤不需要部署的文件
        $changedFiles = $allChangedFiles | Select-Object -Unique | Where-Object {
            $file = $_.Replace("\", "/")
            $shouldInclude = $true
            
            # 检查是否在排除目录中
            foreach ($excludedDir in $excludedDirs) {
                if ($file -like "$excludedDir/*" -or $file -eq $excludedDir) {
                    $shouldInclude = $false
                    break
                }
            }
            
            $shouldInclude
        }
        
        Pop-Location
        
        if ($changedFiles.Count -gt 0) {
            Write-Host "  发现 $($changedFiles.Count) 个工作区变更文件（未提交的修改，已过滤排除目录）" -ForegroundColor Cyan
            if ($gitUntracked) {
                $untrackedCount = ($gitUntracked -split "`n" | Where-Object { $_ -and $_.Trim() }).Count
                Write-Host "    - 未跟踪文件（新文件）: $untrackedCount 个文件" -ForegroundColor Gray
            }
            if ($gitWorktreeChanged) {
                $worktreeCount = ($gitWorktreeChanged -split "`n" | Where-Object { $_ -and $_.Trim() }).Count
                Write-Host "    - 已修改未提交: $worktreeCount 个文件" -ForegroundColor Gray
            }
            # 统一路径分隔符为 Unix 风格（/）
            $changedFiles = $changedFiles | ForEach-Object { $_.Replace("\", "/") }
            
            # 提取需要同步的目录（去重）
            foreach ($file in $changedFiles) {
                # 统一路径分隔符
                $normalizedFile = $file.Replace("\", "/")
                
                # 使用 LiteralPath 和 try-catch 来处理可能包含特殊字符的路径
                try {
                    $filePath = [System.IO.Path]::Combine($LOCAL_DIR, $normalizedFile)
                    $filePath = [System.IO.Path]::GetFullPath($filePath)
                    
                    if ([System.IO.File]::Exists($filePath) -or [System.IO.Directory]::Exists($filePath)) {
                        # 提取根目录（第一个路径段）
                        $pathParts = $normalizedFile -split "/"
                        if ($pathParts.Count -gt 1) {
                            $rootDir = $pathParts[0]
                            if ($rootDir -and $rootDir -notin $changedDirs) {
                                $changedDirs += $rootDir
                                Write-Host "    检测到变更目录: $rootDir (来自文件: $normalizedFile)" -ForegroundColor Gray
                            }
                        } elseif ($pathParts.Count -eq 1) {
                            # 根目录下的文件，不需要同步目录
                            Write-Host "    检测到根目录文件: $normalizedFile" -ForegroundColor Gray
                        }
                    } else {
                        Write-Host "    警告: 变更文件不存在: $normalizedFile" -ForegroundColor Yellow
                    }
                } catch {
                    # 如果路径处理失败（可能是编码问题），跳过该文件
                    Write-Host "    警告: 无法处理文件路径（可能包含特殊字符）: $normalizedFile" -ForegroundColor Yellow
                    Write-Host "      错误: $($_.Exception.Message)" -ForegroundColor DarkYellow
                }
            }
            
            if ($changedDirs.Count -gt 0) {
                Write-Host "  需要同步的目录: $($changedDirs -join ', ')" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  未发现工作区变更文件，将跳过文件同步" -ForegroundColor Yellow
            Write-Host "    (提示: 已提交但未 push 的文件不会自动部署，需要手动 push 后再部署)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  警告: 当前目录不是 git 仓库，增量部署需要 git 支持" -ForegroundColor Yellow
        Write-Host "  将执行全量部署..." -ForegroundColor Yellow
        $Incremental = $false
    }
}

# 同步函数：根据模式选择同步方式
function Sync-Directory {
    param(
        [string]$LocalPath,
        [string]$RemotePath,
        [string]$Description,
        [bool]$AlwaysSync = $false
    )
    
    if (-not (Test-Path $LocalPath)) {
        return
    }
    
    # 增量部署时，只同步变更的文件
    if ($Incremental -and -not $AlwaysSync) {
        $dirName = Split-Path $LocalPath -Leaf
        if ($dirName -notin $changedDirs) {
            Write-Host "  跳过 $Description (未变更)" -ForegroundColor Gray
            return
        }
        
        # 增量模式：只同步变更的文件
        Write-Host "  增量同步 $Description (只同步变更的文件)..." -ForegroundColor Cyan
        $dirName = Split-Path $LocalPath -Leaf
        
        # 统一路径分隔符并匹配文件
        $filesInDir = $changedFiles | Where-Object { 
            $normalizedFile = $_.Replace("\", "/")
            $normalizedFile -like "$dirName/*" -or $normalizedFile -eq "$dirName"
        }
        
        if ($filesInDir.Count -eq 0) {
            Write-Host "    跳过：目录下没有变更的文件" -ForegroundColor Gray
            Write-Host "    调试: dirName=$dirName, changedFiles=$($changedFiles -join ', ')" -ForegroundColor Gray
            return
        }
        
        Write-Host "    发现 $($filesInDir.Count) 个变更文件需要同步" -ForegroundColor Cyan
        foreach ($f in $filesInDir) {
            Write-Host "      - $f" -ForegroundColor Gray
        }
        
        $syncSuccessCount = 0
        $syncFailCount = 0
        
        foreach ($file in $filesInDir) {
            # 统一路径分隔符为 Unix 风格
            $normalizedFile = $file.Replace("\", "/")
            
            # 使用 System.IO.Path 来处理路径，避免编码问题
            try {
                $localFilePath = [System.IO.Path]::Combine($LOCAL_DIR, $normalizedFile)
                $localFilePath = [System.IO.Path]::GetFullPath($localFilePath)
                
                if (-not ([System.IO.File]::Exists($localFilePath) -or [System.IO.Directory]::Exists($localFilePath))) {
                    Write-Host "    跳过 $normalizedFile (文件不存在)" -ForegroundColor Yellow
                    continue
                }
            } catch {
                Write-Host "    跳过 $normalizedFile (路径处理失败: $($_.Exception.Message))" -ForegroundColor Yellow
                continue
            }
            
            # 计算远程路径：从文件路径中去掉目录前缀
            # 例如：如果 $normalizedFile = "app/api/image_edit_v2.py"，$dirName = "app"
            # 那么相对路径应该是 "api/image_edit_v2.py"
            $relativePath = $normalizedFile
            if ($normalizedFile.StartsWith("$dirName/")) {
                $relativePath = $normalizedFile.Substring($dirName.Length + 1)
            }
            
            # 拼接远程路径：$RemotePath 已经包含了目录名，只需要加上相对路径
            $remoteFilePath = "${RemotePath}/$relativePath"
            
            Write-Host "    同步文件: $normalizedFile" -ForegroundColor Gray
            Write-Host "      本地: $localFilePath" -ForegroundColor Gray
            Write-Host "      远程: ${SERVER}:${remoteFilePath}" -ForegroundColor Gray
            
            # 先确保远程目录存在
            $remoteDir = Split-Path $remoteFilePath -Parent
            ssh $SERVER "mkdir -p `"$remoteDir`"" 2>&1 | Out-Null
            
            # 同步文件（确保路径使用正斜杠，避免Windows路径问题）
            $scpLocalPath = $localFilePath.Replace("\", "/")
            $scpOutput = scp "$scpLocalPath" "${SERVER}:${remoteFilePath}" 2>&1
            $scpExitCode = $LASTEXITCODE
            
            if ($scpExitCode -eq 0) {
                $syncSuccessCount++
                if ($normalizedFile -notin $script:deployedFiles) {
                    $script:deployedFiles += $normalizedFile
                }
            } else {
                $syncFailCount++
                Write-Host "      ✗ 同步失败 (退出码: $scpExitCode)" -ForegroundColor Red
                if ($scpOutput) {
                    $scpOutput | ForEach-Object { Write-Host "        $_" -ForegroundColor Red }
                }
            }
        }
        
        Write-Host "    ✓ 同步完成: 成功 $syncSuccessCount 个, 失败 $syncFailCount 个" -ForegroundColor $(if ($syncFailCount -eq 0) { "Green" } else { "Yellow" })
        $script:deployedDirs += $Description
        
        if ($syncFailCount -gt 0 -and $Description -eq "app/ 目录") {
            Write-Host "    错误: app/ 目录同步失败，退出部署" -ForegroundColor Red
            exit 1
        }
        
        return
    }
    
    # 全量模式：同步整个目录
    Write-Host "  同步 $Description (全量模式)..." -ForegroundColor Cyan
    $normalizedLocalPath = $LocalPath.Replace("\", "/")
    $remoteParentPath = Split-Path $RemotePath -Parent
    
    # 先确保远程父目录存在
    Write-Host "    创建远程目录: $remoteParentPath" -ForegroundColor Gray
    ssh $SERVER "mkdir -p `"$remoteParentPath`"" 2>&1 | Out-Null
    
    # 使用 scp -r，目标目录设为父目录，这样 scp 会在父目录下创建同名目录，不会嵌套
    # 例如：scp -r app root@web:/opt/ICBackend/versions/debug/ 
    # 结果：/opt/ICBackend/versions/debug/app/（正确）
    $scpCmd = "scp -r `"$normalizedLocalPath`" ${SERVER}:${remoteParentPath}/"
    Write-Host "    执行命令: $scpCmd" -ForegroundColor Gray
    Write-Host "    本地路径: $normalizedLocalPath" -ForegroundColor Gray
    Write-Host "    远程路径: ${SERVER}:${remoteParentPath}/" -ForegroundColor Gray
    
    $scpOutput = scp -r "$normalizedLocalPath" "${SERVER}:${remoteParentPath}/" 2>&1
    $scpExitCode = $LASTEXITCODE
    
    if ($scpOutput) {
        $scpOutput | ForEach-Object {
            if ($_ -match "error|Error|ERROR|failed|Failed|FAILED|warning|Warning|WARNING") {
                Write-Host "    $_" -ForegroundColor Yellow
            } else {
                Write-Host "    $_" -ForegroundColor Gray
            }
        }
    }
    
    if ($scpExitCode -eq 0) {
        Write-Host "    ✓ 同步成功 (退出码: $scpExitCode)" -ForegroundColor Green
        $script:deployedDirs += $Description
        # 记录目录下所有文件（限制数量，避免输出过长）
        $files = Get-ChildItem -Path $LocalPath -Recurse -File | Select-Object -First 100 | ForEach-Object {
            $_.FullName.Replace($LOCAL_DIR, "").TrimStart("\", "/").Replace("\", "/")
        }
        $script:deployedFiles += $files
    } else {
        Write-Host "    ✗ 同步失败 (退出码: $scpExitCode)" -ForegroundColor Red
        if ($scpOutput) {
            Write-Host "    错误信息:" -ForegroundColor Red
            $scpOutput | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
        }
        if ($Description -eq "app/ 目录") {
            exit 1
        }
    }
}

function Sync-File {
    param(
        [string]$LocalPath,
        [string]$RemotePath,
        [string]$Description,
        [bool]$AlwaysSync = $false
    )
    
    if (-not (Test-Path $LocalPath)) {
        return
    }
    
    # 增量部署时，检查文件是否需要同步
    if ($Incremental -and -not $AlwaysSync) {
        $relativePath = $LocalPath.Replace($LOCAL_DIR, "").TrimStart("\", "/")
        if ($relativePath -notin $changedFiles) {
            Write-Host "  跳过 $Description (未变更)" -ForegroundColor Gray
            return
        }
    }
    
    Write-Host "  同步 $Description..." -ForegroundColor Cyan
    # 确保路径格式正确（Windows路径转Unix路径）
    $normalizedLocalPath = $LocalPath.Replace("\", "/")
    $scpCmd = "scp `"$normalizedLocalPath`" ${SERVER}:${RemotePath}"
    Write-Host "    执行命令: $scpCmd" -ForegroundColor Gray
    Write-Host "    本地路径: $normalizedLocalPath" -ForegroundColor Gray
    Write-Host "    远程路径: ${SERVER}:${RemotePath}" -ForegroundColor Gray
    
    $scpOutput = scp "$normalizedLocalPath" "${SERVER}:${RemotePath}" 2>&1
    $scpExitCode = $LASTEXITCODE
    
    if ($scpOutput) {
        $scpOutput | ForEach-Object {
            if ($_ -match "error|Error|ERROR|failed|Failed|FAILED|warning|Warning|WARNING") {
                Write-Host "    $_" -ForegroundColor Yellow
            } else {
                Write-Host "    $_" -ForegroundColor Gray
            }
        }
    }
    
    if ($scpExitCode -eq 0) {
        Write-Host "    ✓ 同步成功 (退出码: $scpExitCode)" -ForegroundColor Green
        # 记录已部署的文件
        $relativePath = $LocalPath.Replace($LOCAL_DIR, "").TrimStart("\", "/").Replace("\", "/")
        if ($relativePath -notin $script:deployedFiles) {
            $script:deployedFiles += $relativePath
        }
    } else {
        Write-Host "    ✗ 同步失败 (退出码: $scpExitCode)" -ForegroundColor Yellow
        if ($scpOutput) {
            Write-Host "    错误信息:" -ForegroundColor Yellow
            $scpOutput | ForEach-Object { Write-Host "      $_" -ForegroundColor Yellow }
        }
    }
}

# 同步 app 目录到版本目录
Sync-Directory -LocalPath "$LOCAL_DIR\app" -RemotePath "${VERSION_DIR}/app" -Description "app/ 目录"

# 同步其他重要文件到版本目录（requirements.txt 等重要文件总是同步）
$importantFiles = @(
    @{File="requirements.txt"; Desc="requirements.txt"},
    @{File="gunicorn_config.py"; Desc="gunicorn_config.py"},
    @{File="env.example"; Desc="env.example"},
    @{File="env.example.secrets"; Desc="env.example.secrets"}
)

foreach ($item in $importantFiles) {
    $filePath = Join-Path $LOCAL_DIR $item.File
    Sync-File -LocalPath $filePath -RemotePath "${VERSION_DIR}/$($item.File)" -Description $item.Desc -AlwaysSync $true
}

# 同步 prompts 目录（如果存在）
Sync-Directory -LocalPath "$LOCAL_DIR\prompts" -RemotePath "${VERSION_DIR}/prompts" -Description "prompts/ 目录"

# 同步 tests 目录（用于服务器端测试）
Sync-Directory -LocalPath "$LOCAL_DIR\tests" -RemotePath "${VERSION_DIR}/tests" -Description "tests/ 目录"

# 同步 scripts 目录（用于服务器端脚本和检查工具）
Sync-Directory -LocalPath "$LOCAL_DIR\scripts" -RemotePath "${VERSION_DIR}/scripts" -Description "scripts/ 目录"

# 同步 wechat 目录（微信公众号前端页面）
Sync-Directory -LocalPath "$LOCAL_DIR\wechat" -RemotePath "${VERSION_DIR}/wechat" -Description "wechat/ 目录"

# 同步 pytest.ini（如果存在）
Sync-File -LocalPath "$LOCAL_DIR\pytest.ini" -RemotePath "${VERSION_DIR}/pytest.ini" -Description "pytest.ini"

Write-Host "✓ 代码同步完成" -ForegroundColor Green

# 打印部署的文件列表
Write-Host "`n已部署的文件列表:" -ForegroundColor Cyan
if ($deployedDirs.Count -gt 0) {
    Write-Host "  已部署的目录 ($($deployedDirs.Count) 个):" -ForegroundColor Yellow
    foreach ($dir in $deployedDirs) {
        Write-Host "    - $dir" -ForegroundColor Gray
    }
}
if ($deployedFiles.Count -gt 0) {
    Write-Host "  已部署的文件 ($($deployedFiles.Count) 个):" -ForegroundColor Yellow
    # 只显示前50个文件，避免输出过长
    $filesToShow = if ($deployedFiles.Count -le 50) { $deployedFiles } else { $deployedFiles[0..49] }
    foreach ($file in $filesToShow) {
        Write-Host "    - $file" -ForegroundColor Gray
    }
    if ($deployedFiles.Count -gt 50) {
        Write-Host "    ... 还有 $($deployedFiles.Count - 50) 个文件" -ForegroundColor Gray
    }
} else {
    Write-Host "  (无文件被部署，可能是增量部署且无变更文件)" -ForegroundColor Gray
}

Write-Host "`n[2.5/6] 转换 shell 脚本行结束符..." -ForegroundColor Green
# 转换所有 .sh 文件的行结束符（CRLF -> LF）
$convertLineEndingsCmd = 'cd ' + $VERSION_DIR + ' && ' +
    'echo "  转换 .sh 文件的行结束符..."; ' +
    'find . -name "*.sh" -type f | while read file; do ' +
    'if command -v dos2unix >/dev/null 2>&1; then ' +
    'dos2unix "$file" 2>/dev/null; ' +
    'elif command -v sed >/dev/null 2>&1; then ' +
    'sed -i "s/\r$//" "$file" 2>/dev/null; ' +
    'else ' +
    'perl -pi -e "s/\r\n/\n/" "$file" 2>/dev/null || ' +
    'python3 -c "import sys; data=open(\"$file\",\"rb\").read().replace(b\"\r\n\",b\"\n\"); open(\"$file\",\"wb\").write(data)" 2>/dev/null; ' +
    'fi; ' +
    'done && ' +
    'echo "  ✓ 行结束符转换完成"'
ssh $SERVER $convertLineEndingsCmd 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Shell 脚本行结束符转换完成" -ForegroundColor Green
} else {
    Write-Host "  警告: 行结束符转换可能失败，请手动检查" -ForegroundColor Yellow
}

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

