"""Slay the Spire 2 决策器（AI 教练，MCTS 核心）。

通过 autoSpire 的 HTTP 接口读取真实游戏战斗状态，用蒙特卡洛树搜索给出
最优出牌 / 结束回合的推荐，供玩家手动执行或半自动执行。
"""

__version__ = "0.1.0"
