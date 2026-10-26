"""OpenAI 兼容接口客户端（DeepSeek / 通义千问 / 智谱 / Kimi / Ollama 等均可）。"""
import httpx

from .config import settings


class LLMError(RuntimeError):
    pass


def chat_completion(messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.3) -> dict:
    url = f"{settings.base_url}/chat/completions"
    payload = {"model": settings.model, "messages": messages, "temperature": temperature}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    headers = {"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=settings.timeout)
    except httpx.HTTPError as e:
        raise LLMError(f"网络错误：{e}") from e
    if r.status_code != 200:
        raise LLMError(f"接口返回 {r.status_code}：{r.text[:300]}")
    data = r.json()
    try:
        return data["choices"][0]["message"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"响应格式异常：{str(data)[:300]}") from e
