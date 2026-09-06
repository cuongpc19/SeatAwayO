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
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    for lvl, tag, wait in ((1, "l1", 2600), (14, "l14", 3000), (45, "l45", 3000)):
        pg.evaluate("L => load(L)", lvl)
        pg.wait_for_timeout(wait)
        pg.locator(".stage").screenshot(path="cam_%s.png" % tag)
        print(lvl, pg.evaluate("({seated:S.seated,total:S.total,moves:S.moves})"))
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open("cam_%s.png" % t).convert("RGB") for t in ("l1", "l14")]
w = 600
ts = [im.resize((w, int(im.height*w/im.width))) for im in ims]
sh = Image.new("RGB", (w, sum(t.height for t in ts)), (235,238,242))
y = 0
for t in ts: sh.paste(t, (0,y)); y += t.height
sh.save("cam_sheet.png"); print(sh.size)
