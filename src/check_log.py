"""Prove the recorder reaches the server before asking a human to use it."""
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto("http://127.0.0.1:8080/level_player.html")
    pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(129)"); pg.wait_for_timeout(300)
    pg.locator("#board").scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    p = pg.evaluate("""(() => { const b = S.seats[6], box = cv.getBoundingClientRect();
        const [sx, sz] = seatCentre(b); const [px, py] = P(sx, 0, sz);
        return [box.left + px/(cv.width/box.width), box.top + py/(cv.height/box.height)]; })()""")
    pg.mouse.move(*p); pg.mouse.down(); pg.mouse.move(p[0] + 70, p[1] + 40, steps=8); pg.mouse.up()
    pg.wait_for_timeout(600)
    print("on-screen readout:\n" + pg.locator("#trace").inner_text())
    print("errors:", errs[:3] or "none")
    br.close()
