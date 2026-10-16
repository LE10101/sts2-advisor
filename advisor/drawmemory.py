"""SL 牌序记忆：利用游戏可 SL 看牌序，自动记录并确定性推演。"""
from __future__ import annotations
from typing import Optional
from .model import CombatState, Card


class DrawOrderMemory:
    """记录抽牌顺序，SL 时回到起点重新确认。

    原理：autoSpire 每帧返回手牌，通过帧间手牌差异检测新抽的牌，
    用 card.fingerprint() 去重，按出现顺序记录。SL（回退到战斗起点）
    时 pos 归零，重新确认。
    """

    def __init__(self):
        self.order: list[str] = []       # 抽牌顺序（fingerprint 列表）
        self.pos = 0                     # 当前已确认到第几张
        self.prev_hand_fps: set[str] = set()
        self.confirmed = False

    def observe_new_cards(self, state: CombatState):
        """观察当前手牌，检测新抽的牌并记录。"""
        current_fps = {c.fingerprint() for c in state.hand}
        new_cards = current_fps - self.prev_hand_fps
        for fp in sorted(new_cards):
            if fp not in self.order:
                self.order.append(fp)
        self.prev_hand_fps = current_fps
        if len(self.order) >= 5 and not self.confirmed:
            self.confirmed = True

    def on_sl(self):
        """SL 回退：pos 归零，重新确认牌序。"""
        self.pos = 0
        self.prev_hand_fps = set()
        self.confirmed = False

    def predict_next(self, n: int = 1) -> list[str]:
        """预测接下来 n 张抽牌（基于已记忆顺序）。"""
        return self.order[self.pos:self.pos + n]

    def advance(self, n: int = 1):
        """推演时推进抽牌位置。"""
        self.pos = min(self.pos + n, len(self.order))


def diff_new_cards(prev: list[Card], curr: list[Card]) -> list[Card]:
    """对比两帧手牌，返回新出现的牌。"""
    prev_fps = {c.fingerprint() for c in prev}
    return [c for c in curr if c.fingerprint() not in prev_fps]
