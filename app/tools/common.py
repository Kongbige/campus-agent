import json
from functools import lru_cache
from datetime import date, timedelta

from ..config import DATA_DIR, settings

WEEKDAY_CN = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
DATA_NOTE = "（示例数据，仅供演示）"


@lru_cache(maxsize=None)
def load_json(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def parse_day(day: str | None, today: date | None = None) -> date:
    """把“今天/明天/后天/周三/2026-11-16”等解析为日期。"""
    today = today or settings.today()
    if not day:
        return today
    d = str(day).strip()
    rel = {"今天": 0, "今日": 0, "明天": 1, "明日": 1, "后天": 2, "大后天": 3, "昨天": -1}
    if d in rel:
        return today + timedelta(days=rel[d])
    try:
        return date.fromisoformat(d)
    except ValueError:
        pass
    cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}
    next_week = "下" in d
    for prefix in ("下周", "下星期", "周", "星期", "礼拜"):
        if d.startswith(prefix) and len(d) > len(prefix):
            ch = d[len(prefix)]
            if ch in cn:
                target = cn[ch]
                monday = today - timedelta(days=today.weekday())
                if next_week:
                    monday += timedelta(days=7)
                return monday + timedelta(days=target - 1)
    return today
