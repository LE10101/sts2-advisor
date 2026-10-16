"""战斗模拟器：给定一个战斗状态，推进玩家动作与敌人回合，供 MCTS 推演。

覆盖静默猎手核心机制：毒 / 小刀 / 弃牌 / Sly / 敏捷 / 能力牌。

模拟口径（近似点均在注释中标明）：
- 手牌是"已知牌"，抽牌堆只有计数；抽牌时优先使用 SL 牌序记忆中的真实牌，
  记忆耗尽再从基础牌池随机生成新牌。
- 弃牌为"随机弃 N 张"，被弃的 Sly 牌自动按原费打出，触发战术家/反射。
- 能力牌（精准/淬毒/无尽刀刃/毒雾/无形等）用玩家 buff 键建模。
- 敌人行为只按当前 intent 结算一轮；复杂特殊效果用近似。

目标是"够用"的决策推演引擎：把相对强弱排序做对，而非逐字节复刻。
"""

from __future__ import annotations

import random
from typing import List, Optional

from .cards import effects_for_card, make_shiv
from .evaluate import evaluate_state
from .model import Action, Card, CombatState, Enemy
from .prune import prune_actions

# 可插拔评估函数（默认启发式；CLI --model 可换成训练好的模型）
EVAL_FN = evaluate_state


def set_evaluator(fn):
    """切换状态评估函数（如注入训练好的模型评估器）。传入 None 恢复默认。"""
    global EVAL_FN
    EVAL_FN = fn if fn is not None else evaluate_state

MAX_STEPS = 60   # rollout 最大步数上限
HAND_SIZE = 5    # 每回合满手牌数（近似）
EARLY_CHECK = 6  # 每几步做一次早停评估
EARLY_LOW, EARLY_HIGH = 0.22, 0.88  # 评估稳定且明显定局时提前终止

# 基础牌池：抽牌堆未知且 SL 记忆耗尽时，抽到的牌按此概率生成
BASIC_POOL = [("打击", 1, 6, 0), ("打击", 1, 6, 0), ("防御", 1, 0, 5), ("防御", 1, 0, 5)]


# ---------------------------------------------------------------------------
# buff 数值口径
# ---------------------------------------------------------------------------
def _str(state: CombatState) -> int:   return state.player_buffs.get("力量", 0)
def _dex(state: CombatState) -> int:   return state.player_buffs.get("敏捷", 0)
def _vuln(state: CombatState) -> int:  return state.player_buffs.get("易伤", 0)
def _weak(state: CombatState) -> int:  return state.player_buffs.get("虚弱", 0)
def _acc(state: CombatState) -> int:   return state.player_buffs.get("精准", 0)
def _envenom(state: CombatState) -> int: return state.player_buffs.get("淬毒", 0)
def _intangible(state: CombatState) -> int: return state.player_buffs.get("无形", 0)


def _player_damage_modifier(state: CombatState) -> float:
    """玩家造成的伤害倍率（虚弱 -25%）。"""
    return 0.75 if _weak(state) > 0 else 1.0


def _player_taken_damage_modifier(state: CombatState) -> float:
    """玩家受到的伤害倍率（易伤 +50%）。"""
    return 1.5 if _vuln(state) > 0 else 1.0


# ---------------------------------------------------------------------------
# 战斗终止
# ---------------------------------------------------------------------------
def is_terminal(state: CombatState) -> bool:
    return state.player_hp <= 0 or not state.any_enemy_alive()


def terminal_score(state: CombatState) -> Optional[float]:
    if state.player_hp <= 0:
        return 0.0
    if not state.any_enemy_alive():
        return 1.0
    return None


def heuristic_value(state: CombatState) -> float:
    """非终局启发式（多特征加权评估，见 evaluate.py；可被 set_evaluator 替换）。"""
    return EVAL_FN(state)


# ---------------------------------------------------------------------------
# 合法动作
# ---------------------------------------------------------------------------
def legal_actions(state: CombatState) -> List[Action]:
    """当前手牌的合法动作：每张可支付牌（含目标选择）+ 结束回合。"""
    acts: List[Action] = []
    for card in state.hand:
        if card.cost > state.energy:
            continue
        ef = effects_for_card(card)
        # 无目标可打：AOE / 纯技能（无伤害无单体毒）
        no_target = ef.aoe or (ef.damage <= 0 and ef.poison <= 0)
        if no_target:
            acts.append(Action.play(card.hand_index, target_id=None))
        else:
            targets = [e for e in state.enemies if e.alive]
            if targets:
                for e in targets:
                    acts.append(Action.play(card.hand_index, target_id=e.id))
            else:
                acts.append(Action.play(card.hand_index, target_id=None))
    acts.append(Action.end_turn())
    return prune_actions(state, acts)


