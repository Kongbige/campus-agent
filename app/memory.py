"""多轮对话记忆：按 session_id 保存消息历史与对话状态（槽位、上一意图等）。"""
import threading
import time
from dataclasses import dataclass, field

MAX_HISTORY = 24  # 最多保留的消息条数（超出后按“用户轮”截断）


@dataclass
class Session:
    session_id: str
    messages: list[dict] = field(default_factory=list)   # OpenAI 格式（不含 system）
    state: dict = field(default_factory=dict)            # 离线规划器使用的对话状态
    updated: float = field(default_factory=time.time)

    def trim(self) -> None:
        if len(self.messages) <= MAX_HISTORY:
            return
        cut = len(self.messages) - MAX_HISTORY
        # 从一个 user 消息开始，避免切断 tool_call 与 tool 结果的对应关系
        while cut < len(self.messages) and self.messages[cut].get("role") != "user":
            cut += 1
        self.messages = self.messages[cut:]


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, sid: str) -> Session:
        with self._lock:
            if sid not in self._sessions:
                self._sessions[sid] = Session(sid)
            s = self._sessions[sid]
            s.updated = time.time()
            return s

    def reset(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)


memory = MemoryStore()
