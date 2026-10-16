"""字幕推荐模块：把决策推荐以"字幕"形式实时显示。

两种输出形态：
1. **Overlay 浮窗**（tkinter，Python 标准库）：无边框、置顶、半透明、可拖拽，
   放在游戏画面角落，像游戏内字幕一样显示推荐与理由。
2. **OBS 文本文件**（可选）：持续把最新推荐写入一个 .txt，供 OBS/直播软件
   作为"文字源"读取，实现直播字幕。

无图形环境（无 DISPLAY / 未装 python3-tk）时自动降级为终端轮播打印。

用法（独立脚本）：
    python3 scripts/run_subtitle.py --port 8765 --iterations 600
    python3 scripts/run_subtitle.py --obs-file obs_subtitle.txt
"""

from __future__ import annotations

import os
import queue
import threading
import time
from typing import Optional

from .drawmemory import DrawOrderMemory, diff_new_cards
from .explanation import explain_combat
from .model import CombatState
from .simulator import is_terminal


# ============================================================================
# 浮窗（tkinter）
# ============================================================================

class SubtitleOverlay:
    """置顶半透明无边框浮窗。后台线程通过 update() 投递文本，主线程刷新。"""

    def __init__(self, title: str = "STS2 决策字幕", alpha: float = 0.88,
                 font_size: int = 13, width: int = 380):
        self.title = title
        self.alpha = alpha
        self.font_size = font_size
        self.width = width
        self._q: "queue.Queue[str]" = queue.Queue()
        self._drag = {"x": 0, "y": 0}
        self.gui_available = False
        self.root = None

    def _build(self) -> bool:
        try:
            import tkinter as tk  # 标准库，但部分环境缺 python3-tk
        except Exception:
            return False
        try:
            self.root = tk.Tk()
        except Exception:
            return False
        self.gui_available = True
        r = self.root
        r.title(self.title)
        r.overrideredirect(True)          # 无边框
        r.attributes("-topmost", True)    # 置顶
        try:
            r.attributes("-alpha", self.alpha)
        except Exception:
            pass
        r.configure(bg="#0f1626")

        frame = tk.Frame(r, bg="#0f1626")
        frame.pack(fill="both", expand=True)

        # 标题栏（拖拽区 + 关闭按钮）
        bar = tk.Frame(frame, bg="#1a2744")
        bar.pack(fill="x")
        self.header = tk.Label(bar, text="  " + self.title, font=("Arial", 10, "bold"),
                               bg="#1a2744", fg="#5ec8e6", anchor="w")
        self.header.pack(side="left", fill="x", expand=True)
        close_btn = tk.Label(bar, text="× ", font=("Arial", 12, "bold"),
                             bg="#1a2744", fg="#e94560", cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self._quit())

        self.body = tk.Label(frame, text="等待游戏状态...", justify="left", anchor="nw",
                             font=("Arial", self.font_size), bg="#0f1626", fg="#e8ecf1",
                             padx=10, pady=8, wraplength=self.width - 20)
        self.body.pack(fill="both", expand=True)

        # 拖拽
        for w in (bar, self.header, self.body, frame):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        r.geometry(f"{self.width}+60+60")
        self._poll()
        return True

    def _start_drag(self, e):
        self._drag["x"] = e.x
        self._drag["y"] = e.y

    def _on_drag(self, e):
        if self.root is None:
            return
        x = self.root.winfo_x() + e.x - self._drag["x"]
        y = self.root.winfo_y() + e.y - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    def _poll(self):
        try:
            while True:
                text = self._q.get_nowait()
                self.body.config(text=text)
        except queue.Empty:
            pass
        if self.root is not None:
            self.root.after(150, self._poll)

    def _quit(self):
        if self.root is not None:
            self.root.destroy()
            self.root = None

    def update(self, text: str):
        """后台线程安全地更新字幕文本。"""
        self._q.put(text)

    def run(self):
        """阻塞运行浮窗主循环。无 GUI 时立即返回 False。"""
        if not self._build():
            return False
        self.root.mainloop()
        return True


# ============================================================================
# 字幕文本格式化
# ============================================================================

def format_combat_subtitle(state: CombatState, ranked: list) -> str:
    if not ranked:
        return f"⚔ 战斗 · 回合{state.turn}\n（无可行动作）"
    best, best_avg, _ = ranked[0]
    reason = explain_combat(state, best, ranked)
    lines = [f"⚔ 战斗 · 回合{state.turn} · HP{state.player_hp}/{state.max_hp} · 能量{state.energy}"]
    lines.append(f"推荐：{best.describe(state)}")
    lines.append(f"理由：{reason}")
    lines.append("─" * 24)
    for i, (a, avg, v) in enumerate(ranked[:3], 1):
        lines.append(f"[{i}] {a.describe(state)}  {avg*100:.1f}%")
    return "\n".join(lines)


