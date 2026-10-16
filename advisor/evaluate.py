"""V3 多特征状态评估器：9 维特征加权线性评估，输出 [0,1]。
state_features() 也是 V4 MLP 训练的输入向量。"""
from __future__ import annotations
from typing import Optional
from .model import CombatState

# [hp_ratio, enemy_damage_done, enemy_threat, block, poison_potential,
#  intangible, strength, dexterity, alive_enemies]
DEFAULT_WEIGHTS = [0.35, 0.22, -0.28, 0.08, 0.12, 0.06, 0.05, 0.04, -0.06]


def state_features(state: CombatState) -> list[float]:
    """9 维特征向量，归一化到 [-1,1] 左右。"""
    hp_ratio = state.player_hp / max(1, state.player_max_hp)
    alive = state.alive_enemies()
    enemy_hp = sum(e.hp for e in alive)
    enemy_max = sum(e.max_hp for e in state.enemies) or 1
    enemy_damage_done = 1.0 - (enemy_hp / enemy_max)

    # 敌人威胁：用总伤害（多段攻击），AOE 权重 1.3，力量加成预测
    threat = 0.0
    for e in alive:
        dmg = e.intent_total_damage or e.intent_damage
        if dmg <= 0:
            continue
        weight = 1.3 if e.is_aoe else 1.0
        # 力量每点 +1 伤害/段，粗略预测
        pred_bonus = e.strength * (e.intent_hits or 1) * 0.5
        threat += (dmg + pred_bonus) * weight
    # 归一化：20点伤害为满威胁（更敏感）
    enemy_threat = threat / max(1, len(alive)) / 20.0

    # 格挡：相对于敌人威胁的覆盖率（更有意义）
    if threat > 0:
        block_ratio = min(1.0, state.player_block / threat)
    else:
        block_ratio = state.player_block / 20.0

    poison_potential = sum(e.poison for e in alive) / 20.0
    intangible = 1.0 if getattr(state, "intangible", False) else 0.0
    strength = state.strength / 8.0
    dexterity = state.dexterity / 8.0
    alive_count = len(alive) / 3.0

    return [hp_ratio, enemy_damage_done, enemy_threat, block_ratio,
            poison_potential, intangible, strength, dexterity, alive_count]


def evaluate_state(state: CombatState, weights: Optional[list[float]] = None) -> float:
    """加权线性评估，输出 [0,1]。"""
    w = weights or DEFAULT_WEIGHTS
    feats = state_features(state)
    v = sum(f * wt for f, wt in zip(feats, w))
    return max(0.0, min(1.0, 0.5 + v))


def heuristic_value(state: CombatState) -> float:
    """供 simulator rollout 早停用的快速评估。"""
    return evaluate_state(state)


def evaluate_with_model(state: CombatState, params: dict) -> float:
    """用训练好的 MLP/逻辑回归评估器评估。"""
    from .network import forward
    feats = state_features(state)
    return float(forward(feats, params))
