"""商店购买决策器：读取 shop 快照，在金币预算内给出性价比推荐。

- 卡牌：用 cardvalue 流派感知评分；性价比 = 评分 / 价格
- 遗物：给基础价值分（核心遗物高、普通低）
- 删牌：若卡组有基础牌/诅咒，删牌性价比高
- 预算约束：按性价比从高到低贪心选取，不超当前金币

对 autoSpire 的 shop 快照做容错解析；无游戏时用内置示例演示。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .cardvalue import score_card

# 遗物基础价值（0-10）。未收录给中性 5。
_RELIC_VALUE = {
    "蛇之戒指": 7.0, "忍者遗物": 6.5, "毒瓶": 6.0, "刀锋": 5.5,
    "香炉": 5.0, "古钱币": 5.0,
}


def _pick(d: Optional[Dict], *keys, default=None):
    if not d:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def choose_shop(snap: Dict[str, Any], deck: Optional[List[str]] = None,
                gold: Optional[int] = None) -> Dict[str, Any]:
    """读取 shop 快照，返回推荐购买列表。"""
    s = snap.get("shop", snap) or {}
    deck = deck or []
    # 金币优先显式传入，否则从 shop / run 快照读取
    if gold is None:
        gold = _pick(s, "gold", default=None)
        if gold is None:
            gold = _pick(snap.get("run", {}) or {}, "gold", default=0)
        gold = gold or 0

    items_raw = _pick(s, "items", "goods", "shop_items", default=[]) or []
    items = []
    for it in items_raw:
        if isinstance(it, dict):
            items.append(it)
        elif isinstance(it, str):
            items.append({"type": "card", "name": it})

    # 解析商品
    cards, relics, potions, removal = [], [], [], []
    for it in items:
        t = str(_pick(it, "type", "kind", default="")).lower()
        name = _pick(it, "name", "card_name", default="?")
        price = _pick(it, "price", "cost", default=0) or 0
        if "relic" in t or "遗物" in name or _pick(it, "relic", default=False):
            relics.append({"name": name, "price": price})
        elif "potion" in t or "药水" in name:
            potions.append({"name": name, "price": price})
        elif "remove" in t or "删" in name:
            removal.append({"price": price})
        else:
            cards.append({"name": name, "price": price, "rarity": _pick(it, "rarity", default="普通")})

    # 卡牌性价比
    card_opts = []
    for c in cards:
        sc, reasons = score_card(c["name"], deck, c.get("rarity", "普通"))
        eff = sc / max(price, 1) if c["price"] > 0 else (sc + 3)
        card_opts.append({**c, "score": sc, "efficiency": eff, "reasons": reasons})

    relic_opts = [{"name": r["name"], "price": r["price"],
                   "score": _RELIC_VALUE.get(r["name"], 5.0)} for r in relics]
    potion_opts = [{"name": p["name"], "price": p["price"], "score": 5.0} for p in potions]

    # 删牌：有基础牌/诅咒时性价比高
    has_basic = any(c in ("打击", "防御", "伤痛", "诅咒") for c in deck)
    remove_opt = None
    if removal:
        rp = removal[0]["price"]
        remove_opt = {"price": rp, "score": 6.0 if has_basic else 4.0,
                      "efficiency": (6.0 if has_basic else 4.0) / max(rp, 1)}

    # 预算贪心：合并所有可买项，按性价比排序
    buy_pool = []
    for c in card_opts:
        buy_pool.append(("card", c))
    for r in relic_opts:
        buy_pool.append(("relic", r))
    if remove_opt and remove_opt["score"] >= 4.0:
        buy_pool.append(("remove", remove_opt))

    buy_pool.sort(key=lambda x: -(x[1].get("efficiency", x[1]["score"] / max(x[1]["price"], 1))))

    # 从最划算的开始买，直到预算不足
    recommendations = []
    spent = 0
    for kind, opt in buy_pool:
        if opt["price"] <= 0:
            continue
        if spent + opt["price"] > gold:
            continue
        recommendations.append({"kind": kind, "name": opt.get("name"), "price": opt["price"],
                                "score": opt["score"]})
        spent += opt["price"]
        if len(recommendations) >= 4:
            break

    return {
        "phase": "shop",
        "gold": gold,
        "recommendations": recommendations,
        "spent": spent,
        "cards": card_opts,
        "relics": relic_opts,
        "remove": remove_opt,
    }


def format_shop_result(res: Dict[str, Any]) -> str:
    lines = [f"== 商店（金币 {res['gold']}） =="]
    if res["cards"]:
        lines.append("  卡牌：")
        for c in res["cards"]:
            lines.append(f"    {c['name']:8s} 价{c['price']} 分{c['score']:.1f} 效率{c['efficiency']:.2f}")
    if res["relics"]:
        lines.append("  遗物：")
        for r in res["relics"]:
            lines.append(f"    {r['name']:8s} 价{r['price']} 分{r['score']:.1f}")
    if res["remove"]:
        lines.append(f"  删牌：价{res['remove']['price']} 分{res['remove']['score']:.1f}")
    if res["recommendations"]:
        lines.append("  推荐购买：")
        for rec in res["recommendations"]:
            lines.append(f"    - {rec['kind']} {rec.get('name','')}（{rec['price']}金）")
        lines.append(f"  合计 {res['spent']} 金，剩 {res['gold']-res['spent']} 金")
    else:
        lines.append("  （预算内无可推荐的购买项）")
    return "\n".join(lines)
