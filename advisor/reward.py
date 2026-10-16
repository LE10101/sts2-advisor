"""奖励选卡决策：三选一 / 药水 / 金币 / 跳过。适配 STS2 AI Agent 真实 state。"""
from __future__ import annotations
from typing import Optional
from .model import Card
from .cardvalue import score_cards


# 药水价值评分（静默猎手视角）
POTION_SCORES = {
    "毒药水": 8.0,
    "精炼混沌": 6.0,
    "火焰药水": 5.0,
    "敏捷药水": 7.0,
    "力量药水": 5.0,
    "再生药水": 4.0,
    "血瓶": 3.0,
    "能量药水": 7.0,
    "烟雾弹": 6.0,
    "飞刀": 5.0,
    "万能药": 5.0,
    "液体记忆": 4.0,
    "幸运药水": 3.0,
    "闪电药水": 5.0,
    "恐惧药水": 4.0,
    "虚弱药水": 5.0,
    "易伤药水": 5.0,
}


def _potion_score(name: str) -> float:
    """药水评分，未知药水给默认分。"""
    for key, val in POTION_SCORES.items():
        if key in name:
            return val
    return 4.0  # 默认


def choose_reward(snap: dict, deck: Optional[list[Card]] = None) -> dict:
    """返回 {action, card, score, reason, alternatives, potions}。

    适配真实 state:
      card_options: 卡牌选项列表
      rewards: 奖励列表 [{reward_type, description, claimable, index}]
      pending_card_choice: 是否有待选卡牌
    """
    # 解析卡牌选项
    cards_raw = snap.get("card_options") or snap.get("reward_cards") or snap.get("cards", [])
    cards = []
    for c in cards_raw:
        if isinstance(c, dict):
            try:
                cards.append(Card.from_dict(c))
            except Exception:
                cards.append(Card(c.get("name", "未知"), c.get("energy_cost", 1)))
        else:
            cards.append(c)

    # 解析奖励列表（药水、金币、遗物等）
    rewards_raw = snap.get("rewards", []) or []
    potions = []
    gold = 0
    relic = None
    for r in rewards_raw:
        if not isinstance(r, dict):
            continue
        rtype = r.get("reward_type", "")
        desc = r.get("description", "")
        if rtype == "Potion" or "药水" in desc or "potion" in rtype.lower():
            potions.append({"index": r.get("index", 0), "name": desc})
        elif rtype == "Gold" or "金币" in desc or "gold" in rtype.lower():
            # 尝试从描述中提取数字
            import re
            m = re.search(r'\d+', desc)
            gold = int(m.group()) if m else 0
        elif rtype == "Relic" or "遗物" in desc or "relic" in rtype.lower():
            relic = desc

    pending = snap.get("pending_card_choice", False)

    # 情况1：有待选卡牌
    if cards and pending:
        scored = score_cards(cards, deck)
        best_card, best_score = scored[0]
        if best_score < 3.0:
            return {
                "action": "skip_cards",
                "reason": f"无值得拿的卡(最高{best_score:.1f})，跳过选卡",
                "alternatives": [(c.name, s) for c, s in scored],
            }
        return {
            "action": "card",
            "card": best_card,
            "score": best_score,
            "reason": f"推荐选「{best_card.name}」分{best_score:.1f}",
            "alternatives": [(c.name, s) for c, s in scored[1:]],
        }

    # 情况2：有卡牌但不是待选状态（可能已经选完，或者是展示）
    if cards and not pending:
        scored = score_cards(cards, deck)
        best_card, best_score = scored[0]
        return {
            "action": "card",
            "card": best_card,
            "score": best_score,
            "reason": f"可选「{best_card.name}」分{best_score:.1f}（如已选完请继续）",
            "alternatives": [(c.name, s) for c, s in scored[1:]],
        }

    # 情况3：有药水奖励
    if potions:
        scored_potions = sorted(potions, key=lambda p: _potion_score(p["name"]), reverse=True)
        best_potion = scored_potions[0]
        best_p_score = _potion_score(best_potion["name"])
        return {
            "action": "potion",
            "potion": best_potion,
            "score": best_p_score,
            "reason": f"推荐拿药水「{best_potion['name']}」(价值{best_p_score:.1f})",
            "potions": [(p["name"], _potion_score(p["name"])) for p in scored_potions],
        }

    # 情况4：有金币
    if gold > 0:
        return {"action": "gold", "reason": f"拿金币 {gold}"}

    # 情况5：有遗物
    if relic:
        return {"action": "relic", "reason": f"拿遗物 {relic}"}

    # 情况6：什么都没有
    if snap.get("can_proceed"):
        return {"action": "proceed", "reason": "奖励已拿完，继续前进"}
    return {"action": "skip", "reason": "无奖励可拿"}


def format_reward_result(res: dict) -> str:
    lines = ["== 奖励推荐 =="]
    if res["action"] == "card":
        lines.append(f"  ★ 选卡: {res['card'].name}  (评分 {res['score']:.1f})")
        lines.append(f"  理由: {res['reason']}")
        if res.get("alternatives"):
            lines.append("  备选: " + ", ".join(f"{n}({s:.1f})" for n, s in res["alternatives"]))
    elif res["action"] == "potion":
        lines.append(f"  ★ 药水: {res['potion']['name']}  (价值 {res['score']:.1f})")
        lines.append(f"  理由: {res['reason']}")
        if res.get("potions"):
            lines.append("  全部: " + ", ".join(f"{n}({s:.1f})" for n, s in res["potions"]))
    elif res["action"] == "skip_cards":
        lines.append(f"  ★ 跳过选卡: {res['reason']}")
        if res.get("alternatives"):
            lines.append("  候选: " + ", ".join(f"{n}({s:.1f})" for n, s in res["alternatives"]))
    else:
        lines.append(f"  ★ {res['action']}: {res['reason']}")
    return "\n".join(lines)
