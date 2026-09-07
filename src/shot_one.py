import pathlib, sys
from playwright.sync_api import sync_playwright
n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
url = pathlib.Path("../index.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 440, "height": 880}, device_scale_factor=3)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("n => startLevel(n)", n)
    pg.wait_for_timeout(2600)          # let a few passengers walk in and sit
    pg.screenshot(path="level_%d.png" % n)
    print("level", n, pg.evaluate("({name:S.name, grid:S.W+'x'+S.H, seats:S.seats.length,"
                                  " queue:S.total, seated:S.seated, time:Math.round(S.time)})"))
    print("errors:", errs[:3] or "none")
    br.close()
