"""智能体核心：大模型 ReAct 工具调用循环 + 离线规则规划器（两种模式调用同一套工具）。"""
import json
from datetime import datetime

from . import mock_planner, responder
from .config import PROMPT_DIR, settings
from .llm_client import LLMError, chat_completion
from .memory import memory
from .tools import execute_tool, tool_label, tool_schemas
from .tools.common import WEEKDAY_CN
from .tools.navigation import all_building_names
from .tools.schedule import week_of

MAX_STEPS = 6


def build_system_prompt() -> str:
    tpl = (PROMPT_DIR / "system_prompt.md").read_text(encoding="utf-8")
    today = settings.today()
    return (tpl.replace("{today}", today.isoformat()).replace("{weekday}", WEEKDAY_CN[today.isoweekday()])
            .replace("{week}", str(week_of(today))).replace("{now}", datetime.now().strftime("%H:%M"))
            .replace("{mode}", settings.mode_label).replace("{buildings}", "、".join(all_building_names())))


def _tool_step(name: str, args: dict, result: dict) -> list[dict]:
    return [{"type": "tool_call", "name": name, "label": tool_label(name), "args": args},
            {"type": "tool_result", "name": name, "label": tool_label(name), "result": result}]


def run_mock(session_id: str, message: str) -> dict:
    sess = memory.get(session_id)
    p = mock_planner.plan(message, sess.state)
    steps = [{"type": "plan", "content": t} for t in p.thoughts]
    results, parts = [], []
    for st in p.steps:
        args = st["args"](results) if callable(st["args"]) else st["args"]
        args = {k: v for k, v in args.items() if v not in (None, "")}
        r = execute_tool(st["tool"], args, session_id)
        steps += _tool_step(st["tool"], args, r)
        results.append(r)
        parts.append(responder.render(st["tool"], r))
        sess.state["last"] = {"tool": st["tool"], "args": args}
    if p.direct_reply is not None:
        reply = p.direct_reply
    else:
        reply = "\n\n".join(parts)
        if sess.state.pop("emergency", False):
            reply = "⚠️ 如有冒烟、漏电、受伤等危险，请先确保安全并立即联系宿管/保卫处，或拨打 119/120！\n\n" + reply
        if responder.has_sample(results):
            reply += responder.NOTE
    sess.messages += [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    sess.trim()
    return {"reply": reply, "steps": steps, "mode": "mock", "mode_label": "离线演示模式"}


def run_llm(session_id: str, message: str) -> dict:
    sess = memory.get(session_id)
    msgs = [{"role": "system", "content": build_system_prompt()}] + sess.messages + [{"role": "user", "content": message}]
    new_msgs = [{"role": "user", "content": message}]
    steps: list[dict] = []
    reply = ""
    for _ in range(MAX_STEPS):
        out = chat_completion(msgs, tools=tool_schemas())
        calls = out.get("tool_calls") or []
        content = out.get("content") or ""
        if not calls:
            reply = content
            break
        if content.strip():
            steps.append({"type": "plan", "content": content.strip()})
        assistant = {"role": "assistant", "content": content, "tool_calls": calls}
        msgs.append(assistant)
        new_msgs.append(assistant)
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            r = execute_tool(name, args, session_id)
            steps += _tool_step(name, args, r)
            tm = {"role": "tool", "tool_call_id": c.get("id", ""), "content": json.dumps(r, ensure_ascii=False)}
            msgs.append(tm)
            new_msgs.append(tm)
    else:
        reply = "这个问题步骤有点多，我先整理到这里，你可以换个更具体的问法再试试。"
    new_msgs.append({"role": "assistant", "content": reply})
    sess.messages += new_msgs
    sess.trim()
    return {"reply": reply, "steps": steps, "mode": "llm", "mode_label": f"大模型模式 · {settings.model}"}


def chat(session_id: str, message: str) -> dict:
    if not settings.use_llm:
        return run_mock(session_id, message)
    try:
        return run_llm(session_id, message)
    except LLMError as e:
        res = run_mock(session_id, message)
        res["steps"].insert(0, {"type": "error", "content": f"大模型调用失败，已自动降级为离线模式：{e}"})
        res["mode_label"] = "离线演示模式（降级）"
        return res
