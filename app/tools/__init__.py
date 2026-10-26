"""工具注册表：统一的 OpenAI function-calling schema + 执行入口。"""
import inspect
import json
from typing import Any, Callable

from . import events, knowledge, life, navigation, reminder, repair, schedule


def _fn(name: str, desc: str, props: dict, required: list[str] | None = None) -> dict:
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required or []}}}


S = {"type": "string"}
TOOLS: dict[str, tuple[Callable, dict, str]] = {
    "query_schedule": (schedule.query_schedule, _fn(
        "query_schedule", "查询学生某天或某一周的课表。",
        {"day": {**S, "description": "日期：今天/明天/后天/周一…周日/下周三/YYYY-MM-DD，默认今天"},
         "scope": {"type": "string", "enum": ["day", "week"], "description": "day=单日，week=整周"}}), "课表查询"),
    "next_class": (schedule.next_class, _fn("next_class", "查询从现在起的下一节课（时间、地点、教师）。", {}), "下一节课"),
    "free_classrooms": (schedule.free_classrooms, _fn(
        "free_classrooms", "查询某天某些节次的空闲教室，可按教学楼或校区过滤，适合找自习室。",
        {"day": {**S, "description": "日期，默认今天"}, "periods": {**S, "description": "节次范围，如 \"3-4\"；不填为全天 1-8 节"},
         "building": {**S, "description": "教学楼名，如 建工楼"}, "zone": {**S, "description": "片区：北校区/西校区/南校区"}}), "空教室"),
    "locate_building": (navigation.locate_building, _fn(
        "locate_building", "查询校园内某个地点（教学楼、食堂、图书馆水晶宫、宿舍社区、体育馆、校门等）的位置、所在片区、相邻建筑，并在官方地图上标注。",
        {"name": {**S, "description": "地点名，如 建工楼、西山会所、水晶宫、玫瑰园、校园大门"}}, ["name"]), "楼宇定位"),
    "plan_route": (navigation.plan_route, _fn(
        "plan_route", "规划校园内两个地点之间的步行路线：方向、直线距离、步行估算时间、沿途参照地标，并在地图上标注起终点。",
        {"origin": {**S, "description": "起点地点，如 建工楼、金菊园"}, "destination": {**S, "description": "终点地点"}}, ["origin", "destination"]), "路线规划"),
    "search_events": (events.search_events, _fn(
        "search_events", "搜索/筛选未来的校园活动（讲座、竞赛、文体、招聘、志愿等）。",
        {"keyword": {**S, "description": "关键词，空格分隔"}, "tag": {**S, "description": "标签，如 竞赛/AI/讲座/体育/就业/志愿/文艺"},
         "location": {**S, "description": "地点关键词，如 绿岛讲堂"}, "days": {"type": "integer", "description": "未来多少天内，默认30"}}), "活动搜索"),
    "recommend_events": (events.recommend_events, _fn(
        "recommend_events", "根据用户兴趣推荐即将举办的活动。",
        {"interests": {"type": "array", "items": S, "description": "兴趣标签列表，如 [\"AI\",\"编程\"]"},
         "top_k": {"type": "integer", "description": "推荐数量，默认3"}}, ["interests"]), "活动推荐"),
    "create_repair_ticket": (repair.create_repair_ticket, _fn(
        "create_repair_ticket", "提交宿舍报修工单。必须已获得宿舍楼号（公寓号）、房间号和问题描述，缺少时先向用户追问，不要编造。",
        {"building": {**S, "description": "宿舍楼号，如 12号公寓"}, "room": {**S, "description": "房间号，如 302"},
         "description": {**S, "description": "故障描述"}, "category": {"type": "string", "enum": repair.CATEGORIES},
         "phone": {**S, "description": "联系电话，可选"}}, ["building", "room", "description"]), "宿舍报修"),
    "query_repair_tickets": (repair.query_repair_tickets, _fn(
        "query_repair_tickets", "查询报修工单进度；不填工单号则返回当前用户最近的工单。",
        {"ticket_no": {**S, "description": "工单号，如 BX2026..."}}), "报修查询"),
    "search_knowledge": (knowledge.search_knowledge, _fn(
        "search_knowledge", "检索校园知识库（图书馆、选课、校园卡、宿舍管理、奖助学金、请假、楼宇场馆等办事指南），回答政策流程类问题时必须先检索。",
        {"query": {**S, "description": "检索问题"}, "top_k": {"type": "integer", "description": "返回条数，默认3"}}, ["query"]), "知识库检索"),
    "add_reminder": (reminder.add_reminder, _fn(
        "add_reminder", "为用户添加提醒/待办事项。",
        {"content": {**S, "description": "提醒内容"}, "remind_at": {**S, "description": "提醒时间，如 2026-11-04 13:30 或 明天早上8点"}}, ["content"]), "添加提醒"),
    "list_reminders": (reminder.list_reminders, _fn("list_reminders", "列出用户未完成的提醒/待办。", {}), "待办列表"),
    "canteen_info": (life.canteen_info, _fn(
        "canteen_info", "查询食堂/餐厅（绿岛俱乐部、西山会所、芙蓉餐厅、百荷园餐厅、凤凰餐厅等）的位置与营业时间。",
        {"name": {**S, "description": "食堂名，可选"}, "zone": {**S, "description": "片区，可选"}}), "食堂信息"),
    "transport_info": (life.transport_info, _fn(
        "transport_info", "查询学校地址与公共交通到校方式（公交、地铁换乘）、校门位置。", {}), "交通出行"),
}

SESSION_AWARE = {"create_repair_ticket", "query_repair_tickets", "add_reminder", "list_reminders"}


def tool_schemas() -> list[dict]:
    return [t[1] for t in TOOLS.values()]


def tool_label(name: str) -> str:
    return TOOLS[name][2] if name in TOOLS else name


def execute_tool(name: str, args: dict | str | None, session_id: str = "") -> dict[str, Any]:
    if name not in TOOLS:
        return {"ok": False, "错误": f"未知工具 {name}"}
    if isinstance(args, str):
        try:
            args = json.loads(args or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "错误": "参数不是合法 JSON"}
    args = dict(args or {})
    fn = TOOLS[name][0]
    allowed = set(inspect.signature(fn).parameters)
    clean = {k: v for k, v in args.items() if k in allowed and v not in (None, "")}
    if name in SESSION_AWARE:
        clean["session_id"] = session_id
    try:
        return fn(**clean)
    except TypeError as e:
        return {"ok": False, "错误": f"参数错误：{e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "错误": f"工具执行失败：{e}"}
