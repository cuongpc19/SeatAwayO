import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri() + "?theme=cinema"
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("startLevel(10)"); pg.wait_for_timeout(2000)
    print("theme        :", pg.evaluate("THEME"))
    print("still inlined:", pg.evaluate("!!(MOVIE && MOVIE.complete && MOVIE.naturalWidth)"),
          pg.evaluate("MOVIE ? MOVIE.naturalWidth + 'x' + MOVIE.naturalHeight : ''"))
    print("errors:", errs[:3] or "none")
    br.close()
