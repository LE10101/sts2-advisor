"""游戏内悬浮字幕：始终置顶的半透明窗口，实时显示推荐与理由。

autoSpire 只提供 HTTP 接口、没有 UI 注入能力，所以用一个独立的 tkinter 置顶窗
覆盖在游戏画面上方，作为"字幕"层。Linux 桌面（X11/XWayland）原生支持 topmost。

线程模型（重要）：
    tkinter/Tk 必须在主线程创建并运行 mainloop，否则 X11 会多线程断言崩溃。
    因此 SubtitleOverlay 由调用方在主线程创建并调用 run()；决策循环放后台线程，
    通过线程安全队列 push() 更新字幕。

用法（CLI 已封装）：
    ov = SubtitleOverlay()          # 主线程创建
    threading.Thread(target=decision_loop, args=(ov,), daemon=True).start()
    ov.run()                        # 主线程阻塞，跑 tkinter mainloop

tkinter 不可用时自动降级（available=False，push 静默）。
"""

from __future__ import annotations

import queue
import sys
from typing import Optional

# Linux X11 下多线程触碰 Tk 必须先初始化 X11 线程安全，否则 XCB 断言崩溃。
# 必须在 import tkinter 之前调用。
if sys.platform.startswith("linux"):
    try:
        import ctypes
        for _lib in ("libX11.so.6", "libX11.so"):
            try:
                ctypes.CDLL(_lib).XInitThreads()
                break
            except Exception:
                continue
    except Exception:
        pass

try:
    import tkinter as tk
    _HAS_TK = True
except Exception:  # pragma: no cover
    _HAS_TK = False

_CLOSE_SENTINEL = "__CLOSE__"


class SubtitleOverlay:
    """置顶半透明悬浮字幕窗。必须在主线程创建并 run()。"""

    def __init__(self, title: str = "STS2 推荐字幕", x: int = 40, y: int = 40,
                 width: int = 440, alpha: float = 0.88, font_size: int = 14):
        self._q: "queue.Queue[str]" = queue.Queue()
        self._root = None
        self._label = None
        self._closed = False
        self._title = title
        self._x, self._y = x, y
        self._width = width
        self._alpha = alpha
        self._font_size = font_size
        self._drag_offset = (0, 0)
        if _HAS_TK:
            try:
                self._build()
            except Exception:
                self._root = None

    @property
    def available(self) -> bool:
        return _HAS_TK and self._root is not None

    def _build(self):
        self._root = tk.Tk()
        self._root.title(self._title)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", self._alpha)
        self._root.overrideredirect(True)
        self._root.geometry(f"+{self._x}+{self._y}")
        self._root.configure(bg="#101018")

        frame = tk.Frame(self._root, bg="#101018", bd=0)
        frame.pack(fill="both", expand=True)

        bar = tk.Frame(frame, bg="#1f1f2e", height=22)
        bar.pack(fill="x")
        tk.Label(bar, text="  STS2 推荐字幕（拖动移动）", bg="#1f1f2e",
                 fg="#8a8aa8", font=("Sans", 9)).pack(side="left")
        bar.bind("<ButtonPress-1>", self._on_press)
        bar.bind("<B1-Motion>", self._on_drag)

        self._label = tk.Label(
            frame, text="等待游戏状态...", fg="#f0f0ff", bg="#101018",
            font=("Sans", self._font_size), justify="left", anchor="nw",
            padx=12, pady=8, wraplength=self._width - 24,
        )
        self._label.pack(fill="both", expand=True)
        self._label.bind("<ButtonPress-1>", self._on_press)
        self._label.bind("<B1-Motion>", self._on_drag)
        self._poll()

    def _poll(self):
        if self._closed or self._root is None:
            return
        try:
            while True:
                text = self._q.get_nowait()
                if text == _CLOSE_SENTINEL:
                    self._closed = True
                    self._root.destroy()
                    return
                if self._label is not None:
                    self._label.config(text=text)
        except queue.Empty:
            pass
        self._root.after(120, self._poll)

    def _on_press(self, event):
        self._drag_offset = (event.x, event.y)

    def _on_drag(self, event):
        if self._root is None:
            return
        x = self._root.winfo_x() + event.x - self._drag_offset[0]
        y = self._root.winfo_y() + event.y - self._drag_offset[1]
        self._root.geometry(f"+{x}+{y}")

    def push(self, text: str) -> None:
        """推送新的字幕内容（线程安全，可从后台决策线程调用）。"""
        if not self.available:
            return
        self._q.put(text)

    def run(self) -> None:
        """阻塞运行 tkinter mainloop。必须在创建窗口的主线程调用。"""
        if self._root is not None:
            self._root.mainloop()

    def close(self) -> None:
        """线程安全关闭：只往队列放哨兵，由主线程 _poll 执行 destroy。"""
        self._q.put(_CLOSE_SENTINEL)


def format_combat_subtitle(state, ranked, reason: str, top_n: int = 3) -> str:
    """把战斗推荐格式化成字幕文本。"""
    lines = ["【战斗】MCTS 推荐"]
    for i, (action, avg, visits) in enumerate(ranked[:top_n]):
        mark = "★" if i == 0 else " "
        lines.append(f"{mark}[{i}] {action.describe(state)}  {avg*100:.0f}%")
    if reason:
        lines.append("")
        lines.append(f"理由: {reason}")
    return "\n".join(lines)


def format_phase_subtitle(phase: str, body: str) -> str:
    """非战斗阶段字幕。"""
    label = {"map": "【路线】", "reward": "【奖励】", "shop": "【商店】",
             "rest": "【篝火】", "event": "【事件】"}.get(phase, f"【{phase}】")
    return f"{label}\n{body}"
