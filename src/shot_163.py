"""Screenshot a few 1.63.1 boards in the real game, to see the packed benches."""
import pathlib, sys
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()
LEVELS = [1, 40, 300, 900]
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 900, "height": 1400}, device_scale_factor=2)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for L in LEVELS:
        pg.goto(url + "?reset=1&level=%d" % L)
        pg.wait_for_load_state("networkidle")
        pg.wait_for_timeout(2500)
        pg.screenshot(path="s163_%d.png" % L)
        info = pg.evaluate("({w:S.W,h:S.H,seats:S.seats.length,"
                           "caps:S.seats.map(b=>b.cap).join(''),total:S.total,time:S.time})")
        print("level %-4d %dx%d seats=%d riders=%d clock=%ds caps=%s"
              % (L, info["w"], info["h"], info["seats"], info["total"], info["time"], info["caps"][:26]))
    print("page errors:", errs[:3])
    br.close()
