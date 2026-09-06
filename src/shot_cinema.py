import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate('THEME = "cinema"; startLevel(10)'); pg.wait_for_timeout(1200)
    pg.evaluate("t => { NOW = t; draw(); }", 3.0); pg.wait_for_timeout(150)
    pg.screenshot(path="cine_1.png")
    pg.evaluate("t => { NOW = t; draw(); }", 24.0); pg.wait_for_timeout(150)
    pg.screenshot(path="cine_2.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open("cine_1.png"), Image.open("cine_2.png")]
k = 0.42
ts = [im.resize((int(im.width*k), int(im.height*k))) for im in ims]
sh = Image.new("RGB", (ts[0].width, sum(t.height for t in ts) + 6), (10, 10, 14))
sh.paste(ts[0], (0, 0)); sh.paste(ts[1], (0, ts[0].height + 6))
sh.save("cine_cmp.png"); print(sh.size)
