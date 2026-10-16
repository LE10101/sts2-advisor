"""战斗模拟器：可 rollout 的状态转移，支持毒/Shiv/弃牌/Sly/能力牌。"""
from __future__ import annotations
import random
from typing import Callable, Optional
from .model import CombatState, Card, Enemy, Action
from .cards import effects_for_card, make_shiv

# 可注入的评估器（V3 启发式 / V4 MLP）。None 时 rollout 用随机终止。
EVAL_FN: Optional[Callable[[CombatState], float]] = None


def set_evaluator(fn: Optional[Callable[[CombatState], float]]):
    global EVAL_FN
    EVAL_FN = fn


_next_index_counter = [10000]


def _fresh_hand_index() -> int:
    _next_index_counter[0] += 1
    return _next_index_counter[0]


def legal_actions(state: CombatState, prune: bool = True) -> list[Action]:
    """当前可执行动作：所有能打的牌（每个存活敌人一个目标）+ 结束回合。"""
    actions: list[Action] = []
    alive = state.alive_enemies()
    for card in state.hand:
        # 跳过不可打出的牌（状态牌/诅咒/已满额等）
        if not getattr(card, "playable", True):
            continue
        # 诅咒牌 cost=-1，直接跳过
        if card.cost < 0:
            continue
        eff = effects_for_card(card)
        cost = eff.get("cost", card.cost if card.cost >= 0 else 1)
        if cost > state.energy:
            continue
        if eff.get("power") or eff.get("attack", 0) == 0 and eff.get("block", 0) == 0 \
                and not eff.get("poison") and not eff.get("draw") and not eff.get("shiv"):
            actions.append(Action("play_card", card, -1))
            continue
        if eff.get("attack", 0) > 0 or eff.get("poison") or eff.get("weak") \
                or eff.get("vulnerable") or eff.get("poison_multiply"):
            for e in alive:
                actions.append(Action("play_card", card, e.index))
        else:
            actions.append(Action("play_card", card, -1))
    actions.append(Action("end_turn"))
    if prune:
        from .prune import prune_actions
        actions = prune_actions(state, actions)
    return actions


def _draw_cards(state: CombatState, n: int):
    for _ in range(n):
        if not state.draw_pile:
            if not state.discard_pile:
                return
            state.draw_pile = state.discard_pile
            state.discard_pile = []
            random.shuffle(state.draw_pile)
        c = state.draw_pile.pop(0)
        c.hand_index = _fresh_hand_index()
        state.hand.append(c)
        state.draw_pos += 1


def _discard_card(state: CombatState, card: Card):
    """弃牌：触发 Sly（被弃时自动打出）。"""
    if card in state.hand:
        state.hand.remove(card)
    eff = effects_for_card(card)
    if eff.get("sly"):
        # Sly：被弃时按原费自动打出（不消耗能量，不进弃牌堆）
        _apply_card_effect(state, card, -1, free=True)
        state.exhaust_pile.append(card)
    else:
        state.discard_pile.append(card)


def _deal_damage(state: CombatState, target: Enemy, dmg: int):
    """玩家攻击敌人：敌人脆弱 +50%，玩家虚弱 -25%。"""
    if dmg <= 0:
        return
    if target.vulnerable > 0:
        dmg = int(dmg * 1.5)
    if state.weak > 0:
        dmg = int(dmg * 0.75)
    if target.block > 0:
        absorbed = min(target.block, dmg)
        target.block -= absorbed
        dmg -= absorbed
    target.hp -= dmg


