"""智慧课表工具：按天/周查询课表、下一节课、空教室。"""
from datetime import date, datetime, timedelta

from ..config import settings
from .common import DATA_NOTE, WEEKDAY_CN, load_json, parse_day
from .navigation import find_place


def zone_of(building: str) -> str:
    p = find_place(building)
    return p["zone"] if p else ""


def _semester():
    return load_json("schedule.json")


def week_of(d: date) -> int:
    start = date.fromisoformat(_semester()["semester"]["start_date"])
    return (d - start).days // 7 + 1


def _period_time(p: int) -> tuple[str, str]:
    return tuple(_semester()["periods"][str(p)])


def _fmt_course(c: dict) -> dict:
    s, _ = _period_time(c["periods"][0])
    _, e = _period_time(c["periods"][-1])
    return {
        "课程": c["name"], "教师": c["teacher"], "节次": f"第{c['periods'][0]}-{c['periods'][-1]}节",
        "时间": f"{s}-{e}", "片区": zone_of(c["building"]), "教学楼": c["building"], "教室": c["room"],
    }


def courses_on(d: date) -> list[dict]:
    w = week_of(d)
    wd = d.isoweekday()
    items = [c for c in _semester()["courses"] if c["weekday"] == wd and c["weeks"][0] <= w <= c["weeks"][1]]
    return sorted(items, key=lambda c: c["periods"][0])


def query_schedule(day: str = "今天", scope: str = "day") -> dict:
    """查询某天或某周课表。scope: day | week"""
    d = parse_day(day)
    w = week_of(d)
    total = _semester()["semester"]["total_weeks"]
    if w < 1 or w > total:
        return {"ok": True, "日期": d.isoformat(), "说明": f"该日期不在教学周内（第{w}周）", "课程": [], "数据说明": DATA_NOTE}
    if scope == "week":
        monday = d - timedelta(days=d.weekday())
        week = {}
        for i in range(7):
            dd = monday + timedelta(days=i)
            cs = courses_on(dd)
            if cs:
                week[f"{WEEKDAY_CN[dd.isoweekday()]}({dd.isoformat()})"] = [_fmt_course(c) for c in cs]
        return {"ok": True, "教学周": w, "本周课表": week, "数据说明": DATA_NOTE}
    cs = courses_on(d)
    return {"ok": True, "日期": d.isoformat(), "星期": WEEKDAY_CN[d.isoweekday()], "教学周": w,
            "课程": [_fmt_course(c) for c in cs], "数据说明": DATA_NOTE}


def next_class(now: str | None = None) -> dict:
    """查询下一节课（从当前时间起，最多向后找 7 天）。"""
    if now:
        cur = datetime.fromisoformat(now)
    else:
        t = datetime.now()
        cur = datetime.combine(settings.today(), t.time())
    for i in range(8):
        d = cur.date() + timedelta(days=i)
        for c in courses_on(d):
            s, _ = _period_time(c["periods"][0])
            start = datetime.combine(d, datetime.strptime(s, "%H:%M").time())
            if start >= cur:
                mins = int((start - cur).total_seconds() // 60)
                info = _fmt_course(c)
                info.update({"日期": d.isoformat(), "星期": WEEKDAY_CN[d.isoweekday()], "距离上课(分钟)": mins})
                return {"ok": True, "下一节课": info, "数据说明": DATA_NOTE}
    return {"ok": True, "下一节课": None, "说明": "未来 7 天内没有课程", "数据说明": DATA_NOTE}


def _parse_periods(periods) -> list[int]:
    if not periods:
        return []
    if isinstance(periods, list):
        return [int(p) for p in periods]
    txt = str(periods).replace("节", "").replace("第", "")
    if "-" in txt:
        a, b = txt.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in txt.replace("，", ",").split(",") if x.strip().isdigit()]


def free_classrooms(day: str = "今天", periods=None, building: str | None = None, zone: str | None = None) -> dict:
    """查询空闲教室。periods 如 "3-4" 或 [3,4]；可按教学楼/片区过滤。"""
    d = parse_day(day)
    wd = d.isoweekday()
    ps = _parse_periods(periods) or [1, 2, 3, 4, 5, 6, 7, 8]
    result = []
    for r in load_json("classrooms.json")["rooms"]:
        if building and building not in r["building"]:
            continue
        if zone and zone not in zone_of(r["building"]):
            continue
        busy = set()
        for owd, ops in r["occupied"]:
            if owd == wd:
                busy.update(ops)
        if not busy.intersection(ps):
            result.append({"教室": r["room"], "教学楼": r["building"], "片区": zone_of(r["building"]), "座位数": r["seats"]})
    return {"ok": True, "日期": d.isoformat(), "星期": WEEKDAY_CN[wd], "节次": f"第{ps[0]}-{ps[-1]}节",
            "空闲教室": result, "数量": len(result), "数据说明": DATA_NOTE}
