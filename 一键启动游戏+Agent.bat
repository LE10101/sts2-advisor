@echo off
chcp 65001 >nul
title STS2 一键启动
cd /d "%~dp0"

echo ========================================
echo   STS2 一键启动（游戏+云端Agent）
echo ========================================
echo.

REM 启动云端Agent（隐藏窗口）
echo [1/2] 启动云端Agent...
start "" /min python cloud_agent.py --server https://sts2-advisor.onrender.com

REM 等待2秒让Agent启动
timeout /t 2 /nobreak >nul

REM 启动游戏
echo [2/2] 启动杀戮尖塔2...
start "" "D:\LeStoreDownload\steam\steamapps\common\Slay the Spire 2\SlayTheSpire2.exe"

echo.
echo ========================================
echo   启动完成！
echo   游戏和云端Agent都已启动
echo   手机访问: https://sts2-advisor.onrender.com
echo ========================================
echo.
echo 提示：关闭游戏后，Agent窗口也可以关闭
echo.

REM 保持窗口3秒后自动关闭
timeout /t 3 /nobreak >nul
exit
