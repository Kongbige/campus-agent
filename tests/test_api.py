from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_status_and_index():
    s = client.get("/api/status").json()
    assert s["mode"] == "mock" and s["mode_label"] == "离线演示模式" and len(s["tools"]) >= 6
    assert "城院小助手" in client.get("/").text
    assert client.get("/static/campus_map.jpg").status_code == 200


def test_chat_flow():
    r = client.post("/api/chat", json={"message": "从经管楼到医科楼怎么走"}).json()
    sid = r["session_id"]
    assert "步行估算" in r["reply"]
    res = [s for s in r["steps"] if s["type"] == "tool_result"][0]["result"]
    assert [m["name"] for m in res["地图标注"]][:2] == ["经管楼", "医科楼"]
    r2 = client.post("/api/chat", json={"message": "提醒我明天8点交报告", "session_id": sid}).json()
    assert [s["name"] for s in r2["steps"] if s["type"] == "tool_call"] == ["add_reminder"]
    side = client.get(f"/api/sidebar/{sid}").json()
    assert side["reminders"]["待办"]
    h = client.get(f"/api/history/{sid}").json()
    assert len(h["messages"]) == 4
    client.post("/api/reset", json={"session_id": sid})
    assert client.get(f"/api/history/{sid}").json()["messages"] == []


def test_validation():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
