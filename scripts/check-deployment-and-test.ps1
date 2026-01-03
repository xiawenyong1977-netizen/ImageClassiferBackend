# =====================================================
# 检查部署状态并运行测试 (PowerShell 版本)
# 使用方法: .\scripts\check-deployment-and-test.ps1
#   或指定服务器和目录: .\scripts\check-deployment-and-test.ps1 -Server "root@web" -RemoteDir "/opt/ICBackend"
# =====================================================

param(
    [string]$Server = "root@web",
    [string]$RemoteDir = "/opt/ICBackend"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "检查部署状态并运行测试" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "服务器: $Server" -ForegroundColor Yellow
Write-Host "部署目录: $RemoteDir" -ForegroundColor Yellow
Write-Host ""

# 检查部署状态
Write-Host "[1/6] 检查部署状态..." -ForegroundColor Cyan
ssh $Server "echo '检查部署目录结构...'; cd $RemoteDir && echo '  当前版本目录:' && if [ -L current ]; then readlink -f current; ls -la current | head -5; else echo '    ✗ current 符号链接不存在'; fi && echo '' && echo '检查服务状态...' && systemctl status image-classifier --no-pager | head -10"

Write-Host ""
Write-Host "[2/6] 检查系统依赖..." -ForegroundColor Cyan
ssh $Server "echo '检查 libzbar (zbar 库)...'; if command -v dpkg >/dev/null 2>&1; then if dpkg -l | grep -q '^ii.*libzbar0'; then echo '  ✓ libzbar0 已安装 (Debian/Ubuntu)'; else echo '  ✗ libzbar0 未安装'; fi; elif command -v rpm >/dev/null 2>&1; then if rpm -qa | grep -q 'zbar'; then echo '  ✓ zbar 已安装 (CentOS/RHEL)'; else echo '  ✗ zbar 未安装'; fi; else echo '  ⚠ 无法检测系统类型'; fi"

Write-Host ""
Write-Host "[3/6] 检查环境配置文件..." -ForegroundColor Cyan
# 检查环境配置文件，优先使用虚拟环境的 Python，否则使用系统 Python
$envCheckCmd = "cd $RemoteDir && " +
    "CURRENT_DIR=`$(readlink -f current 2>/dev/null || echo 'current') && " +
    "cd `$CURRENT_DIR && " +
    "if [ -d ../venv ]; then " +
    "PYTHON='../venv/bin/python'; " +
    "elif command -v python3 >/dev/null 2>&1; then " +
    "PYTHON='python3'; " +
    "elif command -v python >/dev/null 2>&1; then " +
    "PYTHON='python'; " +
    "else " +
    "echo '  ✗ 未找到 Python 解释器'; exit 1; " +
    "fi && " +
    "ENV_FILE='.env' && " +
    "if [ ! -f `$ENV_FILE ]; then " +
    "echo '  ⚠ .env 文件不存在: `$ENV_FILE'; " +
    "fi && " +
    "SCRIPT_FOUND='' && " +
    "if [ -f scripts/check_env_config.py ]; then " +
    "SCRIPT_FOUND='scripts/check_env_config.py'; " +
    "elif [ -f ../scripts/check_env_config.py ]; then " +
    "SCRIPT_FOUND='../scripts/check_env_config.py'; " +
    "elif [ -f $RemoteDir/scripts/check_env_config.py ]; then " +
    "SCRIPT_FOUND='$RemoteDir/scripts/check_env_config.py'; " +
    "elif [ -f versions/debug/scripts/check_env_config.py ]; then " +
    "SCRIPT_FOUND='versions/debug/scripts/check_env_config.py'; " +
    "fi && " +
    "if [ -n `"`$SCRIPT_FOUND`" ]; then " +
    "echo '  运行环境配置检查脚本: `$SCRIPT_FOUND'; " +
    "`$PYTHON `$SCRIPT_FOUND `$ENV_FILE 2>&1; " +
    "else " +
    "echo '  ⚠ 检查脚本不存在，尝试查找...'; " +
    "echo '  查找 scripts 目录:'; " +
    "find . -type d -name scripts 2>/dev/null | head -3; " +
    "echo '  查找 check_env_config.py:'; " +
    "find . -name check_env_config.py 2>/dev/null | head -3; " +
    "echo '  手动检查: 对比 .env 和 env.example 文件'; " +
    "fi"
ssh $Server $envCheckCmd

Write-Host ""
Write-Host "[4/6] 检查虚拟环境..." -ForegroundColor Cyan
ssh $Server "cd $RemoteDir && if [ -d venv ]; then echo '✓ 虚拟环境存在'; VENV_PYTHON='$RemoteDir/venv/bin/python'; VENV_PIP='$RemoteDir/venv/bin/pip'; echo '  Python 版本:'; `$VENV_PYTHON --version; echo '  检查关键包:'; `$VENV_PIP list 2>/dev/null | grep '^fastapi' && echo '    ✓ fastapi' || echo '    ✗ fastapi'; `$VENV_PIP list 2>/dev/null | grep '^torch' && echo '    ✓ torch' || echo '    ✗ torch'; `$VENV_PIP list 2>/dev/null | grep '^pyzbar' && echo '    ✓ pyzbar' || echo '    ✗ pyzbar'; else echo '✗ 虚拟环境不存在'; fi"

Write-Host ""
Write-Host "[5/6] 检查日志文件..." -ForegroundColor Cyan
ssh $Server "echo '检查日志文件...'; if [ -f /var/log/image-classifier/app.log ]; then echo '  ✓ 日志文件存在'; echo '  最近日志（最后5行）:'; tail -n 5 /var/log/image-classifier/app.log; else echo '  ✗ 日志文件不存在'; fi"

Write-Host ""
Write-Host "[6/6] 运行自动化测试..." -ForegroundColor Cyan
Write-Host "  先转换 shell 脚本的行结束符..." -ForegroundColor Yellow
# 转换行结束符：优先使用 dos2unix，否则使用 sed（大多数系统都有）
$convertCmd = 'cd ' + $RemoteDir + '/current/tests && ' +
    'if command -v dos2unix >/dev/null 2>&1; then ' +
    'dos2unix run-tests-on-server.sh 2>/dev/null && echo "  ✓ 使用 dos2unix 转换完成"; ' +
    'elif command -v sed >/dev/null 2>&1; then ' +
    'sed -i "s/\r$//" run-tests-on-server.sh 2>/dev/null && echo "  ✓ 使用 sed 转换完成"; ' +
    'else ' +
    'tr -d "\r" < run-tests-on-server.sh > run-tests-on-server.sh.tmp && mv run-tests-on-server.sh.tmp run-tests-on-server.sh && echo "  ✓ 使用 tr 转换完成"; ' +
    'fi'
ssh $Server $convertCmd
Write-Host "执行测试脚本: cd $RemoteDir/current/tests && ./run-tests-on-server.sh" -ForegroundColor Yellow
ssh $Server "cd $RemoteDir/current/tests && bash ./run-tests-on-server.sh"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "检查和测试完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

