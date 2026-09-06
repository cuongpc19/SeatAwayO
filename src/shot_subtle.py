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
    pg.evaluate("load(45)"); pg.wait_for_timeout(2400)
    pg.evaluate("selectSeat(S.seats.find(b=>placements(S,b).length))")
    pg.wait_for_timeout(300)
    n = pg.evaluate("S.dragTargets ? S.dragTargets.length : 0")
    print("legal destinations for the held seat:", n, "(none of them are painted now)")
    pg.locator(".stage").screenshot(path="sub_sel.png")
    pg.click("#b-guides"); pg.wait_for_timeout(200)
    pg.evaluate("selectSeat(S.seats.find(b=>placements(S,b).length))")
    pg.wait_for_timeout(250)
    pg.locator(".stage").screenshot(path="sub_off.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open(n).convert("RGB") for n in ("sub_sel.png","sub_off.png")]
w = 480
ts = [im.resize((w, int(im.height*w/im.width))) for im in ims]
sh = Image.new("RGB", (w*2, ts[0].height), (232,236,240))
for i,t in enumerate(ts): sh.paste(t,(i*w,0))
sh.save("subtle_sheet.png"); print(sh.size)
