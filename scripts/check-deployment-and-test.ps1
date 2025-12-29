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
Write-Host "[1/5] 检查部署状态..." -ForegroundColor Cyan
ssh $Server "echo '检查部署目录结构...'; cd $RemoteDir && echo '  当前版本目录:' && if [ -L current ]; then readlink -f current; ls -la current | head -5; else echo '    ✗ current 符号链接不存在'; fi && echo '' && echo '检查服务状态...' && systemctl status image-classifier --no-pager | head -10"

Write-Host ""
Write-Host "[2/5] 检查系统依赖..." -ForegroundColor Cyan
ssh $Server "echo '检查 libzbar (zbar 库)...'; if command -v dpkg >/dev/null 2>&1; then if dpkg -l | grep -q '^ii.*libzbar0'; then echo '  ✓ libzbar0 已安装 (Debian/Ubuntu)'; else echo '  ✗ libzbar0 未安装'; fi; elif command -v rpm >/dev/null 2>&1; then if rpm -qa | grep -q 'zbar'; then echo '  ✓ zbar 已安装 (CentOS/RHEL)'; else echo '  ✗ zbar 未安装'; fi; else echo '  ⚠ 无法检测系统类型'; fi"

Write-Host ""
Write-Host "[3/5] 检查虚拟环境..." -ForegroundColor Cyan
ssh $Server "cd $RemoteDir && if [ -d venv ]; then echo '✓ 虚拟环境存在'; VENV_PYTHON='$RemoteDir/venv/bin/python'; VENV_PIP='$RemoteDir/venv/bin/pip'; echo '  Python 版本:'; `$VENV_PYTHON --version; echo '  检查关键包:'; `$VENV_PIP list 2>/dev/null | grep '^fastapi' && echo '    ✓ fastapi' || echo '    ✗ fastapi'; `$VENV_PIP list 2>/dev/null | grep '^torch' && echo '    ✓ torch' || echo '    ✗ torch'; `$VENV_PIP list 2>/dev/null | grep '^pyzbar' && echo '    ✓ pyzbar' || echo '    ✗ pyzbar'; else echo '✗ 虚拟环境不存在'; fi"

Write-Host ""
Write-Host "[4/5] 检查日志文件..." -ForegroundColor Cyan
ssh $Server "echo '检查日志文件...'; if [ -f /var/log/image-classifier/app.log ]; then echo '  ✓ 日志文件存在'; echo '  最近日志（最后5行）:'; tail -n 5 /var/log/image-classifier/app.log; else echo '  ✗ 日志文件不存在'; fi"

Write-Host ""
Write-Host "[5/5] 运行自动化测试..." -ForegroundColor Cyan
Write-Host "执行测试脚本: cd $RemoteDir/current/tests && ./run-tests-on-server.sh" -ForegroundColor Yellow
ssh $Server "cd $RemoteDir/current/tests && bash ./run-tests-on-server.sh"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "检查和测试完成" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

