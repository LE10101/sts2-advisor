"""
本地云端推送Agent
运行在用户电脑上，读取游戏状态→运行MCTS→推送到云端网站
不需要运行Web服务器，云端网站永久在线
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from advisor.client import AutoSpireClient
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

    def __init__(self, cloud_url: str = "", game_host: str = "127.0.0.1",
                 game_port: int = 8080, interval: float = 1.5):
        self.cloud_url = cloud_url or os.environ.get(
            "STS2_CLOUD_URL", "https://sts2-advisor.onrender.com")
        self.client = AutoSpireClient(host=game_host, port=game_port)
        self.mcts = MCTS(default_policy=greedy_policy, seed=42)
        self.draw_memory = DrawOrderMemory()
        self.interval = interval

        # 对局记录
        self.run_id = None
        self.current_floor = 0
        self.last_phase = ""
        self.state_hash = ""

        print(f"=" * 50)
        print(f"STS2 Cloud Agent")
        print(f"=" * 50)
        print(f"云端地址: {self.cloud_url}")
        print(f"游戏API: http://{game_host}:{game_port}")
        print(f"推送间隔: {interval}秒")
        print(f"=" * 50)

    def _post(self, path: str, data: dict) -> dict:
        """推送数据到云端"""
        try:
            req = urllib.request.Request(
                f"{self.cloud_url}{path}",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  [推送失败] {path}: {e}")
            return {"ok": False, "error": str(e)}

    def _get_game_state(self):
        """获取游戏状态"""
        try:
            return self.client.get_state()
        except Exception as e:
            return {"error": str(e), "screen": "disconnected"}

    def _compute_recommendation(self, snap: dict) -> dict:
        """计算推荐（战斗MCTS / 路线 / 奖励 / 商店）"""
        d = snap.get("data", snap)
        screen = d.get("screen", "")

        if screen == "COMBAT":
            combat_snap = d.get("combat", d)
            state = CombatState.from_snapshot(combat_snap)
            self.draw_memory.observe_new_cards(state.hand)

            root = self.mcts.search(state, iterations=500)
            ranked = self.mcts.ranked_actions(root)
            best = ranked[0][0] if ranked else None
            reason = explain_combat(state, best, ranked)

            # 构建已知牌序
            known_order = []
            for i in range(self.draw_memory.known_length()):
                c = self.draw_memory.peek(i)
                if c:
                    known_order.append(c.name)

            # 动作转字典
            def action_to_dict(action):
                if action.kind == "end_turn":
                    return {"kind": "end_turn", "label": "结束回合"}
                if action.kind == "play_card" and action.card:
                    target = "自己"
                    if action.target_index >= 0 and action.target_index < len(state.enemies):
                        target = state.enemies[action.target_index].name
                    return {"kind": "play_card", "card": action.card.name,
                            "cost": action.card.cost, "target": target,
                            "label": f"打[{action.card.name}]→{target}"}
                return {"kind": action.kind, "label": action.kind}

            return {
                "phase": "combat",
                "best": action_to_dict(best) if best else None,
                "ranked": [{"action": action_to_dict(a), "value": v, "visits": n}
                           for a, v, n in ranked[:5]],
                "reason": reason,
                "state": {
                    "hp": state.player_hp, "max_hp": state.player_max_hp,
                    "block": state.player_block, "energy": state.energy,
                    "turn": state.turn,
                    "hand": [{"name": c.name, "cost": c.cost, "playable": c.playable}
                             for c in state.hand],
                    "enemies": [{
                        "name": e.name, "hp": e.hp, "max_hp": e.max_hp,
                        "block": e.block, "poison": e.poison,
                        "intent_type": e.intent_type,
                        "intent_damage": e.intent_total_damage,
                        "is_aoe": e.is_aoe
                    } for e in state.enemies]
                },
                "draw_order": known_order
            }
        elif screen == "MAP":
            return {"phase": "map", "recommendation": choose_route(snap)}
        elif screen == "REWARD":
            return {"phase": "reward", "recommendation": choose_reward(snap)}
        elif screen == "SHOP":
            return {"phase": "shop", "recommendation": choose_shop(snap)}
        else:
            return {"phase": screen, "message": "等待游戏阶段..."}

    def _update_run(self, snap: dict):
        """更新对局记录"""
        d = snap.get("data", snap)
        run = d.get("run", {}) or {}
        floor = run.get("floor", 0)

        # 新对局开始
        if floor < self.current_floor or self.run_id is None:
            self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"\n[新对局] {self.run_id}")

        self.current_floor = floor

        # 推送对局数据
        run_data = {
            "id": self.run_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "character": "静默猎手",
            "ascension": run.get("ascension_level", 0),
            "current_hp": run.get("current_hp", 70),
            "max_hp": run.get("max_hp", 70),
            "gold": run.get("gold", 99),
            "floor": floor,
            "max_floor": max(floor, self.current_floor),
            "deck": [c.get("name", "?") for c in run.get("deck", [])],
            "relics": [r.get("name", "?") if isinstance(r, dict) else str(r)
                       for r in run.get("relics", [])],
            "result": "进行中"
        }
        self._post("/api/agent/run", run_data)

    def run(self):
        """主循环"""
        print("\n开始监控，按 Ctrl+C 停止...\n")
        try:
            while True:
                snap = self._get_game_state()

                if "error" in snap:
                    print(f"\r等待游戏连接... ({snap['error'][:30]})", end="", flush=True)
                    time.sleep(self.interval)
                    continue

                d = snap.get("data", snap)
                screen = d.get("screen", "")
                phase = screen

                # 状态去重
                state_str = json.dumps(d, sort_keys=True, ensure_ascii=False)[:500]
                current_hash = hash(state_str)
                if current_hash == self.state_hash and phase == self.last_phase:
                    time.sleep(self.interval)
                    continue
                self.state_hash = current_hash
                self.last_phase = phase

                # 计算推荐
                recommendation = self._compute_recommendation(snap)

                # 推送到云端
                self._post("/api/agent/state", {
                    "screen": screen,
                    "phase": recommendation.get("phase", phase),
                    "state": d,
                    "recommendation": recommendation
                })

                # 更新对局记录
                self._update_run(snap)

                # 控制台输出
                ts = datetime.now().strftime("%H:%M:%S")
                if recommendation.get("phase") == "combat" and recommendation.get("best"):
                    print(f"[{ts}] 战斗: {recommendation['best']['label']} | {recommendation.get('reason', '')[:50]}")
                elif recommendation.get("phase") == "map":
                    print(f"[{ts}] 路线: {json.dumps(recommendation.get('recommendation', {}), ensure_ascii=False)[:50]}")
                elif recommendation.get("phase") == "reward":
                    print(f"[{ts}] 奖励: {json.dumps(recommendation.get('recommendation', {}), ensure_ascii=False)[:50]}")
                elif recommendation.get("phase") == "shop":
                    print(f"[{ts}] 商店: {json.dumps(recommendation.get('recommendation', {}), ensure_ascii=False)[:50]}")
                else:
                    print(f"[{ts}] {screen}")

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n停止监控")
            # 标记对局结束
            if self.run_id:
                self._post("/api/agent/run", {
                    "id": self.run_id,
                    "result": "已结束"
                })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="STS2 云端推送Agent")
    parser.add_argument("--url", default="", help="云端网站地址")
    parser.add_argument("--interval", type=float, default=1.5, help="推送间隔（秒）")
    args = parser.parse_args()

    agent = CloudAgent(cloud_url=args.url, interval=args.interval)
    agent.run()
