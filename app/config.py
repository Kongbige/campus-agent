"""配置加载：从 .env / 环境变量读取大模型接口配置。"""
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPT_DIR = BASE_DIR / "prompts"
STATIC_DIR = BASE_DIR / "static"

load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.force_mock = os.getenv("FORCE_MOCK", "0") in ("1", "true", "True")
        self.port = int(os.getenv("PORT", "8000"))
        self.demo_today = os.getenv("DEMO_TODAY", "").strip()
        self.db_path = Path(os.getenv("DB_PATH", str(DATA_DIR / "runtime.db")))
        self.timeout = float(os.getenv("LLM_TIMEOUT", "60"))

    @property
    def use_llm(self) -> bool:
        return bool(self.api_key) and not self.force_mock

    @property
    def mode_label(self) -> str:
        return "大模型模式" if self.use_llm else "离线演示模式"

    def today(self) -> date:
        if self.demo_today:
            try:
                return date.fromisoformat(self.demo_today)
            except ValueError:
                pass
        return date.today()


settings = Settings()
