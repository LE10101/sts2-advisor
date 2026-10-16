"""V3 支配剪枝：同牌多目标只保留 top-k，同名牌同目标去重。"""
from __future__ import annotations
from .model import CombatState, Action
from .cards import effects_for_card

TARGET_KEEP = 2   # 同张牌打多目标时保留 top-k
PRUNE_MIN = 14    # 候选数 ≤ 此值时跳过剪枝（小状态零收益）


def prune_actions(state: CombatState, actions: list[Action]) -> list[Action]:
    if len(actions) <= PRUNE_MIN:
        return actions
    # 按 (card_name, kind) 分组
    groups: dict[str, list[Action]] = {}
    for a in actions:
        if a.kind == "end_turn":
            continue
        key = a.card.fingerprint()
        groups.setdefault(key, []).append(a)

    result: list[Action] = []
    for key, group in groups.items():
        if len(group) <= TARGET_KEEP:
            result.extend(group)
            continue
        # 多目标：按目标价值排序保留 top-k
        scored = [(a, _target_value(state, a)) for a in group]
        scored.sort(key=lambda x: x[1], reverse=True)
        result.extend(a for a, _ in scored[:TARGET_KEEP])

    # 结束回合始终保留
    for a in actions:
        if a.kind == "end_turn":
            result.append(a)
            break
    return result


def _target_value(state: CombatState, action: Action) -> float:
    """目标价值：击杀 > 高威胁 > 残血 > 高毒。"""
    if action.target_index < 0 or action.target_index >= len(state.enemies):
        return 0.0
    e = state.enemies[action.target_index]
    if not e.alive():
        return -1.0
    eff = effects_for_card(action.card)
    atk = eff.get("attack", 0) + state.strength
    score = 0.0
    if atk >= e.hp + e.block:
        score += 100.0  # 击杀
    score += e.intent_damage * 2.0  # 高威胁
    score += (1.0 - e.hp / max(1, e.max_hp)) * 10.0  # 残血
    score += e.poison * 0.5  # 已叠毒
    return score
