import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900},
                                                device_scale_factor=2)
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.wait_for_timeout(400)
    pg.screenshot(path="s_home.png")
    pg.evaluate("startLevel(12)"); pg.wait_for_timeout(1400)
    pg.screenshot(path="s_play.png")
    pg.evaluate("startLevel(240)"); pg.wait_for_timeout(1400)
    pg.screenshot(path="s_play2.png")
    # force a clear so the card can be looked at
    pg.evaluate("S.left = S.time * 0.7; S.seated = S.total; finish(true)")
    pg.wait_for_timeout(1100)
    pg.screenshot(path="s_win.png")
    pg.evaluate("S.left = 0; finish(false)"); pg.wait_for_timeout(700)
    pg.screenshot(path="s_lose.png")
    print("errors:", errs[:3] or "none")
    br.close()

ims = [Image.open(n) for n in ("s_home.png", "s_play.png", "s_play2.png", "s_win.png", "s_lose.png")]
k = 0.46
ts = [im.resize((int(im.width*k), int(im.height*k))) for im in ims]
sheet = Image.new("RGB", (sum(t.width for t in ts) + 6*len(ts), ts[0].height), (26, 30, 42))
x = 3
for t in ts: sheet.paste(t, (x, 0)); x += t.width + 6
sheet.save("s_sheet.png"); print("s_sheet.png", sheet.size)
