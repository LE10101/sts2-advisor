"""与 autoSpire 对接的 HTTP 客户端。

两种模式：
- ``real``   : 请求本机 autoSpire 的 HTTP 服务（默认 http://127.0.0.1:8765）
- ``offline``: 不连游戏，返回内置的示例战斗快照，用于无游戏时自测 MCTS

autoSpire 接口（见项目文档）：
- GET  /state   -> GameStateSnapshot（phase + 各阶段子快照）
- POST /action  -> ActionResult（提交动作）
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

DEFAULT_PORT = 8765  # autoSpire 主机默认端口（客机为 8766）


class AutoSpireClient:
    """对接 autoSpire HTTP 服务。"""

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 5.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    # -- 基础请求 ----------------------------------------------------------
    def _request(self, method: str, path: str, body: Optional[Dict] = None) -> Dict[str, Any]:
        url = self.base + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_state(self) -> Dict[str, Any]:
        """获取游戏状态快照。"""
        return self._request("GET", "/state")

    def take_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """提交动作，如 {"action": "play_card", "hand_index": 0, "target_id": 2}。"""
        return self._request("POST", "/action", body=action)

    def ping(self) -> bool:
        """探测服务是否可用。"""
        try:
            self.get_state()
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# 离线示例（用于无游戏自测）。字段刻意贴近 autoSpire combat 快照风格。
# ---------------------------------------------------------------------------
def _sample_combat_snapshot() -> Dict[str, Any]:
    return {
        "phase": "combat",
        "run": {"chapter": 1, "floor": 5, "gold": 40, "deck": [{"name": "打击", "count": 5}, {"name": "防御", "count": 4}]},
        "combat": {
            "player": {
                "hp": 62,
                "max_hp": 80,
                "block": 5,
                "energy": 3,
                "buffs": {"力量": 2, "易伤": 1},
                "relics": [],
            },
            "hand": [
                {"hand_index": 0, "name": "打击", "cost": 1, "damage": 8, "description": "造成 8 点伤害"},
                {"hand_index": 1, "name": "打击", "cost": 1, "damage": 8, "description": "造成 8 点伤害"},
                {"hand_index": 2, "name": "防御", "cost": 1, "block": 5, "description": "获得 5 点格挡"},
                {"hand_index": 3, "name": "痛击", "cost": 2, "damage": 8, "description": "造成 8 点伤害，附加 2 层易伤"},
                {"hand_index": 4, "name": "重刃", "cost": 2, "damage": 14, "description": "造成 14 点伤害"},
            ],
            "enemies": [
                {
                    "id": 1,
                    "name": "邪教徒",
                    "hp": 42,
                    "max_hp": 42,
                    "block": 0,
                    "intent": "attack",
                    "intent_value": 12,
                    "buffs": {"仪式": 3},
                },
                {
                    "id": 2,
                    "name": "邪教徒",
                    "hp": 42,
                    "max_hp": 42,
                    "block": 0,
                    "intent": "defend",
                    "intent_value": 6,
                    "buffs": {},
                },
            ],
            "potions": [
                {"slot_index": 0, "name": "力量药水", "description": "获得 2 点力量"},
                {"slot_index": 1, "name": "血瓶", "description": "回复 10 点生命"},
            ],
            "draw_pile": 8,
            "discard_pile": 3,
            "turn": 1,
            "seed": 20261015,
        },
    }


class OfflineClient:
    """不连游戏的离线客户端：固定返回示例战斗快照，动作记录到 self.actions。"""

    def __init__(self):
        self.actions: list = []
        self._snapshot = _sample_combat_snapshot()

    def get_state(self) -> Dict[str, Any]:
        return self._snapshot

    def take_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self.actions.append(action)
        return {"success": True, "error": None}


def build_client(mode: str = "offline", host: str = "127.0.0.1", port: int = DEFAULT_PORT):
    """按模式构建客户端。mode: "offline" 或 "real"。"""
    if mode == "real":
        return AutoSpireClient(host=host, port=port)
    return OfflineClient()
