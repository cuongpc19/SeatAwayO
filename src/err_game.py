from playwright.sync_api import sync_playwright
import sys, pathlib
url = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "../game.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 460, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.type.upper() + " " + m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_timeout(3500)
    print("ready =", pg.evaluate("typeof ready !== 'undefined' ? ready : 'undefined'"))
    for e in errs[:8]: print(e[:300])
    br.close()