# ---------------------------------------------------------------------------
# 抽牌（支持 SL 牌序记忆）
# ---------------------------------------------------------------------------
def _draw_card(state: CombatState, rng: random.Random, memory=None):
    """从抽牌堆抽一张。memory: DrawOrderMemory，按 state.draw_pos 取已知真实牌。"""
    if memory is not None:
        real = memory.peek(state.draw_pos)
        if real is not None:
            state.hand.append(Card(name=real.name, hand_index=_next_index(state), cost=real.cost,
                                   damage=real.damage, block=real.block, description=real.description,
                                   card_type=real.card_type, shiv=real.shiv, sly=real.sly,
                                   exhaust=real.exhaust))
            state.draw_pos += 1
            state.draw_pile = max(0, state.draw_pile - 1)
            return
    if state.draw_pile <= 0:
        state.draw_pile = state.discard_pile
        state.discard_pile = 0
    if state.draw_pile > 0:
        state.draw_pile -= 1
        name, cost, dmg, blk = rng.choice(BASIC_POOL)
        state.hand.append(Card(name=name, hand_index=_next_index(state), cost=cost,
                               damage=dmg, block=blk))
        state.draw_pos += 1


def _next_index(state: CombatState) -> int:
    """返回一个不与现有手牌冲突的手牌索引（单调递增，不复用已空出索引）。"""
    return max([c.hand_index for c in state.hand] + [-1]) + 1


def _draw_cards(state: CombatState, n: int, rng: random.Random, memory):
    for _ in range(n):
        _draw_card(state, rng, memory)


# ---------------------------------------------------------------------------
# 伤害 / 毒结算辅助
# ---------------------------------------------------------------------------
def _enemy_deal_damage(e: Enemy, dmg: int):
    if e.block > 0:
        absorbed = min(e.block, dmg)
        e.block -= absorbed
        dmg -= absorbed
    if e.buffs.get("易伤", 0) > 0:
        dmg = int(dmg * 1.5)
    e.hp = max(0, e.hp - dmg)


def _apply_poison(e: Enemy, amount: int):
    if amount > 0:
        e.buffs["毒"] = e.buffs.get("毒", 0) + amount


def _target(state: CombatState, target_id: Optional[int]) -> Optional[Enemy]:
    if target_id is None:
        return None
    return next((e for e in state.enemies if e.id == target_id), None)


def _lookup_rule(name: str):
    from .cards import CARD_EFFECTS
    rule = CARD_EFFECTS.get(name)
    if rule is None:
        for k, r in CARD_EFFECTS.items():
            if name in r.get("aliases", []):
                return r
    return rule


def _is_aoe_rule(name: str) -> bool:
    rule = _lookup_rule(name)
    return bool(rule and rule.get("aoe"))


# ---------------------------------------------------------------------------
# 弃牌：随机弃 N 张，触发 Sly 与弃牌收益
# ---------------------------------------------------------------------------
def _discard_cards(state: CombatState, n: int, rng: random.Random, memory):
    discardable = [c for c in state.hand]
    n = min(n, len(discardable))
    if n <= 0:
        return
    chosen = rng.sample(discardable, n)
    for card in chosen:
        state.hand = [c for c in state.hand if c.hand_index != card.hand_index]
        if card.sly:
            _resolve_played_card(state, card, None, rng, memory)
        state.discard_pile += 1
        if state.player_buffs.get("战术家", 0) > 0:
            state.energy += 1
        if state.player_buffs.get("反射", 0) > 0:
            _draw_cards(state, 2, rng, memory)


