"""STS2 AI Agent HTTP 客户端：真实模式连游戏，离线模式用内置示例快照。

适配 CharTyr/STS2-Agent mod v0.16.2+，API 端口 8080。
所有响应包裹在 {ok, request_id, data} 中，本客户端自动解包取 data。
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Any, Optional


class Sts2AgentClient:
    """连接 STS2 AI Agent mod 的本地 HTTP 服务（端口 8080）。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 5.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _get(self, path: str) -> Optional[dict]:
        try:
            with urllib.request.urlopen(f"{self.base}{path}", timeout=self.timeout) as r:
                raw = json.loads(r.read().decode("utf-8"))
                return raw.get("data", raw) if isinstance(raw, dict) else raw
        except Exception:
            return None

    def _post(self, path: str, payload: dict) -> Optional[dict]:
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base}{path}", data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = json.loads(r.read().decode("utf-8"))
                return raw.get("data", raw) if isinstance(raw, dict) else raw
        except Exception:
            return None

    def ping(self) -> bool:
        h = self._get("/health")
        return h is not None and h.get("status") == "ready"

    def get_state(self) -> dict:
        """获取完整游戏状态（已解包 data）。"""
        s = self._get("/state")
        return s if s is not None else {"screen": "UNKNOWN", "in_combat": False}

    def get_agent_view(self) -> dict:
        """获取精简版 agent_view（决策用）。"""
        s = self.get_state()
        return s.get("agent_view", s)

    def get_available_actions(self) -> list[dict]:
        """获取当前可用动作描述符列表。"""
        d = self._get("/actions/available")
        if d and isinstance(d, dict):
            return d.get("actions", [])
        return []

    def get_decision_snapshot(self) -> Optional[dict]:
        """一次性获取 state + available_actions（同一帧，避免两帧不一致）。"""
        return self._get("/decision-snapshot")

    # ---- 动作执行 ----
    def _action(self, name: str, **params) -> Optional[dict]:
        payload = {
            "action": name,
            "card_index": params.get("card_index"),
            "target_index": params.get("target_index"),
            "option_index": params.get("option_index"),
            "x": params.get("x"),
            "y": params.get("y"),
            "tool": params.get("tool"),
            "command": params.get("command"),
            "client_context": {"source": "sts2_advisor", "tool_name": name},
        }
        return self._post("/action", payload)

    def play_card(self, card_index: int, target_index: Optional[int] = None) -> Optional[dict]:
        return self._action("play_card", card_index=card_index, target_index=target_index)

    def end_turn(self) -> Optional[dict]:
        return self._action("end_turn")

    def choose_event_option(self, option_index: int) -> Optional[dict]:
        return self._action("choose_event_option", option_index=option_index)

    def choose_reward(self, option_index: int) -> Optional[dict]:
        return self._action("choose_reward_card", option_index=option_index)

    def claim_reward(self, option_index: int = 0) -> Optional[dict]:
        return self._action("claim_reward", option_index=option_index)

    def skip_reward_cards(self) -> Optional[dict]:
        return self._action("skip_reward_cards")

    def proceed(self) -> Optional[dict]:
        return self._action("proceed")

    def choose_map_node(self, option_index: int) -> Optional[dict]:
        return self._action("choose_map_node", option_index=option_index)

    def buy_card(self, option_index: int) -> Optional[dict]:
        return self._action("buy_card", option_index=option_index)

    def buy_relic(self, option_index: int) -> Optional[dict]:
        return self._action("buy_relic", option_index=option_index)

    def buy_potion(self, option_index: int) -> Optional[dict]:
        return self._action("buy_potion", option_index=option_index)

    def rest(self) -> Optional[dict]:
        return self._action("rest")

    def upgrade(self, option_index: int) -> Optional[dict]:
        return self._action("upgrade", option_index=option_index)

    def take_action(self, action: dict) -> bool:
        """兼容旧接口：接受 {type, card_index, target_index} 格式。"""
        atype = action.get("type", action.get("action", ""))
        if atype in ("play_card", "play"):
            return self.play_card(
                action.get("card_index", action.get("index", 0)),
                action.get("target_index"),
            ) is not None
        elif atype in ("end_turn", "end"):
            return self.end_turn() is not None
        elif atype == "choose_event_option":
            return self.choose_event_option(action.get("option_index", 0)) is not None
        elif atype == "choose_reward":
            return self.choose_reward(action.get("option_index", 0)) is not None
        else:
            return self._action(atype, **action) is not None


class OfflineClient:
    """离线模式：返回内置示例快照，用于自测。"""

    def __init__(self):
        self._i = 0

    def ping(self) -> bool:
        return True

    def get_state(self) -> dict:
        from .cli import _silent_combat_snapshot
        return _silent_combat_snapshot()

    def get_agent_view(self) -> dict:
        return self.get_state()

    def get_available_actions(self) -> list[dict]:
        return []

    def get_decision_snapshot(self) -> Optional[dict]:
        return None

    def play_card(self, card_index: int, target_index=None):
        return {"ok": True}

    def end_turn(self):
        return {"ok": True}

    def take_action(self, action: dict) -> bool:
        return True
