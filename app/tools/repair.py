"""宿舍报修工具：创建与查询报修工单（写入 SQLite）。"""
import random
import re
from datetime import datetime

from ..db import get_conn

CATEGORIES = ["水电", "门窗", "家具", "网络", "空调/暖气", "其他"]
URGENT_WORDS = ["漏水", "断电", "跳闸", "门锁", "进不去", "冒烟", "火花"]


def _norm_category(cat: str | None, desc: str) -> str:
    if cat in CATEGORIES:
        return cat
    text = (cat or "") + desc
    rules = [("水电", ["水", "电", "灯", "插座", "跳闸", "马桶", "龙头"]), ("门窗", ["门", "窗", "锁"]),
             ("家具", ["床", "桌", "椅", "柜"]), ("网络", ["网", "wifi", "WiFi", "路由"]), ("空调/暖气", ["暖气", "空调", "冷", "热"])]
    for c, kws in rules:
        if any(k in text for k in kws):
            return c
    return "其他"


def create_repair_ticket(building: str, room: str, description: str, category: str | None = None,
                         phone: str | None = None, session_id: str = "") -> dict:
    missing = [n for n, v in (("宿舍楼号", building), ("房间号", room), ("问题描述", description)) if not v]
    if missing:
        return {"ok": False, "错误": "信息不完整", "缺少": missing}
    cat = _norm_category(category, description)
    community = None
    m = re.search(r"(\d{1,2})", building or "")
    if m:
        from .navigation import dorm_community
        community = dorm_community(int(m.group(1)))
    urgent = any(w in description for w in URGENT_WORDS)
    now = datetime.now()
    ticket_no = f"BX{now.strftime('%Y%m%d%H%M%S')}{random.randint(10, 99)}"
    with get_conn() as conn:
        conn.execute("INSERT INTO repair_tickets(ticket_no, session_id, building, room, category, description, phone, urgent, created_at)"
                     " VALUES (?,?,?,?,?,?,?,?,?)",
                     (ticket_no, session_id, building, room, cat, description, phone or "", int(urgent), now.isoformat(timespec="seconds")))
    return {"ok": True, "工单号": ticket_no, "宿舍": f"{building} {room}", "所属社区": (community + "（依官方地图推断）") if community else "未知",
            "类型": cat, "紧急": urgent,
            "状态": "已提交", "预计响应": "2小时内" if urgent else "24小时内",
            "说明": "演示系统：工单仅保存在本地数据库，未对接学校后勤系统"}


def query_repair_tickets(ticket_no: str | None = None, session_id: str = "") -> dict:
    with get_conn() as conn:
        if ticket_no:
            rows = conn.execute("SELECT * FROM repair_tickets WHERE ticket_no=?", (ticket_no,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM repair_tickets WHERE session_id=? ORDER BY id DESC LIMIT 10", (session_id,)).fetchall()
    items = [{"工单号": r["ticket_no"], "宿舍": f"{r['building']} {r['room']}", "类型": r["category"], "描述": r["description"],
              "状态": r["status"], "提交时间": r["created_at"]} for r in rows]
    return {"ok": True, "工单": items, "数量": len(items)}
