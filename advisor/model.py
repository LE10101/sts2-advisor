"""战斗状态数据模型：从 STS2 AI Agent 快照容错解析成内部结构。

适配 CharTyr/STS2-Agent mod v0.16.2+ 的 state 结构：
- combat.player: {current_hp, max_hp, block, energy, powers:[...]}
- combat.hand: [{index, card_id, name, energy_cost, resolved_rules_text, dynamic_values, playable}]
- combat.enemies: [{index, enemy_id, name, current_hp, max_hp, block, powers, intents}]
"""
from __future__ import annotations
import copy
from typing import Any, Optional


def _pick(d: dict, *keys, default=None):
    """按优先级从嵌套 dict 里取值，容错字段名差异。"""
    for k in keys:
        if isinstance(k, str) and "." in k:
            cur = d
            ok = True
            for part in k.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok:
                return cur
        elif isinstance(d, dict) and k in d:
            return d[k]
    return default


def _power_amount(powers: list, *power_ids: str) -> int:
    """从 powers 数组里提取指定 power_id 的 amount，容错大小写和后缀。"""
    if not isinstance(powers, list):
        return 0
    target_ids = {pid.upper().replace("_POWER", "") for pid in power_ids}
    for p in powers:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("power_id", p.get("id", ""))).upper().replace("_POWER", "")
        if pid in target_ids:
            try:
                return int(p.get("amount", 0))
            except (ValueError, TypeError):
                return 0
    return 0


def _intent_info(intents: list) -> dict:
    """从 intents 数组提取完整意图信息。"""
    info = {"type": "?", "damage": 0, "hits": 1, "total_damage": 0,
            "is_aoe": False, "status_card_count": 0}
    if not isinstance(intents, list) or not intents:
        return info
    total = 0
    for it in intents:
        if not isinstance(it, dict):
            continue
        itype = str(it.get("intent_type", "")).lower()
        if itype and info["type"] == "?":
            info["type"] = it.get("intent_type", "?")
        dmg = it.get("damage", 0)
        hits = it.get("hits", 1) or 1
        try:
            dmg = int(dmg) if dmg is not None else 0
            hits = int(hits) if hits is not None else 1
        except (ValueError, TypeError):
            dmg, hits = 0, 1
        total += dmg * hits
        if "attack" in itype and info["damage"] == 0:
            info["damage"] = dmg
            info["hits"] = hits
        if it.get("status_card_count"):
            try:
                info["status_card_count"] = int(it.get("status_card_count"))
            except (ValueError, TypeError):
                pass
    info["total_damage"] = total
    # AOE 判断：intent_type 包含 attack 且没有明确目标，或标签包含 all/aoe
    first = intents[0] if intents else {}
    label = str(first.get("label", "")).lower()
    if "all" in label or "aoe" in label or "全体" in label:
        info["is_aoe"] = True
    return info


class Card:
    def __init__(self, name: str, cost: int = -1, card_type: str = "attack",
                 upgraded: bool = False, hand_index: int = -1, exhaust: bool = False,
                 card_id: str = "", requires_target: bool = False,
                 target_type: str = "", playable: bool = True,
                 resolved_text: str = "", dynamic_values: Optional[list] = None):
        self.name = name
        self.cost = cost
        self.type = card_type
        self.upgraded = upgraded
        self.hand_index = hand_index
        self.exhaust = exhaust
        self.card_id = card_id
        self.requires_target = requires_target
        self.target_type = target_type
        self.playable = playable
        self.resolved_text = resolved_text
        self.dynamic_values = dynamic_values or []

    def dynamic_value(self, name: str) -> Optional[int]:
        """从 dynamic_values 里取指定名称的 current_value。"""
        for dv in self.dynamic_values:
            if isinstance(dv, dict) and dv.get("name", "").lower() == name.lower():
                try:
                    return int(dv.get("current_value", dv.get("base_value")))
                except (ValueError, TypeError):
                    return None
        return None

    def fingerprint(self) -> str:
        return f"{self.card_id or self.name}|{self.cost}|{self.type}|{1 if self.upgraded else 0}"

    def __repr__(self):
        return f"Card({self.name},cost={self.cost},id={self.card_id})"

    @staticmethod
    def from_dict(d: dict, hand_index: int = -1) -> "Card":
        ctype = str(_pick(d, "card_type", "type", default="")).lower()
        # mod 可能不提供 card_type，从 card_id / resolved_text 推断
        if not ctype or ctype == "none":
            cid = str(d.get("card_id", "")).upper()
            rtext = str(d.get("resolved_rules_text", ""))
            if "POWER" in cid:
                ctype = "power"
            elif "ATTACK" in cid or cid in ("STRIKE", "BASH", "NEUTRALIZE", "SNAKEBITE",
                                              "POISONED_STAB", "DAGGER_THROW", "FINISHER"):
                ctype = "attack"
            elif "DEFEND" in cid or "SKILL" in cid:
                ctype = "skill"
            elif "伤害" in rtext and "格挡" not in rtext:
                ctype = "attack"
            elif "获得" in rtext and ("力量" in rtext or "敏捷" in rtext or "能力" in rtext):
                ctype = "power"
            else:
                ctype = "skill"
        return Card(
            name=str(_pick(d, "name", "card_name", default="?")),
            cost=int(_pick(d, "energy_cost", "cost", default=-1)),
            card_type=ctype,
            upgraded=bool(_pick(d, "upgraded", default=False)),
            hand_index=hand_index if hand_index >= 0 else int(_pick(d, "index", default=hand_index)),
            exhaust=bool(_pick(d, "exhaust", default=False)),
            card_id=str(_pick(d, "card_id", "id", default="")),
            requires_target=bool(_pick(d, "requires_target", default=False)),
            target_type=str(_pick(d, "target_type", default="")),
            playable=bool(_pick(d, "playable", "can_play_result", default=True)),
            resolved_text=str(_pick(d, "resolved_rules_text", default="")),
            dynamic_values=_pick(d, "dynamic_values", default=[]),
        )


