"""离线演示模式的回答生成：把工具结果组织成自然语言（大模型模式下由 LLM 生成）。"""

NOTE = "\n\n<small>（演示数据，以学校官方信息为准）</small>"


def _course_line(c: dict) -> str:
    return f"- **{c['时间']}** {c['课程']}（{c['教师']}）@ **{c['教室']}**（{c['片区']}）"


def render(tool: str, r: dict) -> str:
    if not r.get("ok", True):
        extra = f"\n可选：{'、'.join(r['可选楼宇'])}" if r.get("可选楼宇") else ""
        return f"抱歉，{r.get('错误', '查询失败')}。{extra}"
    if tool == "query_schedule":
        if "本周课表" in r:
            if not r["本周课表"]:
                return f"第{r['教学周']}周没有课程安排。"
            lines = [f"📅 **第{r['教学周']}周课表**"]
            for d, cs in r["本周课表"].items():
                lines.append(f"\n**{d}**")
                lines += [_course_line(c) for c in cs]
            return "\n".join(lines)
        if not r["课程"]:
            return f"{r['日期']}（{r.get('星期', '')}）没有课，可以好好安排自己的时间 😊" + (f"\n{r['说明']}" if r.get("说明") else "")
        lines = [f"📅 **{r['日期']} {r['星期']}**（第{r['教学周']}周）共 {len(r['课程'])} 门课："]
        lines += [_course_line(c) for c in r["课程"]]
        from .tools.navigation import distance_m, find_place
        for x, y in zip(r["课程"], r["课程"][1:]):
            a, b = find_place(x["教学楼"]), find_place(y["教学楼"])
            if a and b and distance_m(a, b) > 350:
                lines.append(f"\n💡 {x['教学楼']}→{y['教学楼']}直线约 {int(distance_m(a, b))} 米（步行估算 {int(distance_m(a, b) // 80) + 1} 分钟以上），注意预留换楼时间。")
        return "\n".join(lines)
    if tool == "next_class":
        c = r.get("下一节课")
        if not c:
            return "未来 7 天内没有课程。"
        m = c["距离上课(分钟)"]
        when = f"还有 {m} 分钟" if m < 180 else f"{c['日期']} {c['星期']}"
        return (f"⏰ 下一节课：**{c['课程']}**（{c['教师']}）\n- 时间：**{c['时间']}**（{when}）\n- 地点：**{c['教室']}**（{c['片区']}）")
    if tool == "free_classrooms":
        if not r["空闲教室"]:
            return f"{r['日期']} {r['节次']} 没有找到空闲教室，换个时间段试试？"
        rooms = "\n".join(f"- **{x['教室']}**（{x['片区']}，{x['座位数']}座）" for x in r["空闲教室"])
        return f"🏫 {r['日期']} {r['星期']} {r['节次']} 共有 {r['数量']} 间空教室：\n{rooms}"
    if tool == "locate_building":
        no = f"（地图 {r['图例编号']} 号）" if r.get("图例编号") else ""
        nb = f"\n相邻：{'、'.join(r['相邻建筑'])}" if r["相邻建筑"] else ""
        return (f"📍 **{r['名称']}**{no}：{r['类型']}，位于 **{r['片区']}**。\n{r['位置描述']}{nb}\n附近：{'、'.join(r['附近地点'])}\n"
                f"<small>坐标：{r['坐标状态']}。已在下方地图标注；告诉我从哪出发可帮你规划路线。</small>")
    if tool == "plan_route":
        if "路线" in r:
            return r["路线"]
        unsure = f"；{'、'.join(r['坐标待核实'])}坐标待核实" if r["坐标待核实"] else ""
        return (f"🚶 **{r['起点']} → {r['终点']}**：向{r['方向']}，直线约 **{r['直线距离(米)']} 米**，步行估算约 **{r['步行估算(分钟)']} 分钟**\n"
                + "\n".join(f"- {x}" for x in r["路线说明"]) + f"\n<small>（估算：按直线距离 80 米/分钟，实际路线更长{unsure}）</small>")
    if tool == "search_events":
        if not r["活动"]:
            return f"{r['时间范围']} 内没有找到符合条件的活动。"
        lines = [f"🎉 {r['时间范围']} 共找到 {r['数量']} 个活动："]
        lines += [f"- **{e['date']} {e['time']}** {e['title']} @ {e['location']}" for e in r["活动"][:8]]
        return "\n".join(lines)
    if tool == "recommend_events":
        if not r["推荐"]:
            return f"暂时没有和「{'、'.join(r['兴趣'])}」相关的近期活动。"
        lines = [f"✨ 根据你的兴趣（{'、'.join(r['兴趣'])}），推荐："]
        lines += [f"- **{e['title']}**：{e['date']} {e['time']} @ {e['location']}\n  {e['简介']}" for e in r["推荐"]]
        lines.append("需要的话我可以帮你把感兴趣的活动加入提醒。")
        return "\n".join(lines)
    if tool == "create_repair_ticket":
        if not r.get("ok"):
            return f"报修信息不完整，缺少：{'、'.join(r.get('缺少', []))}"
        urgent = "（已标记为**紧急**）" if r["紧急"] else ""
        return (f"🔧 报修已提交{urgent}\n- 工单号：**{r['工单号']}**\n- 宿舍：{r['宿舍']}（{r['所属社区']}）\n- 类型：{r['类型']}\n"
                f"- 预计响应：{r['预计响应']}\n\n可随时问我“我的报修进度”。\n<small>{r['说明']}</small>")
    if tool == "query_repair_tickets":
        if not r["工单"]:
            return "没有查到你的报修记录。"
        return "📋 你的报修记录：\n" + "\n".join(f"- {t['工单号']}｜{t['宿舍']}｜{t['类型']}｜**{t['状态']}**｜{t['提交时间']}" for t in r["工单"])
    if tool == "search_knowledge":
        hits = r["检索结果"]
        if not hits:
            return "知识库里暂时没有找到相关内容，建议咨询辅导员或相关部门。"
        top = hits[0]
        more = "".join(f"\n- 相关：{h['来源']}" for h in hits[1:2])
        return f"📚 {top['内容']}\n\n来源：《{top['来源']}》{more}"
    if tool == "add_reminder":
        return f"✅ 已添加提醒：**{r['内容']}**（时间：{r['时间']}）\n<small>{r['说明']}</small>"
    if tool == "list_reminders":
        if not r["待办"]:
            return "你目前没有待办事项。"
        return "📝 你的待办：\n" + "\n".join(f"- {x['内容']}（{x['时间']}）" for x in r["待办"])
    if tool == "canteen_info":
        return "🍚 食堂与餐厅：\n" + "\n".join(
            f"- **{c['name']}**（{c['type']}，{c['location']}）：" + "；".join(f"{k} {v}" for k, v in c["hours"].items())
            for c in r["食堂与餐厅"]) + "\n<small>名称与位置来自学校官网/官方地图；营业时间为示例数据，待核实。</small>"
    if tool == "transport_info":
        return (f"🚌 **交通出行**\n- 地址：{r['地址']}\n- 公交：{'；'.join(r['公交'])}\n- 地铁：{r['地铁']}\n- 校门：{r['校门']}\n"
                f"- {r['校园说明']}\n<small>来源：学校官网交通地图页面，出行前请以最新公交信息为准。</small>")
    return str(r)


def has_sample(results: list[dict]) -> bool:
    return any("示例" in str(r) for r in results)
