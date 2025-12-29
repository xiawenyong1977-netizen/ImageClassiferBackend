@echo off
REM Windows批处理脚本：本地测试运行
REM 自动加载测试环境变量并运行测试

setlocal enabledelayedexpansion

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM 检查测试环境变量文件
set "TEST_ENV_FILE=%SCRIPT_DIR%.env.test"

if exist "%TEST_ENV_FILE%" (
    echo ✓ 找到测试环境变量文件: %TEST_ENV_FILE%
    REM 注意：Windows批处理不能直接source .env文件
    REM 需要手动设置环境变量或使用其他工具
    echo   请确保已设置测试数据库环境变量
) else (
    echo ⚠ 未找到测试环境变量文件: %TEST_ENV_FILE%
    echo   使用系统环境变量或默认配置
)

REM 切换到项目目录
cd /d "%PROJECT_DIR%"

REM 检查pytest是否安装
where pytest >nul 2>&1
if errorlevel 1 (
    echo ❌ pytest未安装，正在安装...
    pip install pytest pytest-asyncio pytest-cov
)

REM 运行测试
echo.
echo ========================================
echo 开始运行测试...
echo ========================================
echo.

REM 如果提供了参数，传递给pytest
if "%~1"=="" (
    pytest tests\ -v
) else (
    pytest %*
)

endlocal

