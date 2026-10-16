"""
对局战略复盘分析模块
分析牌组构成、流派识别、战斗表现、改进建议
"""
from typing import Dict, List, Any


def analyze_run(run_data: dict) -> Dict[str, Any]:
    """分析一局游戏，返回综合评估"""
    deck = run_data.get("deck", [])
    relics = run_data.get("relics", [])
    combats = run_data.get("combats", [])
    ascension = run_data.get("ascension", 0)
    result = run_data.get("result", "未知")

    # 1. 流派识别
    archetype = identify_archetype(deck, relics)

    # 2. 牌组评估
    deck_eval = evaluate_deck(deck, relics)

    # 3. 战斗表现分析
    combat_eval = analyze_combats(combats)

    # 4. 改进建议
    suggestions = generate_suggestions(deck, relics, archetype, deck_eval, combat_eval, ascension)

    # 5. 综合评分
    score = calculate_score(archetype, deck_eval, combat_eval, result, ascension)

    return {
        "score": score,
        "archetype": archetype,
        "deck_evaluation": deck_eval,
        "combat_analysis": combat_eval,
        "suggestions": suggestions,
        "ascension": ascension,
        "result": result,
    }


def identify_archetype(deck: List[str], relics: List[str]) -> Dict[str, Any]:
    """识别主要流派"""
    poison_cards = ["致命毒药", "毒性爆发", "咕嘟冒泡", "带毒刺击", "蛇咬", "腐蚀波", "腐蚀", "磨蚀"]
    shiv_cards = ["墨之刃", "袖里乾坤", "终结技", "啄击", "突然一拳"]
    discard_cards = ["逃脱计划", "早有准备", "后空翻", "余像", "侧步"]
    defense_cards = ["防御", "防御+", "蜃景", "生存者", "潦草急救", "必备工具"]

    poison_count = sum(1 for c in deck if any(p in c for p in poison_cards))
    shiv_count = sum(1 for c in deck if any(s in c for s in shiv_cards))
    discard_count = sum(1 for c in deck if any(d in c for d in discard_cards))
    defense_count = sum(1 for c in deck if any(d in c for d in defense_cards))

    archetypes = {
        "毒流": poison_count,
        "飞刀流": shiv_count,
        "弃牌流": discard_count,
        "防御流": defense_count,
    }

    primary = max(archetypes, key=archetypes.get)
    secondary = sorted(archetypes.items(), key=lambda x: -x[1])[1]

    return {
        "primary": primary,
        "primary_score": archetypes[primary],
        "secondary": secondary[0],
        "secondary_score": secondary[1],
        "all_scores": archetypes,
        "is_pure": archetypes[primary] > sum(v for k, v in archetypes.items() if k != primary) * 0.8,
    }


def evaluate_deck(deck: List[str], relics: List[str]) -> Dict[str, Any]:
    """评估牌组质量"""
    deck_size = len(deck)
    strikes = sum(1 for c in deck if c == "打击" or c == "打击+")
    defends = sum(1 for c in deck if c == "防御" or c == "防御+")
    curses = sum(1 for c in deck if c in ["进阶之灾", "笨拙", "睡眠不佳", "诅咒"])
    upgraded = sum(1 for c in deck if "+" in c)

    # 牌组大小评分（理想20-30张）
    if deck_size <= 15:
        size_score = 70
    elif deck_size <= 25:
        size_score = 95
    elif deck_size <= 35:
        size_score = 80
    elif deck_size <= 45:
        size_score = 60
    else:
        size_score = 40

    # 基础卡比例
    basic_ratio = (strikes + defends) / max(deck_size, 1)
    basic_score = max(0, 100 - basic_ratio * 150)

    # 诅咒惩罚
    curse_penalty = curses * 15

    # 升级比例
    upgrade_ratio = upgraded / max(deck_size, 1)
    upgrade_score = min(100, upgrade_ratio * 200)

    overall = int((size_score * 0.3 + basic_score * 0.3 + upgrade_score * 0.2) - curse_penalty)
    overall = max(0, min(100, overall))

    return {
        "deck_size": deck_size,
        "strikes": strikes,
        "defends": defends,
        "curses": curses,
        "upgraded": upgraded,
        "size_score": size_score,
        "basic_score": int(basic_score),
        "upgrade_score": int(upgrade_score),
        "overall": overall,
    }


def analyze_combats(combats: List[dict]) -> Dict[str, Any]:
    """分析战斗表现"""
    if not combats:
        return {
            "total": 0, "wins": 0, "win_rate": 0,
            "avg_hp_loss": 0, "max_hp_loss": 0,
            "perfect_wins": 0,
        }

    wins = sum(1 for c in combats if c.get("result") == "胜利")
    hp_losses = [c.get("hp_loss", 0) for c in combats if "hp_loss" in c]
    perfect = sum(1 for c in combats if c.get("hp_loss", 0) == 0)

    return {
        "total": len(combats),
        "wins": wins,
        "win_rate": wins / len(combats) * 100 if combats else 0,
        "avg_hp_loss": sum(hp_losses) / len(hp_losses) if hp_losses else 0,
        "max_hp_loss": max(hp_losses) if hp_losses else 0,
        "perfect_wins": perfect,
    }


