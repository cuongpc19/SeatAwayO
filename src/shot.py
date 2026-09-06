import sys, pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("level_curve.html").resolve().as_uri()
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for mode, name in (("light", "shot_light.png"), ("dark", "shot_dark.png")):
        pg = b.new_page(viewport={"width": 1320, "height": 1200}, color_scheme=mode)
        errs = []
        pg.on("console", lambda m: errs.append(m.type + ": " + m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.goto(url); pg.wait_for_timeout(2500)
        pg.screenshot(path=name, full_page=True)
        print(name, "console errors:", errs or "none")
        h = pg.evaluate("document.body.scrollWidth")
        print("  scrollWidth", h, "(viewport 1320)")
        pg.close()
    b.close()
