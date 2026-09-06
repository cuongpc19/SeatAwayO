"""A seat that becomes a walker's destination mid-drag must not land."""
import pathlib
from playwright.sync_api import sync_playwright
url = pathlib.Path("../level_player.html").resolve().as_uri()
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1200, "height": 1400})
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
    pg.goto(url); pg.wait_for_function("typeof ready !== 'undefined' && ready", timeout=20000)
    pg.evaluate("load(129)"); pg.wait_for_timeout(200)
    pg.locator("#board").scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    p = pg.evaluate("""(() => {
      const i = S.seats.findIndex(b => !b.locked && placements(S, b).length);
      const b = S.seats[i], t = placements(S, b)[0];
      const box = cv.getBoundingClientRect(), kx = cv.width/box.width, ky = cv.height/box.height;
      const A = P(cellW(b.c), 0, cellZ(b.r)), B = P(cellW(t[0]), 0, cellZ(t[1]));
      return { i, home: [b.c, b.r], target: t,
               from: [box.left+A[0]/kx, box.top+A[1]/ky],
               to:   [box.left+B[0]/kx, box.top+B[1]/ky] }; })()""")
    pg.mouse.move(*p["from"]); pg.mouse.down()
    pg.mouse.move(p["to"][0], p["to"][1], steps=10)
    # a passenger commits to this seat while it is still in hand
    pg.evaluate("i => S.seats[i].locked = true", p["i"])
    pg.mouse.up(); pg.wait_for_timeout(80)
    now = pg.evaluate("i => [S.seats[i].c, S.seats[i].r]", p["i"])
    print("seat %d %s aimed %s -> landed %s   %s" % (p["i"], p["home"], p["target"], now,
          "HELD PUT (correct)" if now == p["home"] else "MOVED ANYWAY (bug)"))
    print("hint:", repr(pg.evaluate("document.getElementById('hint').textContent")))
    print("errors:", errs[:3] or "none")
    br.close()
