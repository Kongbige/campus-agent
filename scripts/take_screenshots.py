"""用无头浏览器为文档截图（需先 python run.py 启动服务，并 pip install playwright）。"""
import asyncio
import sys

from playwright.async_api import async_playwright

URL = "http://127.0.0.1:8000"
CHROME = sys.argv[1] if len(sys.argv) > 1 else None


async def send(pg, text, wait=700):
    await pg.fill("#input", text)
    await pg.press("#input", "Enter")
    await pg.wait_for_timeout(wait)


async def main():
    async with async_playwright() as p:
        kw = {"executable_path": CHROME, "args": ["--no-sandbox"]} if CHROME else {}
        b = await p.chromium.launch(**kw)
        pg = await b.new_page(viewport={"width": 1366, "height": 900})
        await pg.goto(URL)
        await pg.evaluate("localStorage.clear()")
        await pg.reload()
        await pg.wait_for_timeout(800)
        for m in ["提醒我明天下午2点去绿岛讲堂听讲座", "宿舍水龙头坏了一直漏水", "12号公寓 302", "下节课在哪，从建工楼怎么过去？"]:
            await send(pg, m)
        await pg.evaluate("const d=[...document.querySelectorAll('details.trace')].pop(); d.open=true")
        await pg.wait_for_timeout(500)
        await pg.evaluate("const m=document.querySelector('#messages'); const d=[...document.querySelectorAll('.msg.user')].pop(); m.scrollTop=d.offsetTop+40")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path="docs/screenshot.png")
        await pg.evaluate("const m=document.querySelector('#messages'); m.scrollTop=[...document.querySelectorAll('details.trace')].pop().offsetTop+200")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path="docs/screenshot_trace.png")
        mp = await b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        await mp.goto(URL)
        await mp.evaluate("localStorage.clear()")
        await mp.reload()
        await mp.wait_for_timeout(800)
        await send(mp, "从金菊园到南楼怎么走", 1200)
        await mp.evaluate("const m=document.querySelector('#messages'); const d=[...document.querySelectorAll('.msg.user')].pop(); m.scrollTop=d.offsetTop-10")
        await mp.wait_for_timeout(300)
        await mp.screenshot(path="docs/screenshot_mobile.png")
        await b.close()

asyncio.run(main())
