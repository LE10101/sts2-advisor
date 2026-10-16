"""状态评估器：把战斗状态打成一个 [0,1] 的期望胜率分。

设计：
- ``state_features(state)`` 抽取一维数值特征向量（也是未来训练 MLP 评估器的输入）。
- ``evaluate_state(state)`` 用可调权重线性加权 + 归一化，输出 [0,1] 分。
- 权重是默认启发式；未来可从自玩样本回归/训练得到（实验室服务器用武之地）。

特征（归一化到约 [0,1]）：
0  我方 HP 占比
1  敌人已削弱比例（1 - 存活敌人 HP / 最大 HP）
2  敌人即将造成的威胁（攻击意图敌人的意图伤害和 / 我方最大 HP）
3  我方格挡占比
4  敌人毒层数潜力（未来伤害 / 我方最大 HP，封顶）
5  我方"无形"是否生效
6  我方力量加成
7  我方敏捷加成
8  存活敌人数（越大越危险，归一化）
"""

from __future__ import annotations

import os
from typing import List, Optional

from .model import CombatState
from . import network as _network

# 默认权重（对应上面特征下标）
DEFAULT_WEIGHTS: List[float] = [
    0.32,   # 0 我方HP占比
    0.26,   # 1 敌人已削弱
    -0.22,  # 2 敌人威胁
    0.07,   # 3 我方格挡
    0.10,   # 4 毒潜力
    0.05,   # 5 无形
    0.04,   # 6 力量
    0.03,   # 7 敏捷
    -0.05,  # 8 存活敌人数
]

_WEIGHT_SUM = sum(abs(w) for w in DEFAULT_WEIGHTS)

# 学到的模型（由 scripts/train_evaluator.py 生成，放 advisor/weights.json）
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weights.json")
_LEARNED_MODEL: Optional[dict] = None


def _learned_model() -> Optional[dict]:
    """懒加载训练好的评估器（存在则用，否则回退默认线性权重）。"""
    global _LEARNED_MODEL
    if _LEARNED_MODEL is None:
        if os.path.exists(_MODEL_PATH):
            try:
                _LEARNED_MODEL = _network.load_params(_MODEL_PATH)
            except Exception:
                _LEARNED_MODEL = None
    return _LEARNED_MODEL


def state_features(state: CombatState) -> List[float]:
    """抽取特征向量（长度与 DEFAULT_WEIGHTS 对齐）。"""
    max_hp = max(state.max_hp, 1)
    p_hp = max(0.0, min(1.0, state.player_hp / max_hp))

    alive = [e for e in state.enemies if e.alive]
    total_max = sum(max(1, e.max_hp) for e in state.enemies)
    total_hp = sum(max(0, e.hp) for e in state.enemies)
    enemy_shaved = 1.0 - (total_hp / max(total_max, 1)) if state.enemies else 1.0

    threat = sum(max(0, e.intent_value) for e in alive if e.intent in ("attack", "强攻", "重击")) / max_hp
    block = min(1.0, state.player_block / max_hp)
    poison = min(1.0, sum(e.buffs.get("毒", 0) for e in alive) / max_hp)
    intangible = 1.0 if state.player_buffs.get("无形", 0) > 0 else 0.0
    strength = min(1.0, max(0, state.player_buffs.get("力量", 0)) / 5.0)
    dexterity = min(1.0, max(0, state.player_buffs.get("敏捷", 0)) / 5.0)
    enemy_count_norm = min(1.0, len(alive) / 5.0)

    return [p_hp, enemy_shaved, threat, block, poison, intangible, strength, dexterity, enemy_count_norm]


def evaluate_state(state: CombatState, weights: Optional[List[float]] = None) -> float:
    """默认评估器：加权线性启发式，输出 [0,1]。稳定、可解释、无需训练。

    注意：默认不用训练好的模型。训练模型存在分布漂移风险（self-play 采样与真实
    状态分布不一致时外推很差），可能劣化决策。想启用学习模型，请显式
    ``evaluate_with_model`` 或 CLI ``--model``。这是刻意为之，保证默认可靠。
    """
    # 终局精确值
    if state.player_hp <= 0:
        return 0.0
    if not any(e.alive for e in state.enemies):
        return 1.0
    w = weights if weights is not None else DEFAULT_WEIGHTS
    feats = state_features(state)
    score = sum(wi * fi for wi, fi in zip(w, feats))
    # 归一化到 [0,1]：以"权重绝对值和的可行域"近似映射
    norm = sum(abs(wi) for wi in w)
    val = 0.5 + score / max(norm, 1e-9)
    return max(0.0, min(1.0, val))


def evaluate_with_model(state: CombatState, params: Optional[dict] = None) -> float:
    """用训练好的模型评估（显式启用）。params 缺省时尝试加载 weights.json。"""
    if state.player_hp <= 0:
        return 0.0
    if not any(e.alive for e in state.enemies):
        return 1.0
    p = params if params is not None else _learned_model()
    if p is None:
        return evaluate_state(state)
    try:
        return max(0.0, min(1.0, _network.model_predict(p, state_features(state))))
    except Exception:
        return evaluate_state(state)


# 兼容旧接口名：供模拟器 / MCTS 调用
def heuristic_value(state: CombatState) -> float:
    return evaluate_state(state)
