"""静默猎手卡牌效果库：精确表 + 描述关键词回退。"""
from __future__ import annotations
from typing import Optional
from .model import Card

SHIV_BASE_DAMAGE = 4

# 精确效果表：name -> dict(attack, block, poison, draw, energy, weak, vulnerable,
#                             shiv, discard, sly, exhaust, innate, ethereal)
CARD_EFFECTS: dict[str, dict] = {
    # ===== 攻击牌 =====
    "中和": dict(attack=3, weak=1, cost=1),
    "中和+": dict(attack=5, weak=1, cost=1),
    "致命毒药": dict(attack=0, poison=3, cost=1),
    "致命毒药+": dict(attack=0, poison=4, cost=1),
    "毒雾": dict(attack=0, poison=2, aoe_poison=True, cost=1, power=True),
    "毒雾+": dict(attack=0, poison=3, aoe_poison=True, cost=1, power=True),
    "无尽刀刃": dict(attack=0, shiv_per_turn=1, cost=1, power=True),
    "无尽刀刃+": dict(attack=0, shiv_per_turn=2, cost=1, power=True),
    "杂技": dict(attack=0, draw=2, discard=1, cost=1),
    "杂技+": dict(attack=0, draw=3, discard=1, cost=1),
    "背刺": dict(attack=6, cost=0, innate=True),
    "背刺+": dict(attack=9, cost=0, innate=True),
    "蛇咬": dict(attack=0, poison=7, cost=2, retain=True),
    "蛇咬+": dict(attack=0, poison=9, cost=2, retain=True),
    # ===== STS2 静默猎手卡牌（根据真实游戏数据修正） =====
    "暴露": dict(attack=0, vulnerable=2, remove_block=True, cost=0, exhaust=True),
    "暴露+": dict(attack=0, vulnerable=3, remove_block=True, cost=0, exhaust=True),
    "啄击": dict(attack=2, hits=3, cost=1),
    "啄击+": dict(attack=3, hits=3, cost=1),
    "终结技": dict(attack=0, finisher=True, finisher_damage=6, cost=1),
    "终结技+": dict(attack=0, finisher=True, finisher_damage=8, cost=1),
    "袖里乾坤": dict(attack=0, add_shiv=3, cost=2),
    "袖里乾坤+": dict(attack=0, add_shiv=4, cost=1),
    "猛扑": dict(attack=14, next_skill_free=True, cost=2),
    "猛扑+": dict(attack=18, next_skill_free=True, cost=2),
    "逃脱计划": dict(attack=0, draw=1, cost=0, sly=True),
    "逃脱计划+": dict(attack=0, draw=2, cost=0, sly=True),
    "早有准备": dict(attack=0, draw=1, discard=1, cost=0),
    "早有准备+": dict(attack=0, draw=2, discard=1, cost=0),
    "余像": dict(attack=0, block=4, cost=1, retain=True),
    "余像+": dict(attack=0, block=6, cost=1, retain=True),
    "咕嘟冒泡": dict(attack=0, poison=9, conditional_poison=True, cost=1),
    "咕嘟冒泡+": dict(attack=0, poison=12, conditional_poison=True, cost=1),
    "生存者": dict(block=8, discard=1, cost=1),
    "生存者+": dict(block=11, discard=1, cost=1),
    "后空翻": dict(block=5, draw=2, cost=1),
    "后空翻+": dict(block=8, draw=2, cost=1),
    "侧步": dict(energy_next_turn=1, cost=0),
    "侧步+": dict(energy_next_turn=2, cost=0),
    "偏折": dict(block=5, cost=0),
    "偏折+": dict(block=7, cost=0),
    "余像": dict(cost=1, power=True, block_per_card=1),
    "余像+": dict(cost=1, power=True, block_per_card=1),
    "灵动步法": dict(dexterity=2, cost=1, power=True),
    "灵动步法+": dict(dexterity=3, cost=1, power=True),
    "蜃景": dict(block_from_poison=True, cost=1),
    "蜃景+": dict(block_from_poison=True, cost=1),
    "墨之刃": dict(add_shiv=2, cost=1),
    "墨之刃+": dict(add_shiv=3, cost=1),
    "尖啸": dict(strength_loss=6, exhaust=True, cost=1),
    "尖啸+": dict(strength_loss=9, exhaust=True, cost=1),
    "扫腿": dict(weak=2, block=11, cost=2),
    "扫腿+": dict(weak=2, block=15, cost=2),
    "毒性爆发": dict(aoe_poison=True, poison=9, trigger_poison=True, cost=3),
    "毒性爆发+": dict(aoe_poison=True, poison=12, trigger_poison=True, cost=3),
    "闪躲翻滚": dict(block=4, block_next_turn=4, cost=1),
    "闪躲翻滚+": dict(block=6, block_next_turn=6, cost=1),
    "非凡技艺": dict(strength=1, dexterity=1, cost=1, power=True),
    "非凡技艺+": dict(strength=2, dexterity=2, cost=1, power=True),
    "匕首投掷": dict(attack=4, draw=1, cost=1),
    "匕首投掷+": dict(attack=6, draw=1, cost=1),
    "防御": dict(block=5, cost=1),
    "防御+": dict(block=8, cost=1),
    "打击": dict(attack=6, cost=1),
    "打击+": dict(attack=9, cost=1),
    "飞刀": dict(attack=4, shiv=1, cost=1),
    "飞刀+": dict(attack=6, shiv=1, cost=1),
    "刀锋之舞": dict(attack=0, shiv=2, cost=1),
    "刀锋之舞+": dict(attack=0, shiv=3, cost=1),
    "弹射之刃": dict(attack=4, random_hits=3, cost=1),
    "弹射之刃+": dict(attack=5, random_hits=3, cost=1),
    "肾上腺素": dict(energy=2, draw=1, cost=0),
    "肾上腺素+": dict(energy=2, draw=2, cost=0),
    "计划妥当": dict(block=8, draw=1, cost=1),
    "计划妥当+": dict(block=11, draw=1, cost=1),
    "精准": dict(dexterity=2, cost=1, power=True),
    "精准+": dict(dexterity=3, cost=1, power=True),
    "淬毒": dict(attack=0, poison=1, cost=0, innate=True),
    "淬毒+": dict(attack=0, poison=2, cost=0, innate=True),
    "斗篷与匕首": dict(block=6, shiv=1, cost=1),
    "斗篷与匕首+": dict(block=9, shiv=1, cost=1),
    "飞膝踢": dict(attack=8, draw=1, cost=1),
    "飞膝踢+": dict(attack=10, draw=1, cost=1),
    "愤怒": dict(attack=6, vulnerable=1, cost=1),
    "愤怒+": dict(attack=9, vulnerable=1, cost=1),
    "秘法宝典": dict(draw=2, cost=0),
    "秘法宝典+": dict(draw=3, cost=0),
    "冲刺": dict(block=6, draw=1, cost=0),
    "冲刺+": dict(block=8, draw=1, cost=0),
    "残影": dict(block=4, cost=0, ethereal=True),
    "残影+": dict(block=6, cost=0, ethereal=True),
    "战术家": dict(attack=0, energy=1, cost=0, sly=True),
    "战术家+": dict(attack=0, energy=2, cost=0, sly=True),
    "反射": dict(attack=0, draw=2, cost=0, sly=True),
    "反射+": dict(attack=0, draw=3, cost=0, sly=True),
    "逃脱计划": dict(block=4, draw=1, cost=0),
    "逃脱计划+": dict(block=6, draw=1, cost=0),
    "致命倒计时": dict(attack=0, poison=5, cost=2),
    "致命倒计时+": dict(attack=0, poison=7, cost=2),
    "催化剂": dict(poison_multiply=2, cost=1),
    "催化剂+": dict(poison_multiply=3, cost=1),
    "弹弹乐": dict(attack=3, random_hits=4, cost=1),
    "弹弹乐+": dict(attack=4, random_hits=4, cost=1),
    "连环腿": dict(attack=5, weak=1, cost=1),
    "连环腿+": dict(attack=7, weak=1, cost=1),
    "得意": dict(attack=0, draw=1, energy=1, cost=0),
    "得意+": dict(attack=0, draw=2, energy=1, cost=0),
    # ===== 能力牌 =====
    "无形": dict(cost=3, power=True, intangible=True),
    "无形+": dict(cost=2, power=True, intangible=True),
    "模糊": dict(block_per_turn=5, cost=1, power=True),
    "模糊+": dict(block_per_turn=8, cost=1, power=True),
    "黑暗之拥": dict(cost=2, power=True, on_exhaust_draw=1),
    "黑暗之拥+": dict(cost=1, power=True, on_exhaust_draw=1),
    "尸爆术": dict(cost=2, enemy_kill_explode=True),
    "尸爆术+": dict(cost=1, enemy_kill_explode=True),
    "tools of the trade": dict(cost=1, power=True, draw_per_turn=1, discard_per_turn=1),
}

