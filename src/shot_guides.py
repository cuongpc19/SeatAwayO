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
    pg.evaluate("load(45)"); pg.wait_for_timeout(2600)
    pg.locator(".stage").screenshot(path="gd_on.png")
    pg.click("#b-guides"); pg.wait_for_timeout(400)
    print("button now:", pg.evaluate("document.getElementById('b-guides').textContent"),
          "GUIDES =", pg.evaluate("GUIDES"))
    pg.locator(".stage").screenshot(path="gd_off.png")
    # picking a seat up must still show where it can go
    pg.evaluate("selectSeat(S.seats.find(b=>placements(S,b).length))"); pg.wait_for_timeout(300)
    pg.locator(".stage").screenshot(path="gd_sel.png")
    print("errors:", errs[:3] or "none")
    br.close()
ims = [Image.open(n).convert("RGB") for n in ("gd_on.png","gd_off.png","gd_sel.png")]
w = 400
ts = [im.resize((w, int(im.height*w/im.width))) for im in ims]
sh = Image.new("RGB", (w*3, ts[0].height), (232,236,240))
for i,t in enumerate(ts): sh.paste(t,(i*w,0))
sh.save("guides_sheet.png"); print(sh.size)
