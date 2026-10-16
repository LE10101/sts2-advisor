"""
云端SQLite数据库模块
存储历史对局、实时状态、配置、优化记录
支持多用户隔离 + GitHub持久化（防止云端重启丢失数据）
"""
import sqlite3
import json
import os
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.environ.get("STS2_DB_PATH", os.path.join(os.path.expanduser("~"), ".sts2_advisor", "cloud.db"))

# GitHub持久化（可选，配置环境变量后启用）
try:
    from advisor.github_storage import get_github_storage
    _github = get_github_storage()
except Exception:
    _github = None


def get_conn():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        token TEXT,
        token_expires INTEGER,
        steam_id TEXT,
        steam_name TEXT,
        avatar_url TEXT,
        created_at INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        user_id INTEGER DEFAULT 0,
        date TEXT,
        character TEXT,
        ascension INTEGER,
        max_floor INTEGER,
        current_hp INTEGER,
        max_hp INTEGER,
        gold INTEGER,
        result TEXT,
        deck TEXT,
        relics TEXT,
        combats TEXT,
        decisions TEXT,
        map_path TEXT,
        seed TEXT,
        created_at INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS live_state (
        user_id INTEGER PRIMARY KEY,
        screen TEXT,
        phase TEXT,
        state TEXT,
        recommendation TEXT,
        updated_at INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 0,
        run_id TEXT,
        floor INTEGER,
        phase TEXT,
        action TEXT,
        reason TEXT,
        value REAL,
        created_at INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS optimizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 0,
        type TEXT,
        description TEXT,
        data TEXT,
        created_at INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id, run_id)")

    conn.commit()
    conn.close()


# 初始化
init_db()


def save_run(data: dict, user_id: int = 0) -> str:
    """保存对局数据（同时保存到GitHub持久化）"""
    conn = get_conn()
    run_id = data.get("id", f"run_{int(time.time())}")
    now = int(time.time())

    conn.execute("""INSERT OR REPLACE INTO runs
        (id, user_id, date, character, ascension, max_floor, current_hp, max_hp, gold, result, deck, relics, combats, decisions, map_path, seed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, user_id,
         data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
         data.get("character", "静默猎手"),
         data.get("ascension", 0),
         data.get("max_floor", 0),
         data.get("current_hp", 70),
         data.get("max_hp", 70),
         data.get("gold", 99),
         data.get("result", "进行中"),
         json.dumps(data.get("deck", []), ensure_ascii=False),
         json.dumps(data.get("relics", []), ensure_ascii=False),
         json.dumps(data.get("combats", []), ensure_ascii=False),
         json.dumps(data.get("decisions", []), ensure_ascii=False),
         json.dumps(data.get("map_path", []), ensure_ascii=False),
         data.get("seed", ""),
         now))
    conn.commit()
    conn.close()

    # 同时保存到GitHub（异步不阻塞）
    if _github and _github.enabled:
        try:
            full_data = dict(data)
            full_data["id"] = run_id
            _github.save_run(full_data, user_id)
        except Exception as e:
            print(f"[cloud_db] GitHub保存失败: {e}")

    return run_id


def get_run(run_id: str, user_id: int = 0) -> Optional[dict]:
    """获取对局详情"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM runs WHERE id=? AND user_id=?", (run_id, user_id)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "date": row["date"],
        "character": row["character"],
        "ascension": row["ascension"],
        "max_floor": row["max_floor"],
        "current_hp": row["current_hp"],
        "max_hp": row["max_hp"],
        "gold": row["gold"],
        "result": row["result"],
        "deck": json.loads(row["deck"] or "[]"),
        "relics": json.loads(row["relics"] or "[]"),
        "combats": json.loads(row["combats"] or "[]"),
        "decisions": json.loads(row["decisions"] or "[]"),
        "map_path": json.loads(row["map_path"] or "[]"),
        "seed": row["seed"],
    }


