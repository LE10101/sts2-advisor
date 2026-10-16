"""自动监控模式：持续轮询游戏状态，各阶段自动算推荐并推送到字幕。
不阻塞、不等待输入，适合后台运行。

用法：python watch.py
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
from typing import Optional

sys.path.insert(0, r"C:\Users\21508\Doubao\chats\2026-10-15\new-chat-1\sts2_advisor")

from advisor.client import Sts2AgentClient
from advisor.model import CombatState, Card
from advisor.mcts import MCTS
from advisor.policy import greedy_policy
from advisor.drawmemory import DrawOrderMemory
from advisor.route import choose_route
from advisor.reward import choose_reward, format_reward_result
from advisor.shop import choose_shop, format_shop_result
from advisor.rest import choose_rest, format_rest_result
from advisor.explanation import explain_combat
from advisor.combat_logger import CombatLogger
from advisor.web_overlay import (WebOverlay, format_combat_subtitle,
                                  format_phase_subtitle, get_lan_ip)

POLL_INTERVAL = 1.0       # 状态轮询间隔（秒）
COMBAT_ITERATIONS = 800   # 战斗 MCTS 迭代次数
COMBAT_CACHE_TIME = 2.0   # 战斗推荐缓存时间（秒），避免每帧重算


class GameWatcher:
    def __init__(self, host="127.0.0.1", port=8080, overlay_port=8766):
        self.client = Sts2AgentClient(host, port)
        self.mem = DrawOrderMemory()
        self.prev_state: Optional[CombatState] = None
        self.prev_phase = ""
        self.last_combat_calc = 0.0
        self.last_combat_hash = ""
        self.overlay = WebOverlay(port=overlay_port, host="0.0.0.0")
        self.logger = CombatLogger()
        self.running = False

    def start(self):
        if not self.overlay.start():
            print("字幕启动失败，继续无字幕运行")
        self.running = True
        lan = get_lan_ip()
        print(f"=== 杀戮尖塔2 决策器 · 自动监控 ===")
        print(f"  本机字幕: http://127.0.0.1:{self.overlay.port}")
        print(f"  手机字幕: http://{lan}:{self.overlay.port}  (同一WiFi)")
        print(f"  游戏API:  http://127.0.0.1:8080")
        print(f"  轮询间隔: {POLL_INTERVAL}s, 战斗MCTS: {COMBAT_ITERATIONS}次")
        print(f"  按 Ctrl+C 停止")
        print()
        try:
            self._loop()
        except KeyboardInterrupt:
            print("\n已停止")
        finally:
            self.overlay.stop()

    def _fetch_state(self) -> Optional[dict]:
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:8080/state", timeout=3)
            snap = json.loads(req.read().decode())
            return snap.get("data", snap)
        except Exception as e:
            return None

    def _state_hash(self, state: CombatState) -> str:
        """状态哈希：手牌+能量+敌人HP，用于判断是否需要重算。"""
        hand = ",".join(sorted(c.fingerprint() for c in state.hand))
        enemies = ",".join(f"{e.name}:{e.hp}:{e.intent_damage}" for e in state.enemies)
        return f"{state.energy}|{state.player_hp}|{hand}|{enemies}"

    def _loop(self):
        while self.running:
            snap = self._fetch_state()
            if snap is None:
                self.overlay.push("连接游戏中... (http://127.0.0.1:8080)")
                time.sleep(POLL_INTERVAL)
                continue

            screen = str(snap.get("screen", "UNKNOWN")).upper()
            phase_map = {
                "COMBAT": "combat", "MAP": "map", "REWARD": "reward",
                "SHOP": "shop", "REST": "rest", "EVENT": "event",
                "CARD_SELECTION": "reward",  # 选卡阶段复用奖励逻辑
            }
            phase = phase_map.get(screen, screen.lower())

            if phase != self.prev_phase:
                print(f"[{time.strftime('%H:%M:%S')}] 阶段切换: {self.prev_phase} -> {phase}")
                # 战斗复盘日志：开始/结束
                if phase == "combat" and self.prev_phase != "combat":
                    combat_snap = snap.get("combat", snap)
                    enemies = [e.get("name", "?") for e in combat_snap.get("enemies", [])]
                    player_hp = combat_snap.get("player", {}).get("current_hp", 70)
                    floor = snap.get("run", {}).get("floor", 0)
                    self.logger.start_combat(enemies, player_hp, floor)
                elif self.prev_phase == "combat" and phase != "combat":
                    # 战斗结束，判断胜负（进入 reward 通常是胜利）
                    result = "win" if phase == "reward" else "flee"
                    combat_snap = snap.get("combat", {}) or {}
                    player_hp = combat_snap.get("player", {}).get("current_hp",
                               snap.get("run", {}).get("current_hp", 70))
                    self.logger.end_combat(result, player_hp)
                self.prev_phase = phase

            try:
                if phase == "combat":
                    self._handle_combat(snap)
                elif phase == "map":
                    self._handle_map(snap)
                elif phase == "reward":
                    self._handle_reward(snap)
                elif phase == "shop":
                    self._handle_shop(snap)
                elif phase == "rest":
                    deck = self._extract_deck(snap)
                    res = choose_rest(snap, deck)
                    self.overlay.push(format_phase_subtitle("rest", res.get("reason", "")))
                    print(f"  篝火: {res.get('reason', '')}")
                elif phase == "event":
                    self.overlay.push("【事件】\n请根据事件选项自行判断\n\n等待选择...")
                else:
                    self.overlay.push(f"当前: {phase}\n等待进入可决策阶段...")
            except Exception as e:
                self.overlay.push(f"计算出错: {e}\n继续监控...")

            time.sleep(POLL_INTERVAL)

    def _handle_combat(self, snap: dict):
        combat_snap = snap.get("combat", snap)
        state = CombatState.from_snapshot(combat_snap)
        # 传入遗物信息
        run = snap.get("run", {}) or {}
        relics = run.get("relics", []) or []
        state.relics = [r.get("relic_id", "") for r in relics if isinstance(r, dict)]

        # SL 检测
        if self.prev_state and state.turn < self.prev_state.turn:
            self.mem.on_sl()
            print("  检测到 SL，牌序记忆已重置")
        self.mem.observe_new_cards(state)
        self.prev_state = state

        # 状态哈希：只有状态变化时才重算
        h = self._state_hash(state)
        now = time.time()
        if h == self.last_combat_hash and (now - self.last_combat_calc) < COMBAT_CACHE_TIME:
            return  # 状态没变，用缓存的字幕

        # 跑 MCTS
        mcts = MCTS(default_policy=greedy_policy, seed=42)
        root = mcts.search(state, iterations=COMBAT_ITERATIONS)
        ranked = mcts.ranked_actions(root)
        best = ranked[0][0] if ranked else None
        reason = explain_combat(state, best, ranked)

        subtitle = format_combat_subtitle(state, ranked, reason, mem=self.mem)
        self.overlay.push(subtitle)

        self.last_combat_hash = h
        self.last_combat_calc = now

        # 记录决策到复盘日志
        if ranked:
            top_actions = [
                {"action": a.describe(state), "win_rate": float(wr), "visits": int(v)}
                for a, wr, v in ranked[:3]
            ]
            state_summary = {
                "player_hp": state.player_hp,
                "player_block": state.player_block,
                "energy": state.energy,
                "enemies": [
                    {"name": e.name, "hp": e.hp, "poison": e.poison,
                     "intent": e.intent_type, "intent_damage": e.intent_total_damage}
                    for e in state.enemies
                ],
            }
            self.logger.log_decision(
                turn=state.turn,
                hand=[c.name for c in state.hand],
                top_actions=top_actions,
                state_summary=state_summary,
            )

        # 控制台输出
        if ranked:
            top = ranked[0]
            print(f"  战斗 T{state.turn}: 推荐 {top[0].describe(state)} 胜率{top[1]*100:.0f}%")

    def _handle_map(self, snap: dict):
        # 传完整 snap 给路线决策器（用于血量/金币/楼层状态感知）
        options = choose_route(snap)
        if options:
            body = "\n".join(
                f"{'★' if i==0 else ' '} [{o['type']}] 分{o['score']:.1f}\n   {o['reason']}"
                for i, o in enumerate(options[:3])
            )
            self.overlay.push(format_phase_subtitle("map", body))
            print(f"  路线: {options[0]['type']} {options[0]['reason']}")
        else:
            self.overlay.push("【路线】\n等待地图节点选择...")

    def _handle_reward(self, snap: dict):
        reward_data = snap.get("reward", snap)
        deck = self._extract_deck(snap)
        res = choose_reward(reward_data, deck)
        self.overlay.push(format_phase_subtitle("reward", res.get("reason", "")))
        print(f"  奖励: {res.get('reason', '')}")

    def _handle_shop(self, snap: dict):
        shop_data = snap.get("shop", snap)
        # 把金币信息合并
        if "gold" not in shop_data and "run" in snap:
            shop_data["gold"] = snap["run"].get("gold", 0)
        deck = self._extract_deck(snap)
        res = choose_shop(shop_data, deck)
        self.overlay.push(format_phase_subtitle("shop", res.get("reason", "")))
        print(f"  商店: {res.get('reason', '')}")

    def _extract_deck(self, snap: dict) -> list[Card]:
        deck = []
        run = snap.get("run", {})
        for key in ("deck", "master_deck", "cards"):
            cards = run.get(key, []) or snap.get(key, [])
            if isinstance(cards, list):
                deck.extend(Card.from_dict(c) if isinstance(c, dict) else c for c in cards)
        return deck


if __name__ == "__main__":
    watcher = GameWatcher()
    watcher.start()
