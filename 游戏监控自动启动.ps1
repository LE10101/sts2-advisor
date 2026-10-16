# STS2 游戏进程监控脚本
# 放在开机启动文件夹，检测到游戏启动时自动启动云端Agent
# 启动文件夹路径: shell:startup

$ErrorActionPreference = "SilentlyContinue"
$gameProcess = "SlayTheSpire2"
$agentStarted = $false
$projectDir = "C:\Users\21508\Doubao\chats\2026-10-15\new-chat-1\sts2_advisor"
$serverUrl = "https://sts2-advisor.onrender.com"

Write-Host "STS2 监控已启动，等待游戏运行..." -ForegroundColor Green

while ($true) {
    # 检测游戏进程
    $gameRunning = Get-Process -Name $gameProcess -ErrorAction SilentlyContinue

    if ($gameRunning -and -not $agentStarted) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 检测到游戏启动，正在启动云端Agent..." -ForegroundColor Cyan

        # 启动Agent（隐藏窗口）
        Start-Process -FilePath "python" -ArgumentList "cloud_agent.py", "--server", $serverUrl `
            -WorkingDirectory $projectDir `
            -WindowStyle Minimized `
            -ErrorAction SilentlyContinue

        $agentStarted = $true
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 云端Agent已启动" -ForegroundColor Green
    }
    elseif (-not $gameRunning -and $agentStarted) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 游戏已关闭" -ForegroundColor Yellow
        $agentStarted = $false
    }

    # 每5秒检查一次
    Start-Sleep -Seconds 5
}
