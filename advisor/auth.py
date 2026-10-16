"""
用户认证模块
支持用户名密码注册登录，Steam账号绑定
"""
import hashlib
import secrets
import sqlite3
import time
from typing import Optional
from flask import session

# 数据库路径
DB_PATH = "/tmp/sts2_cloud.db"  # 会被cloud_db覆盖


def _hash_password(password: str, salt: str = "") -> str:
    """密码哈希"""
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """验证密码"""
    try:
        salt, hash_val = stored.split("$", 1)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return secrets.compare_digest(h.hex(), hash_val)
    except:
        return False


def init_users_db(db_path: str = None):
    """初始化用户表"""
    global DB_PATH
    if db_path:
        DB_PATH = db_path
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            steam_id TEXT,
            steam_name TEXT,
            avatar_url TEXT,
            created_at REAL,
            last_login REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at REAL,
            expires_at REAL
        )
    """)
    conn.commit()
    conn.close()


def register(username: str, password: str) -> dict:
    """注册新用户"""
    if len(username) < 3:
        return {"ok": False, "error": "用户名至少3个字符"}
    if len(password) < 6:
        return {"ok": False, "error": "密码至少6个字符"}

    conn = sqlite3.connect(DB_PATH)
    try:
        # 检查用户名是否存在
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return {"ok": False, "error": "用户名已存在"}

        # 创建用户
        password_hash = _hash_password(password)
        now = time.time()
        cur = conn.execute("""
            INSERT INTO users (username, password_hash, created_at, last_login)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, now, now))
        user_id = cur.lastrowid
        conn.commit()

        # 创建session
        token = secrets.token_hex(32)
        conn.execute("""
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, now, now + 86400 * 30))  # 30天有效
        conn.commit()

        return {"ok": True, "user_id": user_id, "username": username, "token": token}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def login(username: str, password: str) -> dict:
    """用户登录"""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": "用户名或密码错误"}

        user_id, uname, password_hash = row
        if not _verify_password(password, password_hash):
            return {"ok": False, "error": "用户名或密码错误"}

        # 更新登录时间
        now = time.time()
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))

        # 创建session
        token = secrets.token_hex(32)
        conn.execute("""
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, now, now + 86400 * 30))
        conn.commit()

        return {"ok": True, "user_id": user_id, "username": uname, "token": token}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def verify_token(token: str) -> Optional[dict]:
    """验证token，返回用户信息"""
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("""
            SELECT u.id, u.username, u.steam_id, u.steam_name, u.avatar_url, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,)).fetchone()
        if not row:
            return None
        if row[5] < time.time():
            # token过期
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "steam_id": row[2],
            "steam_name": row[3],
            "avatar_url": row[4]
        }
    finally:
        conn.close()


def get_user(user_id: int) -> Optional[dict]:
    """获取用户信息"""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT id, username, steam_id, steam_name, avatar_url, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "steam_id": row[2],
            "steam_name": row[3],
            "avatar_url": row[4],
            "created_at": row[5]
        }
    finally:
        conn.close()


def bind_steam(user_id: int, steam_id: str, steam_name: str, avatar_url: str = "") -> bool:
    """绑定Steam账号"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            UPDATE users SET steam_id = ?, steam_name = ?, avatar_url = ?
            WHERE id = ?
        """, (steam_id, steam_name, avatar_url, user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def logout(token: str):
    """登出，删除session"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# Flask session辅助函数
def current_user() -> Optional[dict]:
    """从Flask session获取当前用户"""
    token = session.get("token", "")
    return verify_token(token)


def require_auth(f):
    """装饰器：要求登录"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user:
            return {"error": "需要登录"}, 401
        return f(*args, **kwargs)
    return decorated
