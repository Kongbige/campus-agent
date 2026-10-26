"""校园导航工具：地点定位、楼宇间步行路线（基于官方鸟瞰图 + OSM 坐标，步行时间为估算）。"""
import math

from .common import load_json

EST_NOTE = "步行时间按直线距离、80米/分钟估算，实际路线更长；标注“待核实”的坐标为地图换算估算"
DIRS = ["东", "东北", "北", "西北", "西", "西南", "南", "东南"]


def _map() -> dict:
    return load_json("campus_map.json")


def places() -> list[dict]:
    return _map()["places"]


def all_building_names() -> list[str]:
    """9 栋核心楼宇（真实楼名）。"""
    return [p["name"] for p in places() if p["is_core_building"]]


def all_place_names() -> list[str]:
    return [p["name"] for p in places()]


def find_place(name: str) -> dict | None:
    if not name:
        return None
    name = name.strip()
    for p in places():
        if name == p["name"] or name in p["aliases"]:
            return p
    for p in places():  # 去掉“社区”等后缀的模糊匹配
        if p["name"] in name or (len(name) >= 2 and name in p["name"]):
            return p
    for p in places():
        if any(a and a in name for a in p["aliases"]):
            return p
    return None


find_building = find_place  # 兼容旧名称


def _xy(p: dict, ref_lat: float) -> tuple[float, float]:
    return p["lng"] * 111320 * math.cos(math.radians(ref_lat)), p["lat"] * 110540


def distance_m(a: dict, b: dict) -> float:
    ref = (a["lat"] + b["lat"]) / 2
    (x1, y1), (x2, y2) = _xy(a, ref), _xy(b, ref)
    return math.hypot(x2 - x1, y2 - y1)


def direction(a: dict, b: dict) -> str:
    ref = (a["lat"] + b["lat"]) / 2
    (x1, y1), (x2, y2) = _xy(a, ref), _xy(b, ref)
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360
    return DIRS[int(((ang + 22.5) % 360) // 45)]


def _marker(p: dict, role: str) -> dict:
    return {"name": p["name"], "px": p["map_px"], "role": role, "legend_no": p.get("legend_no")}


def _seg_dist(p: dict, a: dict, b: dict) -> float:
    ref = a["lat"]
    (px, py), (ax, ay), (bx, by) = _xy(p, ref), _xy(a, ref), _xy(b, ref)
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def locate_building(name: str) -> dict:
    p = find_place(name)
    if not p:
        return {"ok": False, "错误": f"地图中未找到“{name}”", "可选地点": all_place_names()}
    others = [x for x in places() if x["name"] != p["name"] and x["map_px"] != p["map_px"]]
    near = sorted(others, key=lambda x: distance_m(p, x))[:4]
    res = {"ok": True, "名称": p["name"], "图例编号": p["legend_no"], "类型": p["type"], "片区": p["zone"],
           "片区依据": {"official": "学校官网", "inferred": "依地图推断", "map": "依地图位置"}.get(p["zone_source"], ""),
           "位置描述": p["area"] or f"位于{p['zone']}", "相邻建筑": p["neighbors"],
           "附近地点": [f"{x['name']}（{direction(p, x)}侧约{int(distance_m(p, x))}米）" for x in near],
           "坐标": [p["lat"], p["lng"]], "坐标状态": p["coord_status"], "地图标注": [_marker(p, "目的地")],
           "数据说明": "地点来自学校官方鸟瞰图图例；距离为直线估算"}
    return res


def plan_route(origin: str, destination: str) -> dict:
    a, b = find_place(origin), find_place(destination)
    if not a or not b:
        missing = origin if not a else destination
        return {"ok": False, "错误": f"地图中未找到“{missing}”", "可选地点": all_place_names()}
    if a["name"] == b["name"] or a["map_px"] == b["map_px"]:
        return {"ok": True, "路线": f"{b['name']}{'就在' + a['name'] + '内' if a['name'] != b['name'] else ''}，您已在附近。",
                "地图标注": [_marker(b, "目的地")]}
    dist = distance_m(a, b)
    mins = max(1, math.ceil(dist / _map()["walk_speed_m_per_min"]))
    via = [p for p in places() if p["name"] in _map()["route_landmarks"] and p["name"] not in (a["name"], b["name"])]
    via = sorted((p for p in via if _seg_dist(p, a, b) < 110 and distance_m(p, a) > 60 and distance_m(p, b) > 60),
                 key=lambda p: distance_m(a, p))[:2]
    steps = [f"从{a['name']}（{a['zone']}）出发，向**{direction(a, b)}**方向前往{b['name']}（{b['zone']}）。"]
    if via:
        steps.append("沿途可参考：" + "、".join(p["name"] for p in via) + "。")
    if b["neighbors"]:
        steps.append(f"{b['name']}紧邻：{'、'.join(b['neighbors'][:3])}，可作为寻找时的参照。")
    if b["area"]:
        steps.append(f"位置提示：{b['area']}")
    unsure = [p["name"] for p in (a, b) if p["coord_status"].startswith("待核实")]
    return {"ok": True, "起点": a["name"], "终点": b["name"], "方向": direction(a, b),
            "直线距离(米)": int(dist), "步行估算(分钟)": mins, "路线说明": steps,
            "坐标待核实": unsure, "地图标注": [_marker(a, "起点"), _marker(b, "终点")] + [_marker(p, "途经") for p in via],
            "数据说明": EST_NOTE}


def dorm_community(apartment_no: int) -> str | None:
    """根据“X号公寓”在官方图例中的位置，推断所属宿舍社区。"""
    cn = "零一二三四五六七八九"

    def to_cn(n: int) -> str:
        if n < 10:
            return cn[n]
        t, o = divmod(n, 10)
        return (("" if t == 1 else cn[t]) + "十" + (cn[o] if o else ""))
    legend = load_json("map/legend.json")
    target = next((x for x in legend if x["name"] == f"{to_cn(apartment_no)}号公寓"), None)
    if not target:
        return None
    comms = [x for x in legend if x["name"].endswith("社区")]
    tx, ty = target["marker_px"]
    best = min(comms, key=lambda c: (c["marker_px"][0] - tx) ** 2 + (c["marker_px"][1] - ty) ** 2)
    return best["name"]
