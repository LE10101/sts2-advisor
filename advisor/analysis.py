"""
对局战略复盘分析模块
分析历史对局，提供战略建议和改进方向
"""
from __future__ import annotations
from typing import Optional
from collections import Counter


# 静默猎手流派关键词
ARCHETYPES = {
    "毒流": ["致命毒药", "毒性爆发", "咕嘟冒泡", "淬毒", "毒雾", "毒液", "剧毒"],
    "小刀流": ["墨之刃", "袖里乾坤", "刀刃之舞", "飞刀", "无限刀刃", "锋利"],
    "弃牌流": ["逃脱计划", "早有准备", "生存者", "弃牌", "战术大师", "精炼"],
    "敏捷流": ["侧步", "蜃景", "余像", "后空翻", "敏捷", "残影"],
    "力量流": ["尖啸", "力量药剂", "猛扑", "终结技", "暴露"],
}


def analyze_run(run_data: dict) -> dict:
    """分析一局游戏，返回复盘报告"""
    deck = run_data.get("deck", [])
    relics = run_data.get("relics", [])
    combats = run_data.get("combats", [])
    decisions = run_data.get("decisions", [])
    rewards = run_data.get("rewards", [])

    result = {
        "summary": {},
        "archetype": {},
        "deck_analysis": {},
        "combat_analysis": {},
        "relic_analysis": {},
        "suggestions": [],
        "score": 0
    }

    # ===== 基本信息 =====
    result["summary"] = {
        "character": run_data.get("character", "静默猎手"),
        "ascension": run_data.get("ascension", 0),
        "max_floor": run_data.get("max_floor", 0),
        "result": run_data.get("result", "未知"),
        "deck_size": len(deck),
        "relic_count": len(relics),
        "combat_count": len(combats),
        "final_hp": run_data.get("current_hp", 0),
        "max_hp": run_data.get("max_hp", 70)
    }

    # ===== 流派分析 =====
    archetype_scores = {}
    for arch, keywords in ARCHETYPES.items():
        score = sum(1 for card in deck if any(kw in card for kw in keywords))
        archetype_scores[arch] = score

    primary_arch = max(archetype_scores, key=archetype_scores.get) if archetype_scores else "混合"
    result["archetype"] = {
        "primary": primary_arch,
        "scores": archetype_scores,
        "is_pure": archetype_scores[primary_arch] >= len(deck) * 0.3
    }

    # ===== 牌组分析 =====
    deck_counter = Counter(deck)
    result["deck_analysis"] = {
        "total": len(deck),
        "duplicates": {k: v for k, v in deck_counter.items() if v > 1},
        "basic_cards": sum(1 for c in deck if c in ["打击", "防御"]),
        "curse_count": sum(1 for c in deck if "诅咒" in c or "进阶之灾" in c),
        "recommended_size": 20 if primary_arch == "毒流" else 15,
        "is_overloaded": len(deck) > 25
    }

    # ===== 战斗分析 =====
    if combats:
        wins = sum(1 for c in combats if c.get("result") == "胜利")
        hp_losses = []
        for c in combats:
            if "start_hp" in c and "hp_after" in c:
                hp_losses.append(c["start_hp"] - c["hp_after"])
        avg_hp_loss = sum(hp_losses) / len(hp_losses) if hp_losses else 0
        result["combat_analysis"] = {
            "total": len(combats),
            "wins": wins,
            "win_rate": wins / len(combats) * 100,
            "avg_hp_loss": round(avg_hp_loss, 1),
            "max_hp_loss": max(hp_losses) if hp_losses else 0,
            "boss_fights": [c for c in combats if any("Boss" in e or "永世" in e for e in c.get("enemies", []))]
        }
    else:
        result["combat_analysis"] = {"total": 0, "win_rate": 0}

    # ===== 遗物分析 =====
    good_relics = ["风的女儿", "水银沙漏", "投斧", "金纸", "蛇之戒指", "钨合金棍"]
    bad_relics = ["红面具", "节日拉炮"]
    result["relic_analysis"] = {
        "total": len(relics),
        "good": [r for r in relics if r in good_relics],
        "bad": [r for r in relics if r in bad_relics],
        "synergy": _check_relic_synergy(relics, primary_arch)
    }

    # ===== 战略建议 =====
    suggestions = []

    # 牌组大小建议
    if len(deck) > 25:
        suggestions.append({
            "type": "warning",
            "title": "牌组过大",
            "content": f"当前牌组{len(deck)}张，建议控制在20张以内。更多的删牌机会（商店、事件）能提高关键牌上手率。"
        })
    elif len(deck) < 12:
        suggestions.append({
            "type": "info",
            "title": "牌组精简",
            "content": f"牌组只有{len(deck)}张，非常精简。注意是否缺少过牌或防御手段。"
        })

    # 流派纯度建议
    if not result["archetype"]["is_pure"]:
        suggestions.append({
            "type": "warning",
            "title": "流派不集中",
            "content": f"主要流派是{primary_arch}，但牌组中流派卡占比不足30%。建议选卡时更聚焦，避免混合太多流派。"
        })

    # 基础牌建议
    basic_count = result["deck_analysis"]["basic_cards"]
    if basic_count > 4:
        suggestions.append({
            "type": "warning",
            "title": "基础牌过多",
            "content": f"还有{basic_count}张基础打击/防御，建议在商店或休息处删除，提高牌组质量。"
        })

    # 战斗表现建议
    if result["combat_analysis"].get("avg_hp_loss", 0) > 8:
        suggestions.append({
            "type": "warning",
            "title": "血量消耗偏大",
            "content": f"平均每场战斗损失{result['combat_analysis']['avg_hp_loss']}点HP。建议增加防御牌或优先处理高威胁敌人。"
        })

    # 流派-specific建议
    if primary_arch == "毒流" and "毒性爆发" not in deck:
        suggestions.append({
            "type": "info",
            "title": "毒流核心缺失",
            "content": "毒流派推荐携带「毒性爆发」来立即触发所有毒层，大幅提升爆发伤害。"
        })
    if primary_arch == "小刀流" and "墨之刃" not in deck:
        suggestions.append({
            "type": "info",
            "title": "小刀流核心缺失",
            "content": "小刀流派推荐携带「墨之刃」，每打出一张攻击牌就生成一把小刀，是核心输出引擎。"
        })

    # 诅咒牌建议
    if result["deck_analysis"]["curse_count"] > 0:
        suggestions.append({
            "type": "danger",
            "title": "牌组中有诅咒",
            "content": f"有{result['deck_analysis']['curse_count']}张诅咒牌，会严重影响牌组效率。建议尽快通过商店或事件移除。"
        })

    result["suggestions"] = suggestions

    # ===== 综合评分 =====
    score = 50
    if result["combat_analysis"].get("win_rate", 0) > 80:
        score += 15
    if len(deck) <= 20:
        score += 10
    if result["archetype"]["is_pure"]:
        score += 10
    if result["combat_analysis"].get("avg_hp_loss", 10) < 6:
        score += 10
    if run_data.get("result") == "胜利":
        score += 5
    result["score"] = min(100, score)

    return result


