"""
数据库模型和初始化
使用 SQLite，后续可迁移到 PostgreSQL
"""

import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "server.db")


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 激活码表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activation_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'unused' CHECK(status IN ('unused', 'used', 'expired')),
                machine_fingerprint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activated_at TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        # 激活日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                action TEXT NOT NULL,
                machine_fingerprint TEXT,
                ip_address TEXT,
                detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


# ==================== 激活码操作 ====================

def create_activation_code(code: str, valid_hours: int = 24) -> dict:
    """创建一个新的激活码"""
    expires_at = datetime.utcnow() + timedelta(hours=valid_hours)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activation_codes (code, expires_at) VALUES (?, ?)",
            (code, expires_at.isoformat())
        )
    return {"code": code, "expires_at": expires_at.isoformat(), "status": "unused"}


def get_activation_code(code: str) -> dict | None:
    """查询激活码信息"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activation_codes WHERE code = ?", (code,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def activate_code(code: str, fingerprint: str) -> dict:
    """
    激活一个激活码
    返回: {"status": "success/invalid/expired/used/fingerprint_mismatch", "message": "..."}
    """
    code_info = get_activation_code(code)

    if not code_info:
        return {"status": "invalid", "message": "激活码不存在"}

    if code_info["status"] == "used":
        # 如果已使用，检查是否是同一台机器（允许重复激活）
        if code_info["machine_fingerprint"] == fingerprint:
            return {"status": "success", "message": "激活码已绑定此设备，验证通过"}
        return {"status": "used", "message": "激活码已被其他设备使用"}

    # 检查是否过期
    expires_at = datetime.fromisoformat(code_info["expires_at"])
    if datetime.utcnow() > expires_at:
        with get_connection() as conn:
            conn.cursor().execute(
                "UPDATE activation_codes SET status = 'expired' WHERE code = ?",
                (code,)
            )
        return {"status": "expired", "message": "激活码已过期，请重新购买"}

    # 激活
    with get_connection() as conn:
        conn.cursor().execute(
            """UPDATE activation_codes 
               SET status = 'used', machine_fingerprint = ?, activated_at = ? 
               WHERE code = ?""",
            (fingerprint, datetime.utcnow().isoformat(), code)
        )

    return {"status": "success", "message": "激活成功"}


def log_activation(code: str, action: str, fingerprint: str = None,
                   ip_address: str = None, detail: str = None):
    """记录激活日志"""
    with get_connection() as conn:
        conn.cursor().execute(
            """INSERT INTO activation_logs (code, action, machine_fingerprint, ip_address, detail)
               VALUES (?, ?, ?, ?, ?)""",
            (code, action, fingerprint, ip_address, detail)
        )

