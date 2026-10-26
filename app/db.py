"""SQLite 存储：报修工单、提醒待办。"""
import sqlite3
import threading
from contextlib import contextmanager

from .config import settings

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS repair_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_no TEXT UNIQUE,
    session_id TEXT,
    building TEXT,
    room TEXT,
    category TEXT,
    description TEXT,
    phone TEXT,
    urgent INTEGER DEFAULT 0,
    status TEXT DEFAULT '已提交',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    content TEXT,
    remind_at TEXT,
    done INTEGER DEFAULT 0,
    created_at TEXT
);
"""


@contextmanager
def get_conn():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(settings.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(SCHEMA)
            yield conn
            conn.commit()
        finally:
            conn.close()
