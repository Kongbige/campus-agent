"""生活服务工具：食堂/餐厅信息、交通出行。"""
from .common import load_json


def canteen_info(name: str | None = None, zone: str | None = None) -> dict:
    cs = load_json("canteens.json")["canteens"]
    if name:
        cs = [c for c in cs if name in c["name"] or c["name"] in name] or cs
    if zone:
        cs = [c for c in cs if zone in c["location"]] or cs
    return {"ok": True, "食堂与餐厅": cs, "数据说明": "名称与位置来自学校官网/官方地图（西山会所、绿岛俱乐部为食堂已确认）；营业时间为示例数据，待核实"}


def transport_info() -> dict:
    t = load_json("transport.json")
    return {"ok": True, "地址": t["address"], "校园说明": t["campus_note"], "校门": t["gate"],
            "公交": [f"{b['line']} → {b['stop']}站" for b in t["bus"]], "地铁": t["metro"], "来源": t["_说明"]}
