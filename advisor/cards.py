"""卡牌效果库：把一张手牌解析成可供模拟器推演的离散效果。

设计原则：
- autoSpire 已直接给出伤害 / 格挡数值，这两项直接使用，不需查表。
- 额外效果（上毒、生成小刀、弃牌、抽牌、加敏捷/力量、叠易伤/虚弱、AOE、
  敌人降力量、回血、加能量等）无法从快照数值里拿到，需要从卡牌名 + 描述解析。
- 优先查 ``CARD_EFFECTS`` 精确表（卡名唯一，兼容别名），查不到再回退到
  描述关键词解析。目前覆盖静默猎手主流牌 + 少量通用牌，新牌只需在表里补一行。

静默猎手关键机制：
- 毒(Poison)  : 每回合开始结算，造成 = 毒层数伤害，然后层数 -1
- 小刀(Shiv)  : 0 费攻击，打出后消耗，可被"精准"等强化
- 弃牌        : 弃掉手牌，可触发弃牌收益（战术家回能、反射抽牌）与 Sly
- Sly         : 被弃时按原费用自动打出
- 敏捷        : 每点敏捷提供 +1 格挡
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Optional

from .model import Card

SHIV_BASE_DAMAGE = 4  # 小刀基础伤害


@dataclass
class CardEffects:
    """一次打出产生的效果集合（模拟器按此推进状态）。"""

    damage: int = 0          # 对单目标或 AOE 的伤害
    block: int = 0           # 玩家获得格挡
    draw: int = 0            # 抽牌数
    energy_gain: int = 0     # 额外获得能量
    self_buffs: Dict[str, int] = field(default_factory=dict)   # 玩家 buff / 能力
    enemy_debuffs: Dict[str, int] = field(default_factory=dict)  # 对目标的 debuff
    aoe: bool = False        # 是否对所有敌人生效
    heal: int = 0            # 回复生命
    exhaust: bool = False    # 是否消耗
    unknown: bool = False    # 是否未识别（用于标记启发式近似）
    # ---- 静默猎手专属 ----
    poison: int = 0              # 对目标施加毒层数
    poison_aoe: int = 0          # 对所有敌人施加毒
    shiv_count: int = 0          # 加入手牌的小刀数
    discard: int = 0             # 弃牌数（从手牌随机弃）
    sly: bool = False            # 该牌带 Sly：被弃时按原费自动打出
    weak_aoe: int = 0            # 对所有敌人施加虚弱
    vulnerable_aoe: int = 0      # 对所有敌人施加易伤
    enemy_strength_loss: int = 0  # 所有敌人本回合 -力量
    retain_block: bool = False   # 格挡不清零（模糊）


def make_shiv(hand_index: int = 0, damage: int = SHIV_BASE_DAMAGE) -> Card:
    """构造一张小刀卡：0 费攻击、打出后消耗。"""
    return Card(
        name="小刀",
        hand_index=hand_index,
        cost=0,
        damage=damage,
        description=f"造成 {damage} 点伤害。消耗。",
        card_type="attack",
        shiv=True,
        exhaust=True,
    )


# 精确表：卡牌名 -> 效果覆盖。值为 dict，字段名与 CardEffects 对齐。
# damage / block 数值由 autoSpire 快照提供，表里只补"额外效果"。
# 可同时给出多个别名（aliases 字段）。能力牌用 self_buffs 的能力键注册。
CARD_EFFECTS: Dict[str, Dict] = {
    # ---------------- 基础 / 初始 ----------------
    "打击": {},
    "防御": {},
    "中和": {"enemy_debuffs": {"虚弱": 1}},                       # 3伤+1虚弱
    "生存者": {"discard": 1},                                    # 8格挡+弃1
    "切": {},
    # ---------------- 静默猎手 · 毒 ----------------
    "淬毒之刃": {"poison": 3},
    "毒刺": {"poison": 3},
    "致命毒药": {"poison": 5},
    "弹跳药瓶": {"poison": 9},                                   # 随机3次×3 ≈ 单目标9
    "催化": {"poison_x": 3},                                     # 毒翻倍（模拟器特殊处理）
    "蛇咬": {"poison": 7},
    "迷雾": {"poison_aoe": 4},
    "腐蚀波": {"poison_aoe_per_draw": 3},                        # 抽牌时全体上毒
    "加速器": {"poison_extra_tick": 1},                          # 毒额外结算一次
    # ---------------- 静默猎手 · 小刀 ----------------
    "刀刃之舞": {"shiv_count": 3},
    "斗篷与匕首": {"shiv_count": 1},
    "无尽刀刃": {"self_buffs": {"无尽刀刃": 1}},                 # 能力：回合开始+1小刀
    "精准": {"self_buffs": {"精准": 1}},                         # 能力：小刀+4伤
    "刀刃之扇": {"self_buffs": {"刀刃之扇": 1}, "shiv_count": 4},  # 能力+4小刀
    "幻影之刃": {"self_buffs": {"幻影之刃": 1}},                 # 能力：首刀+9
    "隐秘匕首": {"discard": 2, "shiv_count": 2},
    # ---------------- 静默猎手 · 弃牌 / Sly ----------------
    "杂技": {"draw": 3, "discard": 1},
    "后空翻": {"draw": 2},                                       # 5格挡抽2
    "早有准备": {"draw": 1, "discard": 1},
    "算计": {"discard_hand": True},                              # 弃手牌抽回
    "战术家": {"self_buffs": {"战术家": 1}},                     # 弃牌回1能量
    "反射": {"self_buffs": {"反射": 1}},                         # 弃牌抽2
    "投掷匕首": {"draw": 1, "discard": 1},
    "突袭": {},
    "偷袭": {"enemy_debuffs": {"虚弱": 1}},
    "扫腿": {"enemy_debuffs": {"虚弱": 2}},
    "暗杀": {"enemy_debuffs": {"易伤": 1}},
    "精准打击": {},                                             # 17伤（每技能降费，动态）
    "串刺": {"damage_x": True},                                # X次7伤
    "终结技": {"damage_per_attack": 6},                         # 每攻击+6
    "飞刀": {"damage_per_skill": 5},                            # 每技能+5
    # ---------------- 静默猎手 · 敏捷 / 防御 ----------------
    "步法": {"self_buffs": {"敏捷": 2}},                        # 能力：+2敏捷
    "冲刺": {},                                                 # 10格挡10伤
    "模糊": {"retain_block": True},
    "幽灵形态": {"self_buffs": {"无形": 3}, "exhaust": True},    # 能力：无形3回合
    "尖啸": {"enemy_strength_loss": 6},
    "逃脱计划": {"draw": 1},                                    # 抽1，若技能+3格挡
    "暴露": {"enemy_debuffs": {"易伤": 2}, "remove_enemy_block": True},
    "肾上腺素": {"energy_gain": 1, "draw": 2},
    # ---------------- 通用 / 其他 ----------------
    "重刃": {"self_buffs": {"力量": 1}},
    "旋风斩": {"aoe": True},
}


# 描述关键词 -> 效果。用于 CARD_EFFECTS 未覆盖的牌。
_KEYWORDS = [
    (r"抽\s*(\d+)\s*张牌", "draw"),
    (r"抽\s*(\d+)\s*张", "draw"),
    (r"获得\s*(\d+)\s*点力量", "self_buffs_力量"),
    (r"力量\s*\+\s*(\d+)", "self_buffs_力量"),
    (r"获得\s*(\d+)\s*点敏捷", "self_buffs_敏捷"),
    (r"敏捷\s*\+\s*(\d+)", "self_buffs_敏捷"),
    (r"获得\s*(\d+)\s*点能量", "energy_gain"),
    (r"附加\s*(\d+)\s*层易伤", "enemy_debuffs_易伤"),
    (r"易伤\s*(\d+)", "enemy_debuffs_易伤"),
    (r"附加\s*(\d+)\s*层虚弱", "enemy_debuffs_虚弱"),
    (r"虚弱\s*(\d+)", "enemy_debuffs_虚弱"),
    (r"施加\s*(\d+)\s*点中毒", "poison"),
    (r"上毒\s*(\d+)", "poison"),
    (r"回复\s*(\d+)\s*点生命", "heal"),
    (r"回复\s*(\d+)\s*点血", "heal"),
    (r"所有敌人", "aoe"),
    (r"全体敌人", "aoe"),
    (r"丢弃\s*(\d+)\s*张牌", "discard"),
    (r"弃\s*(\d+)\s*张", "discard"),
    (r"将\s*(\d+)\s*张小刀", "shiv_count"),
    (r"加入\s*(\d+)\s*张小刀", "shiv_count"),
    (r"造成\s*(\d+)\s*点伤害", "damage_from_desc"),
    (r"获得\s*(\d+)\s*点格挡", "block_from_desc"),
]


def effects_for_card(card: Card) -> CardEffects:
    """解析一张牌的效果（按卡牌原子字段缓存，效果解析是每步结算/剪枝的热点）。"""
    return _effects_cached(card.name, card.damage, card.block, card.cost,
                           card.description, card.card_type, card.shiv, card.sly, card.exhaust)


@lru_cache(maxsize=8192)
def _effects_cached(name, damage, block, cost, description, card_type, shiv, sly, exhaust) -> CardEffects:
    """实际解析实现（结果缓存；返回的 CardEffects 只读，调用方不得修改）。"""
    card = Card(name=name, hand_index=-1, cost=cost, damage=damage, block=block,
                description=description, card_type=card_type, shiv=shiv, sly=sly, exhaust=exhaust)
    ef = CardEffects(damage=card.damage, block=card.block)

    key = card.name.strip()
    rule = CARD_EFFECTS.get(key)
    if rule is None:
        for k, r in CARD_EFFECTS.items():
            if key in r.get("aliases", []):
                rule = r
                break
    if rule is not None:
        if rule.get("aoe"):
            ef.aoe = True
        ef.draw += rule.get("draw", 0)
        ef.energy_gain += rule.get("energy_gain", 0)
        ef.heal += rule.get("heal", 0)
        ef.poison += rule.get("poison", 0)
        ef.poison_aoe += rule.get("poison_aoe", 0)
        ef.shiv_count += rule.get("shiv_count", 0)
        ef.discard += rule.get("discard", 0)
        ef.weak_aoe += rule.get("weak_aoe", 0)
        ef.vulnerable_aoe += rule.get("vulnerable_aoe", 0)
        ef.enemy_strength_loss += rule.get("enemy_strength_loss", 0)
        ef.retain_block = ef.retain_block or rule.get("retain_block", False)
        ef.exhaust = ef.exhaust or rule.get("exhaust", False)
        for k, v in rule.get("self_buffs", {}).items():
            ef.self_buffs[k] = ef.self_buffs.get(k, 0) + v
        for k, v in rule.get("enemy_debuffs", {}).items():
            ef.enemy_debuffs[k] = ef.enemy_debuffs.get(k, 0) + v
        ef.unknown = bool(rule.get("damage_x") or rule.get("damage_per_attack")
                          or rule.get("damage_per_skill") or rule.get("discard_hand")
                          or rule.get("remove_enemy_block") or rule.get("poison_x")
                          or rule.get("poison_extra_tick") or rule.get("poison_aoe_per_draw"))
        return ef

    # 描述关键词回退
    desc = card.description or ""
    for pat, kind in _KEYWORDS:
        m = re.search(pat, desc)
        if not m:
            continue
        val = _parse_int(m.group(1) if m.groups() else m.group(0))
        if val is None:
            val = _parse_int(m.group(0))
        val = val or 0
        if kind == "draw":
            ef.draw += val
        elif kind == "energy_gain":
            ef.energy_gain += val
        elif kind == "heal":
            ef.heal += val
        elif kind == "aoe":
            ef.aoe = True
        elif kind == "poison":
            ef.poison += val
        elif kind == "discard":
            ef.discard += val
        elif kind == "shiv_count":
            ef.shiv_count += val
        elif kind == "self_buffs_力量":
            ef.self_buffs["力量"] = ef.self_buffs.get("力量", 0) + val
        elif kind == "self_buffs_敏捷":
            ef.self_buffs["敏捷"] = ef.self_buffs.get("敏捷", 0) + val
        elif kind == "enemy_debuffs_易伤":
            ef.enemy_debuffs["易伤"] = ef.enemy_debuffs.get("易伤", 0) + val
        elif kind == "enemy_debuffs_虚弱":
            ef.enemy_debuffs["虚弱"] = ef.enemy_debuffs.get("虚弱", 0) + val
        elif kind == "damage_from_desc":
            ef.damage = ef.damage or val
        elif kind == "block_from_desc":
            ef.block = ef.block or val
    return ef


def _parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None
