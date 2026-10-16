"""战斗状态与动作的数据结构。

autoSpire 返回的 JSON 字段名在不同版本可能有出入，因此这里统一提供
``from_snapshot`` 做"容错解析"：对每个字段尝试多个候选键名，缺省给合理默认值，
保证离线 demo 与真实对接都能工作。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 小工具：宽松取键
# ---------------------------------------------------------------------------
def _pick(d: Optional[Dict[str, Any]], *keys, default=None):
    """按顺序尝试多个键名，返回第一个命中；都没有则返回 default。"""
    if not d:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


# ---------------------------------------------------------------------------
# 卡牌
# ---------------------------------------------------------------------------
@dataclass
class Card:
    """手牌中的一张卡。hand_index 是 autoSpire 动作所需的索引。"""

    name: str
    hand_index: int
    cost: int = 1
    damage: int = 0
    block: int = 0
    description: str = ""
    card_type: str = "attack"  # attack / skill / power
    shiv: bool = False   # 小刀：0费攻击，打出自消耗
    sly: bool = False    # Sly：被弃时按原费用自动打出
    exhaust: bool = False  # 打出后消耗

    @classmethod
    def from_dict(cls, d: Dict[str, Any], fallback_index: int) -> "Card":
        name = _pick(d, "name", "card_name", "title", default="?")
        desc = _pick(d, "description", "desc", default="")
        # 卡牌类型推断：仅根据名字/描述启发式，真实场景可从 autoSpire 字段读取
        ctype = _pick(d, "type", "card_type", "rarity", default="")
        if ctype not in ("attack", "skill", "power"):
            name_l = name.lower() + " " + desc
            if "power" in name_l or "能力" in name:
                ctype = "power"
            elif "skill" in name_l or "技能" in name:
                ctype = "skill"
            else:
                ctype = "attack"
        return cls(
            name=name,
            hand_index=_pick(d, "hand_index", "index", "idx", default=fallback_index),
            cost=_pick(d, "cost", "energy_cost", "energy", default=1),
            damage=_pick(d, "damage", default=0) or 0,
            block=_pick(d, "block", "block_value", default=0) or 0,
            description=desc,
            card_type=ctype,
        )

    def fingerprint(self) -> tuple:
        """卡牌身份指纹：用于 SL 牌序去重与手牌差异识别。"""
        return (self.name, self.damage, self.block, self.cost, self.card_type)

    def __repr__(self) -> str:  # 便于打印
        extra = f"{self.damage}伤害" if self.damage else ""
        if self.block:
            extra += f"{self.block}格挡"
        tag = "小刀" if self.shiv else ("Sly" if self.sly else "")
        if tag:
            extra += f"[{tag}]"
        return f"[{self.hand_index}]{self.name}({self.cost}费{extra})"


# ---------------------------------------------------------------------------
# 敌人
# ---------------------------------------------------------------------------
@dataclass
class Enemy:
    id: int
    name: str
    hp: int
    max_hp: int = 0
    block: int = 0
    intent: str = "unknown"  # attack / defend / buff / unknown ...
    intent_value: int = 0  # 意图数值（攻击伤害 / 格挡量）
    buffs: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Enemy":
        hp = _pick(d, "hp", "current_hp", "health", default=0) or 0
        return cls(
            id=_pick(d, "id", "entity_id", "combat_id", default=0) or 0,
            name=_pick(d, "name", "enemy_name", "title", default="敌人"),
            hp=hp,
            max_hp=_pick(d, "max_hp", "maxHealth", default=hp) or hp,
            block=_pick(d, "block", default=0) or 0,
            intent=_pick(d, "intent", "intent_name", "move", default="unknown"),
            intent_value=_pick(d, "intent_value", "intent_damage", "move_value", default=0) or 0,
            buffs=_pick(d, "buffs", "statuses", default={}) or {},
        )

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def __repr__(self) -> str:
        return f"[{self.id}]{self.name}(HP {self.hp})意图:{self.intent}{self.intent_value}"


# ---------------------------------------------------------------------------
# 战斗状态（模拟器与 MCTS 共同使用的核心状态）
# ---------------------------------------------------------------------------
@dataclass
class CombatState:
    player_hp: int
    max_hp: int
    energy: int
    hand: List[Card]
    enemies: List[Enemy]
    player_block: int = 0
    player_buffs: Dict[str, int] = field(default_factory=dict)
    potions: List[Dict[str, Any]] = field(default_factory=list)
    draw_pile: int = 0
    discard_pile: int = 0
    turn: int = 1
    seed: int = 0  # 供模拟器做确定性伪随机
    deck: List[str] = field(default_factory=list)  # 当前卡组牌名列表（用于价值评估）
    draw_pos: int = 0  # 本战斗累计抽牌数（配合 SL 牌序记忆，沿搜索路径各自累计）

    @classmethod
    def from_snapshot(cls, snap: Dict[str, Any]) -> "CombatState":
        """从 autoSpire 的 combat 子快照解析战斗状态。"""
        combat = snap.get("combat", snap)  # 兼容直接传子快照
        player = _pick(combat, "player", "self", default={}) or {}
        player_stats = _pick(player, "stats", "character", default=player)
        hp = _pick(player_stats, "hp", "current_hp", "health", default=0) or 0
        max_hp = _pick(player_stats, "max_hp", "maxHealth", default=hp) or hp

        hand_raw = _pick(combat, "hand", "hand_cards", "cards", default=[]) or []
        hand = [
            Card.from_dict(c, i)
            for i, c in enumerate(hand_raw)
        ]

        enemies_raw = _pick(combat, "enemies", "monsters", default=[]) or []
        enemies = [Enemy.from_dict(e) for e in enemies_raw]

        # 卡组：从 run.deck 提取牌名（合并计数）
        run = snap.get("run", {}) or {}
        deck_raw = _pick(run, "deck", "cards", "deck_cards", default=[]) or []
        deck = []
        for d in deck_raw:
            if isinstance(d, dict):
                nm = _pick(d, "name", "card_name", default="")
                cnt = _pick(d, "count", "copies", default=1) or 1
                deck += [nm] * max(0, int(cnt))
            else:
                deck.append(str(d))

        return cls(
            player_hp=hp,
            max_hp=max_hp or 80,
            energy=_pick(player_stats, "energy", "energy_now", "current_energy", default=3) or 0,
            hand=hand,
            enemies=enemies,
            player_block=_pick(player, "block", default=0) or 0,
            player_buffs=_pick(player, "buffs", "statuses", default={}) or {},
            potions=_pick(combat, "potions", default=[]) or [],
            draw_pile=_pick(combat, "draw_pile", "drawPileCount", "draw_count", default=0) or 0,
            discard_pile=_pick(combat, "discard_pile", "discardPileCount", default=0) or 0,
            turn=_pick(combat, "turn", "turn_number", default=1) or 1,
            seed=_pick(combat, "seed", default=0) or 0,
            deck=deck,
        )

    def copy(self) -> "CombatState":
        """深拷贝：手牌、敌人、buff 均复制为新对象，避免状态转换污染共享引用。"""
        return CombatState(
            player_hp=self.player_hp,
            max_hp=self.max_hp,
            energy=self.energy,
            hand=[Card(c.name, c.hand_index, c.cost, c.damage, c.block, c.description, c.card_type)
                  for c in self.hand],
            enemies=[Enemy(e.id, e.name, e.hp, e.max_hp, e.block, e.intent, e.intent_value,
                           dict(e.buffs)) for e in self.enemies],
            player_block=self.player_block,
            player_buffs=dict(self.player_buffs),
            potions=[dict(p) for p in self.potions],
            draw_pile=self.draw_pile,
            discard_pile=self.discard_pile,
            turn=self.turn,
            seed=self.seed,
            deck=list(self.deck),
            draw_pos=self.draw_pos,
        )

    def alive_enemies(self) -> List[Enemy]:
        return [e for e in self.enemies if e.alive]

    def any_enemy_alive(self) -> bool:
        return any(e.alive for e in self.enemies)

    def __repr__(self) -> str:
        return (f"Combat[turn{self.turn} 玩家HP{self.player_hp}/{self.max_hp} "
                f"能量{self.energy} 手牌{len(self.hand)}] "
                f"敌人:{self.alive_enemies()}")


# ---------------------------------------------------------------------------
# 动作
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Action:
    kind: str  # "play_card" / "end_turn" / "use_potion"
    hand_index: Optional[int] = None
    target_id: Optional[int] = None
    potion_slot: Optional[int] = None

    @classmethod
    def play(cls, hand_index: int, target_id: Optional[int] = None) -> "Action":
        return cls(kind="play_card", hand_index=hand_index, target_id=target_id)

    @classmethod
    def end_turn(cls) -> "Action":
        return cls(kind="end_turn")

    @classmethod
    def potion(cls, slot: int, target_id: Optional[int] = None) -> "Action":
        return cls(kind="use_potion", potion_slot=slot, target_id=target_id)

    def describe(self, state: CombatState) -> str:
        if self.kind == "end_turn":
            return "结束回合"
        if self.kind == "play_card":
            card = next((c for c in state.hand if c.hand_index == self.hand_index), None)
            name = card.name if card else f"卡{self.hand_index}"
            if self.target_id is not None:
                en = next((e for e in state.enemies if e.id == self.target_id), None)
                tgt = en.name if en else str(self.target_id)
                return f"打出[{name}] → {tgt}"
            return f"打出[{name}]"
        if self.kind == "use_potion":
            return f"使用药水槽{self.potion_slot}"
        return str(self)
