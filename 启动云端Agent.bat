@echo off
chcp 65001 >nul
title STS2 Cloud Agent
cd /d "%~dp0"

echo ========================================
echo   STS2 云端推送Agent
echo ========================================
echo.

REM 检查Python
set PYTHON=C:\Users\21508\AppData\Local\Doubao\User Data\sandbox_runtime\bases\d0ace100fdff5b2d247847aca1e3d83b\python\python.exe
if not exist "%PYTHON%" (
    echo [错误] 找不到Python: %PYTHON%
    pause
    exit /b 1
)

REM 云端地址（部署后替换为你的固定网址）
set CLOUD_URL=https://sts2-advisor.onrender.com

echo 云端地址: %CLOUD_URL%
echo 游戏API: http://127.0.0.1:8080
echo.
echo 启动后会自动:
echo   1. 读取游戏状态
echo   2. 运行MCTS计算推荐
echo   3. 推送到云端网站
echo   4. 记录历史对局
echo.
echo 网站永久在线，不打开游戏也能复盘历史
echo.

"%PYTHON%" -u cloud_agent.py --url %CLOUD_URL%

echo.
echo Agent已停止
pause
