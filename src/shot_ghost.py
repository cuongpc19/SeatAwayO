import pathlib
from PIL import Image
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
TO_CLIENT = ("([c,r]) => { const [x,y] = P(cellW(c), 0, cellZ(r));"
             " const rect = cv.getBoundingClientRect();"
             " return [rect.left + x/cv.width*rect.width, rect.top + y/cv.height*rect.height]; }")
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=25000)
    pg.evaluate("load(45)")
    pg.wait_for_function("S && !S.boarding && S.anim.length === 0", timeout=20000)
    pg.wait_for_timeout(300)
    # prefer a seat that has somebody on it, so the rider rides along too
    sid = pg.evaluate("S.seats.findIndex(b=>b.occ.length && !b.locked && placements(S,b).length)")
    if sid < 0: sid = pg.evaluate("S.seats.findIndex(b=>placements(S,b).length)")
    print("dragging seat", sid, "riders:", pg.evaluate("s=>S.seats[s].occ.length", sid))
    pos = pg.evaluate(TO_CLIENT, pg.evaluate("s=>[S.seats[s].c,S.seats[s].r]", sid))
    pg.mouse.move(pos[0], pos[1]); pg.mouse.down()
    for k, (dx, dy) in enumerate([(-14, 8), (-46, 26), (-84, 48)]):
        pg.mouse.move(pos[0] + dx, pos[1] + dy)
        pg.wait_for_timeout(110)
        pg.locator(".stage").screenshot(path="gh_%d.png" % k)
    print("ghost offset while held:", pg.evaluate("S.drag && S.drag.ghost"))
    pg.mouse.up()
    pg.wait_for_timeout(200)
    pg.locator(".stage").screenshot(path="gh_drop.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open("gh_%d.png" % i).convert("RGB") for i in range(3)] + [Image.open("gh_drop.png").convert("RGB")]
w = 300
cs = [im.crop((0, 0, im.width, int(im.height*0.6))) for im in ims]
ts = [c.resize((w, int(c.height*w/c.width))) for c in cs]
sh = Image.new("RGB", (w*4, ts[0].height), (232,236,240))
for i,t in enumerate(ts): sh.paste(t,(i*w,0))
sh.save("ghost_sheet.png"); print(sh.size)
