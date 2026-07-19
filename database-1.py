"""
Хранилище настроек персонажа для каждого пользователя.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "companion_bot.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personas (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                age TEXT,
                gender TEXT,
                personality TEXT,
                voice TEXT,
                avatar_file_id TEXT,
                setup_complete INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at REAL
            )
        """)
        conn.commit()


def get_persona(user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT name, age, gender, personality, voice, avatar_file_id, setup_complete "
            "FROM personas WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    keys = ["name", "age", "gender", "personality", "voice", "avatar_file_id", "setup_complete"]
    return dict(zip(keys, row))


def upsert_persona(user_id: int, **fields):
    existing = get_persona(user_id)
    with get_conn() as conn:
        if existing is None:
            conn.execute(
                "INSERT INTO personas (user_id) VALUES (?)", (user_id,)
            )
        for key, value in fields.items():
            conn.execute(
                f"UPDATE personas SET {key} = ? WHERE user_id = ?", (value, user_id)
            )
        conn.commit()


def save_message(user_id: int, role: str, content: str):
    import time
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, time.time()),
        )
        conn.commit()


def get_recent_history(user_id: int, limit: int = 12):
    """Последние N сообщений диалога для контекста (не бесконечно растим промпт)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]