def list_runs(limit: int = 50, user_id: int = 0) -> List[dict]:
    """列出对局列表（数据库为空时自动从GitHub同步）"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()

    # 如果数据库为空且GitHub可用，从GitHub同步
    if not rows and _github and _github.enabled:
        print(f"[cloud_db] 数据库为空，从GitHub同步用户{user_id}的对局...")
        try:
            github_runs = _github.list_runs(user_id)
            for run_summary in github_runs:
                run_data = _github.load_run(run_summary["id"], user_id)
                if run_data:
                    # 直接保存到数据库（不递归保存到GitHub）
                    conn = get_conn()
                    conn.execute("""INSERT OR REPLACE INTO runs
                        (id, user_id, date, character, ascension, max_floor, current_hp, max_hp, gold, result, deck, relics, combats, decisions, map_path, seed, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (run_data.get("id"), user_id,
                         run_data.get("date", ""),
                         run_data.get("character", "静默猎手"),
                         run_data.get("ascension", 0),
                         run_data.get("max_floor", 0),
                         run_data.get("current_hp", 70),
                         run_data.get("max_hp", 70),
                         run_data.get("gold", 99),
                         run_data.get("result", ""),
                         json.dumps(run_data.get("deck", []), ensure_ascii=False),
                         json.dumps(run_data.get("relics", []), ensure_ascii=False),
                         json.dumps(run_data.get("combats", []), ensure_ascii=False),
                         json.dumps(run_data.get("decisions", []), ensure_ascii=False),
                         json.dumps(run_data.get("map_path", []), ensure_ascii=False),
                         run_data.get("seed", ""),
                         int(time.time())))
                    conn.commit()
                    conn.close()
            # 重新查询
            conn = get_conn()
            rows = conn.execute(
                "SELECT * FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            conn.close()
        except Exception as e:
            print(f"[cloud_db] GitHub同步失败: {e}")

    return [{
        "id": r["id"],
        "date": r["date"],
        "character": r["character"],
        "ascension": r["ascension"],
        "floor": r["max_floor"],
        "result": r["result"],
        "deck_size": len(json.loads(r["deck"] or "[]")),
        "relics": len(json.loads(r["relics"] or "[]")),
    } for r in rows]


def update_live_state(screen: str, phase: str, state: dict, recommendation: dict, user_id: int = 0):
    """更新实时状态"""
    conn = get_conn()
    now = int(time.time())
    conn.execute("""INSERT OR REPLACE INTO live_state (user_id, screen, phase, state, recommendation, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, screen, phase, json.dumps(state, ensure_ascii=False),
         json.dumps(recommendation, ensure_ascii=False), now))
    conn.commit()
    conn.close()


def get_live_state(user_id: int = 0) -> Optional[dict]:
    """获取实时状态"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM live_state WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    now = int(time.time())
    return {
        "screen": row["screen"],
        "phase": row["phase"],
        "state": json.loads(row["state"] or "{}"),
        "recommendation": json.loads(row["recommendation"] or "{}"),
        "updated_at": row["updated_at"],
        "age_seconds": now - row["updated_at"],
    }


def save_decision(run_id: str, floor: int, phase: str, action: str, reason: str, value: float, user_id: int = 0):
    """保存决策记录"""
    conn = get_conn()
    conn.execute("""INSERT INTO decisions (user_id, run_id, floor, phase, action, reason, value, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, run_id, floor, phase, action, reason, value, int(time.time())))
    conn.commit()
    conn.close()


def save_optimization(opt_type: str, description: str, data: dict, user_id: int = 0):
    """保存优化记录"""
    conn = get_conn()
    conn.execute("""INSERT INTO optimizations (user_id, type, description, data, created_at)
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, opt_type, description, json.dumps(data, ensure_ascii=False), int(time.time())))
    conn.commit()
    conn.close()


def list_optimizations(limit: int = 20, user_id: int = 0) -> List[dict]:
    """列出优化记录"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM optimizations WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [{
        "type": r["type"],
        "description": r["description"],
        "data": json.loads(r["data"] or "{}"),
        "created_at": r["created_at"],
    } for r in rows]
