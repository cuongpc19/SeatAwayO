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
    for lvl, tag, wait in ((1, "a", 3200), (45, "b", 3600)):
        pg.evaluate("L => load(L)", lvl); pg.wait_for_timeout(wait)
        pg.locator(".stage").screenshot(path="fl_%s.png" % tag)
        print(lvl, pg.evaluate("({seated:S.seated,total:S.total})"))
    print("errors:", errs[:3] or "none")
    br.close()
a = Image.open("fl_a.png").convert("RGB"); b = Image.open("fl_b.png").convert("RGB")
w = 380
ta = a.resize((w, int(a.height*w/a.width))); tb = b.resize((w, int(b.height*w/b.width)))
sh = Image.new("RGB", (w*2, max(ta.height, tb.height)), (232,236,240))
sh.paste(ta,(0,0)); sh.paste(tb,(w,0))
sh.save("flip_sheet.png"); print(sh.size)
