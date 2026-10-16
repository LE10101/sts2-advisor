"""地图路线决策器：读取 map 快照，推荐最优的下一步节点（并向前看 N 步）。

节点类型收益-风险评估（结合当前状态）：
- 战斗(monster)    ：稳定收益，前期成长
- 精英(elite)      ：高收益（遗物）高风险
- 事件(event)      ：高变数，可能大赚/大亏
- 商店(shop)       ：花金币买卡/删牌
- 篝火(rest)       ：回血或锻造（HP 低时优先级高）
- 宝箱(treasure)   ：免费遗物，必去
- 休息?(campfire)

对 autoSpire 的 map 快照做容错解析；无游戏时用内置示例演示。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

LOOKAHEAD = 2  # 向前看的层数


def _pick(d: Optional[Dict], *keys, default=None):
    if not d:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _node_type(node: Dict[str, Any]) -> str:
    """归一化节点类型。兼容英文/中文。"""
    t = str(_pick(node, "type", "kind", "name", default="")).lower()
    if "elite" in t or "精英" in t:
        return "elite"
    if "event" in t or "事件" in t:
        return "event"
    if "shop" in t or "商店" in t:
        return "shop"
    if "rest" in t or "篝火" in t or "休息" in t:
        return "rest"
    if "treasure" in t or "宝箱" in t or "宝藏" in t:
        return "treasure"
    if "boss" in t or "首领" in t or "最终" in t:
        return "boss"
    if "monster" in t or "战斗" in t or "怪" in t:
        return "monster"
    return "monster"


# 节点类型基础分
_BASE = {"monster": 0.6, "elite": 0.9, "event": 0.7, "shop": 0.75,
         "rest": 0.7, "treasure": 1.0, "boss": 0.0}


def _risk_adj(n_type: str, hp_ratio: float) -> float:
    """根据当前血量调整：血少时避精英、偏好篝火。"""
    adj = 0.0
    if hp_ratio < 0.4:
        if n_type == "elite":
            adj -= 0.5
        elif n_type == "rest":
            adj += 0.4
    elif hp_ratio > 0.75:
        if n_type == "rest":
            adj -= 0.2  # 血足时篝火价值略降
        elif n_type == "elite":
            adj += 0.2
    return adj


def parse_map(snap: Dict[str, Any]):
    m = snap.get("map", snap) or {}
    nodes = _pick(m, "nodes", "map_nodes", default=[]) or []
    current = _pick(m, "current", "current_node", default={}) or {}
    cur_row = _pick(current, "row", "y", default=None)
    cur_col = _pick(current, "col", "x", default=None)
    options = _pick(m, "options", "next", "next_nodes", default=None)
    if options is None:
        # 从 nodes 推断下一层可选项：row == cur_row+1 的节点
        target_row = (cur_row + 1) if cur_row is not None else 1
        options = [n for n in nodes if _pick(n, "row", "y", default=None) == target_row]
    return nodes, current, options


def score_option(node: Dict[str, Any], hp_ratio: float, floor: int) -> Tuple[float, str]:
    n_type = _node_type(node)
    score = _BASE.get(n_type, 0.6) + _risk_adj(n_type, hp_ratio)
    # 前期（floor 小）偏向战斗成长
    if floor <= 6 and n_type == "monster":
        score += 0.15
    reason = f"{n_type}({_pick(node, 'name', default='')}) 分{score:.2f}"
    return score, reason


def choose_route(snap: Dict[str, Any], hp_ratio: float = 1.0,
                 floor: int = 1) -> List[dict]:
    """返回按分数降序的可选节点列表：[{node, score, reason}]。"""
    _, _, options = parse_map(snap)
    scored = []
    for node in options:
        s, r = score_option(node, hp_ratio, floor)
        # 简单 lookahead：给"有更多高价值后续"的节点加分
        lookahead = _lookahead_bonus(node, snap)
        s += lookahead
        scored.append({"node": node, "score": s, "reason": r + (f" 前瞻+{lookahead:.2f}" if lookahead else "")})
    scored.sort(key=lambda x: -x["score"])
    return scored


def _lookahead_bonus(node: Dict[str, Any], snap: Dict[str, Any]) -> float:
    """粗略前瞻：该节点后是否通向宝箱/商店等有利节点。"""
    m = snap.get("map", snap) or {}
    nodes = _pick(m, "nodes", "map_nodes", default=[]) or []
    node_id = _pick(node, "id", "col", "row", default=None)
    if node_id is None:
        return 0.0
    n_type = _node_type(node)
    bonus = 0.0
    # 节点本身是宝箱/商店/篝火 → 后续价值已含，不再叠加
    for other in nodes:
        if other is node:
            continue
        links = _pick(other, "next", "children", "next_nodes", default=[]) or []
        if any(l == node_id for l in links):
            t = _node_type(other)
            if t == "elite":
                bonus += 0.1
            elif t == "treasure":
                bonus += 0.15
    if n_type in ("shop", "treasure"):
        bonus += 0.1
    return min(bonus, 0.3)
