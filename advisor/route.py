"""地图路线决策：节点类型评分 + 前瞻 + 状态感知。适配 STS2 AI Agent 真实 state。"""
from __future__ import annotations
from typing import Optional


# 节点基础评分（静默猎手视角）
NODE_SCORES = {
    "enemy": 5.0, "monster": 5.0, "normal": 5.0,
    "elite": 7.5, "elite_enemy": 7.5,
    "rest": 4.5, "rest_site": 4.5, "campfire": 4.5,
    "shop": 4.0, "store": 4.0,
    "event": 5.0, "unknown": 4.5, "mystery": 4.5,
    "treasure": 6.5, "chest": 6.5,
    "boss": 8.0, "boss_quest": 8.0,
}


def _normalize_type(t: str) -> str:
    """标准化节点类型。"""
    t = str(t).lower().strip()
    # 映射各种可能的类型名
    mapping = {
        "monster": "enemy", "normal": "enemy", "monster_room": "enemy",
        "elite_enemy": "elite", "elite_room": "elite",
        "rest_site": "rest", "campfire": "rest", "rest_room": "rest",
        "store": "shop", "shop_room": "shop",
        "mystery": "unknown", "event_room": "event", "unknown_room": "unknown",
        "chest": "treasure", "treasure_room": "treasure",
        "boss_quest": "boss", "boss_room": "boss",
    }
    return mapping.get(t, t)


def parse_map(snap: dict) -> list[dict]:
    """从快照解析当前可选节点。支持多种字段名。"""
    # 尝试多种位置
    nodes = None
    if isinstance(snap.get("map"), dict):
        m = snap["map"]
        nodes = (m.get("available_nodes") or m.get("next_nodes") or
                 m.get("current_nodes") or m.get("nodes") or
                 m.get("paths") or [])
    if not nodes:
        nodes = (snap.get("map_nodes") or snap.get("available_nodes") or
                 snap.get("next_nodes") or snap.get("nodes") or [])

    result = []
    for n in nodes:
        if isinstance(n, dict):
            result.append(n)
    return result


def score_option(node: dict, state: Optional[dict] = None) -> tuple[float, str]:
    """评分单个路线节点，返回 (score, reason)。"""
    ntype_raw = str(node.get("type", node.get("node_type",
                    node.get("room_type", "unknown"))))
    ntype = _normalize_type(ntype_raw)
    base = NODE_SCORES.get(ntype, 4.0)
    reasons = [f"{ntype}基础分{base:.1f}"]

    # 状态感知评分
    if state:
        # 从 run 或 player 中获取血量
        run = state.get("run", {}) or {}
        player = state.get("player", {}) or {}
        hp = run.get("current_hp", player.get("current_hp",
               player.get("hp", 70)))
        max_hp = run.get("max_hp", player.get("max_hp", 75))
        gold = run.get("gold", 0)
        floor = run.get("floor", 0)

        hp_ratio = hp / max(1, max_hp)

        # 血量低时偏好休息
        if hp_ratio < 0.4 and ntype == "rest":
            base += 4.0
            reasons.append(f"血量低({hp}/{max_hp})优先休息")
        elif hp_ratio < 0.5 and ntype == "rest":
            base += 2.0
            reasons.append(f"血量偏低({hp}/{max_hp})考虑休息")

        # 血量健康时偏好精英
        if hp_ratio > 0.75 and ntype == "elite":
            base += 2.0
            reasons.append("血量健康可打精英")
        elif hp_ratio > 0.6 and ntype == "elite":
            base += 1.0
            reasons.append("血量尚可可打精英")

        # 血量低时避免精英
        if hp_ratio < 0.5 and ntype == "elite":
            base -= 2.0
            reasons.append("血量低避免精英")

        # 金币多时商店更有价值
        if gold > 150 and ntype == "shop":
            base += 1.5
            reasons.append(f"金币充足({gold})可购物")

        # 高层数时休息更重要
        if floor > 30 and ntype == "rest":
            base += 1.0
            reasons.append("高层数优先保血")

        # 高层数时精英风险更高
        if floor > 40 and ntype == "elite":
            base -= 1.0
            reasons.append("高层精英风险高")

    # 前瞻：该节点后续路径
    children = node.get("children", node.get("next", []))
    if children and isinstance(children, list):
        child_scores = []
        for c in children:
            if isinstance(c, dict):
                ct = _normalize_type(c.get("type", c.get("node_type", "unknown")))
                child_scores.append(NODE_SCORES.get(ct, 4.0))
        if child_scores:
            best_child = max(child_scores)
            base += best_child * 0.25
            reasons.append(f"后续最优{best_child:.1f}")

    return base, "；".join(reasons)


def choose_route(snap: dict) -> list[dict]:
    """返回排序后的路线选项 [{node, score, reason, type}]。"""
    nodes = parse_map(snap)
    results = []
    for n in nodes:
        score, reason = score_option(n, snap)
        ntype = _normalize_type(n.get("type", n.get("node_type", "unknown")))
        results.append({"node": n, "score": score, "reason": reason, "type": ntype})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def format_route_result(results: list[dict]) -> str:
    lines = ["== 路线推荐 =="]
    for i, r in enumerate(results[:3]):
        marker = "★" if i == 0 else " "
        lines.append(f"  {marker} [{r['type']}] 评分{r['score']:.1f}")
        lines.append(f"      {r['reason']}")
    return "\n".join(lines)
