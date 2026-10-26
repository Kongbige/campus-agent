"""校园知识库问答：基于 BM25 的轻量检索（中文字符二元组切分，无第三方依赖）。"""
import math
import re
from functools import lru_cache

from ..config import DATA_DIR

STOP = set("的了吗呢啊是在有和与及或怎么如何什么哪里多少请问一下我要想")
# 口语 → 文档术语 的同义扩展，提升召回
SYNONYMS = {"几点": "开放时间", "关门": "开放时间", "开门": "开放时间", "丢": "挂失补办", "掉了": "挂失补办",
            "补卡": "补办", "借书": "借阅", "续借": "借阅续借", "选修": "选课", "抢课": "选课正选", "退课": "补退选",
            "坏了": "报修", "修": "报修", "请假": "请假流程", "奖学金": "奖学金评定", "充钱": "充值", "占座": "座位预约",
            "大功率": "用电安全", "暖气": "暖气供暖", "门禁": "作息门禁", "借场地": "场地借用"}


def expand(query: str) -> str:
    extra = [v for k, v in SYNONYMS.items() if k in query]
    return query + " " + " ".join(extra)


def tokenize(text: str) -> list[str]:
    text = text.lower()
    toks = re.findall(r"[a-z0-9]+", text)
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        chars = [c for c in seg]
        toks += [c for c in chars if c not in STOP]
        toks += [seg[i:i + 2] for i in range(len(seg) - 1)]
    return toks


@lru_cache(maxsize=1)
def _index():
    chunks = []
    for f in sorted((DATA_DIR / "knowledge").glob("*.md")):
        doc = f.stem
        title = doc
        for block in re.split(r"\n(?=## )", f.read_text(encoding="utf-8")):
            lines = block.strip().splitlines()
            if not lines:
                continue
            head = lines[0].lstrip("# ").strip()
            body = "\n".join(lines[1:]).strip()
            if not body or all(l.startswith(">") or not l.strip() for l in body.splitlines()):
                continue
            chunks.append({"doc": doc, "section": head if head != title else "概述", "text": body,
                           "tokens": tokenize(doc + head + body)})
    N = len(chunks)
    avgdl = sum(len(c["tokens"]) for c in chunks) / max(N, 1)
    df = {}
    for c in chunks:
        for t in set(c["tokens"]):
            df[t] = df.get(t, 0) + 1
    return chunks, df, N, avgdl


def search_knowledge(query: str, top_k: int = 3) -> dict:
    chunks, df, N, avgdl = _index()
    q = tokenize(expand(query))
    k1, b = 1.5, 0.75
    scored = []
    for c in chunks:
        tf = {}
        for t in c["tokens"]:
            tf[t] = tf.get(t, 0) + 1
        dl = len(c["tokens"])
        s = 0.0
        for t in set(q):
            if t not in tf:
                continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    hits = [{"来源": f"{c['doc']} · {c['section']}", "内容": c["text"], "得分": round(s, 2)} for s, c in scored[: int(top_k)]]
    return {"ok": True, "查询": query, "检索结果": hits,
            "说明": "知识库为示例文档，回答需注明来源并提示以学校官方通知为准" if hits else "知识库中未找到相关内容"}
