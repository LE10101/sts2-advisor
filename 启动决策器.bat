@echo off
chcp 65001 >nul
title STS2决策器 - 本地Agent
echo ========================================
echo    STS2 决策器 - 本地Agent启动中
echo ========================================
echo.

cd /d "%~dp0"

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: 检查依赖
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ⏳ 正在安装依赖...
    pip install flask requests -i https://pypi.tuna.tsinghua.edu.cn/simple
)

:: 检查游戏mod连接
echo.
echo 🔍 正在检测游戏mod连接...
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  未检测到游戏mod，请确认：
    echo    1. 游戏已启动
    echo    2. STS2 AI Agent mod已启用
    echo    3. 已进入一局游戏
    echo.
    echo 程序将继续运行，游戏启动后会自动连接...
    echo.
) else (
    echo ✅ 游戏mod连接正常！
    echo.
)

:: 启动本地Agent
echo 🚀 启动本地Agent，推送到云端...
echo 网址: https://sts2-advisor.onrender.com
echo 保持此窗口开启，关闭即停止
echo ========================================
echo.

python cloud_agent.py --server https://sts2-advisor.onrender.com

pause
