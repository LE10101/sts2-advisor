@echo off
chcp 65001 >nul
title STS2 Advisor - 公网版
cd /d "%~dp0"

echo ========================================
echo   STS2 Advisor 公网版启动器
echo ========================================
echo.

REM 检查Python
set PYTHON=C:\Users\21508\AppData\Local\Doubao\User Data\sandbox_runtime\bases\d0ace100fdff5b2d247847aca1e3d83b\python\python.exe
if not exist "%PYTHON%" (
    echo [错误] 找不到Python: %PYTHON%
    pause
    exit /b 1
)

REM 启动Web应用
echo [1/2] 启动Web应用 (端口8766)...
start "STS2 Web" /min "%PYTHON%" -u web_app.py
timeout /t 3 /nobreak >nul

REM 启动公网隧道
echo [2/2] 启动公网隧道...
echo.
echo 选择公网暴露方式:
echo   1. localtunnel (免费, 快速, URL可能变化)
echo   2. ngrok (需注册, 稳定)
echo   3. 仅局域网 (不暴露公网)
echo.
set /p choice="请选择 (1/2/3, 默认1): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo 正在启动localtunnel...
    echo 注意: 需要Node.js, 首次运行会自动下载localtunnel
    npx -y localtunnel --port 8766 --subdomain sts2-advisor
) else if "%choice%"=="2" (
    echo 正在启动ngrok...
    ngrok http 8766
) else (
    echo 仅局域网模式
    echo 本机访问: http://127.0.0.1:8766
    echo 手机访问: http://[你的局域网IP]:8766
)

echo.
echo 按任意键退出...
pause >nul
