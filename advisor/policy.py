"""rollout 默认策略：MCTS 模拟阶段的快速行动选择。

纯随机 rollout 无偏但慢；带一点启发式的策略收敛更快。
可注入到 ``mcts.MCTS`` 作为 ``default_policy``。
"""

from __future__ import annotations

import random
from typing import Callable, List

from .model import Action, CombatState
from .cards import effects_for_card


def random_policy(state: CombatState, actions: List[Action], rng: random.Random) -> Action:
    """均匀随机选一个动作。"""
    return rng.choice(actions)


def greedy_policy(state: CombatState, actions: List[Action], rng: random.Random) -> Action:
    """启发式：优先打伤害最高的攻击，其次格挡，再结束回合。

    用于加速 rollout 收敛（比纯随机更贴近合理打法）。
    """
    if not actions:
        raise ValueError("empty actions")

    # 权重评分
    scored = []
    for a in actions:
        if a.kind == "end_turn":
            scored.append((0.0, a))
            continue
        if a.kind == "play_card":
            card = next((c for c in state.hand if c.hand_index == a.hand_index), None)
            if card is None:
                scored.append((0.0, a))
                continue
            ef = effects_for_card(card)
            score = (
                ef.damage * (1.2 if ef.aoe else 1.0)
                + ef.block * 0.8
                + ef.draw * 1.1
                + ef.poison * 1.3
                + ef.poison_aoe * 1.3
                + ef.shiv_count * 1.0
                + sum(ef.enemy_debuffs.values()) * 1.0
                + ef.weak_aoe * 1.0
                + ef.vulnerable_aoe * 1.0
            )
            score -= card.cost * 0.5
            scored.append((score, a))
        else:
            scored.append((0.5, a))

    # 加入随机扰动，避免贪婪导致 rollout 过度确定性
    max_score = max(s for s, _ in scored) if scored else 1.0
    jittered = [(s + rng.uniform(0, 0.3 * max(max_score, 0.1)), a) for s, a in scored]
    jittered.sort(key=lambda x: -x[0])
    return jittered[0][1]


DefaultPolicy = Callable[[CombatState, List[Action], random.Random], Action]
