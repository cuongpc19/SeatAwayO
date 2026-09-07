"""Served over http so the painted backdrop is actually fetched."""
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for tag, vp in (("desk", {"width": 1440, "height": 900}), ("phone", {"width": 430, "height": 860})):
        pg = br.new_page(viewport=vp, device_scale_factor=2)
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8080/")
        pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
        pg.evaluate("startLevel(10)"); pg.wait_for_timeout(2000)
        print("%-6s backdrop loaded: %s" % (tag, pg.evaluate("!!(BG && BG.complete && BG.naturalWidth)")))
        pg.screenshot(path="bg_%s.png" % tag)
        pg.close()
    # and the procedural station, for comparison, by asking for a name that is not there
    pg = br.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    pg.goto("http://127.0.0.1:8080/?bg=none")
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("startLevel(10)"); pg.wait_for_timeout(1800)
    pg.screenshot(path="bg_station.png")
    br.close()
