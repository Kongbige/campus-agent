"""离线演示模式：基于规则/关键词的任务规划器。

无需大模型密钥即可运行。它模拟智能体的「意图识别 → 任务规划 → 槽位追问 → 工具调用 → 结果组织」流程，
调用与大模型模式完全相同的工具，便于评审在无网络/无密钥时也能看到智能体架构。
"""
import re
from typing import Any, Callable

from .tools.navigation import all_building_names, all_place_names, find_place

DAY_RE = re.compile(r"(大后天|后天|明天|明日|今天|今日|昨天|下(?:周|星期)[一二三四五六日天1-7]|(?:周|星期|礼拜)[一二三四五六日天1-7]|\d{4}-\d{2}-\d{2})")
PERIOD_RE = re.compile(r"第?\s*(\d{1,2})\s*[-到至~]\s*(\d{1,2})\s*节|第\s*(\d{1,2})\s*节")
DORM_RE = re.compile(r"(\d{1,2})\s*(?:号)?(?:公寓|宿舍楼|号楼|栋|舍)")
ROOM_RE = re.compile(r"(?<![\d.:-])(\d{3,4})(?:室|房间|寝室|宿舍)?(?![\d:号])")
TIME_RE = re.compile(r"((?:今天|明天|后天|下?周[一二三四五六日天]|\d{1,2}月\d{1,2}[日号])?\s*(?:早上|上午|中午|下午|晚上)?\s*\d{1,2}(?:[:：点]\d{0,2}分?|点半?)?)")

INTEREST_WORDS = ["AI", "人工智能", "编程", "竞赛", "讲座", "体育", "篮球", "考研", "学习", "文艺", "音乐", "就业", "招聘",
                  "志愿", "公益", "读书", "晚会"]
TAG_MAP = {"人工智能": "AI", "大模型": "AI", "比赛": "竞赛", "宣讲": "讲座", "找工作": "就业", "唱歌": "音乐", "球": "体育"}
OUT_OF_SCOPE = ["代考", "替考", "写作业", "写论文", "病毒", "木马", "黑进", "破解", "炒股", "股票", "彩票", "赌", "翻墙"]
EMERGENCY = ["着火", "火灾", "冒烟", "触电", "受伤", "晕倒"]


def _has(text: str, words) -> bool:
    return any(w in text for w in words)


def extract_day(text: str) -> str | None:
    m = DAY_RE.search(text)
    return m.group(1) if m else None


def extract_buildings(text: str) -> list[str]:
    """按出现顺序提取地点名（楼宇、食堂、图书馆、宿舍社区等，含简称），重叠时取最长匹配。"""
    spans = []
    for name in all_place_names():
        p = find_place(name)
        keys = {name, name.replace("社区", "")} | {a for a in p["aliases"] if a}
        for k in keys:
            i = text.find(k)
            if i >= 0:
                spans.append((i, -len(k), name))
    spans.sort()
    taken, out = [], []
    for i, neg, name in spans:
        j = i - neg
        if any(not (j <= a or i >= b) for a, b in taken):
            continue
        taken.append((i, j))
        if name not in out:
            out.append(name)
    return out


def extract_periods(text: str) -> str | None:
    m = PERIOD_RE.search(text)
    if m:
        if m.group(1):
            return f"{m.group(1)}-{m.group(2)}"
        return f"{m.group(3)}-{m.group(3)}"
    if "上午" in text:
        return "1-4"
    if "下午" in text:
        return "5-8"
    if "晚上" in text:
        return "9-10"
    return None


def extract_dorm(text: str) -> tuple[str | None, str | None]:
    b = DORM_RE.search(text)
    if b:
        raw = b.group(0).replace(" ", "")
        num = b.group(1)
        if "号楼" in raw or (raw.endswith("楼") and "宿舍楼" not in raw):
            building = f"{num}号楼"
        elif "宿舍楼" in raw:
            building = f"{num}号公寓"
        elif raw.endswith("栋"):
            building = f"{num}栋"
        elif raw.endswith("舍") and "宿舍" not in raw:
            building = f"{num}舍"
        else:
            building = f"{num}号公寓"
    else:
        building = None
    rest = text[b.end():] if b else text
    r = ROOM_RE.search(rest) or ROOM_RE.search(text)
    room = r.group(1) if r else None
    if b and room == b.group(1):
        room = None
    return building, room


def extract_interests(text: str) -> list[str]:
    out = [w for w in INTEREST_WORDS if w in text]
    out += [v for k, v in TAG_MAP.items() if k in text]
    return list(dict.fromkeys(out))


