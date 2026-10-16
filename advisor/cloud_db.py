"""
云端数据库存储模块
SQLite数据库，存储历史对局、实时状态、用户配置、自我优化数据
"""
import sqlite3
import json
import os
import time
from datetime import datetime
from typing import Optional

# 数据库路径（云端环境用 /tmp，本地用 ~/.sts2_advisor）
DB_PATH = os.environ.get(
    "STS2_DB_PATH",
    os.path.join(os.path.expanduser("~"), ".sts2_advisor", "sts2_cloud.db")
)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            user_id INTEGER DEFAULT 0,
            date TEXT,
            character TEXT,
            ascension INTEGER,
            max_floor INTEGER,
            result TEXT,
            deck_size INTEGER,
            relic_count INTEGER,
            final_hp INTEGER,
            max_hp INTEGER,
            data TEXT,
            created_at REAL
        );

        CREATE TABLE IF NOT EXISTS live_state (
            user_id INTEGER PRIMARY KEY,
            screen TEXT,
            phase TEXT,
            state_json TEXT,
            recommendation_json TEXT,
            updated_at REAL
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            run_id TEXT,
            floor INTEGER,
            phase TEXT,
            action TEXT,
            reason TEXT,
            value REAL,
            created_at REAL
        );

        CREATE TABLE IF NOT EXISTS config (
            user_id INTEGER DEFAULT 0,
            key TEXT,
            value TEXT,
            updated_at REAL,
            PRIMARY KEY (user_id, key)
        );

        CREATE TABLE IF NOT EXISTS optimizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 0,
            type TEXT,
            description TEXT,
            data TEXT,
            created_at REAL
        );

        CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id, run_id);
    """)
    conn.commit()
    conn.close()


# ============ 历史对局 ============
def save_run(run_data: dict, user_id: int = 0) -> str:
    """保存一局对局"""
    run_id = run_data.get("id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO runs
        (id, user_id, date, character, ascension, max_floor, result, deck_size, relic_count, final_hp, max_hp, data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, user_id,
        run_data.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        run_data.get("character", "静默猎手"),
        run_data.get("ascension", 0),
        run_data.get("max_floor", 0),
        run_data.get("result", "进行中"),
        len(run_data.get("deck", [])),
        len(run_data.get("relics", [])),
        run_data.get("current_hp", 0),
        run_data.get("max_hp", 70),
        json.dumps(run_data, ensure_ascii=False),
        time.time()
    ))
    conn.commit()
    conn.close()
    return run_id


def list_runs(limit: int = 50, user_id: int = 0) -> list[dict]:
    """列出历史对局"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run(run_id: str, user_id: int = 0) -> Optional[dict]:
    """获取单局详情"""
    conn = get_db()
    row = conn.execute(
        "SELECT data FROM runs WHERE id = ? AND user_id = ?", (run_id, user_id)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["data"])
    return None


def delete_run(run_id: str) -> bool:
    """删除一局对局"""
    conn = get_db()
    cur = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ============ 实时状态 ============
def update_live_state(screen: str, phase: str, state: dict, recommendation: dict,
                      user_id: int = 0):
    """更新实时状态（云端接收agent推送）"""
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO live_state (user_id, screen, phase, state_json, recommendation_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, screen, phase, json.dumps(state, ensure_ascii=False),
          json.dumps(recommendation, ensure_ascii=False), time.time()))
    conn.commit()
    conn.close()


def get_live_state(user_id: int = 0) -> Optional[dict]:
    """获取实时状态"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM live_state WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "screen": row["screen"],
            "phase": row["phase"],
            "state": json.loads(row["state_json"]),
            "recommendation": json.loads(row["recommendation_json"]),
            "updated_at": row["updated_at"],
            "age_seconds": time.time() - row["updated_at"]
        }
    return None


# ============ 决策记录 ============
def save_decision(run_id: str, floor: int, phase: str, action: str,
                  reason: str, value: float = 0, user_id: int = 0):
    """保存决策记录"""
    conn = get_db()
    conn.execute("""
        INSERT INTO decisions (user_id, run_id, floor, phase, action, reason, value, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, run_id, floor, phase, action, reason, value, time.time()))
    conn.commit()
    conn.close()


def get_decisions(run_id: str, user_id: int = 0) -> list[dict]:
    """获取一局的所有决策"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM decisions WHERE run_id = ? AND user_id = ? ORDER BY created_at",
        (run_id, user_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============ 用户配置 ============
def set_config(key: str, value, user_id: int = 0):
    """设置配置项"""
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO config (user_id, key, value, updated_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, key, json.dumps(value, ensure_ascii=False), time.time()))
    conn.commit()
    conn.close()


def get_config(key: str, default=None, user_id: int = 0):
    """获取配置项"""
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM config WHERE key = ? AND user_id = ?", (key, user_id)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default


# ============ 自我优化记录 ============
def save_optimization(opt_type: str, description: str, data: dict, user_id: int = 0):
    """保存自我优化记录"""
    conn = get_db()
    conn.execute("""
        INSERT INTO optimizations (user_id, type, description, data, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, opt_type, description, json.dumps(data, ensure_ascii=False), time.time()))
    conn.commit()
    conn.close()


def list_optimizations(limit: int = 20, user_id: int = 0) -> list[dict]:
    """列出自我优化记录"""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM optimizations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 初始化数据库
init_db()
