"""把 docs/设计文档.md 转为 Word：渲染 mermaid 图为 PNG（需联网加载 mermaid.js、已安装 playwright 浏览器），再用 pandoc 转换。
依赖：pip install pypandoc_binary playwright && playwright install chromium
"""
import re, asyncio, pypandoc, pathlib
from playwright.async_api import async_playwright
D = pathlib.Path(__file__).resolve().parent.parent / "docs"
md = (D / "设计文档.md").read_text(encoding="utf-8")
blocks = re.findall(r"```mermaid\n(.*?)```", md, re.S)
names = ["系统架构图", "请求时序图", "多轮对话状态图"]

async def render():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        pg = await b.new_page(device_scale_factor=2, viewport={"width": 1100, "height": 900})
        for code, name in zip(blocks, names):
            html = f"""<html><body style='margin:0;background:#fff'><pre class='mermaid'>{code}</pre>
<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>
<script>mermaid.initialize({{startOnLoad:true,theme:'default',fontFamily:'Noto Sans CJK SC'}});</script></body></html>"""
            await pg.set_content(html, wait_until="load", timeout=30000)
            await pg.wait_for_selector("pre.mermaid svg", timeout=20000)
            await pg.wait_for_timeout(500)
            await pg.locator("pre.mermaid svg").screenshot(path=str(D / "images" / f"{name}.png"))
        await b.close()
asyncio.run(render())
i = iter(names)
md2 = re.sub(r"```mermaid\n.*?```", lambda m: (lambda n: f"![{n}](images/{n}.png)")(next(i)), md, flags=re.S)
tmp = D / "_tmp_docx.md"; tmp.write_text(md2, encoding="utf-8")
pypandoc.convert_file(str(tmp), "docx", outputfile=str(D / "设计文档.docx"), extra_args=[f"--resource-path={D}", "--toc", "--metadata=title:城院小助手 设计文档", "--metadata=toc-title:目录"])
tmp.unlink()
print("ok")
