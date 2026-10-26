"""效果评估脚本：python eval/evaluate.py [--llm] [--holdout]

默认在离线演示模式下运行（无需密钥），统计：
- 工具选择准确率：实际调用的工具序列 == 期望序列
- 参数准确率：期望参数均正确（子串匹配）
- 知识库检索命中率（Top1 来源正确）
加 --holdout 使用泛化测试集（未针对其调整规则）；加 --llm 参数且配置了密钥时，使用大模型模式评估（结果受模型影响）。
"""
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_TODAY", "2026-11-02")
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "eval.db")
if "--llm" not in sys.argv:
    os.environ["FORCE_MOCK"] = "1"

from app.agent import chat  # noqa: E402
from app.config import settings  # noqa: E402


def match_args(expect: dict, actual: dict) -> bool:
    for k, v in (expect or {}).items():
        if str(v) not in json.dumps(actual.get(k, ""), ensure_ascii=False):
            return False
    return True


def main() -> int:
    fname = "holdout_cases.json" if "--holdout" in sys.argv else "test_cases.json"
    cases = json.loads((ROOT / "eval" / fname).read_text(encoding="utf-8"))["cases"]
    print(f"用例集：{fname}")
    print(f"评估模式：{settings.mode_label}    演示日期：{settings.today()}    用例数：{len(cases)}\n")
    tool_ok = arg_ok = kb_total = kb_ok = 0
    by_cat: dict[str, list[int]] = {}
    t0 = time.time()
    for c in cases:
        sid = uuid.uuid4().hex
        res = None
        for turn in c["turns"]:
            res = chat(sid, turn)
        calls = [s for s in res["steps"] if s["type"] == "tool_call"]
        names = [s["name"] for s in calls]
        exp_names = [e["tool"] for e in c["expect"]]
        t_pass = names == exp_names
        if "expect_reply_contains" in c:
            t_pass = t_pass and c["expect_reply_contains"] in res["reply"]
        a_pass = t_pass and all(match_args(e.get("args"), s["args"]) for e, s in zip(c["expect"], calls))
        if "expect_source" in c:
            kb_total += 1
            results = [s["result"] for s in res["steps"] if s["type"] == "tool_result" and s["name"] == "search_knowledge"]
            if results and results[0]["检索结果"] and c["expect_source"] in results[0]["检索结果"][0]["来源"]:
                kb_ok += 1
            else:
                a_pass = False
        tool_ok += t_pass
        arg_ok += a_pass
        by_cat.setdefault(c["类别"], [0, 0])
        by_cat[c["类别"]][0] += a_pass
        by_cat[c["类别"]][1] += 1
        flag = "✅" if a_pass else ("⚠️" if t_pass else "❌")
        print(f"{flag} [{c['id']:02d}] {c['类别']:<6} {' / '.join(c['turns'])}")
        if not a_pass:
            print(f"      期望：{exp_names}  实际：{names}  参数：{[s['args'] for s in calls]}")
    n = len(cases)
    print("\n================ 评估结果 ================")
    print(f"工具选择准确率：{tool_ok}/{n} = {tool_ok / n:.1%}")
    print(f"端到端准确率（工具+参数）：{arg_ok}/{n} = {arg_ok / n:.1%}")
    if kb_total:
        print(f"知识库 Top1 命中率：{kb_ok}/{kb_total} = {kb_ok / kb_total:.1%}")
    print("分类别：" + "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in by_cat.items()))
    print(f"平均每例耗时：{(time.time() - t0) / n * 1000:.1f} ms")
    if "--holdout" in sys.argv:
        return 0  # 泛化集仅作参考，不作为通过门槛
    return 0 if arg_ok / n >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
