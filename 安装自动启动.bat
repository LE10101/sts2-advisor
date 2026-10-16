@echo off
chcp 65001 >nul
title 安装STS2自动启动

echo ========================================
echo   安装STS2游戏监控（开机自动启动）
echo ========================================
echo.

REM 创建启动文件夹的快捷方式
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT_DIR=%~dp0"

REM 创建一个启动监控的VBS脚本（隐藏窗口）
echo Set WshShell = CreateObject("WScript.Shell") > "%STARTUP_DIR%\STS2_Monitor.vbs"
echo WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File ""%SCRIPT_DIR%游戏监控自动启动.ps1""", 0, False >> "%STARTUP_DIR%\STS2_Monitor.vbs"

echo 安装完成！
echo.
echo 监控脚本已加入开机启动
echo 以后每次开机都会自动运行
echo 你只需要打开游戏，Agent会自动启动
echo.
echo 要卸载：删除 %STARTUP_DIR%\STS2_Monitor.vbs
echo.
pause
