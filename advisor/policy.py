"""rollout 默认策略：贪心（毒/小刀加权）+ 随机。"""
from __future__ import annotations
import random
from typing import Optional
from .model import CombatState, Action
from .cards import effects_for_card


def greedy_policy(state: CombatState, actions: list[Action],
                  rng: Optional[random.Random] = None) -> Action:
    """启发式贪心：优先毒/攻击高威胁/小刀，其次防御，最后结束回合。"""
    rng = rng or random
    best = None
    best_score = -1e9
    for a in actions:
        score = _score_action(state, a)
        score += rng.uniform(-0.5, 0.5)
        if score > best_score:
            best_score = score
            best = a
    return best or actions[-1]


def _score_action(state: CombatState, action: Action) -> float:
    if action.kind == "end_turn":
        # 如果手牌打不完，结束回合；否则轻微惩罚
        return 0.1

    eff = effects_for_card(action.card)
    score = 0.0

    # 计算敌人总威胁
    total_threat = sum(
        (e.intent_total_damage or e.intent_damage) * (1.3 if e.is_aoe else 1.0)
        for e in state.alive_enemies()
    )
    # 玩家当前格挡
    current_block = state.player_block

    # 毒效果（核心）
    if eff.get("poison", 0) > 0:
        score += eff["poison"] * 2.5
    # AOE 毒（毒性爆发）
    if eff.get("aoe_poison"):
        score += eff.get("poison", 0) * 3.0 * len(state.alive_enemies())
    # 立即触发毒（毒性爆发）
    if eff.get("trigger_poison"):
        total_poison = sum(e.poison for e in state.alive_enemies())
        score += total_poison * 1.5
    # 攻击
    if eff.get("attack", 0) > 0:
        score += eff["attack"] * 1.0
    # 小刀
    if eff.get("shiv", 0) > 0 or eff.get("add_shiv", 0) > 0:
        shiv_count = eff.get("shiv", 0) + eff.get("add_shiv", 0)
        score += shiv_count * 3.0
    # 格挡（高威胁时更重要）
    if eff.get("block", 0) > 0:
        block_value = eff["block"]
        if total_threat > current_block:
            score += block_value * 1.2  # 缺格挡时更重视
        else:
            score += block_value * 0.6
    # 毒转格挡（蜃景）
    if eff.get("block_from_poison"):
        total_poison = sum(e.poison for e in state.alive_enemies())
        score += total_poison * 0.8
    # 抽牌
    if eff.get("draw", 0) > 0:
        score += eff["draw"] * 1.5
    # 能量
    if eff.get("energy", 0) > 0:
        score += eff["energy"] * 2.0
    # 下回合能量（侧步）
    if eff.get("energy_next_turn", 0) > 0:
        score += eff["energy_next_turn"] * 1.5
    # 虚弱
    if eff.get("weak", 0) > 0:
        score += 2.5
    # 易伤
    if eff.get("vulnerable", 0) > 0:
        score += 2.0
    # 力量流失（尖啸）
    if eff.get("strength_loss", 0) > 0:
        score += eff["strength_loss"] * 1.5
    # 弃牌
    if eff.get("discard", 0) > 0:
        score += 1.0
    # 0费牌
    if eff.get("cost", 1) == 0 or action.card.cost == 0:
        score += 1.0
    # 消耗牌（配合金纸）
    if eff.get("exhaust") or action.card.exhaust:
        if "JOSS_PAPER" in state.relics:
            score += 0.5  # 金纸：消耗牌有额外价值

    return score


def random_policy(state: CombatState, actions: list[Action],
                  rng: Optional[random.Random] = None) -> Action:
    rng = rng or random
    return rng.choice(actions)
