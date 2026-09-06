import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../game.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for tag, vp in (("desk", {"width": 1440, "height": 900}), ("phone", {"width": 430, "height": 860})):
        pg = br.new_page(viewport=vp, device_scale_factor=2)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        pg.evaluate("startLevel(10)"); pg.wait_for_timeout(1800)
        pg.screenshot(path="wide_%s.png" % tag)
        r = pg.evaluate("({cw: cv.clientWidth, ch: cv.clientHeight, scale: +LAY.s.toFixed(1)})")
        print("%-6s viewport %dx%-4d canvas %dx%-4d board scale %.1f  %s"
              % (tag, vp["width"], vp["height"], r["cw"], r["ch"], r["scale"], errs[:1] or ""))
        pg.close()
    br.close()
