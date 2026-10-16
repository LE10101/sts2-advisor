"""奖励选卡决策器：战斗胜利后的三选一 / 金币 / 跳过，给出推荐。

用 cardvalue 的流派感知评分，结合当前卡组给出"选哪张/是否拿金币"的建议，
并给出评分理由。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .cardvalue import score_card


def _pick(d: Optional[Dict], *keys, default=None):
    if not d:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def choose_reward(snap: Dict[str, Any], deck: Optional[List[str]] = None) -> Dict[str, Any]:
    """读取 reward 快照，返回推荐选择。"""
    r = snap.get("reward", snap) or {}
    deck = deck or []

    cards_raw = _pick(r, "cards", "card_rewards", "cards_options", "choices", default=[]) or []
    cards = []
    for c in cards_raw:
        if isinstance(c, str):
            cards.append({"name": c})
        elif isinstance(c, dict):
            cards.append({"name": _pick(c, "name", "card_name", default="?"),
                          "rarity": _pick(c, "rarity", default="普通")})

    gold = _pick(r, "gold", "gold_reward", default=0) or 0
    can_skip = _pick(r, "can_skip", "skip", default=True)

    scored = []
    for c in cards:
        s, reasons = score_card(c["name"], deck, c.get("rarity", "普通"))
        scored.append({**c, "score": s, "reasons": reasons})
    scored.sort(key=lambda x: -x["score"])

    best = scored[0] if scored else None
    recommendation = None
    reason_lines = []

    if best and best["score"] >= 4.0:
        recommendation = ("card", best["name"])
        reason_lines.append(f"推荐选「{best['name']}」分{best['score']:.1f}：")
        reason_lines += [f"  - {x}" for x in best.get("reasons", [])]
    elif gold > 0 and (best is None or best["score"] < 4.0):
        recommendation = ("gold", gold)
        reason_lines.append(f"卡牌价值偏低，推荐拿金币 {gold}（{best['name'] if best else ''} 分{best['score']:.1f}）")
    elif can_skip:
        recommendation = ("skip", None)
        reason_lines.append("卡牌价值均较低，建议跳过（保持卡组精简）")

    return {
        "phase": "reward",
        "recommendation": recommendation,  # (type, value)
        "cards": scored,
        "gold": gold,
        "reason": "\n".join(reason_lines) if reason_lines else "（无可推荐）",
    }


def format_reward_result(res: Dict[str, Any]) -> str:
    lines = ["== 奖励选择 =="]
    for c in res["cards"]:
        lines.append(f"   {c['name']:8s} 分{c['score']:.1f}  {'; '.join(c['reasons'][:2])}")
    if res["gold"]:
        lines.append(f"   金币 {res['gold']}")
    lines.append("   → " + res["reason"].replace("\n", "\n     "))
    return "\n".join(lines)