# 英文名映射（autoSpire 可能返回英文名）
_EN_TO_ZH = {
    "Neutralize": "中和", "Deadly Poison": "致命毒药", "Noxious Fumes": "毒雾",
    "Infinite Blades": "无尽刀刃", "Acrobatics": "杂技", "Backstab": "背刺",
    "Dagger Throw": "匕首投掷", "Defend": "防御", "Strike": "打击",
    "Blade Dance": "刀锋之舞", "Flying Knee": "飞膝踢", "Sucker Punch": "愤怒",
    "Outmaneuver": "秘法宝典", "Dash": "冲刺", "Blur": "模糊",
    "Tactician": "战术家", "Reflex": "反射", "Escape Plan": "逃脱计划",
    "Deadly Countdown": "致命倒计时", "Catalyst": "催化剂",
    "Well-Laid Plans": "计划妥当", "Footwork": "精准", "Envenom": "淬毒",
    "Cloak And Dagger": "斗篷与匕首", "Adrenaline": "肾上腺素",
    "Wraith Form": "无形", "Dark Embrace": "黑暗之拥", "Corpse Explosion": "尸爆术",
    "Bouncing Flask": "弹弹乐", "Riddle with Holes": "连环腿", "Bravado": "得意",
    "Survivor": "残影", "Shiv": "小刀",
}