def format_route_subtitle(options: list) -> str:
    if not options:
        return "🗺 路线\n（无可用节点）"
    o = options[0]
    node = o.get("node", {})
    lines = ["🗺 地图路线"]
    lines.append(f"推荐：到 ({node.get('col','?')},{node.get('row','?')}) "
                 f"{node.get('type','?')}  分{o.get('score',0):.1f}")
    if o.get("reason"):
        lines.append(f"理由：{o['reason']}")
    lines.append("─" * 24)
    for i, o in enumerate(options[1:4], 2):
        n = o.get("node", {})
        lines.append(f"[{i}] ({n.get('col','?')},{n.get('row','?')}) {n.get('type','?')}  {o.get('score',0):.1f}")
    return "\n".join(lines)


def format_reward_subtitle(result: dict) -> str:
    lines = ["🎁 战斗奖励"]
    cards = result.get("cards", [])
    if cards:
        best = cards[0]
        lines.append(f"推荐：{best.get('name','?')}  分{best.get('score',0):.1f}")
        if best.get("reasons"):
            lines.append(f"理由：{'；'.join(best['reasons'][:2])}")
    if result.get("gold", 0) > 0:
        lines.append(f"金币：{result['gold']}")
    lines.append("─" * 24)
    for i, c in enumerate(cards[:3], 1):
        lines.append(f"[{i}] {c.get('name','?')}  分{c.get('score',0):.1f}")
    if result.get("reason"):
        lines.append("")
        lines.append(result["reason"])
    return "\n".join(lines)


def format_shop_subtitle(result: dict) -> str:
    lines = [f"🏪 商店 · 金币{result.get('gold',0)}"]
    if result.get("recommendation"):
        lines.append(f"推荐：{result['recommendation']}")
    if result.get("reason"):
        lines.append(f"理由：{result['reason']}")
    purchases = result.get("purchases", [])
    if purchases:
        lines.append("─" * 24)
        for i, p in enumerate(purchases[:4], 1):
            lines.append(f"[{i}] {p}")
    return "\n".join(lines)


# ============================================================================
# 后台轮询 worker
# ============================================================================

def subtitle_worker(overlay: SubtitleOverlay, client, iterations: int = 600,
                    obs_file: Optional[str] = None, interval: float = 2.0,
                    stop_event: Optional[threading.Event] = None):
    """后台线程：轮询 autoSpire 状态 → 计算推荐 → 更新字幕。"""
    from .cli import recommend_combat
    from .route import choose_route
    from .reward import choose_reward
    from .shop import choose_shop

    stop = stop_event or threading.Event()
    mem = DrawOrderMemory()
    prev_state: Optional[CombatState] = None

    def emit(text: str):
        overlay.update(text)
        if obs_file:
            try:
                with open(obs_file, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass

    while not stop.is_set():
        try:
            snap = client.get_state()
        except Exception as e:
            emit(f"⚠ 连接 autoSpire 失败\n{e}\n重试中...")
            time.sleep(interval)
            continue

        phase = snap.get("phase", "menu")
        try:
            if phase == "combat":
                state = CombatState.from_snapshot(snap)
                if prev_state is None:
                    mem.on_new_combat()
                elif state.turn < prev_state.turn:
                    mem.on_sl()
                new_cards = diff_new_cards(prev_state.hand, state.hand) if prev_state else []
                if new_cards:
                    mem.observe_new_cards(new_cards)
                prev_state = state

                if is_terminal(state):
                    emit(f"⚔ 战斗结束\n{'胜利' if state.player_hp > 0 else '失败'}")
                else:
                    mcts, root = recommend_combat(state, iterations, mem)
                    ranked = mcts.ranked_actions(root)
                    emit(format_combat_subtitle(state, ranked))

            elif phase == "map":
                emit(format_route_subtitle(choose_route(snap)))

            elif phase == "reward":
                deck = _deck_from_snap_safe(snap)
                emit(format_reward_subtitle(choose_reward(snap, deck)))

            elif phase == "shop":
                deck = _deck_from_snap_safe(snap)
                emit(format_shop_subtitle(choose_shop(snap, deck)))

            else:
                emit(f"⏳ 当前阶段：{phase}\n等待进入可决策阶段...")
        except Exception as e:
            emit(f"⚠ 决策出错\n{type(e).__name__}: {e}")

        time.sleep(interval)


def _deck_from_snap_safe(snap) -> list:
    try:
        from .cli import _deck_from_snap
        return _deck_from_snap(snap)
    except Exception:
        return []
