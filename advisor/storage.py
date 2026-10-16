"""
历史对局存储模块
保存和读取对局数据，支持复盘分析
"""
import json
import os
import time
from datetime import datetime
from typing import Optional

# 历史对局存储目录
HISTORY_DIR = os.path.join(os.path.expanduser("~"), ".sts2_advisor", "history")
os.makedirs(HISTORY_DIR, exist_ok=True)


class RunRecorder:
    """对局记录器：记录一整局游戏的关键数据"""

    def __init__(self):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data = {
            "id": self.run_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "character": "静默猎手",
            "ascension": 0,
            "start_hp": 70,
            "max_hp": 70,
            "current_hp": 70,
            "gold": 99,
            "floor": 0,
            "max_floor": 0,
            "deck": [],
            "relics": [],
            "combats": [],
            "rewards": [],
            "shops": [],
            "events": [],
            "result": "进行中",
            "decisions": []  # 关键决策记录
        }
        self._last_combat_floor = -1

    def update_from_state(self, snap: dict):
        """从游戏状态更新对局数据"""
        d = snap.get("data", snap)
        run = d.get("run", {}) or {}

        self.data["ascension"] = run.get("ascension_level", 0)
        self.data["current_hp"] = run.get("current_hp", self.data["current_hp"])
        self.data["max_hp"] = run.get("max_hp", self.data["max_hp"])
        self.data["gold"] = run.get("gold", self.data["gold"])
        self.data["floor"] = run.get("floor", self.data["floor"])
        self.data["max_floor"] = max(self.data["max_floor"], self.data["floor"])

        # 更新牌组
        deck = run.get("deck", []) or []
        self.data["deck"] = [c.get("name", "?") for c in deck]

        # 更新遗物
        relics = run.get("relics", []) or []
        self.data["relics"] = [r.get("name", "?") if isinstance(r, dict) else str(r) for r in relics]

        # 记录战斗
        screen = d.get("screen", "")
        if screen == "COMBAT" and self.data["floor"] != self._last_combat_floor:
            combat = d.get("combat", {}) or {}
            enemies = combat.get("enemies", []) or []
            self.data["combats"].append({
                "floor": self.data["floor"],
                "enemies": [e.get("name", "?") for e in enemies],
                "enemy_hp": [e.get("max_hp", 0) for e in enemies],
                "start_hp": self.data["current_hp"],
                "result": "进行中"
            })
            self._last_combat_floor = self.data["floor"]

    def record_combat_end(self, hp_after: int, result: str = "胜利"):
        """记录战斗结束"""
        if self.data["combats"]:
            self.data["combats"][-1]["hp_after"] = hp_after
            self.data["combats"][-1]["result"] = result

    def record_decision(self, phase: str, action: str, reason: str, value: float = 0):
        """记录关键决策"""
        self.data["decisions"].append({
            "floor": self.data["floor"],
            "phase": phase,
            "action": action,
            "reason": reason,
            "value": value,
            "time": datetime.now().strftime("%H:%M:%S")
        })

    def record_reward(self, card_name: str, score: float, reason: str):
        """记录选卡决策"""
        self.data["rewards"].append({
            "floor": self.data["floor"],
            "card": card_name,
            "score": score,
            "reason": reason
        })

    def finish(self, result: str = "胜利"):
        """结束对局并保存"""
        self.data["result"] = result
        self.data["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()

    def save(self):
        """保存到文件"""
        path = os.path.join(HISTORY_DIR, f"{self.run_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def list_runs(limit: int = 50) -> list[dict]:
        """列出所有对局"""
        files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        runs = []
        for f in files[:limit]:
            try:
                with open(os.path.join(HISTORY_DIR, f), encoding="utf-8") as fp:
                    data = json.load(fp)
                    runs.append({
                        "id": data.get("id", f.replace(".json", "")),
                        "date": data.get("date", f),
                        "ascension": data.get("ascension", 0),
                        "character": data.get("character", "静默猎手"),
                        "floor": data.get("max_floor", 0),
                        "result": data.get("result", "未知"),
                        "deck_size": len(data.get("deck", [])),
                        "relics": len(data.get("relics", []))
                    })
            except Exception:
                pass
        return runs

    @staticmethod
    def load_run(run_id: str) -> Optional[dict]:
        """加载单局详情"""
        path = os.path.join(HISTORY_DIR, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
