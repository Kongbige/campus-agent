"""提醒/待办工具。"""
from datetime import datetime

import re

from ..db import get_conn
from .common import parse_day

DAY_WORDS = r"(大后天|后天|明天|今天|下?周[一二三四五六日天])"


def normalize_time(t: str | None) -> str:
    """把“明天下午2点”中的相对日期换算为具体日期，如“2026-11-03 下午2点”。"""
    if not t:
        return ""
    m = re.search(DAY_WORDS, t)
    if m:
        t = t.replace(m.group(1), parse_day(m.group(1)).isoformat() + " ", 1)
    return re.sub(r"\s+", " ", t).strip()


def add_reminder(content: str, remind_at: str | None = None, session_id: str = "") -> dict:
    if not content:
        return {"ok": False, "错误": "提醒内容不能为空"}
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO reminders(session_id, content, remind_at, created_at) VALUES (?,?,?,?)",
                           (session_id, content, normalize_time(remind_at), datetime.now().isoformat(timespec="seconds")))
        rid = cur.lastrowid
    return {"ok": True, "提醒ID": rid, "内容": content, "时间": normalize_time(remind_at) or "未指定", "说明": "已加入待办（演示系统，网页内展示，不发送推送）"}


def list_reminders(session_id: str = "") -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM reminders WHERE session_id=? AND done=0 ORDER BY id", (session_id,)).fetchall()
    return {"ok": True, "待办": [{"ID": r["id"], "内容": r["content"], "时间": r["remind_at"] or "未指定"} for r in rows]}