def _check_relic_synergy(relics: list, archetype: str) -> str:
    """检查遗物与流派的协同性"""
    synergy_map = {
        "毒流": ["水银沙漏", "蛇之戒指", "投斧"],
        "小刀流": ["风的女儿", "钨合金棍", "投斧"],
        "弃牌流": ["空鸟笼", "金纸"],
        "敏捷流": ["风的女儿", "余像"],
    }
    good = synergy_map.get(archetype, [])
    matched = [r for r in relics if r in good]
    if matched:
        return f"与{archetype}协同良好: {', '.join(matched)}"
    return f"缺少与{archetype}高度协同的遗物"


def generate_replay_narrative(run_data: dict) -> str:
    """生成对局复盘的文字叙述"""
    analysis = analyze_run(run_data)
    s = analysis["summary"]
    a = analysis["archetype"]

    narrative = f"这是一局进阶{s['ascension']}的静默猎手，最终打到第{s['max_floor']}层，结果：{s['result']}。\n\n"
    narrative += f"牌组共{s['deck_size']}张，主要流派是「{a['primary']}」"
    if a["is_pure"]:
        narrative += "，流派较为集中。"
    else:
        narrative += "，但流派不够集中。"
    narrative += f"共获得{s['relic_count']}个遗物。\n\n"

    if analysis["combat_analysis"]["total"] > 0:
        ca = analysis["combat_analysis"]
        narrative += f"战斗表现：共{ca['total']}场战斗，胜率{ca['win_rate']:.0f}%，平均每场损失{ca['avg_hp_loss']}点HP。\n\n"

    if analysis["suggestions"]:
        narrative += "改进建议：\n"
        for i, sug in enumerate(analysis["suggestions"], 1):
            narrative += f"{i}. {sug['title']}：{sug['content']}\n"

    narrative += f"\n综合评分：{analysis['score']}/100"
    return narrative