# ---------------------------------------------------------------------------
# 结算一张已打出 / 被 Sly 触发的牌
# ---------------------------------------------------------------------------
def _resolve_played_card(state: CombatState, card: Card, target_id: Optional[int],
                         rng: random.Random, memory):
    ef = effects_for_card(card)
    rule = _lookup_rule(card.name)

    # 特殊：催化（毒翻倍）、移除敌人格挡
    if rule and rule.get("poison_x"):
        tgt = _target(state, target_id)
        if tgt is not None and tgt.alive:
            tgt.buffs["毒"] = tgt.buffs.get("毒", 0) * 3
    if rule and rule.get("remove_enemy_block"):
        tgt = _target(state, target_id)
        if tgt is not None and tgt.alive:
            tgt.block = 0

    # 伤害
    dmg = ef.damage + _str(state)
    if card.shiv:
        dmg += _acc(state) * 4
    dmg = max(0, int(dmg * _player_damage_modifier(state)))
    if dmg > 0:
        aoe = ef.aoe or _is_aoe_rule(card.name) or (target_id is None and ef.poison <= 0)
        if aoe:
            for e in state.enemies:
                if e.alive:
                    _enemy_deal_damage(e, dmg)
                    if _envenom(state) > 0:
                        _apply_poison(e, _envenom(state))
        else:
            tgt = _target(state, target_id)
            if tgt is not None and tgt.alive:
                _enemy_deal_damage(tgt, dmg)
                if _envenom(state) > 0:
                    _apply_poison(tgt, _envenom(state))

    # 格挡
    state.player_block += ef.block + _dex(state)

    # 毒
    if ef.poison > 0:
        if ef.aoe:
            for e in state.enemies:
                if e.alive:
                    _apply_poison(e, ef.poison)
        else:
            tgt = _target(state, target_id)
            if tgt is not None and tgt.alive:
                _apply_poison(tgt, ef.poison)
    if ef.poison_aoe > 0:
        for e in state.enemies:
            if e.alive:
                _apply_poison(e, ef.poison_aoe)

    # debuff / 降力量
    if ef.enemy_debuffs:
        for k, v in ef.enemy_debuffs.items():
            tgts = [t for t in state.enemies if t.alive] if (ef.aoe or target_id is None) else [_target(state, target_id)]
            for t in tgts:
                if t:
                    t.buffs[k] = t.buffs.get(k, 0) + v
    if ef.weak_aoe:
        for e in state.enemies:
            if e.alive:
                e.buffs["虚弱"] = e.buffs.get("虚弱", 0) + ef.weak_aoe
    if ef.vulnerable_aoe:
        for e in state.enemies:
            if e.alive:
                e.buffs["易伤"] = e.buffs.get("易伤", 0) + ef.vulnerable_aoe
    if ef.enemy_strength_loss:
        for e in state.enemies:
            if e.alive:
                e.buffs["力量"] = e.buffs.get("力量", 0) - ef.enemy_strength_loss

    # 玩家 buff / 能力
    for k, v in ef.self_buffs.items():
        state.player_buffs[k] = state.player_buffs.get(k, 0) + v
    if ef.retain_block:
        state.player_buffs["模糊"] = 1

    # 能量 / 治疗
    state.energy += ef.energy_gain
    state.player_hp = min(state.max_hp, state.player_hp + ef.heal)

    # 弃牌 -> 抽牌 -> 生成小刀
    if ef.discard > 0:
        _discard_cards(state, ef.discard, rng, memory)
    if ef.draw > 0:
        _draw_cards(state, ef.draw, rng, memory)
    if ef.shiv_count > 0:
        for _ in range(ef.shiv_count):
            state.hand.append(make_shiv(_next_index(state)))


# ---------------------------------------------------------------------------
# 应用单个动作（玩家回合内）
# ---------------------------------------------------------------------------
def apply_action(state: CombatState, action: Action, rng: random.Random,
                 memory=None) -> Optional[CombatState]:
    """应用一个玩家动作，返回新状态。非法动作返回 None（始终基于独立副本）。"""
    if action.kind == "end_turn":
        return state
    if action.kind == "play_card":
        state = state.copy()
        card = next((c for c in state.hand if c.hand_index == action.hand_index), None)
        if card is None or card.cost > state.energy:
            return None
        state.energy -= card.cost
        state.hand = [c for c in state.hand if c.hand_index != card.hand_index]
        if not card.exhaust and not card.shiv:
            state.discard_pile += 1
        _resolve_played_card(state, card, action.target_id, rng, memory)
        return state
    return None