Step = dict[str, Any]  # {"tool": str, "args": dict | Callable[[list], dict], "reason": str}


class Plan:
    def __init__(self) -> None:
        self.steps: list[Step] = []
        self.thoughts: list[str] = []
        self.direct_reply: str | None = None
        self.intent: str | None = None

    def add(self, tool: str, args: dict | Callable, reason: str) -> None:
        self.steps.append({"tool": tool, "args": args, "reason": reason})


def plan(message: str, state: dict) -> Plan:
    """根据用户消息与会话状态生成执行计划。state 会被就地更新（多轮槽位/上下文）。"""
    text = message.strip()
    p = Plan()

    if _has(text, OUT_OF_SCOPE):
        p.thoughts.append("识别为超出校园服务范围/不当请求 → 礼貌拒绝并引导")
        p.direct_reply = ("抱歉，这个请求超出了我的服务范围（我不能协助代考、写作业、违规操作或投资类问题）。\n"
                          "我可以帮你：查课表/空教室、校园导航、活动推荐、宿舍报修、办事指南问答、设置提醒、查食堂和校车。")
        p.intent = "out_of_scope"
        return p

    emergency = _has(text, EMERGENCY)
    if emergency:
        p.thoughts.append("检测到可能的紧急情况 → 优先给出安全提示")

    # ---------- 多轮：报修槽位补全 ----------
    pending = state.get("pending")
    if pending and pending.get("intent") == "repair" and not _has(text, ["算了", "取消", "不用了"]):
        b, r = extract_dorm(text)
        slots = pending["slots"]
        if b and not slots.get("building"):
            slots["building"] = b
        if r and not slots.get("room"):
            slots["room"] = r
        m = re.search(r"1[3-9]\d{9}", text)
        if m:
            slots["phone"] = m.group(0)
        if slots.get("building") and slots.get("room"):
            state.pop("pending", None)
            state["dorm"] = {"building": slots["building"], "room": slots["room"]}
            p.thoughts.append(f"多轮补全：从上文获取故障描述，从本轮获取宿舍 {slots['building']} {slots['room']} → 提交工单")
            p.add("create_repair_ticket", dict(slots), "槽位已齐全，提交报修")
            p.intent = "repair"
            return p
        need = "宿舍楼号" if not slots.get("building") else "房间号"
        p.thoughts.append(f"报修信息仍缺少：{need} → 继续追问")
        p.direct_reply = f"还差一点信息：请告诉我**{need}**（例如“12号公寓 302”）。"
        p.intent = "repair_ask"
        return p
    if pending and _has(text, ["算了", "取消", "不用了"]):
        state.pop("pending", None)
        p.direct_reply = "好的，已取消本次报修。还有什么可以帮你？"
        return p

    # ---------- 追问省略：“那明天呢 / 周三呢” ----------
    last = state.get("last")
    day = extract_day(text)
    if last and len(text) <= 12 and re.search(r"^(那|那么)?.{0,8}(呢|吗)[？?]?$", text) and (day or extract_buildings(text)):
        args = dict(last["args"])
        if day and "day" in args:
            args["day"] = day
        bs = extract_buildings(text)
        if bs:
            for k in ("building", "destination", "name"):
                if k in args:
                    args[k] = bs[0]
        p.thoughts.append(f"识别为省略追问，沿用上一轮意图「{last['tool']}」，更新参数 {args}")
        p.add(last["tool"], args, "沿用上文意图")
        p.intent = last["tool"]
        return p

    if re.fullmatch(r"(你好|您好|hi|hello|嗨|在吗|你是谁|你能做什么|帮助|help)[!！。？?]*", text, re.I):
        p.direct_reply = ("你好！我是**城院小助手**，你的校园服务智能体 👋\n"
                          "你可以问我：\n- 明天有什么课？下节课在哪？\n- 周一3-4节建工楼有空教室吗？\n- 从建工楼到医科楼怎么走？\n"
                          "- 最近有什么AI相关的活动？\n- 宿舍水龙头坏了要报修\n- 校园卡丢了怎么办？\n- 提醒我明天下午2点去西山会所开会")
        p.thoughts.append("问候/帮助类消息，无需调用工具")
        p.intent = "greeting"
        return p

    # ---------- 多意图识别（一句话可触发多个工具，体现自主规划） ----------
    bs = extract_buildings(text)
    sched_dep = False  # 路线终点是否依赖课表结果

    # 1. 报修查询 / 报修
    if _has(text, ["工单", "报修进度", "报修状态", "修好了吗", "报修记录", "我的报修"]):
        m = re.search(r"BX\d+", text)
        p.add("query_repair_tickets", {"ticket_no": m.group(0)} if m else {}, "查询报修工单")
    elif _has(text, ["报修", "坏了", "坏掉", "漏水", "不亮", "堵了", "没网", "断网", "网断", "断电", "跳闸", "暖气不热", "打不开", "修一下", "修一修", "没法上网", "上不了网"]):
        b, r = extract_dorm(text)
        dorm = state.get("dorm", {})
        slots = {"building": b or dorm.get("building"), "room": r or dorm.get("room"), "description": text}
        m = re.search(r"1[3-9]\d{9}", text)
        if m:
            slots["phone"] = m.group(0)
        if slots["building"] and slots["room"]:
            state["dorm"] = {"building": slots["building"], "room": slots["room"]}
            p.add("create_repair_ticket", slots, "信息齐全，提交报修工单")
        else:
            state["pending"] = {"intent": "repair", "slots": slots}
            need = [n for n, k in (("宿舍楼号", "building"), ("房间号", "room")) if not slots[k]]
            p.thoughts.append(f"识别报修意图，但缺少必填信息：{'、'.join(need)} → 追问用户（多轮槽位填充）")
            tip = "⚠️ 如有冒烟、漏电等危险，请先远离并立即联系宿管或拨打 119！\n" if emergency else ""
            p.direct_reply = f"{tip}收到，我来帮你报修。请告诉我**{'和'.join(need)}**（例如“12号公寓 302”）。"
            p.intent = "repair_ask"
            return p

    # 2. 提醒
    if _has(text, ["我的提醒", "待办列表", "有哪些待办", "有什么待办", "查看提醒"]):
        p.add("list_reminders", {}, "列出待办")
    elif _has(text, ["提醒我", "提醒一下", "记得", "别忘", "加个待办", "添加待办", "设个提醒", "设置提醒"]):
        content = re.sub(r"^(请|帮我|麻烦)?(提醒我|提醒一下|设个提醒|设置提醒|加个待办|添加待办|记得|别忘了?)[，,：:]?", "", text).strip("。！ ")
        t = TIME_RE.search(content)
        remind_at = t.group(1).strip() if t and re.search(r"\d", t.group(1)) else (extract_day(content) or None)
        p.add("add_reminder", {"content": content or text, "remind_at": remind_at}, "添加提醒")

    # 3. 空教室
    if _has(text, ["空教室", "自习室", "空闲教室", "找个教室", "上自习", "去自习"]):
        p.add("free_classrooms", {"day": day or "今天", "periods": extract_periods(text),
                                  "building": bs[0] if bs else None}, "查询空闲教室")

    # 4. 课表 / 下节课
    elif _has(text, ["下一节", "下节课", "接下来的课", "下一门课"]):
        p.add("next_class", {}, "查询下一节课")
        sched_dep = True
    elif _has(text, ["课表", "有课", "什么课", "几节课", "哪些课", "上课", "第一节课", "满课", "没课", "的课", "课吗", "课程"]):
        week = _has(text, ["这周", "本周", "下周", "一周", "这星期"]) and not re.search(r"周[一二三四五六日天]", text.replace("下周", ""))
        p.add("query_schedule", {"day": day or ("下周一" if "下周" in text else "今天"), "scope": "week" if week else "day"}, "查询课表")
        sched_dep = "第一节" in text or "在哪" in text

    # 5. 导航
    route_words = ["怎么走", "怎么去", "怎么过去", "路线", "导航", "多远", "带我去", "到达", "过去"]
    if _has(text, route_words) or re.search(r"从.+到.+", text):
        if len(bs) >= 2:
            p.add("plan_route", {"origin": bs[0], "destination": bs[1]}, "规划楼宇间路线")
        elif len(bs) == 1 and sched_dep:
            origin = bs[0]

            def _dest(results, origin=origin):
                r = results[-1]
                c = r.get("下一节课") or (r.get("课程") or [None])[0]
                return {"origin": origin, "destination": c["教学楼"] if c else origin}
            p.thoughts.append("路线终点依赖上一步课表结果 → 先查课，再用结果中的教学楼作为终点")
            p.add("plan_route", _dest, "以课程所在楼为终点规划路线")
        elif len(bs) == 1:
            origin = state.get("location")
            if origin and origin != bs[0]:
                p.add("plan_route", {"origin": origin, "destination": bs[0]}, f"起点沿用上文位置「{origin}」")
            else:
                p.add("locate_building", {"name": bs[0]}, "未给出起点，先介绍目的地位置")
                p.thoughts.append("未提供起点，返回目的地位置并建议用户补充起点")
        elif not p.steps:
            p.direct_reply = f"请告诉我起点和终点，例如“从建工楼到南楼怎么走”。可识别的地点包括：{'、'.join(all_place_names()[:20])} 等。"
            return p
    elif bs and _has(text, ["在哪", "在哪里", "位置", "在什么地方", "哪个校区", "哪个片区", "是干什么", "是什么地方", "介绍", "在地图上"]) and not p.steps:
        p.add("locate_building", {"name": bs[0]}, "查询楼宇位置")
    if bs and _has(text, ["我在", "我现在在"]):
        state["location"] = bs[0]

    # 6. 交通 / 食堂
    if _has(text, ["校车", "班车", "公交", "地铁", "怎么来学校", "怎么到学校", "学校地址", "学校在哪", "坐车", "交通"]):
        p.add("transport_info", {}, "查询交通出行信息")
    canteen_places = [b for b in bs if "食堂" in find_place(b)["type"] or "餐" in find_place(b)["type"] or "咖啡" in find_place(b)["type"]]
    if _has(text, ["食堂", "吃饭", "饭点", "早餐", "早饭", "午饭", "中饭", "晚饭", "夜宵", "餐厅", "开饭", "营业", "早饭几点", "早饭到"]) or (canteen_places and _has(text, ["几点", "吃", "开门"])):
        if not any(s["tool"] in ("plan_route", "locate_building") for s in p.steps):
            p.add("canteen_info", {"name": canteen_places[0] if canteen_places else None}, "查询食堂信息")

    reminding = any(s["tool"] == "add_reminder" for s in p.steps)  # 提醒内容中的词不再触发其他意图

    # 7. 活动
    interests = extract_interests(text)
    if not reminding and _has(text, ["推荐", "感兴趣", "我喜欢", "适合我"]) and (interests or _has(text, ["活动"])):
        if not interests and state.get("interests"):
            interests = state["interests"]
        if interests:
            state["interests"] = interests
            p.add("recommend_events", {"interests": interests}, "按兴趣推荐活动")
        else:
            p.add("search_events", {"days": 30}, "未提供兴趣，列出近期全部活动")
    elif not reminding and _has(text, ["活动", "讲座", "比赛", "竞赛", "宣讲", "招聘", "双选会", "志愿", "晚会", "社团"]) and not _has(text, ["场地借用", "借场地"]):
        tag = None
        for t in ["竞赛", "讲座", "体育", "就业", "志愿", "文艺", "AI", "编程", "考研"]:
            if t in interests or t in text:
                tag = t
                break
        days = 7 if _has(text, ["这周", "本周", "最近一周"]) else 30
        kw = "招聘" if "招聘" in text or "双选会" in text else None
        p.add("search_events", {"tag": None if kw else tag, "keyword": kw, "days": days}, "搜索近期活动")

    # 8. 知识库：规章流程类
    kb_words = ["图书馆", "借书", "借阅", "续借", "借几本", "能借", "座位", "选课", "退课", "补选", "重修", "校园卡", "饭卡", "挂失", "补办", "充值",
                "门禁", "晚归", "锁门", "关门", "大功率", "电器", "暖气", "奖学金", "助学金", "请假", "销假", "场地借用", "借场地", "研讨室", "怎么办", "流程", "规定"]
    navigating = any(s["tool"] in ("locate_building", "plan_route") for s in p.steps)  # 问位置时不再检索规章
    if not reminding and not navigating and _has(text, kb_words) and not any(s["tool"] in ("create_repair_ticket",) for s in p.steps):
        p.add("search_knowledge", {"query": text}, "检索校园知识库")

    if not p.steps and p.direct_reply is None:
        if bs:
            p.add("locate_building", {"name": bs[0]}, "查询楼宇信息")
        elif re.search(r"[？?吗么]|怎么|如何|哪", text):
            p.add("search_knowledge", {"query": text}, "未匹配到专用工具，尝试知识库检索")
        else:
            p.direct_reply = ("我还不太确定你的需求 🤔 可以试试这样问：\n- 明天有什么课？\n- 从建工楼到医科楼怎么走？\n"
                              "- 推荐几个编程相关的活动\n- 8号楼 215 暖气不热，帮我报修")

    if len(p.steps) > 1:
        p.thoughts.insert(0, f"识别到 {len(p.steps)} 个子任务，按顺序执行：" + " → ".join(s["reason"] for s in p.steps))
    elif p.steps:
        p.thoughts.insert(0, f"意图：{p.steps[0]['reason']}")
    if emergency:
        state["emergency"] = True
    p.intent = p.steps[0]["tool"] if p.steps else p.intent
    return p