_effect_cache: dict[str, dict] = {}

# dynamic_values 名称 → 效果字段的映射
_DYNAMIC_FIELD_MAP = {
    "damage": "attack",
    "block": "block",
    "poisonpower": "poison",
    "weakpower": "weak",
    "vulnerablepower": "vulnerable",
    "strengthpower": "strength",
    "dexteritypower": "dexterity",
    "drawpower": "draw",
    "cards": "draw",
    "energy": "energy",
    "repeat": "hits",
    "power": "vulnerable",  # 暴露牌的 Power 字段是易伤层数
}


def _dynamic_values_signature(dv_list: list) -> str:
    """生成 dynamic_values 的短哈希，用于缓存 key。"""
    if not dv_list:
        return ""
    parts = []
    for dv in dv_list:
        if isinstance(dv, dict):
            parts.append(f"{dv.get('name','')}:{dv.get('current_value','')}")
    return "|".join(parts)


def _apply_dynamic_values(eff: dict, card: Card) -> dict:
    """用 mod 提供的 dynamic_values 覆盖基础效果（已包含状态修正的实际数值）。"""
    if not card.dynamic_values:
        return eff
    for dv in card.dynamic_values:
        if not isinstance(dv, dict):
            continue
        name = str(dv.get("name", "")).lower()
        field = _DYNAMIC_FIELD_MAP.get(name)
        if field is None:
            continue
        try:
            val = int(dv.get("current_value", dv.get("base_value")))
            eff[field] = val
        except (ValueError, TypeError):
            continue
    return eff


def _normalize_name(name: str) -> str:
    n = name.strip()
    return _EN_TO_ZH.get(n, n)


