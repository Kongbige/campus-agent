from app.tools import execute_tool, tool_schemas
from app.tools.common import parse_day
import json

from app.config import DATA_DIR
from app.tools.navigation import all_building_names, all_place_names, dorm_community, find_place

REAL_BUILDINGS = {"建工楼", "医工楼", "机电楼", "经管楼", "西山会所", "绿岛俱乐部", "传媒楼", "南楼", "医科楼"}


def test_schemas_valid():
    names = [t["function"]["name"] for t in tool_schemas()]
    assert len(names) >= 6 and len(set(names)) == len(names)
    for t in tool_schemas():
        assert t["function"]["parameters"]["type"] == "object"


def test_only_real_building_names():
    assert set(all_building_names()) == REAL_BUILDINGS
    legend = {x["name"] for x in json.loads((DATA_DIR / "map" / "legend.json").read_text(encoding="utf-8"))}
    official_extra = {"芙蓉餐厅", "百荷咖啡", "百荷园餐厅", "凤凰餐厅"}  # 来自学校官网餐厅页面
    assert set(all_place_names()) <= legend | official_extra


def test_canteens_confirmed():
    for n in ("西山会所", "绿岛俱乐部"):
        assert "食堂" in find_place(n)["type"]
    assert find_place("图书馆")["name"] == "水晶宫"
    assert dorm_community(12) == "玫瑰园社区"


def test_parse_day():
    assert parse_day("明天").isoformat() == "2026-11-03"
    assert parse_day("周五").isoformat() == "2026-11-06"
    assert parse_day("下周一").isoformat() == "2026-11-09"


def test_schedule():
    r = execute_tool("query_schedule", {"day": "2026-11-02"})
    assert r["教学周"] == 9 and r["课程"][0]["课程"] == "数据结构"
    w = execute_tool("query_schedule", {"day": "今天", "scope": "week"})
    assert len(w["本周课表"]) == 5


def test_free_classrooms():
    r = execute_tool("free_classrooms", {"day": "2026-11-02", "periods": "1-2", "building": "建工楼"})
    rooms = [x["教室"] for x in r["空闲教室"]]
    assert "建工楼-203" not in rooms and "建工楼-101" in rooms


def test_route_and_map_markers():
    r = execute_tool("plan_route", {"origin": "建工楼", "destination": "南楼"})
    assert r["ok"] and r["方向"] == "东南" and 600 < r["直线距离(米)"] < 750
    assert r["地图标注"][0]["px"] == [803, 680] and "估算" in r["数据说明"]
    r2 = execute_tool("plan_route", {"origin": "建工", "destination": "传媒楼"})
    assert r2["步行估算(分钟)"] <= 2
    r3 = execute_tool("plan_route", {"origin": "医工楼", "destination": "西山会所"})
    assert "医工楼" in r3["坐标待核实"]
    assert execute_tool("plan_route", {"origin": "火星楼", "destination": "南楼"})["ok"] is False
    assert execute_tool("transport_info", {})["地址"].startswith("沈阳市苏家屯区")


def test_events():
    r = execute_tool("search_events", {"tag": "竞赛"})
    assert all("竞赛" in e["tags"] for e in r["活动"]) and r["数量"] >= 1
    rec = execute_tool("recommend_events", {"interests": ["AI", "编程"]})
    assert rec["推荐"] and rec["推荐"][0]["匹配度"] >= 2


def test_repair_sqlite():
    r = execute_tool("create_repair_ticket", {"building": "5号楼", "room": "302", "description": "水管漏水"}, "t1")
    assert r["ok"] and r["紧急"] and r["类型"] == "水电"
    q = execute_tool("query_repair_tickets", {}, "t1")
    assert q["工单"][0]["工单号"] == r["工单号"]
    bad = execute_tool("create_repair_ticket", {"building": "5号楼", "description": "坏了"}, "t1")
    assert bad["ok"] is False


def test_knowledge_bm25():
    r = execute_tool("search_knowledge", {"query": "校园卡丢了怎么补办"})
    assert "校园卡" in r["检索结果"][0]["来源"]


def test_reminder():
    r = execute_tool("add_reminder", {"content": "交作业", "remind_at": "明天下午3点"}, "t2")
    assert r["ok"] and r["时间"].startswith("2026-11-03")
    assert execute_tool("list_reminders", {}, "t2")["待办"][0]["内容"] == "交作业"


def test_bad_tool():
    assert execute_tool("nope", {})["ok"] is False
    assert execute_tool("plan_route", "not json")["ok"] is False
