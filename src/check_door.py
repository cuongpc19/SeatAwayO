import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1120, "height": 1050})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    blocked = 0
    for L in range(1, 61):
        pg.evaluate("L => load(L)", L)
        b = pg.evaluate("!isFree(S, S.W - 1, S.door)")
        blocked += 1 if b else 0
    print("door blocked at start: %d / 60 levels" % blocked)
    pg.evaluate("load(14)"); pg.wait_for_timeout(300)
    print("hint:", pg.evaluate("document.getElementById('hint').textContent"))
    print("note:", pg.evaluate("document.getElementById('method').textContent")[:220])
    pg.locator(".stage").screenshot(path="door_l14.png")
    pg.evaluate("load(1)"); pg.wait_for_timeout(250)
    pg.locator(".stage").screenshot(path="door_l1.png")
    print("errors:", errs or "none")
    br.close()