def effects_for_card(card: Card) -> dict:
    """获取卡牌效果，带缓存。优先使用 mod 提供的 dynamic_values（已修正状态）。"""
    dyn_sig = _dynamic_values_signature(card.dynamic_values)
    key = card.fingerprint()
    if dyn_sig:
        key = f"{key}|{dyn_sig}"
    if key in _effect_cache:
        return _effect_cache[key]

    name = _normalize_name(card.name)
    up_name = name + "+" if card.upgraded else name
    eff = CARD_EFFECTS.get(up_name) or CARD_EFFECTS.get(name)
    if eff is None:
        eff = _fallback_effects(card)
    eff = dict(eff)
    eff.setdefault("cost", card.cost if card.cost >= 0 else 1)

    # 关键优化：用 mod 提供的动态数值覆盖（包含脆弱/力量/敏捷修正）
    if card.dynamic_values:
        # mod 提供了准确数据，清除 fallback 的默认攻击/格挡（避免误导）
        if "attack" not in (CARD_EFFECTS.get(up_name) or CARD_EFFECTS.get(name) or {}):
            eff.pop("attack", None)
        if "block" not in (CARD_EFFECTS.get(up_name) or CARD_EFFECTS.get(name) or {}):
            eff.pop("block", None)
    eff = _apply_dynamic_values(eff, card)

    _effect_cache[key] = eff
    return eff


def _fallback_effects(card: Card) -> dict:
    """描述关键词回退：从 resolved_rules_text 解析效果，比默认值更准确。"""
    eff = {"cost": card.cost if card.cost >= 0 else 1}
    text = (getattr(card, "resolved_text", "") or "").lower()
    name = card.name.lower()

    # 从描述文本中解析数值效果
    import re
    # 抽牌：抽X张 / Draw X cards
    m = re.search(r"抽\s*(\d+)\s*张|draw\s*(\d+)\s*card", text)
    if m:
        eff["draw"] = int(m.group(1) or m.group(2))
    # 能量：获得X能量 / Gain X energy
    m = re.search(r"获得\s*(\d+)\s*[点能]|gain\s*(\d+)\s*energy", text)
    if m:
        eff["energy"] = int(m.group(1) or m.group(2))
    # 弃牌：弃X张 / Discard X cards
    m = re.search(r"弃\s*(\d+)\s*张|discard\s*(\d+)\s*card", text)
    if m:
        eff["discard"] = int(m.group(1) or m.group(2))
    # 虚弱：施加X层虚弱 / Apply X weak
    m = re.search(r"虚弱\s*(\d+)|apply\s*(\d+)\s*weak", text)
    if m:
        eff["weak"] = int(m.group(1) or m.group(2))
    # 易伤：施加X层易伤 / Apply X vulnerable
    m = re.search(r"易伤\s*(\d+)|apply\s*(\d+)\s*vulnerable", text)
    if m:
        eff["vulnerable"] = int(m.group(1) or m.group(2))
    # 小刀：生成X把小刀 / Create X shiv
    m = re.search(r"小刀\s*(\d+)|create\s*(\d+)\s*shiv", text)
    if m:
        eff["shiv"] = int(m.group(1) or m.group(2))

    # 关键词标记
    if "保留" in text or "retain" in text:
        eff["retain"] = True
    if "消耗" in text or "exhaust" in text:
        eff["exhaust"] = True
    if "固有" in text or "innate" in text:
        eff["innate"] = True
    if "虚无" in text or "ethereal" in text:
        eff["ethereal"] = True
    if "能力" in text or "power" in text:
        eff["power"] = True
    if "sly" in text or "被弃" in text:
        eff["sly"] = True

    # 如果描述文本没有解析出攻击/格挡/毒，用默认值（dynamic_values 会覆盖）
    if "attack" not in eff and "block" not in eff and "poison" not in eff:
        if "defend" in name or "防御" in card.name:
            eff["block"] = 5
        elif "strike" in name or "打击" in card.name:
            eff["attack"] = 6
        else:
            eff["attack"] = 4  # 默认当作小攻击
    return eff


def make_shiv() -> Card:
    c = Card("小刀", cost=0, card_type="attack", exhaust=True)
    return c
