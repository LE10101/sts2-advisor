"""
本地云端推送Agent
读取游戏状态 -> 运行MCTS -> 推送到云端网站
用法: python cloud_agent.py --server https://your-app.onrender.com --token YOUR_TOKEN
"""
import json
import time
import hashlib
import argparse
import urllib.request
from datetime import datetime

from advisor.client import Sts2AgentClient as AutoSpireClient
from advisor.model import CombatState
from advisor.mcts import MCTS
from advisor.policy import greedy_policy
from advisor.explanation import explain_combat
from advisor.drawmemory import DrawOrderMemory
from advisor.route import choose_route
from advisor.reward import choose_reward
from advisor.shop import choose_shop


class CloudAgent:
    """本地云端推送Agent"""

    def __init__(self, server_url: str, token: str = "", interval: float = 1.5):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.interval = interval
        self.client = AutoSpireClient(host="127.0.0.1", port=8080)
        self.mcts = MCTS(default_policy=greedy_policy, seed=42)
        self.draw_memory = DrawOrderMemory()
        self.last_state_hash = ""
        self.current_run_id = None
        self.running = False

    def _post(self, path: str, data: dict) -> dict:
        """发送POST请求到云端"""
        url = f"{self.server_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def _state_hash(self, snap: dict) -> str:
        d = snap.get("data", snap)
        relevant = {
            "screen": d.get("screen"),
            "turn": d.get("turn"),
            "hand": [c.get("name") for c in d.get("combat", {}).get("hand", [])],
        }
        return hashlib.md5(json.dumps(relevant, sort_keys=True).hexdigest().encode()).hexdigest()

    def _get_combat_rec(self, snap: dict) -> dict:
        d = snap.get("data", snap)
        combat_snap = d.get("combat", d)
        state = CombatState.from_snapshot(combat_snap)
        self.draw_memory.observe_new_cards(state.hand)

        root = self.mcts.search(state, iterations=500)
        ranked = self.mcts.ranked_actions(root)
        best = ranked[0][0] if ranked else None
        reason = explain_combat(state, best, ranked)

        known_order = []
        for i in range(self.draw_memory.known_length()):
            c = self.draw_memory.peek(i)
            if c:
                known_order.append(c.name)

        return {
            "phase": "combat",
            "best": self._action_to_dict(best, state) if best else None,
            "ranked": [{"action": self._action_to_dict(a, state), "value": v, "visits": n} for a, v, n in ranked[:5]],
            "reason": reason,
            "state": self._state_to_dict(state),
            "draw_order": known_order,
        }

    def _action_to_dict(self, action, state) -> dict:
        if action.kind == "end_turn":
            return {"kind": "end_turn", "label": "结束回合"}
        if action.kind == "play_card" and action.card:
            target = "自己"
            if action.target_index >= 0 and action.target_index < len(state.enemies):
                target = state.enemies[action.target_index].name
            return {"kind": "play_card", "card": action.card.name,
                    "cost": action.card.cost, "target": target,
                    "label": f"打[{action.card.name}]\u2192{target}"}
        return {"kind": action.kind, "label": action.kind}

    def _state_to_dict(self, state) -> dict:
        return {
            "hp": state.player_hp, "max_hp": state.player_max_hp,
            "block": state.player_block, "energy": state.energy,
            "hand": [{"name": c.name, "cost": c.cost, "playable": c.playable} for c in state.hand],
            "enemies": [{
                "name": e.name, "hp": e.hp, "max_hp": e.max_hp,
                "block": e.block, "poison": e.poison,
                "intent_type": e.intent_type, "intent_damage": e.intent_total_damage,
                "is_aoe": e.is_aoe
            } for e in state.enemies],
            "turn": state.turn
        }

    def tick(self):
        """单次轮询"""
        try:
            snap = self.client.get_state()
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 游戏未连接: {e}")
            return

        h = self._state_hash(snap)
        if h == self.last_state_hash:
            return  # 状态未变化，跳过
        self.last_state_hash = h

        d = snap.get("data", snap)
        screen = d.get("screen", "UNKNOWN")

        # 根据屏幕类型生成推荐
        if screen == "COMBAT":
            recommendation = self._get_combat_rec(snap)
        elif screen == "MAP":
            recommendation = {"phase": "map", "recommendation": choose_route(snap)}
        elif screen == "REWARD":
            recommendation = {"phase": "reward", "recommendation": choose_reward(snap)}
        elif screen == "SHOP":
            recommendation = {"phase": "shop", "recommendation": choose_shop(snap)}
        else:
            recommendation = {"phase": screen.lower(), "message": "等待游戏阶段..."}

        # 推送到云端
        result = self._post("/api/agent/state", {
            "screen": screen,
            "phase": recommendation.get("phase", "unknown"),
            "state": d,
            "recommendation": recommendation,
        })

        phase = recommendation.get("phase", "?")
        best = recommendation.get("best", {}).get("label", "")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {phase}: {best} (推送: {'OK' if result.get('ok') else result.get('error', '?')})")

    def run(self):
        """持续运行"""
        self.running = True
        print("=" * 50)
        print(f"STS2 Cloud Agent 启动")
        print(f"服务器: {self.server_url}")
        print(f"轮询间隔: {self.interval}秒")
        print("=" * 50)
        print("按 Ctrl+C 停止\n")

        while self.running:
            try:
                self.tick()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")
            time.sleep(self.interval)

        print("\nAgent已停止")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STS2 云端推送Agent")
    parser.add_argument("--server", default="http://127.0.0.1:8766", help="云端服务器地址")
    parser.add_argument("--token", default="", help="用户登录token")
    parser.add_argument("--interval", type=float, default=1.5, help="轮询间隔(秒)")
    args = parser.parse_args()

    agent = CloudAgent(args.server, args.token, args.interval)
    agent.run()