# ---------------------------------------------------------------------------
# 敌人回合 + 新回合结算
# ---------------------------------------------------------------------------
def enemy_turn(state: CombatState, rng: random.Random, memory=None) -> CombatState:
    """结算所有存活敌人的意图，然后进入下一个玩家回合（含毒结算与能力结算）。"""
    state = state.copy()
    vuln_mult = _player_taken_damage_modifier(state)

    for e in state.enemies:
        if not e.alive:
            continue
        intent = e.intent
        if intent == "attack":
            dmg = e.intent_value + e.buffs.get("力量", 0)
            if e.buffs.get("易伤", 0) > 0:
                dmg = int(dmg * 1.5)
            dmg = int(dmg * vuln_mult)
            if _intangible(state) > 0:
                dmg = 0
            if state.player_block > 0:
                absorbed = min(state.player_block, dmg)
                state.player_block -= absorbed
                dmg -= absorbed
            state.player_hp = max(0, state.player_hp - dmg)
        elif intent == "defend":
            e.block += e.intent_value
        elif intent in ("buff", "strength"):
            e.buffs["力量"] = e.buffs.get("力量", 0) + (e.intent_value or 2)

    # 新玩家回合开始
    state.turn += 1
    state.energy = 3
    if state.player_buffs.get("模糊", 0) > 0:
        state.player_buffs["模糊"] = 0
    else:
        state.player_block = 0

    # 能力：无尽刀刃 -> +1 小刀；毒雾 -> 全体毒+2
    if state.player_buffs.get("无尽刀刃", 0) > 0:
        state.hand.append(make_shiv(_next_index(state)))
    if state.player_buffs.get("毒雾", 0) > 0:
        for e in state.enemies:
            if e.alive:
                _apply_poison(e, 2 * state.player_buffs.get("毒雾", 0))

    # 无形衰减
    if _intangible(state) > 0:
        state.player_buffs["无形"] -= 1
        if state.player_buffs["无形"] <= 0:
            del state.player_buffs["无形"]

    # 毒结算：敌人受到 = 毒层数伤害，毒 -1（加速器额外结算一次）
    extra = 1 if state.player_buffs.get("加速器", 0) > 0 else 0
    for e in state.enemies:
        if e.alive:
            for _ in range(1 + extra):
                p = e.buffs.get("毒", 0)
                if p > 0:
                    e.hp = max(0, e.hp - p)
                    e.buffs["毒"] = max(0, p - 1)
                else:
                    break

    # 补牌到满手
    while len(state.hand) < HAND_SIZE and (state.draw_pile + state.discard_pile) > 0:
        _draw_card(state, rng, memory)

    # 敌人易伤/虚弱衰减
    for e in state.enemies:
        for k in list(e.buffs.keys()):
            if k in ("易伤", "虚弱"):
                e.buffs[k] -= 1
                if e.buffs[k] <= 0:
                    del e.buffs[k]
    return state


# ---------------------------------------------------------------------------
# rollout：随机打到底
# ---------------------------------------------------------------------------
def rollout(state: CombatState, rng: random.Random, max_steps: int = MAX_STEPS,
            policy=None, memory=None) -> float:
    """从给定状态随机行动直到终局或步数上限，返回收益值。

    带早停：评估值连续稳定且明显定局（大优/大劣）时提前返回，省去白跑步数。
    """
    s = state
    steps = 0
    last_val = None
    while steps < max_steps:
        sc = terminal_score(s)
        if sc is not None:
            return sc
        # 早停检查
        if steps >= EARLY_CHECK and steps % EARLY_CHECK == 0:
            val = EVAL_FN(s)
            if last_val is not None and val <= last_val + 1e-3:
                if val < EARLY_LOW or val > EARLY_HIGH:
                    return val
            last_val = val
        acts = legal_actions(s)
        if not acts:
            return EVAL_FN(s)
        a = policy(s, acts, rng) if policy is not None else rng.choice(acts)
        if a.kind == "end_turn":
            s = enemy_turn(s, rng, memory)
        else:
            ns = apply_action(s, a, rng, memory)
            s = ns if ns is not None else enemy_turn(s, rng, memory)
        steps += 1
    t = terminal_score(s)
    return t if t is not None else EVAL_FN(s)


# ---------------------------------------------------------------------------
# 全回合推进（供 CLI / 离线演示使用）
# ---------------------------------------------------------------------------
def play_player_turn(state: CombatState, actions: List[Action], rng: random.Random,
                     memory=None) -> CombatState:
    s = state
    for a in actions:
        if is_terminal(s):
            break
        if a.kind == "end_turn":
            break
        ns = apply_action(s, a, rng, memory)
        if ns is not None:
            s = ns
    if not is_terminal(s):
        s = enemy_turn(s, rng, memory)
    return s