def _apply_card_effect(state: CombatState, card: Card, target_idx: int,
                       free: bool = False, to_discard: bool = True):
    eff = effects_for_card(card)
    cost = eff.get("cost", card.cost if card.cost >= 0 else 1)
    if not free:
        state.energy -= cost

    # 更新出牌计数（终结技等依赖此值）
    state.cards_played_this_turn += 1
    is_attack = eff.get("attack", 0) > 0 or eff.get("finisher") or eff.get("hits", 1) > 1 and eff.get("attack", 0) > 0
    if is_attack:
        state.attacks_played_this_turn += 1
    else:
        state.skills_played_this_turn += 1

    target = None
    if 0 <= target_idx < len(state.enemies):
        target = state.enemies[target_idx]

    # 暴露：去除目标格挡
    if eff.get("remove_block") and target is not None:
        target.block = 0

    # 多段攻击（啄击等）
    hits = eff.get("hits", 1)
    atk = eff.get("attack", 0) + state.strength if eff.get("attack", 0) > 0 else 0

    # 终结技：伤害 = 本回合已打出攻击牌数 × finisher_damage
    if eff.get("finisher"):
        finisher_dmg = eff.get("finisher_damage", 6) + state.strength
        hits = max(0, state.attacks_played_this_turn)
        atk = finisher_dmg if hits > 0 else 0

    if atk > 0 and target is not None:
        for _ in range(hits):
            _deal_damage(state, target, atk)
        # 风的女儿：打出攻击牌获得格挡（多段攻击只触发一次）
        if "DAUGHTER_OF_THE_WIND" in state.relics:
            state.player_block += 2

    if eff.get("block", 0) > 0:
        state.player_block += eff["block"] + state.dexterity

    if eff.get("poison", 0) > 0 and target is not None:
        # 咕嘟冒泡：只有敌人已中毒时才加毒
        if eff.get("conditional_poison") and target.poison <= 0:
            pass  # 敌人没毒，不生效
        else:
            target.poison += eff["poison"]

    if eff.get("aoe_poison"):
        for e in state.alive_enemies():
            e.poison += eff.get("poison", 0)

    if eff.get("poison_multiply") and target is not None:
        target.poison *= eff["poison_multiply"]

    if eff.get("weak", 0) > 0 and target is not None:
        target.weak += eff["weak"]
    if eff.get("vulnerable", 0) > 0 and target is not None:
        target.vulnerable += eff["vulnerable"]

    if eff.get("draw", 0) > 0:
        _draw_cards(state, eff["draw"])

    if eff.get("energy", 0) > 0:
        state.energy += eff["energy"]

    if eff.get("shiv", 0) > 0:
        for _ in range(eff["shiv"]):
            shiv = make_shiv()
            shiv.hand_index = _fresh_hand_index()
            state.hand.append(shiv)

    if eff.get("discard", 0) > 0:
        for _ in range(eff["discard"]):
            if state.hand:
                _discard_card(state, state.hand[0])

    if eff.get("dexterity", 0) > 0:
        state.dexterity += eff["dexterity"]

    if eff.get("strength", 0) > 0:
        state.strength += eff["strength"]

    # 尖啸：所有敌人失去力量
    if eff.get("strength_loss", 0) > 0:
        for e in state.alive_enemies():
            e.strength = max(0, e.strength - eff["strength_loss"])

    # 侧步：下回合获得能量
    if eff.get("energy_next_turn", 0) > 0:
        state.__dict__.setdefault("next_turn_energy", 0)
        state.next_turn_energy += eff["energy_next_turn"]

    # 毒性爆发：立即触发所有敌人的中毒
    if eff.get("trigger_poison"):
        for e in state.alive_enemies():
            if e.poison > 0:
                e.hp -= e.poison
                e.poison = max(0, e.poison - 1)

    # 蜃景：获得等于所有敌人中毒层数总和的格挡
    if eff.get("block_from_poison"):
        total_poison = sum(e.poison for e in state.alive_enemies())
        state.player_block += total_poison + state.dexterity

    # 墨之刃：添加小刀到手牌（和 shiv 效果相同）
    if eff.get("add_shiv", 0) > 0:
        for _ in range(eff["add_shiv"]):
            shiv = make_shiv()
            shiv.hand_index = _fresh_hand_index()
            state.hand.append(shiv)

    if eff.get("power"):
        if eff.get("shiv_per_turn", 0) > 0:
            state.__dict__.setdefault("shiv_per_turn", 0)
            state.shiv_per_turn += eff["shiv_per_turn"]
        if eff.get("block_per_turn", 0) > 0:
            state.__dict__.setdefault("block_per_turn", 0)
            state.block_per_turn += eff["block_per_turn"]
        if eff.get("intangible"):
            state.__dict__["intangible"] = True
        if eff.get("draw_per_turn", 0) > 0:
            state.__dict__.setdefault("draw_per_turn", 0)
            state.draw_per_turn += eff["draw_per_turn"]
        # 永冻冰晶：第一次打能力牌获得格挡
        if "PERMAFROST" in state.relics and not getattr(state, "power_card_played", False):
            state.player_block += 6
            state.power_card_played = True

    if to_discard:
        if eff.get("exhaust") or card.exhaust:
            state.exhaust_pile.append(card)
            # 金纸：每消耗3张牌抽1张
            state.exhausted_count += 1
            if "JOSS_PAPER" in state.relics and state.exhausted_count % 3 == 0:
                _draw_cards(state, 1)
        elif not eff.get("sly"):
            state.discard_pile.append(card)


