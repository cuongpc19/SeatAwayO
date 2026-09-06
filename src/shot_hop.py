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
    pg.evaluate("load(1)")
    ys, shots = [], []
    for i in range(40):
        pg.wait_for_timeout(60)
        st = pg.evaluate("S.anim.map(a=>({y:+a.y.toFixed(2),f:a.facing,p:a.phase}))")
        if st: ys.append(st[0])
        if i in (8, 14, 18, 22):
            pg.locator(".stage").screenshot(path="hop_%d.png" % i); shots.append(i)
    print("walker y over time (hop shows as a high arc):")
    print(" ", ys)
    pg.wait_for_timeout(2500)
    print("level 1 result:", pg.evaluate("({seated:S.seated,total:S.total,phase:S.phase})"))
    pg.locator(".stage").screenshot(path="hop_done.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open("hop_%d.png" % i).convert("RGB") for i in shots] + [Image.open("hop_done.png").convert("RGB")]
w = 300
ts = [im.crop((0, 0, im.width, int(im.height*0.55))).resize((w, int(im.height*0.55*w/im.width))) for im in ims]
sh = Image.new("RGB", (w*len(ts), ts[0].height), (232,236,240))
for i,t in enumerate(ts): sh.paste(t,(i*w,0))
sh.save("hop_sheet.png"); print(sh.size)
