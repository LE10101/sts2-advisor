"""决策理由生成器：把每个推荐转成可读的"为什么这么选"。

战斗阶段是重点（MCTS 之前只给胜率，不给原因）；路线/奖励/商店已有内置理由，
这里提供统一入口与补充说明。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .cards import effects_for_card
from .model import Action, CombatState


def explain_combat(state: CombatState, best_action: Optional[Action],
                   ranked: List[Tuple[Action, float, int]]) -> str:
    """生成战斗选择理由（一句话 + 关键因素）。"""
    if not ranked or best_action is None:
        return "（无可行动作）"
    top_avg, top_visits = ranked[0][1], ranked[0][2]
    parts = [f"预期胜率 {top_avg * 100:.0f}%（采样 {top_visits} 次）"]
    if len(ranked) > 1:
        gap = top_avg - ranked[1][1]
        if gap > 0.005:
            parts.append(f"领先次优 {gap * 100:.0f}%")

    if best_action.kind == "end_turn":
        parts.append("当前手牌/能量下无更高期望动作，结束回合进入敌人阶段")
        if state.energy > 0:
            parts.append(f"保留 {state.energy} 点能量与手牌")
        return "；".join(parts)

    # play_card
    card = next((c for c in state.hand if c.hand_index == best_action.hand_index), None)
    if card is None:
        return "；".join(parts)
    ef = effects_for_card(card)
    target = next((e for e in state.enemies if e.id == best_action.target_id), None)
    tname = target.name if target else ""

    # 伤害与击杀
    dmg = ef.damage + state.player_buffs.get("力量", 0)
    if card.shiv:
        dmg += state.player_buffs.get("精准", 0) * 4
    if target and dmg > 0 and dmg >= target.hp + target.block:
        parts.append(f"可直接击杀「{tname}」")
    elif target and dmg > 0:
        parts.append(f"对「{tname}」造成约 {dmg} 伤害")

    # 毒
    if ef.poison > 0 and target:
        parts.append(f"对「{tname}」叠 {ef.poison} 层毒（每回合递减伤害，毒流核心）")
    if ef.poison_aoe > 0:
        parts.append(f"全体叠 {ef.poison_aoe} 层毒")

    # 格挡
    if ef.block > 0:
        incoming = sum(e.intent_value for e in state.enemies
                       if e.alive and e.intent in ("attack", "重击", "强攻"))
        if incoming > 0:
            if ef.block >= incoming:
                parts.append(f"获得 {ef.block} 格挡，完全覆盖敌人即将 {incoming} 点攻击")
            else:
                parts.append(f"获得 {ef.block} 格挡（敌人即将 {incoming} 点攻击）")
        else:
            parts.append(f"获得 {ef.block} 格挡")

    # 小刀 / 弃牌 / 抽牌 / AOE / 能量
    if ef.shiv_count > 0:
        parts.append(f"生成 {ef.shiv_count} 把小刀（0 费攻击，小刀流）")
    if ef.discard > 0:
        parts.append("弃牌触发引擎（战术家回能 / 反射抽牌）")
    if ef.draw > 0:
        parts.append(f"抽 {ef.draw} 张牌")
    if ef.aoe and ef.damage > 0:
        parts.append("群体伤害")
    if ef.energy_gain > 0:
        parts.append(f"回复 {ef.energy_gain} 能量")

    # 敌人 debuff（虚弱 / 易伤）
    debuffs = []
    if ef.enemy_debuffs.get("虚弱", 0) > 0:
        debuffs.append(f"虚弱 {ef.enemy_debuffs['虚弱']}")
    if ef.enemy_debuffs.get("易伤", 0) > 0:
        debuffs.append(f"易伤 {ef.enemy_debuffs['易伤']}")
    if debuffs:
        parts.append("施加 " + "、".join(debuffs))
    if ef.weak_aoe > 0:
        parts.append(f"全体虚弱 {ef.weak_aoe}")
    if ef.vulnerable_aoe > 0:
        parts.append(f"全体易伤 {ef.vulnerable_aoe}")
    if ef.enemy_strength_loss > 0:
        parts.append(f"敌人降力量 {ef.enemy_strength_loss}")

    # 自身 buff（力量 / 敏捷 / 无形 / 精准）
    buffs = []
    for k, v in ef.self_buffs.items():
        if v > 0:
            buffs.append(f"{k}+{v}")
    if buffs:
        parts.append("获得 " + "、".join(buffs))
    if ef.retain_block:
        parts.append("格挡保留到下回合")
    if ef.heal > 0:
        parts.append(f"回复 {ef.heal} HP")

    return "；".join(parts)


def explain_route(option: dict) -> str:
    """路线理由（route.py 已给 reason，这里做统一包装）。"""
    return option.get("reason", "")


def explain_reward(result: dict) -> str:
    """奖励理由（reward.py 已汇总 reason）。"""
    return result.get("reason", "")


def explain_shop(result: dict) -> str:
    """商店理由（shop.py 已汇总 reason）。"""
    return result.get("reason", "")