class Enemy:
    def __init__(self, name: str, hp: int, max_hp: int, block: int = 0,
                 intent: str = "?", intent_damage: int = 0, poison: int = 0,
                 weak: int = 0, vulnerable: int = 0, strength: int = 0,
                 index: int = 0, enemy_id: str = "", is_alive: bool = True,
                 intent_hits: int = 1, intent_total_damage: int = 0,
                 is_aoe: bool = False, intent_type: str = "?"):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.block = block
        self.intent = intent
        self.intent_damage = intent_damage
        self.intent_hits = intent_hits
        self.intent_total_damage = intent_total_damage
        self.is_aoe = is_aoe
        self.intent_type = intent_type
        self.poison = poison
        self.weak = weak
        self.vulnerable = vulnerable
        self.strength = strength
        self.index = index
        self.enemy_id = enemy_id
        self.is_alive = is_alive

    def alive(self) -> bool:
        return self.hp > 0 and self.is_alive

    def __repr__(self):
        return f"Enemy({self.name},{self.hp}/{self.max_hp})"

    @staticmethod
    def from_dict(d: dict, index: int = 0) -> "Enemy":
        powers = _pick(d, "powers", default=[]) or []
        intent_info = _intent_info(_pick(d, "intents", default=[]))
        return Enemy(
            name=str(_pick(d, "name", default="enemy")),
            hp=int(_pick(d, "current_hp", "hp", default=1)),
            max_hp=int(_pick(d, "max_hp", "hp_max", default=1)),
            block=int(_pick(d, "block", default=0)),
            intent=str(_pick(d, "intent", "move_id", default=intent_info["type"])),
            intent_damage=intent_info["damage"],
            intent_hits=intent_info["hits"],
            intent_total_damage=intent_info["total_damage"],
            is_aoe=intent_info["is_aoe"],
            intent_type=intent_info["type"],
            poison=_power_amount(powers, "POISON"),
            weak=_power_amount(powers, "WEAK"),
            vulnerable=_power_amount(powers, "VULNERABLE"),
            strength=_power_amount(powers, "STRENGTH"),
            index=index if index >= 0 else int(_pick(d, "index", default=index)),
            enemy_id=str(_pick(d, "enemy_id", "id", default="")),
            is_alive=bool(_pick(d, "is_alive", default=True)),
        )


class Action:
    """玩家动作：出牌(带目标) 或 结束回合。"""
    def __init__(self, kind: str, card: Optional[Card] = None, target_index: int = -1):
        self.kind = kind  # "play_card" / "end_turn"
        self.card = card
        self.target_index = target_index

    def describe(self, state: "CombatState") -> str:
        if self.kind == "end_turn":
            return "结束回合"
        tgt = ""
        if self.target_index >= 0 and self.target_index < len(state.enemies):
            tgt = f" → {state.enemies[self.target_index].name}"
        return f"打出[{self.card.name}]{tgt}"

    def to_dict(self) -> dict:
        if self.kind == "end_turn":
            return {"action": "end_turn"}
        return {"action": "play_card", "card_index": self.card.hand_index,
                "target_index": self.target_index if self.target_index >= 0 else None}


