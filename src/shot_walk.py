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
    shots = []
    for i in range(6):
        pg.wait_for_timeout(420)
        st = pg.evaluate("S.anim.map(a=>({f:a.facing,p:a.phase}))")
        pg.locator(".stage").screenshot(path="wk_%d.png" % i)
        shots.append(st)
    print("walker state per shot:", shots)
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open("wk_%d.png" % i).convert("RGB") for i in range(6)]
# crop the top-right of the board where the door and walkers are
cs = [im.crop((int(im.width*0.30), 0, int(im.width*0.86), int(im.height*0.42))) for im in ims]
w = 430
ts = [c.resize((w, int(c.height*w/c.width))) for c in cs]
sh = Image.new("RGB", (w*3, ts[0].height*2), (30,32,36))
for i,t in enumerate(ts): sh.paste(t, ((i%3)*w, (i//3)*t.height))
sh.save("walk_sheet.png"); print(sh.size)
