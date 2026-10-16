"""商店购买决策：预算内性价比贪心（卡牌/遗物/删牌/药水）。适配 STS2 AI Agent 真实 state。"""
from __future__ import annotations
from typing import Optional
from .model import Card
from .cardvalue import score_card


# 静默猎手视角遗物评分
RELIC_SCORES = {
    # 毒流派核心
    "蛇之戒指": 8.0, "ring_of_the_snake": 8.0,
    "水银沙漏": 7.5, "mercury_hourglass": 7.5,
    "风的女儿": 7.0, "daughter_of_the_wind": 7.0,
    "投斧": 6.5, "throwing_axe": 6.5,
    # 通用强力
    "金色珍珠": 6.0, "golden_pearl": 6.0,
    "草莓": 5.5, "strawberry": 5.5,
    "金纸": 5.0, "joss_paper": 5.0,
    "烫嘴可可": 6.0, "very_hot_cocoa": 6.0,
    "船夹板": 5.0, "horn_cleat": 5.0,
    "风箱": 5.5, "bellows": 5.5,
    "古茶具套装": 4.5, "fake_venerable_tea_set": 4.5,
    "小邮箱": 4.0, "tiny_mailbox": 4.0,
    "准备之袋": 5.0, "bag_of_preparation": 5.0,
    # STS1 经典遗物
    "kunai": 9.0, "shuriken": 8.5, "ornamental_fan": 8.0,
    "dead_branch": 7.5, "bag_of_marbles": 6.0,
    "snecko_eye": 7.0, "runic_pyramid": 7.5,
    "bullet_time": 6.5, "well_laid_plans": 7.0,
    "tough_bandages": 6.0, "evolve": 5.5,
    "footwork": 7.0, "after_image": 7.5,
    "burst": 6.0, "leg_sweep": 5.5,
}

# 药水评分
POTION_SCORES = {
    "毒药水": 8.0, "精炼混沌": 6.0, "火焰药水": 5.0,
    "敏捷药水": 7.0, "力量药水": 5.0, "再生药水": 4.0,
    "血瓶": 3.0, "能量药水": 7.0, "烟雾弹": 6.0,
    "飞刀": 5.0, "万能药": 5.0, "液体记忆": 4.0,
    "闪电药水": 5.0, "恐惧药水": 4.0, "虚弱药水": 5.0,
    "易伤药水": 5.0,
}


def _relic_score(name: str) -> float:
    """遗物评分，未知遗物给默认分。"""
    name_lower = name.lower()
    for key, val in RELIC_SCORES.items():
        if key.lower() in name_lower or name_lower in key.lower():
            return val
    return 4.5  # 默认


def _potion_score(name: str) -> float:
    for key, val in POTION_SCORES.items():
        if key in name:
            return val
    return 4.0


def choose_shop(snap: dict, deck: Optional[list[Card]] = None) -> dict:
    """返回 {purchases, total_cost, remaining_gold, reason}。

    适配真实 state（字段名容错）：
      shop_cards / cards / card_options / items
      shop_relics / relics / relic_options
      shop_potions / potions
      gold / current_gold
      remove_cost / card_removal_cost
    """
    # 金币
    gold = int(snap.get("gold", snap.get("current_gold",
                 snap.get("shop", {}).get("gold", 0))))

    # 卡牌（多种字段名容错）
    shop_cards = (snap.get("shop_cards") or snap.get("cards") or
                  snap.get("card_options") or snap.get("items") or [])
    # 遗物
    relics = (snap.get("shop_relics") or snap.get("relics") or
              snap.get("relic_options") or [])
    # 药水
    potions = (snap.get("shop_potions") or snap.get("potions") or
               snap.get("potion_options") or [])
    # 删牌价格
    remove_cost = int(snap.get("remove_cost",
                     snap.get("card_removal_cost", 75)))

    purchases = []
    remaining = gold

    # 1) 卡牌：按 评分/价格 性价比排序
    card_items = []
    for c in shop_cards:
        if isinstance(c, dict):
            try:
                card = Card.from_dict(c)
            except Exception:
                card = Card(c.get("name", "?"), c.get("energy_cost", 1))
            price = int(c.get("price", c.get("cost", 50)))
        else:
            card = c
            price = 50
        score = score_card(card, deck) if deck else score_card(card)
        ratio = score / max(1, price)
        card_items.append((card, price, score, ratio))
    card_items.sort(key=lambda x: x[3], reverse=True)

    for card, price, score, ratio in card_items:
        if remaining >= price and ratio > 0.06:
            purchases.append({"type": "card", "name": card.name,
                              "price": price, "score": score})
            remaining -= price

    # 2) 遗物：按评分/价格性价比
    relic_items = []
    for r in relics:
        if isinstance(r, dict):
            rname = r.get("name", r.get("relic_name", "?"))
            rprice = int(r.get("price", r.get("cost", 150)))
        else:
            rname, rprice = str(r), 150
        rscore = _relic_score(rname)
        ratio = rscore / max(1, rprice)
        relic_items.append((rname, rprice, rscore, ratio))
    relic_items.sort(key=lambda x: x[3], reverse=True)

    for rname, rprice, rscore, ratio in relic_items:
        if remaining >= rprice and ratio > 0.03:
            purchases.append({"type": "relic", "name": rname,
                              "price": rprice, "score": rscore})
            remaining -= rprice

    # 3) 药水
    potion_items = []
    for p in potions:
        if isinstance(p, dict):
            pname = p.get("name", p.get("description", "?"))
            pprice = int(p.get("price", p.get("cost", 50)))
        else:
            pname, pprice = str(p), 50
        pscore = _potion_score(pname)
        ratio = pscore / max(1, pprice)
        potion_items.append((pname, pprice, pscore, ratio))
    potion_items.sort(key=lambda x: x[3], reverse=True)

    for pname, pprice, pscore, ratio in potion_items:
        if remaining >= pprice and ratio > 0.08:
            purchases.append({"type": "potion", "name": pname,
                              "price": pprice, "score": pscore})
            remaining -= pprice

    # 4) 删牌：如果牌组有基础打击/防御且预算充足
    if deck and remaining >= remove_cost:
        basics = [c for c in deck if c.name in ("打击", "防御", "Strike", "Defend")]
        if basics:
            purchases.append({"type": "remove",
                              "name": f"删除{basics[0].name}",
                              "price": remove_cost, "score": 5.0})
            remaining -= remove_cost

    reason_parts = [f"{p['type']}:{p['name']}({p['price']}金)"
                    for p in purchases]
    return {
        "purchases": purchases,
        "total_cost": gold - remaining,
        "remaining_gold": remaining,
        "reason": "；".join(reason_parts) if reason_parts else "无高性价比物品",
    }


def format_shop_result(res: dict) -> str:
    lines = ["== 商店推荐 =="]
    lines.append(f"  预算使用: {res['total_cost']}金，剩余 {res['remaining_gold']}金")
    for p in res["purchases"]:
        lines.append(f"  ★ 买 {p['name']}  ({p['price']}金, 评分{p['score']:.1f})")
    if not res["purchases"]:
        lines.append("  暂无值得购买的物品")
    return "\n".join(lines)
