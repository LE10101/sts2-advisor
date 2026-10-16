"""决策理由生成：解释 MCTS 为什么推荐这个动作。"""
from __future__ import annotations
from typing import Optional
from .model import CombatState, Action
from .cards import effects_for_card


def explain_combat(state: CombatState, best_action: Optional[Action],
                   ranked: list[tuple[Action, float, int]]) -> str:
    """生成战斗决策的自然语言理由。"""
    if best_action is None or not ranked:
        return "无可用动作"

    best_avg = ranked[0][1]
    parts = [f"胜率{best_avg*100:.0f}%"]

    if len(ranked) >= 2:
        gap = (ranked[0][1] - ranked[1][1]) * 100
        if gap > 5:
            parts.append(f"明显领先次优{gap:.0f}%")
        elif gap < 1:
            parts.append("与次优接近，可灵活选择")

    # 计算敌人总威胁
    total_threat = 0
    for e in state.alive_enemies():
        dmg = e.intent_total_damage or e.intent_damage
        if dmg > 0:
            total_threat += dmg * (1.3 if e.is_aoe else 1.0)

    if best_action.kind == "play_card" and best_action.card:
        eff = effects_for_card(best_action.card)
        detail = []
        target = None
        if best_action.target_index >= 0 and best_action.target_index < len(state.enemies):
            target = state.enemies[best_action.target_index]

        # 卡牌效果描述
        if eff.get("finisher"):
            atk_count = state.attacks_played_this_turn
            detail.append(f"终结技{atk_count}段×{eff.get('finisher_damage', 6)}伤")
        elif eff.get("attack", 0) > 0:
            hits = eff.get("hits", 1)
            if hits > 1:
                detail.append(f"{eff['attack']}×{hits}伤害")
            else:
                detail.append(f"{eff['attack']}伤害")
        if eff.get("poison", 0) > 0:
            if eff.get("conditional_poison"):
                detail.append(f"条件叠{eff['poison']}毒")
            elif eff.get("aoe_poison"):
                detail.append(f"AOE叠{eff['poison']}毒")
            else:
                detail.append(f"叠{eff['poison']}毒")
        if eff.get("block", 0) > 0:
            detail.append(f"{eff['block']}格挡")
        if eff.get("draw", 0) > 0:
            detail.append(f"抽{eff['draw']}牌")
        if eff.get("add_shiv", 0) > 0:
            detail.append(f"加{eff['add_shiv']}小刀")
        if eff.get("weak", 0) > 0:
            detail.append(f"虚弱{eff['weak']}")
        if eff.get("vulnerable", 0) > 0:
            detail.append(f"易伤{eff['vulnerable']}")
        if eff.get("remove_block"):
            detail.append("去格挡")
        if eff.get("energy", 0) > 0 or eff.get("energy_next_turn", 0) > 0:
            detail.append("回能量")
        if eff.get("exhaust"):
            detail.append("消耗")

        # 战略理由
        if target and target.hp <= (eff.get("attack", 0) * eff.get("hits", 1)):
            detail.append("可击杀")
        elif total_threat > state.player_block and eff.get("block", 0) > 0:
            detail.append(f"补格挡(威胁{int(total_threat)})")
        elif target and target.poison > 0 and eff.get("poison", 0) > 0:
            detail.append("持续叠毒")
        elif eff.get("attack", 0) > 0 and len(state.alive_enemies()) > 1:
            detail.append("优先减员")

        if detail:
            parts.append("，".join(detail))

    elif best_action.kind == "end_turn":
        if state.energy == 0:
            parts.append("能量耗尽，结束回合")
        elif not any(c.playable and c.cost <= state.energy for c in state.hand):
            parts.append("无牌可打，结束回合")
        elif total_threat <= state.player_block:
            parts.append(f"格挡{state.player_block}已覆盖威胁{int(total_threat)}")
        else:
            parts.append("保留手牌到下回合更优")

    return "；".join(parts)


def explain_reward(card_name: str, score: float, reason: str) -> str:
    return f"选「{card_name}」评分{score:.1f}：{reason}"
