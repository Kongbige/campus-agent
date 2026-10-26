"""FastAPI 服务入口。"""
import uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .agent import chat
from .config import STATIC_DIR, settings
from .memory import memory
from .tools import TOOLS, execute_tool
from .tools.schedule import week_of

app = FastAPI(title="城院小助手 API", version=__version__, description="沈阳城市学院校园服务智能体（参赛原型）")


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = None


@app.get("/api/status")
def status():
    today = settings.today()
    return {"name": "城院小助手", "version": __version__, "mode": "llm" if settings.use_llm else "mock",
            "mode_label": settings.mode_label, "model": settings.model if settings.use_llm else None,
            "today": today.isoformat(), "week": week_of(today),
            "tools": [{"name": k, "label": v[2], "description": v[1]["function"]["description"]} for k, v in TOOLS.items()]}


@app.post("/api/chat")
def api_chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex
    res = chat(sid, body.message.strip())
    res["session_id"] = sid
    return res


@app.post("/api/reset")
def api_reset(body: dict):
    memory.reset(body.get("session_id", ""))
    return {"ok": True}


@app.get("/api/history/{session_id}")
def api_history(session_id: str):
    s = memory.get(session_id)
    return {"messages": [m for m in s.messages if m["role"] in ("user", "assistant") and m.get("content")]}


@app.get("/api/sidebar/{session_id}")
def api_sidebar(session_id: str):
    """侧边栏数据：今日课表、我的报修、我的待办。"""
    return {"today": execute_tool("query_schedule", {"day": "今天"}),
            "tickets": execute_tool("query_repair_tickets", {}, session_id),
            "reminders": execute_tool("list_reminders", {}, session_id)}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
