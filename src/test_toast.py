"""The hint bar is gone, so a refusal has to reach the player as a toast."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../index.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1440, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("startLevel(250)"); pg.wait_for_timeout(400)
    print("toast hidden at rest:", not pg.locator("#hint").evaluate("e => e.classList.contains('on')"))
    frozen = pg.evaluate("S.seats.findIndex(b => placements(S, b).length === 0)")
    if frozen < 0: print("no boxed-in seat on this board"); br.close(); raise SystemExit
    p = pg.evaluate("""(id => { const b = S.seats[id], box = cv.getBoundingClientRect();
      const [sx, sz] = seatCentre(b); const [px, py] = P(sx, 0, sz);
      return [box.left + px/(cv.width/box.width), box.top + py/(cv.height/box.height)]; })(%d)""" % frozen)
    pg.mouse.move(*p); pg.mouse.down(); pg.mouse.up(); pg.wait_for_timeout(200)
    print("toast shown       :", pg.locator("#hint").evaluate("e => e.classList.contains('on')"))
    print("  text            :", repr(pg.locator("#hint").inner_text()))
    pg.wait_for_timeout(3000)
    print("toast faded after :", not pg.locator("#hint").evaluate("e => e.classList.contains('on')"))
    print("rails visible     :", pg.locator(".rail-l").is_visible(), pg.locator(".rail-r").is_visible(),
          "| topbar hidden:", not pg.locator("#play .topbar").is_visible())
    print("errors:", errs[:3] or "none")
    br.close()