def generate_suggestions(deck, relics, archetype, deck_eval, combat_eval, ascension) -> List[Dict[str, str]]:
    """生成改进建议"""
    suggestions = []

    # 牌组大小建议
    if deck_eval["deck_size"] > 35:
        suggestions.append({
            "type": "warning",
            "title": "牌组过大",
            "content": f"当前牌组{deck_eval['deck_size']}张，建议精简到25-30张。过多的牌会降低关键牌的抽到概率。"
        })
    elif deck_eval["deck_size"] < 15:
        suggestions.append({
            "type": "info",
            "title": "牌组偏小",
            "content": f"当前牌组仅{deck_eval['deck_size']}张，虽然精简但可能缺乏应对不同场景的手段。"
        })

    # 基础卡建议
    if deck_eval["strikes"] > 2:
        suggestions.append({
            "type": "warning",
            "title": "打击卡过多",
            "content": f"还有{deck_eval['strikes']}张打击，建议在商店或事件中移除。打击在后期输出不足。"
        })

    # 流派建议
    if archetype["primary"] == "毒流" and archetype["primary_score"] < 4:
        suggestions.append({
            "type": "info",
            "title": "毒流组件不足",
            "content": "毒流需要足够的叠毒和翻倍卡。建议补充致命毒药、毒性爆发、咕嘟冒泡等核心卡。"
        })

    # 诅咒建议
    if deck_eval["curses"] > 0:
        suggestions.append({
            "type": "warning",
            "title": "牌组中有诅咒",
            "content": f"有{deck_eval['curses']}张诅咒卡，建议尽快通过商店或事件移除。"
        })

    # 战斗表现建议
    if combat_eval.get("avg_hp_loss", 0) > 10:
        suggestions.append({
            "type": "warning",
            "title": "场均失血偏高",
            "content": f"场均失血{combat_eval['avg_hp_loss']:.0f}点，建议加强防御或提高斩杀速度。"
        })

    # 进阶建议
    if ascension >= 10 and deck_eval["upgraded"] < 5:
        suggestions.append({
            "type": "info",
            "title": "升级不足",
            "content": f"进阶{ascension}建议至少升级5张关键卡。优先升级输出和防御核心。"
        })

    if not suggestions:
        suggestions.append({
            "type": "info",
            "title": "牌组状态良好",
            "content": "当前牌组构成合理，继续保持！注意Boss战的血量管理。"
        })

    return suggestions


def calculate_score(archetype, deck_eval, combat_eval, result, ascension) -> int:
    """计算综合评分（0-100）"""
    score = 50  # 基础分

    # 牌组质量
    score += (deck_eval["overall"] - 50) * 0.3

    # 流派纯度
    if archetype["is_pure"]:
        score += 10

    # 战斗表现
    if combat_eval.get("win_rate", 0) > 80:
        score += 15
    elif combat_eval.get("win_rate", 0) > 60:
        score += 5

    if combat_eval.get("avg_hp_loss", 10) < 5:
        score += 10

    # 结果
    if result == "胜利":
        score += 20
    elif result == "失败":
        score -= 10

    # 进阶加成
    score += ascension * 0.5

    return max(0, min(100, int(score)))


def generate_replay_narrative(run_data: dict) -> str:
    """生成复盘文字叙述"""
    analysis = analyze_run(run_data)
    a = analysis["archetype"]
    d = analysis["deck_evaluation"]
    c = analysis["combat_analysis"]

    narrative = f"本局为{run_data.get('character', '静默猎手')}进阶{run_data.get('ascension', 0)}对局，"
    narrative += f"最终{run_data.get('result', '未知')}，到达{run_data.get('max_floor', 0)}层。\n\n"

    narrative += f"【流派分析】主要流派为{a['primary']}（{a['primary_score']}张核心卡），"
    if a["is_pure"]:
        narrative += "流派纯度较高。"
    else:
        narrative += f"次级流派为{a['secondary']}，属于混合流派。"
    narrative += "\n\n"

    narrative += f"【牌组评估】牌组共{d['deck_size']}张，"
    narrative += f"含{d['strikes']}张打击、{d['defends']}张防御、{d['curses']}张诅咒、{d['upgraded']}张升级。"
    narrative += f"牌组质量评分{d['overall']}/100。\n\n"

    if c["total"] > 0:
        narrative += f"【战斗表现】共{c['total']}场战斗，胜率{c['win_rate']:.0f}%，"
        narrative += f"场均失血{c['avg_hp_loss']:.0f}点，{c['perfect_wins']}场零伤。\n\n"

    narrative += f"【综合评分】{analysis['score']}/100\n"

    return narrative
