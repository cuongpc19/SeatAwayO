import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1080})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("load(45)")
    pg.wait_for_function("S && !S.boarding && S.anim.length === 0", timeout=20000)
    pg.wait_for_timeout(300)
    pg.locator(".stage").screenshot(path="q_full.png")
    print("errors:", errs[:3] or "none")
    br.close()
im = Image.open("q_full.png").convert("RGB")
# the queue column on the right
q = im.crop((int(im.width*0.62), 0, im.width, int(im.height*0.75)))
q.resize((int(q.width*1.5), int(q.height*1.5))).save("queue_zoom.png")
print("queue_zoom", q.size)
