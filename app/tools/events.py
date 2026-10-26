"""活动信息聚合工具：搜索、筛选、按兴趣推荐。"""
from datetime import timedelta

from ..config import settings
from .common import DATA_NOTE, load_json, parse_day


def _events():
    return load_json("events.json")["events"]


def search_events(keyword: str | None = None, tag: str | None = None, location: str | None = None,
                  days: int = 30, start: str | None = None) -> dict:
    begin = parse_day(start) if start else settings.today()
    end = begin + timedelta(days=int(days or 30))
    out = []
    for e in _events():
        d = parse_day(e["date"])
        if not (begin <= d <= end):
            continue
        if location and location not in e["location"]:
            continue
        if tag and tag not in e["tags"]:
            continue
        if keyword:
            text = e["title"] + e["desc"] + "".join(e["tags"]) + e["location"]
            if not any(k in text for k in keyword.split()):
                continue
        out.append({k: e[k] for k in ("id", "title", "date", "time", "location", "organizer", "tags")})
    out.sort(key=lambda x: x["date"])
    return {"ok": True, "时间范围": f"{begin.isoformat()} ~ {end.isoformat()}", "活动": out, "数量": len(out), "数据说明": DATA_NOTE}


def recommend_events(interests: list[str] | str, top_k: int = 3) -> dict:
    if isinstance(interests, str):
        interests = [x for x in interests.replace("，", ",").replace("、", ",").split(",") if x.strip()]
    today = settings.today()
    scored = []
    for e in _events():
        if parse_day(e["date"]) < today:
            continue
        text = e["title"] + e["desc"]
        score = sum(2 for i in interests if i in e["tags"]) + sum(1 for i in interests if i in text)
        if score:
            scored.append((score, e))
    scored.sort(key=lambda x: (-x[0], x[1]["date"]))
    recs = [{"title": e["title"], "date": e["date"], "time": e["time"], "location": e["location"],
             "匹配度": s, "简介": e["desc"]} for s, e in scored[: int(top_k)]]
    return {"ok": True, "兴趣": interests, "推荐": recs, "数据说明": DATA_NOTE}
