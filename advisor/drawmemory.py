"""SL 牌序记忆：利用《杀戮尖塔》固定种子机制自动记录真实牌序。

背景
----
杀戮尖塔的牌堆顺序由种子固定，玩家可以"SL"（存档/读档）查看下一张会抽到什么，
读档后牌序不变。这个工具自动做这件事：

- 每次抽牌后，通过对比两帧手牌差异，识别"新抽到的牌"并按顺序记入 ``sequence``。
- 多次 SL 后，``sequence`` 覆盖整个牌堆的真实顺序。
- SL 重抽已见过的牌时，通过 ``pos`` 指针做去重（不重复追加）。
- 模拟器按 ``sequence[pos]`` 确定性抽牌，MCTS 推演因此更精确（而非随机抽样）。

用法
----
在真实/离线模式主循环中：
    mem = DrawOrderMemory()
    # 每帧状态更新后：
    mem.observe_new_cards(new_cards_in_hand)   # new_cards 为本帧相对上帧新增的手牌
    # 检测到 SL（回合回退 / 状态重置）时：
    mem.on_sl()                                 # 回到战斗起点重新确认
    # 进入新战斗时：
    mem.on_new_combat()
    # 模拟器抽牌：
    memory.peek(pos)   # pos 由 state.draw_pos 提供
"""

from __future__ import annotations

from typing import List, Optional

from .model import Card


class DrawOrderMemory:
    def __init__(self):
        self.sequence: List[Card] = []  # 已知抽牌序列（SL 观察积累）
        self.pos: int = 0               # 下一个待确认位置（SL 去重用）
        self.confirmed: int = 0         # 已确认的牌数（便于展示进度）

    # -- 记录 ------------------------------------------------------------
    def observe_new_cards(self, new_cards: List[Card]):
        """把本帧检测到的新抽牌记入序列。

        若该牌与序列当前位置匹配，说明是 SL 重抽（牌序固定），只推进指针不重复追加。
        """
        for c in new_cards:
            fp = c.fingerprint()
            if self.pos < len(self.sequence) and self.sequence[self.pos].fingerprint() == fp:
                # 与已知序列一致：SL 重抽，确认该位置
                self.pos += 1
                self.confirmed = max(self.confirmed, self.pos)
            else:
                self.sequence.append(c)
                self.pos += 1
                self.confirmed = max(self.confirmed, self.pos)

    def on_sl(self):
        """SL 后调用：回到战斗起点重新推进，已学的 sequence 保留（牌序固定）。"""
        self.pos = 0

    def on_new_combat(self):
        """新战斗：清空序列。"""
        self.sequence.clear()
        self.pos = 0
        self.confirmed = 0

    # -- 查询 ------------------------------------------------------------
    def peek(self, index: int) -> Optional[Card]:
        """返回抽牌堆第 index 张的已知牌；未知返回 None。"""
        if 0 <= index < len(self.sequence):
            return self.sequence[index]
        return None

    @property
    def known_length(self) -> int:
        """已确认真实牌序的长度（% of 牌堆）。"""
        return len(self.sequence)

    def describe(self) -> str:
        if not self.sequence:
            return "牌序记忆：空（抽牌后自动记录，SL 可逐步摸清）"
        names = " → ".join(f"{c.name}{c.damage or c.block}" for c in self.sequence[:12])
        more = f" … 共{len(self.sequence)}张" if len(self.sequence) > 12 else ""
        return f"牌序记忆：{names}{more}"


# ---------------------------------------------------------------------------
# 帧间手牌差异检测：给定上/本帧手牌，返回"新增的牌"
# ---------------------------------------------------------------------------
def diff_new_cards(prev_hand: List[Card], cur_hand: List[Card]) -> List[Card]:
    """返回 cur_hand 中相对 prev_hand 新增的牌（按指纹，保留顺序）。

    用指纹计数差判断：cur 中某指纹数量 > prev 中数量，超出部分视为新增。
    """
    from collections import Counter
    prev_cnt = Counter(c.fingerprint() for c in prev_hand)
    cur_cnt = Counter(c.fingerprint() for c in cur_hand)
    new: List[Card] = []
    seen: dict = {}
    for c in cur_hand:
        fp = c.fingerprint()
        seen[fp] = seen.get(fp, 0) + 1
        if seen[fp] > prev_cnt.get(fp, 0):
            new.append(c)
    return new