class CombatState:
    def __init__(self):
        self.player_hp = 70
        self.player_max_hp = 70
        self.player_block = 0
        self.energy = 3
        self.max_energy = 3
        self.hand: list[Card] = []
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []
        self.exhaust_pile: list[Card] = []
        self.enemies: list[Enemy] = []
        self.turn = 1
        self.poison = 0
        self.weak = 0
        self.vulnerable = 0
        self.frail = 0
        self.strength = 0
        self.dexterity = 0
        self.draw_pos = 0
        self.phase = "combat"
        self.cards_played_this_turn = 0
        self.attacks_played_this_turn = 0
        self.skills_played_this_turn = 0
        self.relics: list[str] = []  # 遗物ID列表
        self.first_card_played = False  # 投斧：本回合第一张牌是否已打出
        self.exhausted_count = 0  # 金纸：本回合已消耗牌数
        self.power_card_played = False  # 永冻冰晶：是否已打过能力牌

    def copy(self) -> "CombatState":
        c = CombatState()
        c.player_hp = self.player_hp
        c.player_max_hp = self.player_max_hp
        c.player_block = self.player_block
        c.energy = self.energy
        c.max_energy = self.max_energy
        c.hand = [copy.copy(x) for x in self.hand]
        c.draw_pile = [copy.copy(x) for x in self.draw_pile]
        c.discard_pile = [copy.copy(x) for x in self.discard_pile]
        c.exhaust_pile = [copy.copy(x) for x in self.exhaust_pile]
        c.enemies = [copy.copy(x) for x in self.enemies]
        c.turn = self.turn
        c.poison = self.poison
        c.weak = self.weak
        c.vulnerable = self.vulnerable
        c.frail = self.frail
        c.strength = self.strength
        c.dexterity = self.dexterity
        c.draw_pos = self.draw_pos
        c.phase = self.phase
        c.cards_played_this_turn = self.cards_played_this_turn
        c.attacks_played_this_turn = self.attacks_played_this_turn
        c.skills_played_this_turn = self.skills_played_this_turn
        c.relics = list(self.relics)
        c.first_card_played = self.first_card_played
        c.exhausted_count = self.exhausted_count
        c.power_card_played = self.power_card_played
        return c

    @staticmethod
    def from_snapshot(snap: dict) -> "CombatState":
        """从 STS2 AI Agent 的 combat 快照解析。snap 应为 state.data.combat。"""
        s = CombatState()
        s.phase = str(_pick(snap, "phase", "game_phase", default="combat"))

        # 玩家状态
        player = _pick(snap, "player", "player_state", default={}) or {}
        s.player_hp = int(_pick(player, "current_hp", "hp", default=70))
        s.player_max_hp = int(_pick(player, "max_hp", "hp_max", default=70))
        s.player_block = int(_pick(player, "block", default=0))
        s.energy = int(_pick(player, "energy", "current_energy", default=3))
        s.max_energy = int(_pick(player, "max_energy", default=3))
        s.cards_played_this_turn = int(_pick(player, "cards_played_this_turn", default=0))
        s.attacks_played_this_turn = int(_pick(player, "attacks_played_this_turn", default=0))
        s.skills_played_this_turn = int(_pick(player, "skills_played_this_turn", default=0))

        powers = _pick(player, "powers", default=[]) or []
        s.weak = _power_amount(powers, "WEAK")
        s.vulnerable = _power_amount(powers, "VULNERABLE")
        s.frail = _power_amount(powers, "FRAIL")
        s.strength = _power_amount(powers, "STRENGTH")
        s.dexterity = _power_amount(powers, "DEXTERITY")
        s.poison = _power_amount(powers, "POISON", "NOXIOUS_FUMES")

        # 手牌
        hand = _pick(snap, "hand", default=[]) or []
        s.hand = [Card.from_dict(c, i) for i, c in enumerate(hand)]

        # 抽牌堆/弃牌堆（mod 可能不直接提供，留空由 SL 记忆系统补充）
        draw = _pick(snap, "draw_pile", "draw", default=[]) or []
        s.draw_pile = [Card.from_dict(c) for c in draw]
        disc = _pick(snap, "discard_pile", "discard", default=[]) or []
        s.discard_pile = [Card.from_dict(c) for c in disc]
        exh = _pick(snap, "exhaust_pile", "exhaust", default=[]) or []
        s.exhaust_pile = [Card.from_dict(c) for c in exh]

        # 敌人
        enemies = _pick(snap, "enemies", "monsters", default=[]) or []
        s.enemies = [Enemy.from_dict(e, i) for i, e in enumerate(enemies)]

        # 回合数
        s.turn = int(_pick(snap, "turn", "round", default=1) or 1)
        return s

    def alive_enemies(self) -> list[Enemy]:
        return [e for e in self.enemies if e.alive()]
