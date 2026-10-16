"""
用户认证模块
注册、登录、Session管理、Steam绑定框架
"""
import sqlite3
import hashlib
import secrets
import time
import os
from typing import Optional, Dict, Any

from flask import session as flask_session

DB_PATH = os.environ.get("STS2_DB_PATH", os.path.join(os.path.expanduser("~"), ".sts2_advisor", "cloud.db"))
TOKEN_EXPIRE_SECONDS = 30 * 24 * 3600  # 30天


def init_users_db(db_path: str = None):
    """初始化用户数据库"""
    global DB_PATH
    if db_path:
        DB_PATH = db_path
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _generate_token() -> str:
    """生成登录token"""
    return secrets.token_hex(32)


def register(username: str, password: str) -> Dict[str, Any]:
    """注册新用户"""
    if len(username) < 3:
        return {"ok": False, "error": "用户名至少3个字符"}
    if len(password) < 6:
        return {"ok": False, "error": "密码至少6个字符"}

    conn = sqlite3.connect(DB_PATH)
    try:
        # 检查用户名是否存在
        existing = conn.execute("SELECT user_id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            return {"ok": False, "error": "用户名已存在"}

        token = _generate_token()
        expires = int(time.time()) + TOKEN_EXPIRE_SECONDS
        password_hash = _hash_password(password)

        conn.execute("""INSERT INTO users (username, password_hash, token, token_expires, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (username, password_hash, token, expires, int(time.time())))
        conn.commit()

        user_id = conn.execute("SELECT user_id FROM users WHERE username=?", (username,)).fetchone()[0]
        return {
            "ok": True,
            "user_id": user_id,
            "username": username,
            "token": token,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def login(username: str, password: str) -> Dict[str, Any]:
    """用户登录"""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return {"ok": False, "error": "用户名或密码错误"}

        password_hash = _hash_password(password)
        if row[2] != password_hash:  # password_hash列
            return {"ok": False, "error": "用户名或密码错误"}

        token = _generate_token()
        expires = int(time.time()) + TOKEN_EXPIRE_SECONDS
        conn.execute("UPDATE users SET token=?, token_expires=? WHERE user_id=?",
                     (token, expires, row[0]))
        conn.commit()

        return {
            "ok": True,
            "user_id": row[0],
            "username": row[1],
            "token": token,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def logout(token: str):
    """登出"""
    if not token:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET token=NULL, token_expires=NULL WHERE token=?", (token,))
    conn.commit()
    conn.close()


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证token，返回用户信息"""
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM users WHERE token=?", (token,)).fetchone()
    conn.close()

    if not row:
        return None
    if row[4] and row[4] < int(time.time()):  # token_expires
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "steam_id": row[5],
        "steam_name": row[6],
        "avatar_url": row[7],
    }


def current_user() -> Optional[Dict[str, Any]]:
    """从Flask session获取当前用户"""
    token = flask_session.get("token", "")
    if token:
        return verify_token(token)
    return None


def bind_steam(user_id: int, steam_id: str, steam_name: str, avatar_url: str = "") -> bool:
    """绑定Steam账号"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE users SET steam_id=?, steam_name=?, avatar_url=? WHERE user_id=?",
                     (steam_id, steam_name, avatar_url, user_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
