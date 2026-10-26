"""由调研数据生成导航用的 data/campus_map.json。

输入：data/map/research_buildings.json（9 栋楼，含经纬度/可信度/相邻建筑）
      data/map/legend.json（官方鸟瞰图 96 个图例编号及像素位置）
      data/map/affine.json（地图像素 → 经纬度 的仿射拟合参数，17 个 OSM 地标拟合，中位误差约 36 米）
用法：python scripts/build_campus_map.py   （团队实地核实后修改本脚本中的 LANDMARKS / ZONES 或直接编辑输出文件）
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "data" / "map"
research = json.loads((M / "research_buildings.json").read_text(encoding="utf-8"))
legend = {x["no"]: x for x in json.loads((M / "legend.json").read_text(encoding="utf-8"))}
A = json.loads((M / "affine.json").read_text(encoding="utf-8"))["A"]


def px2ll(x, y):
    lat = A[0][0] * x + A[1][0] * y + A[2][0]
    lng = A[0][1] * x + A[1][1] * y + A[2][1]
    return round(lat, 6), round(lng, 6)


# 片区：官网“北/西/南校区”为同一校园内的片区。official=官网明确列出；inferred=依地图位置推断
ZONES = {
    "建工楼": ("西校区", "official"), "医工楼": ("西校区", "official"), "传媒楼": ("西校区", "official"),
    "经管楼": ("西校区", "official"), "西山会所": ("西校区", "official"), "南楼": ("南校区", "official"),
    "医科楼": ("西校区", "inferred"), "机电楼": ("南校区", "inferred"), "绿岛俱乐部": ("北校区", "inferred"),
}
TYPES = {"建工楼": "教学楼", "医工楼": "教学楼", "传媒楼": "教学楼", "经管楼": "教学楼", "医科楼": "教学楼",
         "机电楼": "教学楼（圆环形“齿轮楼”）", "南楼": "教学/实训楼（内有芙蓉餐厅、百荷咖啡）",
         "西山会所": "食堂（已确认；也可作活动场地）", "绿岛俱乐部": "食堂（已确认；也可作活动场地）"}
ALIASES = {"建工楼": ["建工"], "医工楼": ["医工"], "传媒楼": ["传媒"], "经管楼": ["经管"], "医科楼": ["医科"],
           "机电楼": ["机电", "齿轮楼"], "南楼": [], "西山会所": ["西山", "西山食堂"], "绿岛俱乐部": ["绿岛俱乐部食堂"]}

# 关键地标：(图例号, 类型, 别名, 片区, 片区依据)
LANDMARKS = [
    (1, "校门", ["大门", "校门", "正门", "东门"], "东侧", "map"),
    (65, "图书馆", ["图书馆", "水晶宫图书馆"], "湖区（绿岛湖西岸）", "map"),
    (16, "图书馆/书屋", ["青苹果书屋", "书屋"], "北校区", "inferred"),
    (13, "餐厅/咖啡", ["梨苑", "梨苑餐厅"], "北校区", "inferred"),
    (39, "体育场馆", ["体育场馆"], "西校区", "inferred"),
    (64, "运动场", ["操场", "田径场"], "西南部", "map"),
    (61, "运动场", [], "东南部", "map"),
    (66, "湖", ["湖", "绿岛湖边"], "校园中部", "map"),
    (69, "湖", ["荷塘"], "北校区", "map"),
    (40, "讲堂/活动场所", ["讲堂"], "西校区", "inferred"),
    (49, "会议/活动场所", ["会议中心"], "北校区", "inferred"),
    (63, "广场", [], "北校区", "inferred"),
    (58, "地标", [], "南校区", "inferred"),
    (27, "地标", [], "北校区", "inferred"),
    (25, "办公/教学楼", [], "北校区", "official"),
    (15, "办公/活动楼", [], "北校区", "official"),
    (20, "行政办公", [], "北校区", "inferred"),
    (70, "行政办公", [], "西校区", "inferred"),
    (72, "行政办公", ["团委"], "西校区", "inferred"),
    (38, "创新创业", ["大学生创业服务中心"], "西校区", "inferred"),
    (53, "传媒中心", ["绿岛传媒中心"], "南校区", "official"),
    (3, "宿舍社区", ["园中园"], "北校区", "official"),
    (18, "宿舍社区", ["梧桐园"], "北校区", "official"),
    (75, "宿舍社区", ["金菊园"], "西校区", "official"),
    (37, "宿舍社区", ["白桦园"], "西校区", "official"),
    (93, "宿舍社区", ["金栎园"], "西校区", "official"),
    (92, "宿舍社区", ["紫薇园"], "西校区", "official"),
    (45, "宿舍社区", ["玫瑰园"], "南校区", "inferred"),
    (57, "宿舍社区", ["百荷园"], "南校区", "official"),
]
# 位于其他建筑内部/附近、地图无单独编号的餐厅（位置取所在建筑/社区）
INSIDE = [
    ("芙蓉餐厅", "餐厅", 59, "位于南楼内"), ("百荷咖啡", "咖啡", 59, "位于南楼内"),
    ("百荷园餐厅", "餐厅", 57, "位于百荷园社区（具体位置待核实；可能即 OSM 标注的“三期食堂”）"),
    ("凤凰餐厅", "餐厅", 18, "位于梧桐园社区内（具体位置待核实）"),
]

places = []
for b in research:
    zone, zsrc = ZONES[b["name"]]
    high = b["confidence"].startswith("high")
    places.append({
        "name": b["name"], "legend_no": b["legend_no"], "type": TYPES[b["name"]], "aliases": ALIASES[b["name"]],
        "zone": zone, "zone_source": zsrc, "lat": b["lat"], "lng": b["lng"], "map_px": b["map_marker_px"],
        "coord_status": "较可靠（OSM 建筑中心）" if high else "待核实（由地图像素换算估算，误差约40–100米）",
        "area": b["area_description"], "neighbors": b["neighbors"], "is_core_building": True,
    })
for no, typ, aliases, zone, zsrc in LANDMARKS:
    lg = legend[no]
    lat, lng = px2ll(*lg["marker_px"])
    places.append({"name": lg["name"], "legend_no": no, "type": typ, "aliases": aliases, "zone": zone, "zone_source": zsrc,
                   "lat": lat, "lng": lng, "map_px": lg["marker_px"], "coord_status": "待核实（由地图像素换算估算，误差约40–100米）",
                   "area": "", "neighbors": [], "is_core_building": False})
for name, typ, host_no, note in INSIDE:
    host = next(p for p in places if p["legend_no"] == host_no)
    places.append({"name": name, "legend_no": None, "type": typ, "aliases": [], "zone": host["zone"], "zone_source": host["zone_source"],
                   "lat": host["lat"], "lng": host["lng"], "map_px": host["map_px"], "coord_status": "待核实（取所在建筑位置）",
                   "area": note, "neighbors": [host["name"]], "is_core_building": False})

out = {
    "_说明": ("依据学校官方鸟瞰图（data/map/campus_map_official.png，96 个图例）、OpenStreetMap 与学校官网整理。"
              "沈阳城市学院为单一校园（沈阳市苏家屯区梧桐大街2号），“北/西/南校区”为校园内片区。"
              "坐标标注“待核实”者为地图像素换算估算；步行时间为直线距离按80米/分钟估算，实际路线更长。"
              "zone_source：official=官网列出，inferred/map=依地图位置推断。"),
    "campus": {"name": "沈阳城市学院", "address": "沈阳市苏家屯区梧桐大街2号", "center": [41.6239, 123.5306],
               "map_image": "/static/campus_map.jpg", "map_size_px": [1992, 1377],
               "zones": {"北校区": "园中园、梧桐园、白卿宫、宏志楼等（东北部）", "西校区": "建工楼、医工楼、传媒楼、经管楼、西山会所及金菊园、白桦园、金栎园、紫薇园",
                         "南校区": "南楼、百荷园、绿岛传媒中心（湖南岸/东南部）"},
               "gate_note": "地图 1 号“校园大门”在校园东侧（沈本产业大道/304国道一侧）；其他校门情况未知，待核实。"},
    "walk_speed_m_per_min": 80,
    "route_landmarks": ["水晶宫", "绿岛湖", "体育馆", "五星广场", "绿岛讲堂", "田径场", "校训塔", "凯旋门", "东湖", "宏志楼", "金菊园社区", "白桦园社区"],
    "places": places,
}
(ROOT / "data" / "campus_map.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"已生成 data/campus_map.json：{len(places)} 个地点")
