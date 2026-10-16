"""
历史对局存储模块
记录每局游戏的完整数据，用于复盘分析
"""
import json
import os
import time
from datetime import datetime
from typing import Optional


class RunRecorder:
    """对局记录器 - 记录单局完整数据"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), ".sts2_advisor", "runs")
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.current_run = None

    def start_run(self, character: str = "静默猎手", ascension: int = 0, seed: str = ""):
        """开始新对局"""
        self.current_run = {
            "id": f"run_{int(time.time())}",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "character": character,
            "ascension": ascension,
            "seed": seed,
            "max_floor": 0,
            "current_hp": 70,
            "max_hp": 70,
            "gold": 99,
            "deck": ["打击", "打击", "打击", "打击", "打击", "防御", "防御", "防御", "防御", "生存者"],
            "relics": [],
            "result": "进行中",
            "combats": [],
            "decisions": [],
            "map_path": [],
        }
        return self.current_run["id"]

    def update_state(self, state: dict):
        """更新对局状态"""
        if not self.current_run:
            return
        if "floor" in state:
            self.current_run["max_floor"] = max(self.current_run["max_floor"], state["floor"])
        if "player_hp" in state:
            self.current_run["current_hp"] = state["player_hp"]
        if "max_hp" in state:
            self.current_run["max_hp"] = state["max_hp"]
        if "gold" in state:
            self.current_run["gold"] = state["gold"]
        if "deck" in state:
            self.current_run["deck"] = state["deck"]
        if "relics" in state:
            self.current_run["relics"] = state["relics"]

    def add_combat(self, combat: dict):
        """记录一场战斗"""
        if self.current_run:
            self.current_run["combats"].append(combat)

    def add_decision(self, floor: int, phase: str, action: str, reason: str, value: float):
        """记录一个决策"""
        if self.current_run:
            self.current_run["decisions"].append({
                "floor": floor, "phase": phase, "action": action,
                "reason": reason, "value": value,
                "time": datetime.now().strftime("%H:%M:%S")
            })

    def end_run(self, result: str = "胜利"):
        """结束对局并保存"""
        if not self.current_run:
            return
        self.current_run["result"] = result
        self.save()
        run_id = self.current_run["id"]
        self.current_run = None
        return run_id

    def save(self):
        """保存当前对局到文件"""
        if not self.current_run:
            return
        filepath = os.path.join(self.log_dir, f"{self.current_run['id']}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.current_run, f, ensure_ascii=False, indent=2)

    def load(self, run_id: str) -> Optional[dict]:
        """加载对局记录"""
        filepath = os.path.join(self.log_dir, f"{run_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_runs(self, limit: int = 50) -> list:
        """列出所有对局"""
        runs = []
        if not os.path.exists(self.log_dir):
            return runs
        files = sorted(os.listdir(self.log_dir), reverse=True)
        for f in files[:limit]:
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.log_dir, f), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        runs.append({
                            "id": data.get("id", f.replace(".json", "")),
                            "date": data.get("date", ""),
                            "character": data.get("character", ""),
                            "ascension": data.get("ascension", 0),
                            "floor": data.get("max_floor", 0),
                            "result": data.get("result", ""),
                            "deck_size": len(data.get("deck", [])),
                            "relics": len(data.get("relics", [])),
                        })
                except Exception:
                    pass
        return runs