def apply_action(state: CombatState, action: Action) -> CombatState:
    """执行动作，返回新状态（不修改原状态）。"""
    s = state.copy()
    if action.kind == "end_turn":
        _end_turn(s)
    elif action.kind == "play_card":
        if action.card in s.hand:
            s.hand.remove(action.card)
            _apply_card_effect(s, action.card, action.target_index)
            # 投斧：每场战斗第一张牌多打一次
            if not s.first_card_played and "THROWING_AXE" in s.relics:
                s.first_card_played = True
                _apply_card_effect(s, action.card, action.target_index,
                                   free=True, to_discard=False)
            else:
                s.first_card_played = True
    return s


def _end_turn(state: CombatState):
    # 弃掉手牌
    for c in list(state.hand):
        if c in state.hand:
            state.hand.remove(c)
        if effects_for_card(c).get("ethereal"):
            state.exhaust_pile.append(c)
        else:
            state.discard_pile.append(c)
    state.player_block = 0
    # 敌人回合
    _enemy_turn(state)
    # 新回合
    state.turn += 1
    state.energy = state.max_energy
    state.exhausted_count = 0  # 金纸：每回合重置消耗计数
    state.cards_played_this_turn = 0
    state.attacks_played_this_turn = 0
    state.skills_played_this_turn = 0
    state.first_card_played = False
    # 水银沙漏：回合开始对所有敌人造成3伤害
    if "MERCURY_HOURGLASS" in state.relics:
        for e in state.alive_enemies():
            e.hp -= 3
    # 侧步：下回合额外能量
    if getattr(state, "next_turn_energy", 0) > 0:
        state.energy += state.next_turn_energy
        state.next_turn_energy = 0
    # 船夹板：第二回合开始获得10格挡
    if state.turn == 2 and "HORN_CLEAT" in state.relics:
        state.player_block += 10
    if getattr(state, "block_per_turn", 0) > 0:
        state.player_block += state.block_per_turn
    if getattr(state, "shiv_per_turn", 0) > 0:
        for _ in range(state.shiv_per_turn):
            shiv = make_shiv()
            shiv.hand_index = _fresh_hand_index()
            state.hand.append(shiv)
    draw_n = 5 + getattr(state, "draw_per_turn", 0)
    _draw_cards(state, draw_n)
    # 减益衰减
    if state.weak > 0:
        state.weak -= 1
    if state.vulnerable > 0:
        state.vulnerable -= 1


def _enemy_turn(state: CombatState):
    for e in state.alive_enemies():
        # 毒结算（敌人回合开始）
        if e.poison > 0:
            e.hp -= e.poison
            e.poison -= 1
        if not e.alive():
            continue
        # 敌人攻击
        dmg = e.intent_total_damage or e.intent_damage
        if dmg > 0:
            # 敌人力量加成（每点+1伤害/段，粗略用hits估算）
            dmg += e.strength * (e.intent_hits or 1)
            if e.weak > 0:
                dmg = int(dmg * 0.75)
            if state.vulnerable > 0:
                dmg = int(dmg * 1.5)
            if getattr(state, "intangible", False):
                dmg = min(dmg, 1)
            if state.player_block > 0:
                absorbed = min(state.player_block, dmg)
                state.player_block -= absorbed
                dmg -= absorbed
            # 钨合金棍：每次失去生命减少1点
            if "TUNGSTEN_ROD" in state.relics and dmg > 0:
                dmg = max(0, dmg - 1)
            state.player_hp -= dmg
        if e.weak > 0:
            e.weak -= 1
        if e.vulnerable > 0:
            e.vulnerable -= 1


def is_terminal(state: CombatState) -> bool:
    return state.player_hp <= 0 or not state.alive_enemies()


def rollout(state: CombatState, max_steps: int = 60, policy=None,
            rng: Optional[random.Random] = None) -> float:
    """从 state 开始随机 rollout，返回 [0,1] 收益。带早停与评估器。"""
    rng = rng or random
    s = state.copy()
    for step in range(max_steps):
        if is_terminal(s):
            break
        # 早停：每 8 步用评估器判断是否明显优劣
        if EVAL_FN is not None and step > 0 and step % 8 == 0:
            v = EVAL_FN(s)
            if v > 0.85 or v < 0.15:
                return v
        actions = legal_actions(s, prune=True)
        if not actions:
            break
        if policy:
            action = policy(s, actions, rng)
        else:
            action = rng.choice(actions)
        s = apply_action(s, action)
    if is_terminal(s):
        if s.player_hp <= 0:
            return 0.0
        return 1.0
    if EVAL_FN is not None:
        return EVAL_FN(s)
    hp_ratio = s.player_hp / max(1, s.player_max_hp)
    enemy_hp = sum(e.hp for e in s.alive_enemies())
    enemy_max = sum(e.max_hp for e in s.enemies) or 1
    return max(0.0, min(1.0, 0.5 + 0.3 * hp_ratio - 0.3 * (enemy_hp / enemy_max)))
