"""一键启动：python run.py  然后浏览器打开 http://127.0.0.1:8000"""
import os
import sys
import webbrowser
import threading

import uvicorn

from app.config import settings

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = settings.port
    print("=" * 56)
    print("  城院小助手 · 校园服务智能体")
    print(f"  运行模式：{settings.mode_label}" + (f"（模型：{settings.model}）" if settings.use_llm else "（未配置 LLM_API_KEY）"))
    print(f"  访问地址：http://{host}:{port}")
    print("=" * 56)
    if "--no-browser" not in sys.argv and os.getenv("NO_BROWSER") != "1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
