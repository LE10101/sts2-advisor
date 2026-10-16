#!/usr/bin/env python3
"""杀戮尖塔2 决策器入口。

用法：
    python run.py --mode offline            # 内置示例自测（默认）
    python run.py --mode real --port 8765   # 连接真实游戏
"""
from advisor.cli import main

if __name__ == "__main__":
    main()
