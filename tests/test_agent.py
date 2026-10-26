from app import agent
from app.agent import chat


def calls(res):
    return [s["name"] for s in res["steps"] if s["type"] == "tool_call"]


def test_multi_step_planning():
    r = chat("a1", "下节课在哪，从建工楼怎么过去？")
    assert calls(r) == ["next_class", "plan_route"]
    assert any(s["type"] == "plan" for s in r["steps"])


def test_multi_turn_followup():
    chat("a2", "明天有什么课？")
    r = chat("a2", "那周四呢？")
    assert calls(r) == ["query_schedule"]
    assert "周四" in r["reply"]


def test_slot_filling_repair():
    r1 = chat("a3", "宿舍水龙头坏了")
    assert calls(r1) == [] and "宿舍楼号" in r1["reply"]
    r2 = chat("a3", "12号公寓 215")
    assert calls(r2) == ["create_repair_ticket"] and "工单号" in r2["reply"]


def test_out_of_scope():
    r = chat("a4", "帮我代考")
    assert calls(r) == [] and "超出" in r["reply"]


def test_sample_data_notice():
    r = chat("a5", "明天有什么课")
    assert "演示数据" in r["reply"]
    assert r["mode"] == "mock"


def test_llm_loop_with_fake_model(monkeypatch):
    """模拟 OpenAI 兼容接口的 tool_calls 返回，验证大模型模式的 ReAct 循环。"""
    seq = [
        {"content": "计划：先查明天课表。", "tool_calls": [{"id": "c1", "type": "function",
         "function": {"name": "query_schedule", "arguments": "{\"day\": \"明天\"}"}}]},
        {"content": "明天有高等数学和计算机网络。"},
    ]
    seen = []

    def fake(messages, tools=None, temperature=0.3):
        seen.append(messages)
        return seq[len(seen) - 1]
    monkeypatch.setattr(agent, "chat_completion", fake)
    r = agent.run_llm("a6", "明天什么课")
    assert r["mode"] == "llm" and r["reply"].startswith("明天有")
    assert calls(r) == ["query_schedule"]
    assert seen[1][-1]["role"] == "tool" and seen[0][0]["role"] == "system"
    # 第二轮应带上历史
    seen.clear()
    seq[:] = [{"content": "好的"}]
    agent.run_llm("a6", "谢谢")
    assert any(m.get("role") == "tool" for m in seen[0])


def test_llm_failure_falls_back(monkeypatch):
    from app.llm_client import LLMError

    def boom(*a, **k):
        raise LLMError("401")
    monkeypatch.setattr(agent, "chat_completion", boom)
    monkeypatch.setattr(type(agent.settings), "use_llm", property(lambda self: True))
    r = agent.chat("a7", "明天有什么课")
    assert r["steps"][0]["type"] == "error" and calls(r) == ["query_schedule"]
