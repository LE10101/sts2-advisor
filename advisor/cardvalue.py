"""卡牌价值评分：基于当前卡组与流派，为"奖励选卡 / 商店购买"给出推荐分。

评分维度：
1. 卡牌基础强度（参考静默猎手强度榜，0-10）
2. 流派协同：卡组若已走毒/小刀/弃牌/敏捷，则同流派牌加分
3. 费用曲线：3 费以上与高费偏多时降分，缺低费引擎时补 0-1 费牌加分
4. 稀有度加成

返回 (分数, 理由列表)，便于在 CLI 里展示"为什么推荐这张"。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# 静默猎手主流牌基础强度（0-10，参考社区强度榜与实战常识）
BASE_VALUE: Dict[str, float] = {
    # S级：弃牌引擎 / 最强单卡
    "幽灵形态": 9.0, "杂技": 8.5, "算计": 8.0, "反射": 8.0, "战术家": 8.5,
    "早有准备": 8.0, "精准打击": 8.0, "肾上腺素": 8.0,
    # A级
    "毒雾": 8.0, "后空翻": 7.5, "步法": 7.5, "尖啸": 7.5, "催化": 7.5,
    "弹跳药瓶": 7.0, "扫腿": 7.0, "大结局": 7.0, "致命毒药": 7.0, "蛇咬": 7.0,
    # B级
    "刀刃之舞": 6.5, "斗篷与匕首": 6.5, "精准": 6.5, "冲刺": 6.5,
    "逃脱计划": 6.5, "暗杀": 6.0, "无尽刀刃": 6.0, "匕首喷射": 6.0,
    "飞刀": 6.0, "终结技": 6.0, "模糊": 6.0, "隐秘匕首": 6.0,
    # C/D级
    "生存者": 5.5, "切": 5.0, "中和": 5.0, "投掷匕首": 5.0, "突袭": 5.0,
    "弹射": 4.5, "串刺": 4.5, "偷袭": 4.5, "防御": 4.0, "打击": 3.5,
    "诅咒": 0.5, "伤痛": 0.5, "寄生": 0.5,
}

# 流派：卡牌名 -> 所属流派
POISON = {"致命毒药", "弹跳药瓶", "催化", "蛇咬", "迷雾", "毒雾", "淬毒", "腐蚀波", "爆发", "淬毒之刃", "毒刺", "加速器"}
SHIV = {"刀刃之舞", "斗篷与匕首", "无尽刀刃", "精准", "刀刃之扇", "幻影之刃", "隐秘匕首"}
DISCARD = {"杂技", "早有准备", "算计", "反射", "战术家", "投掷匕首", "隐秘匕首", "突袭", "生存者"}
DEX = {"步法", "后空翻", "逃脱计划", "模糊", "冲刺"}

ARCHETYPES = {"毒": POISON, "小刀": SHIV, "弃牌": DISCARD, "敏捷": DEX}

RARITY = {"普通": 0.0, "罕见": 0.5, "稀有": 1.0, "基础": 0.0}


def _archetype_of(card_name: str) -> List[str]:
    out = []
    for name, group in ARCHETYPES.items():
        if card_name in group:
            out.append(name)
    return out


def score_card(card_name: str, deck: Optional[List[str]] = None,
               rarity: str = "普通") -> Tuple[float, List[str]]:
    """评估一张牌的相对价值（分数越高越值得拿）。"""
    deck = deck or []
    reasons: List[str] = []
    score = BASE_VALUE.get(card_name, 4.5)  # 未收录的牌给中性分

    if card_name not in BASE_VALUE:
        reasons.append("未收录强度表，按中性分")

    # 流派协同
    archetypes = _archetype_of(card_name)
    deck_counts = {a: sum(1 for c in deck if c in group) for a, group in ARCHETYPES.items()}
    for a in archetypes:
        cnt = deck_counts[a]
        bonus = min(1.5, 0.5 * cnt + 0.5)  # 已有该流派牌越多，协同加分越多
        score += bonus
        reasons.append(f"协同[{a}+{bonus:.1f}]（已有{a}系{cnt}张）")

    # 费用曲线：高费牌若卡组高费已多则降分
    cost = COST.get(card_name)
    if cost is not None and cost >= 3:
        high_fee = sum(1 for c in deck if COST.get(c, 1) >= 3)
        if high_fee >= 3:
            score -= 0.8
            reasons.append("高费已多(-0.8)")
    # 0 费引擎补充
    if cost == 0 and deck_counts["弃牌"] >= 2:
        score += 0.5
        reasons.append("补齐0费引擎(+0.5)")

    # 稀有度
    r_bonus = RARITY.get(rarity, 0.0)
    if r_bonus:
        score += r_bonus
        reasons.append(f"稀有度+{r_bonus}")

    score = max(0.0, min(10.0, score))
    return score, reasons


def score_cards(cards: List[dict], deck: Optional[List[str]] = None) -> List[dict]:
    """批量评分。cards 为 [{name, rarity?}, ...]。返回带 score 的列表（升序追加理由）。"""
    out = []
    for c in cards:
        nm = c.get("name", "?")
        s, reasons = score_card(nm, deck, c.get("rarity", "普通"))
        out.append({**c, "score": s, "reasons": reasons})
    out.sort(key=lambda x: -x["score"])
    return out


# 费用表（用于费用曲线；未收录给 None）
COST: Dict[str, int] = {
    "打击": 1, "防御": 1, "中和": 0, "生存者": 1, "切": 0,
    "淬毒之刃": 1, "毒刺": 1, "致命毒药": 1, "弹跳药瓶": 2, "催化": 1,
    "蛇咬": 2, "迷雾": 3, "毒雾": 1, "淬毒": 2, "腐蚀波": 1, "爆发": 1,
    "刀刃之舞": 1, "斗篷与匕首": 1, "无尽刀刃": 1, "精准": 1,
    "刀刃之扇": 2, "幻影之刃": 1, "隐秘匕首": 0,
    "杂技": 1, "后空翻": 1, "早有准备": 0, "算计": 0, "反射": 0,
    "战术家": 1, "投掷匕首": 1, "突袭": 1, "偷袭": 1, "扫腿": 2,
    "暗杀": 0, "精准打击": 3, "串刺": 0, "终结技": 1, "飞刀": 1,
    "步法": 1, "冲刺": 2, "模糊": 1, "幽灵形态": 3, "尖啸": 1,
    "逃脱计划": 0, "肾上腺素": 0, "大结局": 0, "弹射": 2,
}
